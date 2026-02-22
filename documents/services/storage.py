"""
MinIO object-storage service layer.

All public methods are static so callers never need to instantiate the class.
The MinIO client and bucket name are read from Django settings at call time,
so they always reflect the live configuration even during tests that swap them.
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional
import uuid

from minio import S3Error
from django.conf import settings

logger = logging.getLogger(__name__)


class MinIOService:
    """Thin, stateless wrapper around the MinIO SDK for document storage."""

    # ──────────────────────────────────────────────────────────────────────────
    # Bucket helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def ensure_bucket_exists() -> None:
        """
        Idempotently ensure the configured bucket exists.

        Creates the bucket when it is missing. Safe to call before every
        operation — the SDK returns immediately if the bucket is already there.

        Raises:
            S3Error: If the bucket cannot be created or its existence cannot
                     be confirmed (e.g. permission denied, network error).
        """
        bucket = settings.MINIO_BUCKET
        try:
            if not settings.MINIO_CLIENT.bucket_exists(bucket):
                settings.MINIO_CLIENT.make_bucket(bucket)
                logger.info(
                    "MinIO bucket created.",
                    extra={"bucket": bucket},
                )
            else:
                logger.debug("MinIO bucket already exists.", extra={"bucket": bucket})
        except S3Error as exc:
            logger.error(
                "Failed to verify or create MinIO bucket.",
                extra={"bucket": bucket, "error_code": exc.code},
                exc_info=True,
            )
            raise

    # ──────────────────────────────────────────────────────────────────────────
    # Key generation
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def generate_object_key(title: str, security_level: str, file_extension: str) -> str:
        """
        Build a deterministic, human-readable object key.

        Pattern::

            {security_level}/{YYYY}/{MM}/{DD}/{safe_title}_{uuid4}.{ext}

        The title is sanitised (non-word chars replaced with ``_``) and
        truncated to 50 characters to keep keys manageable.

        Args:
            title:          Human-readable document title.
            security_level: Logical security tier (e.g. ``"public"``,
                            ``"confidential"``). Used as the top-level prefix
                            so bucket policies can be scoped by prefix.
            file_extension: Extension *without* the leading dot (e.g. ``"pdf"``).

        Returns:
            A unique object key string.
        """
        now = datetime.now()
        date_path = now.strftime("%Y/%m/%d")
        safe_title = re.sub(r"[^\w\-]", "_", title)[:50]
        unique_id = uuid.uuid4()
        key = f"{security_level}/{date_path}/{safe_title}_{unique_id}.{file_extension}"
        logger.debug("Generated object key.", extra={"object_key": key})
        return key

    # ──────────────────────────────────────────────────────────────────────────
    # CRUD operations
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def upload_file(file_object, object_name: str, content_type: Optional[str] = None) -> str:
        """
        Upload a file-like object to MinIO.

        The bucket is created on demand if it does not exist.

        Args:
            file_object:  A Django ``InMemoryUploadedFile`` / ``TemporaryUploadedFile``
                          or any file-like object that exposes a ``size`` attribute
                          and supports ``read()``.
            object_name:  Destination key inside the bucket.
            content_type: MIME type (e.g. ``"application/pdf"``).  When ``None``
                          MinIO infers the type from the key extension.

        Returns:
            ``object_name`` — unchanged, for convenient chaining.

        Raises:
            AttributeError: If ``file_object`` has no ``size`` attribute.
            S3Error:        On any MinIO / network failure.
        """
        MinIOService.ensure_bucket_exists()

        file_size = getattr(file_object, "size", None)
        if file_size is None:
            raise AttributeError(
                f"file_object {type(file_object).__name__!r} has no 'size' attribute. "
                "Wrap it in a Django UploadedFile or supply the size explicitly."
            )

        try:
            settings.MINIO_CLIENT.put_object(
                settings.MINIO_BUCKET,
                object_name,
                file_object,
                length=file_size,
                content_type=content_type,
            )
            logger.info(
                "File uploaded to MinIO.",
                extra={
                    "object_name": object_name,
                    "size_bytes": file_size,
                    "content_type": content_type,
                },
            )
            return object_name
        except S3Error as exc:
            logger.error(
                "MinIO upload failed.",
                extra={
                    "object_name": object_name,
                    "size_bytes": file_size,
                    "error_code": exc.code,
                },
                exc_info=True,
            )
            raise

    @staticmethod
    def download_file(object_name: str, file_path: str) -> str:
        """
        Download an object from MinIO to a local path.

        Args:
            object_name: Source key inside the bucket.
            file_path:   Absolute local path to write the file to.
                         The parent directory must already exist.

        Returns:
            ``file_path`` — unchanged, for convenient chaining.

        Raises:
            S3Error: If the object does not exist or cannot be downloaded.
        """
        MinIOService.ensure_bucket_exists()

        try:
            settings.MINIO_CLIENT.fget_object(
                settings.MINIO_BUCKET,
                object_name,
                file_path,
            )
            logger.info(
                "File downloaded from MinIO.",
                extra={"object_name": object_name, "local_path": file_path},
            )
            return file_path
        except S3Error as exc:
            logger.error(
                "MinIO download failed.",
                extra={"object_name": object_name, "local_path": file_path, "error_code": exc.code},
                exc_info=True,
            )
            raise

    @staticmethod
    def delete_file(object_name: str) -> None:
        """
        Delete an object from MinIO.

        Failure is logged as a warning rather than raised because a missing
        object is often not actionable (it may have already been removed by
        a previous retry).  Callers that *need* hard failure should catch
        ``S3Error`` themselves.

        Args:
            object_name: Key of the object to remove.
        """
        try:
            settings.MINIO_CLIENT.remove_object(settings.MINIO_BUCKET, object_name)
            logger.info("File deleted from MinIO.", extra={"object_name": object_name})
        except S3Error as exc:
            logger.warning(
                "Failed to delete file from MinIO — it may have already been removed.",
                extra={"object_name": object_name, "error_code": exc.code},
                exc_info=True,
            )

    @staticmethod
    def get_presigned_url(object_name: str, expires_seconds: int = 300) -> str:
        """
        Generate a time-limited, pre-signed download URL for an object.

        The URL is signed with the configured access credentials and expires
        after ``expires_seconds``.  No authentication is required to use it.

        Args:
            object_name:     Key of the object to expose.
            expires_seconds: Validity window in seconds (default: 300 = 5 min).

        Returns:
            A fully-qualified HTTPS URL string.

        Raises:
            S3Error: If the URL cannot be generated (e.g. object does not exist,
                     credentials invalid).
        """
        try:
            url = settings.MINIO_CLIENT.presigned_get_object(
                settings.MINIO_BUCKET,
                object_name,
                expires=timedelta(seconds=expires_seconds),
            )
            logger.debug(
                "Pre-signed URL generated.",
                extra={"object_name": object_name, "expires_seconds": expires_seconds},
            )
            return url
        except S3Error as exc:
            logger.error(
                "Failed to generate pre-signed URL.",
                extra={"object_name": object_name, "error_code": exc.code},
                exc_info=True,
            )
            raise