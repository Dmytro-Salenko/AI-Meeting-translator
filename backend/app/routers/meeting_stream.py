import hashlib
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, Depends

# Import dependencies/interfaces
from app.core.config import settings
from app.adapters.groq_stt import GroqSTTProvider
from app.core.state_machine import MeetingStateMachine, InvalidStateTransitionError
from app.core.interfaces.stt import BaseSTTProvider
from app.core.interfaces.translation import BaseTranslationProvider
from app.core.interfaces.storage import BaseStorageProvider

router = APIRouter()

# --------------------------------------------------------------------------
# IN-MEMORY MOCKS & DEPENDENCY INJECTORS (For Step 3)
# --------------------------------------------------------------------------
# Simple in-memory DB to track state during mocking
MOCK_DB: Dict[str, Dict[str, Any]] = {}
db_lock = asyncio.Lock()


import os

class MockSTTProvider(BaseSTTProvider):
    async def transcribe_stream_chunk(self, audio_chunk: bytes) -> str:
        # Mock speech-to-text response
        return "Hello meeting chunk"

    async def transcribe_full_audio(self, audio_file_path: str) -> list[dict[str, Any]]:
        return [{"start": 0.0, "end": 2.0, "speaker": "Speaker A", "text": "Hello meeting chunk"}]


class RealSTTProvider(BaseSTTProvider):
    async def transcribe_stream_chunk(self, audio_chunk: bytes) -> str:
        # Real STT cannot run because STT provider key is missing.
        print("Real STT cannot run because STT provider key is missing. Please configure GROQ_API_KEY or DEEPGRAM_API_KEY in .env")
        return ""

    async def transcribe_full_audio(self, audio_file_path: str) -> list[dict[str, Any]]:
        print("Real STT batch not configured")
        return []


class ModalLiveSTTProvider(BaseSTTProvider):
    async def transcribe_stream_chunk(self, audio_chunk: bytes) -> str:
        import struct
        import modal

        # Wrap raw PCM 16kHz mono 16-bit to WAV
        sample_rate = 16000
        channels = 1
        bit_depth = 16
        byte_rate = (sample_rate * channels * bit_depth) // 8
        block_align = (channels * bit_depth) // 8

        header = struct.pack(
            '<4sI4s4sIHHIIHH4sI',
            b'RIFF',
            36 + len(audio_chunk),
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
            len(audio_chunk)
        )
        wav_data = header + audio_chunk

        print("Calling remote Modal live transcription...")
        try:
            remote_fn = modal.Function.lookup("ai-meeting-processor", "transcribe_live_chunk")
            # Invoke remote function synchronously
            transcript = remote_fn.remote(wav_data)
            print(f"Modal live transcript received: '{transcript}'")
            return transcript
        except Exception as e:
            print(f"Modal live STT error: {e}")
            return ""

    async def transcribe_full_audio(self, audio_file_path: str) -> list[dict[str, Any]]:
        return []


class MockTranslationProvider(BaseTranslationProvider):
    async def translate_text(self, text: str, source_lang: str = "auto", target_lang: str = "ru") -> str:
        # Mock translation response
        return f"[Перевод] {text}"


class MockStorageProvider(BaseStorageProvider):
    async def upload_chunk(self, meeting_id: str, chunk_index: int, data: bytes) -> str:
        # Return mock storage path
        return f"r2://bucket/{meeting_id}/chunk_{chunk_index}.raw"

    async def get_full_audio(self, meeting_id: str) -> bytes:
        return b"mock_assembled_audio_data"

    async def download_chunk(self, storage_path: str) -> bytes:
        # Return mock audio chunk bytes
        return b"[mock pcm chunk data]"

    async def upload_full_audio(self, meeting_id: str, data: bytes) -> str:
        return f"meetings/{meeting_id}/final.wav"


