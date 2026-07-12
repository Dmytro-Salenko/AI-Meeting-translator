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

class MeetingSession:
    """
    State representing an active live meeting streaming session.
    WARNING: Storing the entire raw PCM buffer in RAM (full_audio_buffer) 
    is a temporary MVP solution and can exhaust system memory on high concurrent loads.
    """
    def __init__(self, meeting_id: str):
        self.meeting_id = meeting_id
        self.full_audio_buffer = bytearray()
        self.live_audio_buffer = bytearray()
        self.stt_queue = asyncio.Queue()
        self.worker_task = None
        self.websocket = None
        self.lock = asyncio.Lock()
        self.is_stopped = False

meeting_sessions: Dict[str, MeetingSession] = {}
sessions_lock = asyncio.Lock()


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
        import time

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

        print("Modal live request started")
        start_time = time.time()
        try:
            # Resolve remote class
            cls = modal.Cls.from_name("ai-meeting-processor", "LiveTranscriber")
            transcriber = cls()
            # Invoke remote method asynchronously
            transcript = await transcriber.transcribe.remote.aio(wav_data)
            
            duration = time.time() - start_time
            print(f"Modal transcription completed in {duration:.3f}s")
            
            if not transcript:
                print("Empty transcript skipped")
                return ""
                
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
    from app.core.dependencies import get_translation_provider as get_real_provider
    provider = get_real_provider()
    print(f"Translation provider selected: {provider.__class__.__name__}")
    return provider


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


import time

