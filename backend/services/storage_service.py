import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError, BotoCoreError

from backend.core.config import settings
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Verification images live under one of two prefixes so a flagged
# customer's photos can be bulk-managed (retained, exported, purged)
# separately from everyone else's, and so a single S3 lifecycle rule can
# target "scans/unflagged/" for routine 7-day expiry without touching
# "scans/flagged/" records, which are kept permanently.
NORMAL_PREFIX = "scans/unflagged/"
BANNED_PREFIX = "scans/flagged/"


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

    def upload_image(self, file_path: str, object_name: str, banned: bool = False) -> str:
        """
        Uploads a file to S3 under scans/flagged/ or scans/unflagged/ and
        returns the full object key (including prefix) — callers must
        persist the returned key, not the original object_name, since
        that's what later get_presigned_url/delete_image/move_to_banned
        calls need.
        """
        prefixed_name = f"{BANNED_PREFIX if banned else NORMAL_PREFIX}{object_name}"

        if not self.client:
            logger.warning("S3 client not configured. Skipping upload.")
            return prefixed_name

        try:
            self.client.upload_file(
                file_path,
                self.bucket_name,
                prefixed_name,
                ExtraArgs={"ContentType": "image/jpeg"},
            )
            logger.info(f"Uploaded {prefixed_name} to S3 bucket {self.bucket_name}.")
            return prefixed_name
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

    def move_to_banned(self, object_name: str) -> str:
        """
        Relocates an object from scans/unflagged/ to scans/flagged/ (S3 has
        no rename, so this is a server-side copy + delete of the original).
        Used when a customer is banned after their images were already
        uploaded under scans/unflagged/ — e.g. a standalone ban against
        someone from a past visit.

        Returns the new scans/flagged/ key, or the original key unchanged
        if the object was already under scans/flagged/, wasn't under
        scans/unflagged/ (unexpected key shape — left alone rather than
        guessed at), or the client isn't configured.
        """
        if not self.client or not object_name:
            return object_name

        if object_name.startswith(BANNED_PREFIX):
            return object_name

        if not object_name.startswith(NORMAL_PREFIX):
            logger.warning(f"Cannot move {object_name} to banned/: unrecognized key prefix.")
            return object_name

        new_name = BANNED_PREFIX + object_name[len(NORMAL_PREFIX):]
        try:
            # Metadata (including ContentType) carries over from the source
            # object automatically since MetadataDirective isn't set to
            # REPLACE — no need to re-specify ContentType here.
            self.client.copy_object(
                Bucket=self.bucket_name,
                CopySource={"Bucket": self.bucket_name, "Key": object_name},
                Key=new_name,
            )
            self.client.delete_object(Bucket=self.bucket_name, Key=object_name)
            logger.info(f"Moved {object_name} to {new_name} (customer banned).")
            return new_name
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Error moving {object_name} to banned/: {e}")
            return object_name


storage_service = StorageService()