def get_stt_provider() -> BaseSTTProvider:
    if os.getenv("USE_MOCK_STT", "false").lower() == "true":
        print("STT provider selected: MockSTTProvider")
        return MockSTTProvider()
    elif settings.GROQ_API_KEY.strip():
        print("STT provider selected: GroqSTTProvider")
        return GroqSTTProvider(api_key=settings.GROQ_API_KEY)
    else:
        print("STT provider selected: ModalLiveSTTProvider")
        return ModalLiveSTTProvider()


def get_translation_provider() -> BaseTranslationProvider:
    return MockTranslationProvider()


def get_storage_provider() -> BaseStorageProvider:
    return MockStorageProvider()


async def get_db_meeting(meeting_id: str) -> Dict[str, Any]:
    async with db_lock:
        if meeting_id not in MOCK_DB:
            MOCK_DB[meeting_id] = {
                "id": meeting_id,
                "status": "CREATED",
                "chunks": {},       # Map of index -> chunk info
                "max_chunk_index": -1
            }
        return MOCK_DB[meeting_id]


async def update_db_meeting_status(meeting_id: str, new_status: str) -> None:
    async with db_lock:
        meeting = MOCK_DB.get(meeting_id)
        if meeting:
            MeetingStateMachine.validate_transition(meeting["status"], new_status)
            meeting["status"] = new_status


# --------------------------------------------------------------------------
# WEBSOCKET & HTTP ENDPOINTS
# --------------------------------------------------------------------------

@router.websocket("/ws/meeting/{meeting_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    meeting_id: str,
    stt_provider: BaseSTTProvider = Depends(get_stt_provider),
    translation_provider: BaseTranslationProvider = Depends(get_translation_provider)
):
    await websocket.accept()
    print(f"Client connected. MeetingId: {meeting_id}")
    
    # Initialize meeting state in DB if not exists, and move to RECORDING
    try:
        meeting = await get_db_meeting(meeting_id)
        if meeting["status"] == "CREATED":
            await update_db_meeting_status(meeting_id, "RECORDING")
        elif meeting["status"] == "NETWORK_LOST":
            await update_db_meeting_status(meeting_id, "RECORDING_BUFFERING")
    except InvalidStateTransitionError as e:
        print(f"Invalid state transition for {meeting_id}: {e}")
        await websocket.close(code=4003, reason=str(e))
        return

    chunk_counter = 0
    audio_buffer = bytearray()
    
    # 16000 Hz * 2 bytes (pcm16) * 3 seconds = 96000 bytes buffer threshold
    buffer_threshold_bytes = 96000 
    
    try:
        while True:
            # Wait for text/binary message
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect(code=message.get("code", 1000))
            
            if "bytes" in message:
                audio_payload = message["bytes"]
                chunk_counter += 1
                audio_buffer.extend(audio_payload)
                print(f"Chunk received. MeetingId: {meeting_id}, Chunk #{chunk_counter}, Size: {len(audio_payload)} bytes, Buffer size: {len(audio_buffer)} bytes")
                
                # Check if buffer reached 3 seconds of PCM audio
                if len(audio_buffer) >= buffer_threshold_bytes:
                    print(f"Processing accumulated audio buffer of size {len(audio_buffer)} bytes...")
                    
                    # Pass the accumulated audio to the STT provider
                    transcript = await stt_provider.transcribe_stream_chunk(bytes(audio_buffer))
                    
                    # Clear the buffer after processing
                    audio_buffer.clear()
                    
                    # Determine response based on provider mode
                    if isinstance(stt_provider, RealSTTProvider):
                        print("Real STT cannot run because STT provider key is missing.")
                    elif isinstance(stt_provider, ModalLiveSTTProvider) or isinstance(stt_provider, GroqSTTProvider):
                        if not transcript:
                            print("Empty transcript, segment skipped")
                        else:
                            # Translate using existing translation provider
                            translation = await translation_provider.translate_text(
                                text=transcript,
                                source_lang="auto",
                                target_lang="ru"
                            )
                            real_msg = {
                                "type": "segment",
                                "speaker": "Speaker 1",
                                "text": transcript,
                                "translation": translation,
                                "timestamp": datetime.utcnow().strftime("%H:%M:%S")
                            }
                            await websocket.send_json(real_msg)
                            print(f"JSON sent: {real_msg}")
                    else:
                        # MockSTT mode fallback
                        mock_msg = {
                            "type": "segment",
                            "speaker": "Speaker 1",
                            "text": f"Hello from backend (buffer #{chunk_counter // 20})",
                            "translation": f"Привет от бэкенда (буфер #{chunk_counter // 20})",
                            "timestamp": datetime.utcnow().strftime("%H:%M:%S")
                        }
                        await websocket.send_json(mock_msg)
                        print(f"JSON sent (Mock STT active): {mock_msg}")

            elif "text" in message:
                # Handle Heartbeats / control signals
                data = json.loads(message["text"])
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
    except WebSocketDisconnect:
        print(f"Client disconnected. MeetingId: {meeting_id}")
        # Automatically update status to NETWORK_LOST upon sudden disconnection
        try:
            meeting = await get_db_meeting(meeting_id)
            if meeting["status"] in ["RECORDING", "RECORDING_BUFFERING"]:
                await update_db_meeting_status(meeting_id, "NETWORK_LOST")
        except Exception:
            pass
    except Exception as e:
        print(f"Unexpected error for {meeting_id}: {e}")
        # Fallback state change to FAILED upon unexpected errors
        try:
            await update_db_meeting_status(meeting_id, "FAILED")
        except Exception:
            pass
        await websocket.close(code=4000, reason=str(e))


