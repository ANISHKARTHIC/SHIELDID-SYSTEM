import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError, BotoCoreError

from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)


class StorageService:
    """
    Thin wrapper around boto3's S3 client.

    Works unmodified against real AWS S3 (credentials come from the
    environment / instance / ECS task IAM role — nothing to configure) or
    against any S3-compatible endpoint such as MinIO for local development
    by setting S3_ENDPOINT_URL.
    """

    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.client = None
        try:
            client_kwargs = {
                "region_name": settings.AWS_REGION,
                "config": BotoConfig(
                    signature_version="s3v4",
                    s3={"addressing_style": "path" if settings.resolved_s3_path_style else "auto"},
                ),
            }

            endpoint_url = settings.resolved_s3_endpoint_url
            if endpoint_url:
                client_kwargs["endpoint_url"] = endpoint_url

            # Only pass explicit credentials for local/MinIO use. In AWS,
            # omit them so boto3 falls back to its default credential chain
            # (env vars, ECS task role, EC2 instance profile, etc).
            access_key = settings.resolved_s3_access_key
            secret_key = settings.resolved_s3_secret_key
            if access_key and secret_key:
                client_kwargs["aws_access_key_id"] = access_key
                client_kwargs["aws_secret_access_key"] = secret_key

            self.client = boto3.client("s3", **client_kwargs)
            self._ensure_bucket()
            logger.info(
                f"S3 storage service initialized "
                f"(bucket={self.bucket_name}, endpoint={endpoint_url or 'aws'})."
            )
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {e}")
            self.client = None

    def _ensure_bucket(self):
        """Create the bucket if it doesn't exist yet (mainly useful for local MinIO)."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError:
            try:
                if settings.AWS_REGION == "us-east-1":
                    self.client.create_bucket(Bucket=self.bucket_name)
                else:
                    self.client.create_bucket(
                        Bucket=self.bucket_name,
                        CreateBucketConfiguration={"LocationConstraint": settings.AWS_REGION},
                    )
                logger.info(f"Created bucket {self.bucket_name}.")
            except ClientError as ce:
                # In AWS, the deployed IAM role often intentionally lacks
                # CreateBucket permission (bucket is provisioned via IaC).
                # Don't fail startup over that — just log it.
                logger.warning(f"Could not create/verify bucket {self.bucket_name}: {ce}")

    def upload_image(self, file_path: str, object_name: str) -> str:
        """Uploads a file to S3 and returns the object key."""
        if not self.client:
            logger.warning("S3 client not configured. Skipping upload.")
            return object_name

        try:
            self.client.upload_file(
                file_path,
                self.bucket_name,
                object_name,
                ExtraArgs={"ContentType": "image/jpeg"},
            )
            logger.info(f"Uploaded {object_name} to S3 bucket {self.bucket_name}.")
            return object_name
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error uploading to S3: {e}")
            return None

    def get_presigned_url(self, object_name: str, expiry_hours: int = 24) -> str:
        """Returns a temporary URL to view the image."""
        if not self.client:
            return ""

        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": object_name},
                ExpiresIn=expiry_hours * 3600,
            )
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error getting presigned URL from S3: {e}")
            return ""

    def delete_image(self, object_name: str):
        """Deletes an image from S3."""
        if not self.client:
            return

        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=object_name)
            logger.info(f"Deleted {object_name} from S3.")
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error deleting from S3: {e}")


storage_service = StorageService()
