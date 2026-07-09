import struct
import asyncio
import logging
from typing import List, Dict, Any
from app.core.state_machine import MeetingStateMachine
from app.core.dependencies import get_storage_provider, get_summary_provider, get_translation_provider
from app.adapters.modal_worker import ModalGPUWorkerAdapter
from app.routers.meeting_stream import get_db_meeting, update_db_meeting_status, MOCK_DB

logger = logging.getLogger("meeting_tasks")

def _wrap_pcm_to_wav(pcm_data: bytes) -> bytes:
    """
    Wraps raw PCM audio bytes with a standard 44-byte WAV RIFF header.
    Configuration: 16000Hz sample rate, 16-bit depth, mono channel.
    """
    sample_rate = 16000
    channels = 1
    bit_depth = 16
    byte_rate = (sample_rate * channels * bit_depth) // 8
    block_align = (channels * bit_depth) // 8

    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + len(pcm_data),
        b'WAVE',
        b'fmt ',
        16,
        1,            # Audio format (1 = PCM)
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bit_depth,
        b'data',
        len(pcm_data)
    )
    return header + pcm_data


async def process_full_meeting_async(meeting_id: str):
    """
    Core async pipeline for processing the full meeting.
    Combines audio chunk assembly, WhisperX GPU diarization on Modal,
    segment translations, and summary generation.
    """
    storage_provider = get_storage_provider()
    summary_provider = get_summary_provider()
    translation_provider = get_translation_provider()
    modal_worker = ModalGPUWorkerAdapter()

    try:
        # 1. Update status to PROCESSING
        logger.info(f"Starting processing pipeline for meeting {meeting_id}")
        await update_db_meeting_status(meeting_id, "PROCESSING")

        # 2. Get meeting and download/assemble all chunks
        meeting = await get_db_meeting(meeting_id)
        chunks = meeting.get("chunks", {})
        sorted_indices = sorted(chunks.keys())

        if not sorted_indices:
            raise Exception("No audio chunks found for this meeting.")

        logger.info(f"Downloading {len(sorted_indices)} chunks for concatenation...")
        assembled_audio = b""
        chunk_paths = []
        for idx in sorted_indices:
            path = chunks[idx]["storage_path"]
            chunk_paths.append(path)
            
            # Download the real chunk bytes from R2 / Storage Provider
            chunk_bytes = await storage_provider.download_chunk(path)
            logger.info(f"Downloaded chunk #{idx} from path '{path}', Size: {len(chunk_bytes)} bytes")
            assembled_audio += chunk_bytes

        logger.info(f"Successfully concatenated {len(sorted_indices)} chunks. Total assembled audio size: {len(assembled_audio)} bytes")

        # Assemble full audio and upload to Cloudflare R2 / Object Storage
        wav_audio_data = _wrap_pcm_to_wav(assembled_audio)
        final_path = await storage_provider.upload_full_audio(meeting_id, wav_audio_data)
        logger.info(f"Final audio WAV assembled (WAV size: {len(wav_audio_data)} bytes) and uploaded to storage path: '{final_path}'")

        # 3. Perform WhisperX Speech-to-Text & Diarization on Serverless GPU
        logger.info("Triggering remote GPU serverless diarization...")
        # Runs WhisperX + PyAnnote on Modal.com
        segments = await modal_worker.trigger_diarization(meeting_id, final_path)

        # 4. Translate segments and compile full transcript
        full_transcript_parts = []
        db_segments = []

        for idx, seg in enumerate(segments):
            original = seg["text"]
            speaker = seg["speaker_id"]
            start = seg["start"]
            end = seg["end"]

            # Translate segment using translation provider
            translation = await translation_provider.translate_text(
                text=original, 
                source_lang="auto", 
                target_lang="ru"
            )
            
            # Format segment representation for LLM Summary
            full_transcript_parts.append(f"{speaker} ({start}-{end}): {original}")
            
            db_segments.append({
                "id": f"segment_{idx}",
                "speaker": speaker,
                "start_time": start,
                "end_time": end,
                "original_text": original,
                "russian_translation": translation
            })

        full_transcript = "\n".join(full_transcript_parts)

        # 5. Generate AI Summary using LLM Provider
        logger.info("Generating AI Summary...")
        summary = await summary_provider.generate_summary(full_transcript)

        # 6. Save results to Database (MOCKED Postgres / Supabase writes)
        logger.info("Writing all outputs to Supabase/PostgreSQL databases...")
        meeting["segments"] = db_segments
        meeting["summary"] = summary.model_dump()
        meeting["audio_file"] = {
            "r2_path": final_path,
            "duration": segments[-1]["end_time"] if segments else 0.0
        }

        # 7. Finalize status to READY
        await update_db_meeting_status(meeting_id, "READY")
        logger.info(f"Meeting {meeting_id} is READY!")

    except Exception as e:
        logger.error(f"Failed to process meeting {meeting_id}: {str(e)}")
        try:
            await update_db_meeting_status(meeting_id, "FAILED")
        except Exception:
            pass
        raise e


# Celery task entrypoint
# @celery_app.task(name="tasks.process_full_meeting_task")
def process_full_meeting_task(meeting_id: str):
    """
    Celery task wrapper that runs the async processing pipeline inside an event loop.
    """
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(process_full_meeting_async(meeting_id))
    else:
        loop.run_until_complete(process_full_meeting_async(meeting_id))