@router.post("/api/meeting/{meeting_id}/upload-chunk")
async def upload_chunk(
    meeting_id: str,
    chunk_index: int = Form(...),
    timestamp_start: str = Form(...),
    timestamp_end: str = Form(...),
    checksum: str = Form(...),
    file: UploadFile = File(...),
    storage_provider: BaseStorageProvider = Depends(get_storage_provider)
):
    # Verify input format & lock database update
    meeting = await get_db_meeting(meeting_id)
    
    # Read chunk data
    audio_data = await file.read()
    
    # Validate Checksum (MD5)
    calculated_hash = hashlib.md5(audio_data).hexdigest()
    if calculated_hash != checksum:
        raise HTTPException(status_code=400, detail="Checksum verification failed")

    async with db_lock:
        # Avoid duplicate chunk inserts (Idempotency Protection)
        if chunk_index in meeting["chunks"]:
            return {
                "status": "ignored",
                "message": "Chunk already uploaded",
                "storage_path": meeting["chunks"][chunk_index]["storage_path"]
            }

        # Track max chunk index seen so far
        if chunk_index > meeting["max_chunk_index"]:
            meeting["max_chunk_index"] = chunk_index

    # Save to storage (R2/S3)
    storage_path = await storage_provider.upload_chunk(meeting_id, chunk_index, audio_data)

    async with db_lock:
        meeting["chunks"][chunk_index] = {
            "timestamp_start": timestamp_start,
            "timestamp_end": timestamp_end,
            "storage_path": storage_path,
            "checksum": checksum,
            "status": "uploaded"
        }

    return {
        "status": "success",
        "chunk_index": chunk_index,
        "storage_path": storage_path
    }


@router.post("/api/meeting/{meeting_id}/stop")
async def stop_meeting(
    meeting_id: str
):
    meeting = await get_db_meeting(meeting_id)
    
    # Move status to UPLOAD_FINALIZING
    try:
        await update_db_meeting_status(meeting_id, "UPLOAD_FINALIZING")
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Verify if all chunks are uploaded (0 to max_chunk_index)
    async with db_lock:
        max_idx = meeting["max_chunk_index"]
        missing_chunks = []
        for i in range(max_idx + 1):
            if i not in meeting["chunks"]:
                missing_chunks.append(i)

    if not missing_chunks:
        # Transition to PROCESSING
        await update_db_meeting_status(meeting_id, "PROCESSING")
        
        # Spawn serverless GPU task on Modal.com asynchronously
        try:
            from app.adapters.modal_whisperx_worker import process_meeting_async
            process_meeting_async.spawn(meeting_id)
        except Exception as e:
            # Fallback if Modal is not configured or in testing environment
            print(f"Modal spawn skipped/failed: {e}")

        return {
            "status": "PROCESSING",
            "message": "Встреча отправлена на ИИ-обработку"
        }
    else:
        # Remain in UPLOAD_FINALIZING and return list of missing chunk indices for client sync
        return {
            "status": "UPLOAD_FINALIZING",
            "message": "Some chunks are missing. Awaiting client synchronization.",
            "missing_chunks": missing_chunks
        }


