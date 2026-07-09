import httpx
import struct
import logging
from app.core.interfaces.stt import BaseSTTProvider

logger = logging.getLogger("groq_stt")

class GroqSTTProvider(BaseSTTProvider):
    """
    STT Provider implementing real-time stream chunk transcription
    using the high-performance Groq Cloud Whisper API.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.groq.com/openai/v1/audio/transcriptions"

    async def transcribe_stream_chunk(self, audio_chunk: bytes) -> str:
        if not self.api_key:
            logger.error("STT error: Groq API key is empty")
            return ""

        # 1. Convert raw PCM 16kHz mono 16-bit audio into a valid WAV file in memory
        logger.info("Groq STT request started")
        wav_data = self._wrap_pcm_to_wav(audio_chunk)
        logger.info(f"WAV size: {len(wav_data)} bytes")

        # 2. Post wav audio data to Groq Whisper API endpoint
        async with httpx.AsyncClient(timeout=15.0) as client:
            files = {"file": ("audio.wav", wav_data, "audio/wav")}
            data = {"model": "whisper-large-v3", "language": "ru"}
            headers = {"Authorization": f"Bearer {self.api_key}"}

            try:
                response = await client.post(
                    self.api_url,
                    files=files,
                    data=data,
                    headers=headers
                )
                logger.info(f"Groq response status: {response.status_code}")

                if response.status_code == 200:
                    transcript = response.json().get("text", "").strip()
                    logger.info(f"Transcript received: '{transcript}'")
                    return transcript
                else:
                    logger.error(f"STT error: Groq API responded with {response.status_code} - {response.text}")
                    return ""
            except Exception as e:
                logger.error(f"STT error: Failed to connect to Groq: {str(e)}")
                return ""

    async def transcribe_full_audio(self, audio_file_path: str) -> list[dict]:
        logger.info("Batch transcription via Groq is not implemented")
        return []

    def _wrap_pcm_to_wav(self, pcm_data: bytes) -> bytes:
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
