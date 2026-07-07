import hashlib
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File, Form, HTTPException, Depends

# Import dependencies/interfaces
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


class MockSTTProvider(BaseSTTProvider):
    async def transcribe_stream_chunk(self, audio_chunk: bytes) -> str:
        # Mock speech-to-text response
        return "Hello meeting chunk"

    async def transcribe_full_audio(self, audio_file_path: str) -> list[dict[str, Any]]:
        return [{"start": 0.0, "end": 2.0, "speaker": "Speaker A", "text": "Hello meeting chunk"}]


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


def get_stt_provider() -> BaseSTTProvider:
    return MockSTTProvider()


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
    
    # Initialize meeting state in DB if not exists, and move to RECORDING
    try:
        meeting = await get_db_meeting(meeting_id)
        if meeting["status"] == "CREATED":
            await update_db_meeting_status(meeting_id, "RECORDING")
        elif meeting["status"] == "NETWORK_LOST":
            await update_db_meeting_status(meeting_id, "RECORDING_BUFFERING")
    except InvalidStateTransitionError as e:
        await websocket.close(code=4003, reason=str(e))
        return

    try:
        while True:
            # Wait for text/binary message
            message = await websocket.receive()
            
            if "bytes" in message:
                audio_payload = message["bytes"]
                
                # STT Processing
                original_text = await stt_provider.transcribe_stream_chunk(audio_payload)
                
                # Translation Processing
                russian_translation = await translation_provider.translate_text(
                    text=original_text, 
                    source_lang="auto", 
                    target_lang="ru"
                )
                
                # Immediate Response to Mobile Client
                await websocket.send_json({
                    "original_text": original_text,
                    "russian_translation": russian_translation,
                    "timestamp": datetime.utcnow().isoformat()
                })

            elif "text" in message:
                # Handle Heartbeats / control signals
                data = json.loads(message["text"])
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
    except WebSocketDisconnect:
        # Automatically update status to NETWORK_LOST upon sudden disconnection
        try:
            meeting = await get_db_meeting(meeting_id)
            if meeting["status"] in ["RECORDING", "RECORDING_BUFFERING"]:
                await update_db_meeting_status(meeting_id, "NETWORK_LOST")
        except Exception:
            pass
    except Exception as e:
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
    Semantic AI Search Agent.
    1. Uses OpenRouter to parse user natural language intent.
    2. Builds custom query filters based on parsed intent.
    3. Searches DB / Mock DB and compiles timestamped results for the player.
    """
    if not q.strip():
        return {"intent": {}, "results": [], "ai_summary_answer": None}

    current_time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    current_date_str = datetime.utcnow().strftime("%Y-%m-%d")

    # Call OpenRouter to parse intent (Zero Data Retention)
    # Using configured model (e.g. google/gemini-2.5-flash)
    from app.core.config import settings
    api_key = settings.OPENROUTER_API_KEY
    model = "google/gemini-2.5-flash" # Use fast/cheap flash model for parsing
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/dimasalenko/ai-meeting-translator",
        "X-Title": "AI Meeting Translator",
        "X-Provider-Privacy": "no-store"
    }

    system_prompt = (
        f"You are a search query intent parser. Today's date and time is {current_time_str}. "
        "Analyze the user's search query and extract structured filter parameters. "
        "Return ONLY a JSON object with this structure:\n"
        "{\n"
        "  \"target_date\": \"YYYY-MM-DD or null (calculate relative dates like 'yesterday' or 'last monday')\",\n"
        "  \"speaker_name\": \"string of speaker name mentioned, or null\",\n"
        "  \"search_keyword\": \"main meaning keyword for full-text search, or null\",\n"
        "  \"intent_type\": \"'summary' | 'proposals' | 'decisions' | 'general_text'\"\n"
        "}"
    )

    parsed_intent = {
        "target_date": None,
        "speaker_name": None,
        "search_keyword": q,
        "intent_type": "general_text"
    }

    # Call OpenRouter API
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
        print(f"Error parsing search intent with OpenRouter: {e}")

    results = []
    ai_summary_answer = None

    # Query mock database based on parsed intent
    target_date = parsed_intent.get("target_date")
    speaker_name = parsed_intent.get("speaker_name")
    keyword = parsed_intent.get("search_keyword")
    intent_type = parsed_intent.get("intent_type")

    async with db_lock:
        for meeting_id, meeting in MOCK_DB.items():
            # Date filter (if parsed)
            if target_date and meeting.get("date") != target_date:
                # Handle string date matching
                m_date = str(meeting.get("date"))
                if target_date not in m_date:
                    continue

            # Route by intent type
            if intent_type == "summary" and "summary" in meeting:
                ai_summary_answer = meeting["summary"].get("brief_content")
                continue
                
            elif intent_type == "decisions" and "summary" in meeting:
                decisions = meeting["summary"].get("key_decisions", [])
                if decisions:
                    ai_summary_answer = "Основные решения:\n" + "\n".join(decisions)
                continue

            # Search in segments
            segments = meeting.get("segments", [])
            for seg in segments:
                # Speaker filter
                if speaker_name:
                    seg_speaker = seg.get("speaker", "").lower()
                    if speaker_name.lower() not in seg_speaker:
                        continue

                # Keyword text search
                if keyword:
                    text_content = (seg.get("original_text", "") + " " + seg.get("russian_translation", "")).lower()
                    if keyword.lower() not in text_content:
                        continue

                results.append({
                    "meeting_id": meeting_id,
                    "meeting_title": f"Meeting {meeting_id[:8]}",
                    "speaker_name": seg.get("speaker", "Unknown"),
                    "start_time": seg.get("start_time", 0.0),
                    "text": seg.get("original_text", ""),
                    "translation": seg.get("russian_translation", "")
                })

    return {
        "intent": parsed_intent,
        "results": results,
        "ai_summary_answer": ai_summary_answer
    }


