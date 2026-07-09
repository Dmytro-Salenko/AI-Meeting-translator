from abc import ABC, abstractmethod


class BaseStorageProvider(ABC):
    """
    Abstract interface for managing object storage operations.
    Handles ephemeral audio chunk storage and finalized audio assets.
    """

    @abstractmethod
    async def upload_chunk(
        self, 
        meeting_id: str, 
        chunk_index: int, 
        data: bytes
    ) -> str:
        """
        Uploads an atomic audio chunk to the storage bucket.
        
        Args:
            meeting_id: The unique identifier of the meeting.
            chunk_index: Index of the current chunk in sequence.
            data: Raw binary payload of the audio chunk.
            
        Returns:
            str: The public/internal path or URL of the stored chunk.
        """
        pass

    @abstractmethod
    async def get_full_audio(self, meeting_id: str) -> bytes:
        """
        Retrieves the complete finalized audio file or assembled audio bytes for a meeting.
        
        Args:
            meeting_id: The unique identifier of the meeting.
            
        Returns:
            bytes: The full audio file binary data.
        """
        pass

    @abstractmethod
    async def download_chunk(self, storage_path: str) -> bytes:
        """
        Downloads a single audio chunk from the storage bucket.
        """
        pass

    @abstractmethod
    async def upload_full_audio(self, meeting_id: str, data: bytes) -> str:
        """
        Uploads the fully assembled meeting master audio file.
        """
        pass
