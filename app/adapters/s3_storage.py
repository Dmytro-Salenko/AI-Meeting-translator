import aioboto3
from app.core.config import settings
from app.core.interfaces.storage import BaseStorageProvider


class S3StorageProvider(BaseStorageProvider):
    """
    Implementation of BaseStorageProvider for Cloudflare R2 / AWS S3 using aioboto3.
    """

    def __init__(self):
        self.session = aioboto3.Session()
        self.bucket_name = settings.R2_BUCKET_NAME
        self.client_kwargs = {
            "aws_access_key_id": settings.R2_ACCESS_KEY_ID,
            "aws_secret_access_key": settings.R2_SECRET_ACCESS_KEY,
            "endpoint_url": settings.R2_ENDPOINT_URL,
        }

    async def upload_chunk(
        self, 
        meeting_id: str, 
        chunk_index: int, 
        data: bytes
    ) -> str:
        key = f"meetings/{meeting_id}/chunks/{chunk_index}.raw"
        async with self.session.client("s3", **self.client_kwargs) as s3:
            await s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType="audio/octet-stream"
            )
        return key

    async def get_full_audio(self, meeting_id: str) -> bytes:
        key = f"meetings/{meeting_id}/final.wav"
        async with self.session.client("s3", **self.client_kwargs) as s3:
            response = await s3.get_object(Bucket=self.bucket_name, Key=key)
            async with response["Body"] as stream:
                return await stream.read()

    async def upload_full_audio(self, meeting_id: str, data: bytes) -> str:
        """Helper to upload assembled final master audio."""
        key = f"meetings/{meeting_id}/final.wav"
        async with self.session.client("s3", **self.client_kwargs) as s3:
            await s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                ContentType="audio/wav"
            )
        return key
