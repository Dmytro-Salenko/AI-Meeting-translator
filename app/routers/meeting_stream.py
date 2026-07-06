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
        # Transition to PROCESSING and trigger Celery task (mocked here)
        await update_db_meeting_status(meeting_id, "PROCESSING")
        # trigger_background_celery_task(meeting_id)
        return {
            "status": "PROCESSING",
            "message": "All chunks received. Server-side post-processing pipeline initiated."
        }
    else:
        # Remain in UPLOAD_FINALIZING and return list of missing chunk indices for client sync
        return {
            "status": "UPLOAD_FINALIZING",
            "message": "Some chunks are missing. Awaiting client synchronization.",
            "missing_chunks": missing_chunks
        }
