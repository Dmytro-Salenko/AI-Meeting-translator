-- SQL Migration DDL for AI Meeting Translator (Supabase/PostgreSQL)

-- =========================================================================
-- 1. ENUMS & CUSTOM TYPES
-- =========================================================================

-- Meeting Lifecycle States
CREATE TYPE meeting_status AS ENUM (
    'CREATED',
    'RECORDING',
    'NETWORK_LOST',
    'RECORDING_BUFFERING',
    'UPLOAD_FINALIZING',
    'PROCESSING',
    'READY',
    'FAILED'
);

-- Chunk Upload Statuses
CREATE TYPE chunk_upload_status AS ENUM (
    'pending',
    'uploaded',
    'failed'
);

-- Training Types (Required by prompt constraints)
CREATE TYPE workout_type AS ENUM (
    'Lifting',
    'Cardio',
    'Other',
    'None'
);

-- Lab Case Study Statuses (Required by prompt constraints)
CREATE TYPE lab_case_status AS ENUM (
    'PENDING',
    'IN_PROGRESS',
    'COMPLETED',
    'ARCHIVED'
);

-- =========================================================================
-- 2. TABLES
-- =========================================================================

-- Profiles / Users (Supabase Auth reference)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Meetings
CREATE TABLE IF NOT EXISTS meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    start_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    duration INTEGER, -- total duration in seconds
    status meeting_status NOT NULL DEFAULT 'CREATED',
    
    -- Versioning of AI models for Selective Reprocessing
    stt_version TEXT NOT NULL DEFAULT 'v1.0',
    translation_version TEXT NOT NULL DEFAULT 'v1.0',
    summary_version TEXT NOT NULL DEFAULT 'v1.0',
    diarization_version TEXT NOT NULL DEFAULT 'v1.0',
    processing_version TEXT NOT NULL DEFAULT 'v1.0',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Profiles (Biometric Voice Fingerprints & Names)
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    voice_fingerprint TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Speakers (Meeting-specific override or participants tracker)
CREATE TABLE IF NOT EXISTS speakers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    user_assigned_name TEXT NOT NULL,
    voiceprint_metadata JSONB, -- Voice embeddings / prints
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Meeting Segments (Transcript text and translation blocks)
CREATE TABLE IF NOT EXISTS meeting_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    speaker_id UUID REFERENCES profiles(id) ON DELETE SET NULL, -- Links segment to biometric profile
    speaker_label TEXT, -- Technical label (e.g. Speaker A)
    
    -- Timings in seconds from meeting start (Numeric supports milliseconds precision)
    start_time NUMERIC(8, 3) NOT NULL,
    end_time NUMERIC(8, 3) NOT NULL,
    
    original_text TEXT NOT NULL,
    russian_translation TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Audio Chunks (Reliability buffer)
CREATE TABLE IF NOT EXISTS audio_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    timestamp_start TIMESTAMPTZ NOT NULL,
    timestamp_end TIMESTAMPTZ NOT NULL,
    upload_status chunk_upload_status NOT NULL DEFAULT 'pending',
    storage_path TEXT,
    checksum TEXT, -- Checksum to validate payload integrity
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Composite unique key to protect against duplicate uploads
    CONSTRAINT unique_meeting_chunk UNIQUE (meeting_id, chunk_index)
);

-- Audio Files (Full finalized audio files in cloud storage)
CREATE TABLE IF NOT EXISTS audio_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    r2_bucket_path TEXT NOT NULL,
    duration_seconds NUMERIC(8, 2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Summaries (AI-generated meeting summaries)
CREATE TABLE IF NOT EXISTS summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    brief_content TEXT NOT NULL,
    key_decisions TEXT[] NOT NULL DEFAULT '{}',
    action_items JSONB NOT NULL DEFAULT '{}', -- Format: {"Name": "Task description"}
    open_questions TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================================================================
-- 3. INDEXES & SEARCH OPTIMIZATION
-- =========================================================================

-- FTS Index for original foreign text (English default/simple)
CREATE INDEX IF NOT EXISTS idx_segments_original_text_fts 
ON meeting_segments 
USING GIN (to_tsvector('english', original_text));

-- FTS Index for Russian translation text (Russian configuration)
CREATE INDEX IF NOT EXISTS idx_segments_russian_translation_fts 
ON meeting_segments 
USING GIN (to_tsvector('russian', russian_translation));

-- Foreign Key & Join optimization indexes
CREATE INDEX IF NOT EXISTS idx_meetings_user_id ON meetings(user_id);
CREATE INDEX IF NOT EXISTS idx_speakers_meeting_id ON speakers(meeting_id);
CREATE INDEX IF NOT EXISTS idx_segments_meeting_id ON meeting_segments(meeting_id);
CREATE INDEX IF NOT EXISTS idx_segments_speaker_id ON meeting_segments(speaker_id);
CREATE INDEX IF NOT EXISTS idx_audio_chunks_meeting_status ON audio_chunks(meeting_id, upload_status);
CREATE INDEX IF NOT EXISTS idx_summaries_meeting_id ON summaries(meeting_id);

-- =========================================================================
-- 4. TRIGGERS & UTILITY FUNCTIONS
-- =========================================================================

-- Auto-update updated_at helper
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_meetings_updated_at
BEFORE UPDATE ON meetings
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