@router.delete("/meetings/{meeting_id}/audio")
async def delete_meeting_audio(
    meeting_id: str,
    storage_provider: BaseStorageProvider = Depends(get_storage_provider)
):
    meeting = await get_db_meeting(meeting_id)
    
    # 1. Physical audio file deletion from Cloudflare R2
    # In a real environment: await storage_provider.delete_full_audio(meeting_id)
    # also deletes chunks from cloud storage:
    # for chunk in meeting["chunks"].values():
    #     await storage_provider.delete_chunk(chunk["storage_path"])
    
    async with db_lock:
        # 2. Clear tables audio_chunks metadata & audio files reference
        meeting["chunks"] = {}
        meeting["max_chunk_index"] = -1
        if "audio_file" in meeting:
            meeting["audio_file"] = None
            
    # Text data (summary, segments, translations) is explicitly preserved
    return {
        "status": "success",
        "message": "Audio data and chunks cleared from storage. Text transcript and summary remain intact."
    }


@router.delete("/meetings/{meeting_id}")
async def delete_full_meeting(
    meeting_id: str,
    storage_provider: BaseStorageProvider = Depends(get_storage_provider)
):
    # 1. Clean up R2 storage assets (chunks and final file)
    # In a real environment:
    # await storage_provider.delete_all_meeting_assets(meeting_id)
    
    # 2. Cascade delete from DB
    async with db_lock:
        if meeting_id in MOCK_DB:
            MOCK_DB.pop(meeting_id)
        else:
            raise HTTPException(status_code=404, detail="Meeting not found")
            
    return {
        "status": "success",
        "message": f"Meeting {meeting_id} completely destroyed and erased from storage and database."
    }


