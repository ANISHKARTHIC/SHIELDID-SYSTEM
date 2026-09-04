import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from backend.api.deps import get_db, get_current_active_user, RoleChecker
from backend.models.models import AppRelease, RoleEnum, User
from backend.services.storage_service import storage_service
from backend.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/releases", tags=["releases"])
require_super_admin = RoleChecker([RoleEnum.super_admin])

# Same S3 bucket/client as verification images (storage_service.py), under
# its own prefix — release APKs aren't PII and don't go through the
# flagged/unflagged retention split, they just need their own namespace so
# they're never touched by the scans/ lifecycle rules or retention cron.
RELEASE_PREFIX = "app_releases/"


@router.get("/latest")
def get_latest_release(db: Session = Depends(get_db)):
    """
    Public: the currently published app version + a short-lived presigned
    download URL for its APK. Used by the app's Connection settings screen
    ("Check for Update"), and safe to call unauthenticated — before login
    is exactly when a stale app most needs to find out it's out of date.
    """
    release = db.query(AppRelease).filter(AppRelease.is_latest.is_(True)).first()
    if not release:
        return {"latest_version": None, "update_url": None, "release_notes": None}

    download_url = storage_service.get_presigned_url(release.s3_key, expiry_hours=1) if release.s3_key else ""
    return {
        "latest_version": release.version,
        "update_url": download_url,
        "release_notes": release.release_notes,
        "size_bytes": release.size_bytes,
    }


@router.get("")
def list_releases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _admin: None = Depends(require_super_admin),
):
    """Admin: full release history, newest first."""
    releases = db.query(AppRelease).order_by(AppRelease.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "version": r.version,
            "size_bytes": r.size_bytes,
            "release_notes": r.release_notes,
            "is_latest": r.is_latest,
            "created_at": r.created_at,
        }
        for r in releases
    ]


@router.post("")
async def publish_release(
    version: str = Form(...),
    release_notes: str = Form(""),
    apk: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _admin: None = Depends(require_super_admin),
):
    """
    Admin: uploads a new APK build to S3 and records it as the latest
    version. The previous latest row is kept (not deleted) so its APK
    stays downloadable — only the is_latest flag moves.
    """
    existing = db.query(AppRelease).filter(AppRelease.version == version).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Version {version} already published.")

    if not apk.filename.lower().endswith(".apk"):
        raise HTTPException(status_code=400, detail="File must be a .apk")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".apk") as tmp:
        tmp_path = tmp.name
        size = 0
        while chunk := await apk.read(1024 * 1024):
            tmp.write(chunk)
            size += len(chunk)

    try:
        object_name = f"venuepass-{version}.apk"
        s3_key = storage_service.upload_apk(tmp_path, RELEASE_PREFIX + object_name)
        if not s3_key:
            raise HTTPException(status_code=502, detail="Failed to upload APK to storage.")

        db.query(AppRelease).filter(AppRelease.is_latest.is_(True)).update({"is_latest": False})
        release = AppRelease(
            version=version,
            s3_key=s3_key,
            size_bytes=size,
            release_notes=release_notes or None,
            is_latest=True,
        )
        db.add(release)
        db.commit()
        db.refresh(release)
        logger.info(f"Published app release {version} ({size} bytes) by user {current_user.id}.")
        return {
            "id": release.id,
            "version": release.version,
            "size_bytes": release.size_bytes,
            "is_latest": release.is_latest,
        }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
