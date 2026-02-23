import os
import logging
from pathlib import Path
import aioboto3
from typing import Optional

from config import get_settings

logger = logging.getLogger(__name__)

class S3Manager:
    def __init__(self):
        self.settings = get_settings()
        self.session = aioboto3.Session()

    def _get_client_kwargs(self):
        """Helper to conditionally inject credentials only if configured"""
        kwargs = {
            "region_name": self.settings.AWS_REGION
        }
        if self.settings.AWS_ACCESS_KEY_ID and self.settings.AWS_SECRET_ACCESS_KEY:
            kwargs["aws_access_key_id"] = self.settings.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = self.settings.AWS_SECRET_ACCESS_KEY
        return kwargs

    async def upload_pdf_to_s3(self, file_bytes: bytes, s3_key: str) -> str:
        """Upload a file to S3 and return the object key."""
        if not self.settings.AWS_S3_BUCKET_NAME:
            raise ValueError("AWS_S3_BUCKET_NAME environment variable is not configured.")

        logger.info(f"Uploading file to S3 bucket {self.settings.AWS_S3_BUCKET_NAME} with key {s3_key}")
        
        async with self.session.client('s3', **self._get_client_kwargs()) as s3:
            await s3.put_object(
                Bucket=self.settings.AWS_S3_BUCKET_NAME,
                Key=s3_key,
                Body=file_bytes,
                ContentType='application/pdf'
            )
        logger.info(f"Successfully uploaded {s3_key} to S3")
        return s3_key

    async def download_pdf_from_s3(self, s3_key: str, local_path: str) -> str:
        """Download a file from S3 to a local path (usually /tmp)."""
        if not self.settings.AWS_S3_BUCKET_NAME:
            raise ValueError("AWS_S3_BUCKET_NAME environment variable is not configured.")

        logger.info(f"Downloading {s3_key} from S3 to {local_path}")
        
        # Ensure target directory exists
        Path(local_path).parent.mkdir(parents=True, exist_ok=True)
        
        async with self.session.client('s3', **self._get_client_kwargs()) as s3:
            response = await s3.get_object(
                Bucket=self.settings.AWS_S3_BUCKET_NAME,
                Key=s3_key
            )
            # aioboto3 streaming read
            async with response['Body'] as stream:
                body_data = await stream.read()
                
            with open(local_path, 'wb') as f:
                f.write(body_data)
                
        logger.info(f"Successfully downloaded {s3_key}")
        return local_path

    async def delete_pdf_from_s3(self, s3_key: str) -> None:
        """Delete a file from S3."""
        if not self.settings.AWS_S3_BUCKET_NAME:
            logger.warning("S3 not configured; skipping deletion.")
            return

        logger.info(f"Deleting {s3_key} from S3")
        
        async with self.session.client('s3', **self._get_client_kwargs()) as s3:
            await s3.delete_object(
                Bucket=self.settings.AWS_S3_BUCKET_NAME,
                Key=s3_key
            )
        logger.info(f"Successfully deleted {s3_key}")

# Singleton instance
s3_manager = S3Manager()
