from typing import Set, Dict


class InvalidStateTransitionError(Exception):
    """Raised when an illegal transition in the Meeting State Machine is attempted."""
    def __init__(self, from_state: str, to_state: str):
        super().__init__(f"Illegal state transition from {from_state} to {to_state}")


class MeetingStateMachine:
    """
    Meeting State Machine to manage and validate the lifecycle of a meeting.
    
    States:
        CREATED: Initial state.
        RECORDING: Live WebSocket streaming active.
        NETWORK_LOST: Connection dropped, client caching chunks locally.
        RECORDING_BUFFERING: WS restored, streaming live + uploading offline buffer via HTTP.
        UPLOAD_FINALIZING: STOP button pressed, client waiting for all chunks to sync.
        PROCESSING: All chunks received, Celery processing (STT, Diarization, LLM).
        READY: Meeting fully processed and available in archive.
        FAILED: Critical failure during recording or processing.
    """
    
    # Map each state to the set of states it can transition to.
    ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
        "CREATED": {"RECORDING", "FAILED"},
        "RECORDING": {"NETWORK_LOST", "UPLOAD_FINALIZING", "FAILED"},
        "NETWORK_LOST": {"RECORDING_BUFFERING", "UPLOAD_FINALIZING", "FAILED"},
        "RECORDING_BUFFERING": {"RECORDING", "NETWORK_LOST", "UPLOAD_FINALIZING", "FAILED"},
        "UPLOAD_FINALIZING": {"PROCESSING", "FAILED"},
        "PROCESSING": {"READY", "FAILED"},
        "READY": {"PROCESSING", "FAILED"},  # Allows re-processing (Selective Reprocessing)
        "FAILED": {"CREATED", "PROCESSING"}  # Allows retrying/re-processing
    }

    @classmethod
    def validate_transition(cls, current_state: str, target_state: str) -> None:
        """
        Validates whether a transition from current_state to target_state is allowed.
        Raises InvalidStateTransitionError if illegal.
        """
        allowed = cls.ALLOWED_TRANSITIONS.get(current_state, set())
        if target_state not in allowed:
            raise InvalidStateTransitionError(current_state, target_state)