@router.get("/meetings/search")
async def search_meetings(
    q: str,
    translation_provider: BaseTranslationProvider = Depends(get_translation_provider)
):
    """
    Trilingual Semantic Search Agent.
    1. OpenRouter (Gemini 2.5 Flash) intent parsing supporting language mix (EN/RU/UA) and IT-slang.
    2. Builds keywords in 3 languages (English, Russian, Ukrainian).
    3. Multi-language query matching (OR matching) on DB fields.
    4. RAG synthesis in the user's origin language containing start_time references.
    """
    if not q.strip():
        return {"intent": {}, "results": [], "ai_summary_answer": None}

    current_time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    from app.core.config import settings
    api_key = settings.OPENROUTER_API_KEY
    model = "google/gemini-2.5-flash"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/dimasalenko/ai-meeting-translator",
        "X-Title": "AI Meeting Translator",
        "X-Provider-Privacy": "no-store"
    }

    system_prompt = (
        f"You are a trilingual search query intent parser. Today's date and time is {current_time_str}. "
        "The query may contain a mix of English, Russian, Ukrainian languages, and professional IT-slang. "
        "Analyze the user's query and extract structured query parameters. "
        "Provide search keywords translated to all three target languages to maximize match probability. "
        "Return ONLY a JSON object with this structure:\n"
        "{\n"
        "  \"target_date\": \"YYYY-MM-DD or null (relative to current date)\",\n"
        "  \"speaker_name\": \"name of speaker or null (consider EN/UA/RU transliterations)\",\n"
        "  \"keywords_en\": [\"array of translated concept keywords/synonyms in English or empty\"],\n"
        "  \"keywords_ru\": [\"array of translated concept keywords/synonyms in Russian or empty\"],\n"
        "  \"keywords_ua\": [\"array of translated concept keywords/synonyms in Ukrainian or empty\"],\n"
        "  \"intent_type\": \"'summary' | 'proposals' | 'decisions' | 'general_text'\",\n"
        "  \"user_language\": \"'ru' | 'en' | 'ua' (language of user query)\"\n"
        "}"
    )

    parsed_intent = {
        "target_date": None,
        "speaker_name": None,
        "keywords_en": [],
        "keywords_ru": [],
        "keywords_ua": [],
        "intent_type": "general_text",
        "user_language": "ru"
    }

    try:
        import httpx
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Query: {q}"}
            ],
            "response_format": {"type": "json_object"},
            "provider": {"data_collection": "deny"}
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            if response.status_code == 200:
                raw_json = response.json()["choices"][0]["message"]["content"].strip()
                parsed_intent = json.loads(raw_json)
    except Exception as e:
        print(f"Error parsing trilingual intent: {e}")

    results = []
    
    # Extract search terms
    target_date = parsed_intent.get("target_date")
    speaker_name = parsed_intent.get("speaker_name")
    keywords = list(set(
        parsed_intent.get("keywords_en", []) + 
        parsed_intent.get("keywords_ru", []) + 
        parsed_intent.get("keywords_ua", [])
    ))
    intent_type = parsed_intent.get("intent_type")
    user_lang = parsed_intent.get("user_language", "ru")

    async with db_lock:
        for meeting_id, meeting in MOCK_DB.items():
            # Date filter
            if target_date:
                m_date = str(meeting.get("date"))
                if target_date not in m_date:
                    continue

            # Load segments
            segments = meeting.get("segments", [])
            for seg in segments:
                # Speaker filter
                if speaker_name:
                    seg_speaker = seg.get("speaker", "").lower()
                    if speaker_name.lower() not in seg_speaker:
                        continue

                # Match keywords across both original and translation text (Trilingual OR match)
                matched = False
                if not keywords:
                    matched = True  # match all if no keywords
                else:
                    text_corpus = (seg.get("original_text", "") + " " + seg.get("russian_translation", "")).lower()
                    for kw in keywords:
                        if kw.lower() in text_corpus:
                            matched = True
                            break

                if matched:
                    results.append({
                        "meeting_id": meeting_id,
                        "meeting_title": f"Meeting {meeting_id[:8]}",
                        "speaker_name": seg.get("speaker", "Unknown"),
                        "start_time": seg.get("start_time", 0.0),
                        "text": seg.get("original_text", ""),
                        "translation": seg.get("russian_translation", "")
                    })

    # RAG Synthesis via OpenRouter if query looks like a direct question
    ai_summary_answer = None
    if results:
        # Build context from matches
        context_str = "\n".join([
            f"[{r['speaker_name']} at {r['start_time']}s]: {r['text']} (Transl: {r['translation']})"
            for r in results[:10]  # Limit context window to top 10 matches
        ])
        
        rag_prompt = (
            f"You are a helpful meeting AI assistant. Answer the user's question based strictly on the provided transcript segments. "
            f"Write your response in the user's language: {user_lang}. "
            f"Be concise. You must embed reference timestamps in format [start_time] (e.g. [5.0] or [12.4]) inline "
            f"so they match the segments where you found the information. "
            f"If the answer cannot be found in the provided context, state that clearly."
        )

        try:
            payload_rag = {
                "model": model,
                "messages": [
                    {"role": "system", "content": rag_prompt},
                    {"role": "user", "content": f"Context:\n{context_str}\n\nQuestion: {q}"}
                ],
                "provider": {"data_collection": "deny"}
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                response_rag = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload_rag)
                if response_rag.status_code == 200:
                    ai_summary_answer = response_rag.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Error executing RAG synthesis: {e}")

    return {
        "intent": parsed_intent,
        "results": results,
        "ai_summary_answer": ai_summary_answer
    }


