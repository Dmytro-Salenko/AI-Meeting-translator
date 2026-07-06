import logging
import modal
from app.core.config import settings

logger = logging.getLogger("modal_worker")


class ModalGPUWorkerAdapter:
    """
    Client-side adapter that invokes the remote serverless GPU pipeline 
    running WhisperX on Modal.com.
    """

    def __init__(self):
        self.app_name = "whisperx-app"
        self.function_name = "process_audio"

    async def trigger_diarization(self, meeting_id: str, r2_file_path: str) -> list[dict]:
        """
        Invokes the remote Modal function to perform Speech-To-Text and Speaker Diarization.
        
        Args:
            meeting_id: Unique identifier for the meeting.
            r2_file_path: Storage path to the finalized wav file in Cloudflare R2 bucket.
            
        Returns:
            list[dict]: Array of parsed segments containing timing, text, and speaker tags.
        """
        logger.info(f"Looking up remote Modal function '{self.function_name}' in app '{self.app_name}'...")
        try:
            # Look up the deployed Modal function from server
            remote_fn = modal.Function.lookup(self.app_name, self.function_name)
            
            logger.info(f"Triggering remote Modal execution for meeting {meeting_id} on GPU...")
            # Execute remote function synchronously/asynchronously inside worker thread
            # .remote() blocks until serverless GPU execution completes
            result = remote_fn.remote(meeting_id, r2_file_path)
            
            logger.info(f"Successfully received {len(result)} segments from Modal GPU worker.")
            return result
        except Exception as e:
            logger.error(f"Failed to execute serverless WhisperX GPU job via Modal: {str(e)}")
            raise e
