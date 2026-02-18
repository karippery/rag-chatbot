import logging
import uuid
from datetime import datetime, timedelta
from django.conf import settings
from minio.error import S3Error

logger = logging.getLogger(__name__)

class MinIOService:
    
    @staticmethod
    def ensure_bucket_exists():
        """
        Idempotent check to ensure the bucket exists.
        Runs safely every time; does nothing if bucket already exists.
        """
        try:
            if not settings.MINIO_CLIENT.bucket_exists(settings.MINIO_BUCKET):
                settings.MINIO_CLIENT.make_bucket(settings.MINIO_BUCKET)
                logger.info(f"Bucket '{settings.MINIO_BUCKET}' created.")
        except S3Error as e:
            logger.error(f"Failed to create/check bucket: {e}")
            raise e

    @staticmethod
    def generate_object_key(title:str, security_level: str, file_extension: str) -> str:
        """
        Generates a structured key: {level}/{YYYY}/{MM}/{DD}/{uuid}.{ext}
        Adheres to KISS and DRY principles.
        """
        now = datetime.now()
        date_path = now.strftime("%Y/%m/%d")
        unique_id = uuid.uuid4()
        
        # Construct the pseudo-folder path
        # Example: HIGH/2023/10/27/a1b2c3d4.pdf
        return f"{security_level}/{date_path}/{title}_{unique_id}.{file_extension}"

    @staticmethod
    def upload_file(file_object, object_name: str, content_type: str = None):
        """
        Uploads a file to MinIO.
        Ensures bucket exists before uploading.
        """
        # Ensure bucket existence (Safe to call every time)
        MinIOService.ensure_bucket_exists()
        
        try:
            settings.MINIO_CLIENT.put_object(
                settings.MINIO_BUCKET,
                object_name,
                file_object,
                length=file_object.size,
                content_type=content_type,
            )
            logger.info(f"File uploaded successfully to: {object_name}")
            return object_name
        except S3Error as e:
            logger.error(f"MinIO upload failed: {e}")
            raise e

    @staticmethod
    def delete_file(object_name: str):
        """Deletes a file from MinIO."""
        try:
            settings.MINIO_CLIENT.remove_object(settings.MINIO_BUCKET, object_name)
            logger.info(f"File deleted from MinIO: {object_name}")
        except S3Error as e:
            logger.warning(f"Failed to delete {object_name} from MinIO: {e}")

    @staticmethod
    def get_presigned_url(object_name: str, expires_seconds: int = 300) -> str:
        """
        Generates a time-limited presigned URL for downloading.
        """
        try:
            url = settings.MINIO_CLIENT.presigned_get_object(
                settings.MINIO_BUCKET,
                object_name,
                expires=timedelta(seconds=expires_seconds)
            )
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL for {object_name}: {e}")
            raise e