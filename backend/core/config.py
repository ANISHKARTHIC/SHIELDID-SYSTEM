import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "VenuePass Verification System API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "adminpassword"
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: str = "5432"
    POSTGRES_DB: str = "pub_entry_db"
    
    REDIS_URL: str = "redis://redis:6379/0"

    # --- Object storage (S3 / S3-compatible) ---
    # In AWS, leave S3_ENDPOINT_URL unset so boto3 talks to real AWS S3 and
    # picks up credentials from the task/instance IAM role. For local dev
    # against MinIO, set S3_ENDPOINT_URL=http://localhost:9000 plus the
    # MinIO access/secret keys below.
    S3_BUCKET_NAME: str = "verification-images"
    AWS_REGION: str = "us-east-1"
    S3_ENDPOINT_URL: str | None = None
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None
    S3_USE_PATH_STYLE: bool = False  # MinIO requires path-style addressing

    # Standard AWS-named vars — accepted so a plain IAM user access key pair
    # (as opposed to an instance-role deployment) can be dropped straight
    # into .env without renaming to the S3_-prefixed vars above.
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None

    # Legacy MinIO-named vars kept as fallbacks so existing .env files/compose
    # configs keep working without edits.
    MINIO_ENDPOINT: str | None = None
    MINIO_ACCESS_KEY: str | None = None
    MINIO_SECRET_KEY: str | None = None
    MINIO_SECURE: bool = False

    SECRET_KEY: str = "CHANGE_THIS_TO_A_SECURE_RANDOM_STRING"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # URL the backend uses to reach the AI microservice. Defaults to
    # localhost for local dev (matches start_ai_service.sh). docker-compose
    # sets this explicitly to http://ai-service:8001 (the compose network
    # service name) via the backend service's environment block — in AWS
    # behind ECS this should be the internal service-discovery/ALB address
    # (e.g. ECS Cloud Map DNS or an internal load balancer DNS name).
    AI_SERVICE_URL: str = "http://localhost:8001"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        # If DB_ENGINE is set to sqlite or postgres unavailable, allow sqlite
        custom_uri = os.getenv("DATABASE_URL")
        if custom_uri:
            return custom_uri
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def resolved_s3_endpoint_url(self) -> str | None:
        """S3_ENDPOINT_URL wins; otherwise fall back to a legacy MINIO_ENDPOINT."""
        if self.S3_ENDPOINT_URL:
            return self.S3_ENDPOINT_URL
        if self.MINIO_ENDPOINT:
            scheme = "https" if self.MINIO_SECURE else "http"
            return f"{scheme}://{self.MINIO_ENDPOINT}"
        return None

    @property
    def resolved_s3_access_key(self) -> str | None:
        return self.S3_ACCESS_KEY_ID or self.AWS_ACCESS_KEY_ID or self.MINIO_ACCESS_KEY

    @property
    def resolved_s3_secret_key(self) -> str | None:
        return self.S3_SECRET_ACCESS_KEY or self.AWS_SECRET_ACCESS_KEY or self.MINIO_SECRET_KEY

    @property
    def resolved_s3_path_style(self) -> bool:
        # MinIO (or any endpoint override) needs path-style addressing;
        # real AWS S3 uses virtual-hosted style.
        return self.S3_USE_PATH_STYLE or self.resolved_s3_endpoint_url is not None

    # Resolved relative to this file (backend/core/config.py -> backend/.env)
    # rather than the process's cwd, so `.env` loads correctly whether the
    # app is launched from the repo root, from backend/, or via Docker.
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        extra="ignore",
    )

settings = Settings()