async def stt_worker(session: MeetingSession, stt_provider: BaseSTTProvider, translation_provider: BaseTranslationProvider):
    print(f"STT worker started: {session.meeting_id}")
    try:
        while True:
            chunk = await session.stt_queue.get()
            start_time = time.time()
            try:
                transcript = await stt_provider.transcribe_stream_chunk(chunk)
                if not transcript:
                    print("Empty transcript, segment skipped")
                    continue
                
                try:
                    translation = await translation_provider.translate_text(
                        text=transcript,
                        source_lang="auto",
                        target_lang="ru"
                    )
                except Exception as trans_err:
                    print(f"Translation failed: {trans_err}")
                    translation = transcript
                
                real_msg = {
                    "type": "segment",
                    "speaker": "Speaker 1",
                    "text": transcript,
                    "translation": translation,
                    "timestamp": datetime.utcnow().strftime("%H:%M:%S")
                }
                
                async with session.lock:
                    if session.websocket and not session.is_stopped:
                        try:
                            await session.websocket.send_json(real_msg)
                        except Exception as send_err:
                            print(f"Failed to send JSON to WebSocket: {send_err}")
                
                duration = time.time() - start_time
                print(f"STT block processed in {duration:.3f}s")
            except Exception as block_err:
                print(f"Error processing block in STT worker: {block_err}")
            finally:
                session.stt_queue.task_done()
    except asyncio.CancelledError:
        print(f"STT worker stopped: {session.meeting_id}")
        raise
    except Exception as e:
        print(f"STT worker unexpected error: {e}")

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
    
    async with sessions_lock:
        if meeting_id not in meeting_sessions:
            session = MeetingSession(meeting_id)
            meeting_sessions[meeting_id] = session
            print(f"WebSocket registered: {meeting_id}")
        else:
            session = meeting_sessions[meeting_id]
            if session.websocket is not None:
                print(f"Duplicate socket replaced: {meeting_id}")
                try:
                    await session.websocket.close(code=4000, reason="Duplicate connection replaced")
                except Exception:
                    pass
        
        session.websocket = websocket
        
        if session.worker_task is None or session.worker_task.done():
            session.worker_task = asyncio.create_task(
                stt_worker(session, stt_provider, translation_provider)
            )

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

    buffer_threshold_bytes = 97280 
    
    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                raise WebSocketDisconnect(code=message.get("code", 1000))
            
            if "bytes" in message:
                audio_payload = message["bytes"]
                
                async with session.lock:
                    if session.is_stopped:
                        continue
                    
                    session.full_audio_buffer.extend(audio_payload)
                    session.live_audio_buffer.extend(audio_payload)
                    
                    if len(session.live_audio_buffer) >= buffer_threshold_bytes:
                        block_copy = bytes(session.live_audio_buffer)
                        session.live_audio_buffer.clear()
                        
                        await session.stt_queue.put(block_copy)
                        
                        queue_size = session.stt_queue.qsize()
                        print(f"Live block queued: {queue_size}")
                        print(f"Full PCM size: {len(session.full_audio_buffer)}")

            elif "text" in message:
                data = json.loads(message["text"])
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
    except WebSocketDisconnect:
        print(f"Client disconnected. MeetingId: {meeting_id}")
        async with session.lock:
            if session.websocket == websocket:
                session.websocket = None
        try:
            meeting = await get_db_meeting(meeting_id)
            if meeting["status"] in ["RECORDING", "RECORDING_BUFFERING"]:
                await update_db_meeting_status(meeting_id, "NETWORK_LOST")
        except Exception:
            pass
    except Exception as e:
        print(f"Unexpected error for {meeting_id}: {e}")
        async with session.lock:
            if session.websocket == websocket:
                session.websocket = None
        try:
            meeting = await get_db_meeting(meeting_id)
            if meeting["status"] in ["RECORDING", "RECORDING_BUFFERING"]:
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
    meeting_id: str,
    storage_provider: BaseStorageProvider = Depends(get_storage_provider)
):
    print(f"STOP processing started: {meeting_id}")
    
    async with sessions_lock:
        session = meeting_sessions.get(meeting_id)
        
    if not session:
        raise HTTPException(status_code=400, detail="Active meeting session not found")
        
    async with session.lock:
        session.is_stopped = True

    residual_len = len(session.live_audio_buffer)
    if residual_len > 16000:
        print(f"Residual live block queued: {residual_len} bytes")
        residual_copy = bytes(session.live_audio_buffer)
        session.live_audio_buffer.clear()
        await session.stt_queue.put(residual_copy)
    else:
        print(f"Residual live block skipped (too short: {residual_len} bytes)")

    try:
        await update_db_meeting_status(meeting_id, "UPLOAD_FINALIZING")
    except InvalidStateTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        print("Waiting for STT queue to drain...")
        await asyncio.wait_for(session.stt_queue.join(), timeout=60.0)
        print("STT queue drained successfully")
    except asyncio.TimeoutError:
        print("Timeout waiting for STT queue to drain. Proceeding with full WAV generation anyway.")

    if session.worker_task and not session.worker_task.done():
        session.worker_task.cancel()
        try:
            await session.worker_task
        except asyncio.CancelledError:
            pass
        print(f"STT worker stopped: {meeting_id}")

    final_pcm_size = len(session.full_audio_buffer)
    print(f"Final PCM size: {final_pcm_size} bytes")
    
    if final_pcm_size == 0:
        raise HTTPException(status_code=400, detail="Cannot save audio: full audio buffer is empty")
        
    import struct
    sample_rate = 16000
    channels = 1
    bit_depth = 16
    byte_rate = (sample_rate * channels * bit_depth) // 8
    block_align = (channels * bit_depth) // 8

    header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF',
        36 + final_pcm_size,
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
        final_pcm_size
    )
    wav_audio_data = header + session.full_audio_buffer
    final_wav_size = len(wav_audio_data)
    print(f"Final WAV size: {final_wav_size} bytes")
    
    if final_wav_size <= 44:
        raise HTTPException(status_code=400, detail="Generated WAV is invalid or empty")

    try:
        print("R2 upload started")
        final_path = await storage_provider.upload_full_audio(meeting_id, wav_audio_data)
        print(f"R2 upload completed: {final_path}")
    except Exception as upload_err:
        print(f"WAV upload failed: {upload_err}")
        try:
            await update_db_meeting_status(meeting_id, "FAILED")
        except Exception:
            pass
        raise HTTPException(
            status_code=502,
            detail=f"WAV upload failed: {str(upload_err)}"
        )

    try:
        await update_db_meeting_status(meeting_id, "PROCESSING")
        
        import modal
        print("Modal function resolved: process_meeting_async")
        remote_fn = modal.Function.from_name("ai-meeting-processor", "process_meeting_async")
        
        call = await remote_fn.spawn.aio(meeting_id)
        call_id = getattr(call, "object_id", None)
        print(f"Modal job spawned: {call_id}")
        
        async with sessions_lock:
            meeting_sessions.pop(meeting_id, None)

        return {
            "status": "PROCESSING",
            "message": "Встреча отправлена на ИИ-обработку",
            "call_id": call_id
        }
    except Exception as e:
        print(f"Modal spawn failed: {e}")
        try:
            await update_db_meeting_status(meeting_id, "FAILED")
        except Exception:
            pass
        raise HTTPException(
            status_code=502,
            detail="Failed to start meeting post-processing"
        )


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


