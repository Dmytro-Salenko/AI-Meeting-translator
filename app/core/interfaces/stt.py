from abc import ABC, abstractmethod
from typing import Any


class BaseSTTProvider(ABC):
    """
    Abstract interface for Speech-To-Text (STT) operations.
    Supports both low-latency stream chunk processing and high-precision batch processing.
    """

    @abstractmethod
    async def transcribe_stream_chunk(self, audio_chunk: bytes) -> str:
        """
        Processes an incoming streaming audio chunk and returns partial/final transcript token.
        Used for real-time translation and display.
        
        Args:
            audio_chunk: Raw binary audio chunk payload.
            
        Returns:
            str: Live transcription text from this chunk.
        """
        pass

    @abstractmethod
    async def transcribe_full_audio(
        self, 
        audio_file_path: str
    ) -> list[dict[str, Any]]:
        """
        Performs high-accuracy post-processing transcription on the fully assembled audio file.
        Must include word-level alignment, diarization (speaker separation), and timestamp segments.
        
        Args:
            audio_file_path: Path/URL to the full assembled audio file.
            
        Returns:
            list[dict]: A list of transcript segments containing:
                - 'start': float (seconds)
                - 'end': float (seconds)
                - 'speaker': str (e.g., 'Speaker A')
                - 'text': str (transcribed content)
        """
        pass
