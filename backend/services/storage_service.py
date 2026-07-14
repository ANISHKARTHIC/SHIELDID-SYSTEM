import os
from minio import Minio
from datetime import timedelta
from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)

class StorageService:
    def __init__(self):
        try:
            self.client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
            self.bucket_name = "verification-images"
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
            logger.info("MinIO storage service initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize MinIO: {e}")
            self.client = None

    def upload_image(self, file_path: str, object_name: str) -> str:
        """Uploads a file to MinIO and returns the object name/path"""
        if not self.client:
            logger.warning("MinIO client not configured. Skipping upload.")
            return object_name
            
        try:
            self.client.fput_object(
                self.bucket_name,
                object_name,
                file_path,
                content_type="image/jpeg"
            )
            logger.info(f"Uploaded {object_name} to MinIO bucket {self.bucket_name}.")
            return object_name
        except Exception as e:
            logger.error(f"Error uploading to MinIO: {e}")
            return None

    def get_presigned_url(self, object_name: str, expiry_hours: int = 24) -> str:
        """Returns a temporary URL to view the image."""
        if not self.client:
            return ""
            
        try:
            url = self.client.get_presigned_url(
                "GET",
                self.bucket_name,
                object_name,
                expires=timedelta(hours=expiry_hours)
            )
            return url
        except Exception as e:
            logger.error(f"Error getting presigned URL from MinIO: {e}")
            return ""

    def delete_image(self, object_name: str):
        """Deletes an image from MinIO."""
        if not self.client:
            return
            
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"Deleted {object_name} from MinIO.")
        except Exception as e:
            logger.error(f"Error deleting from MinIO: {e}")

storage_service = StorageService()
