from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Document
from .services.storage import MinIOService

@receiver(post_delete, sender=Document)
def delete_document_from_minio(sender, instance, **kwargs):
    """
    Ensures data consistency by removing the file from MinIO 
    when the database record is deleted.
    """
    if instance.minio_key:
        MinIOService.delete_file(instance.minio_key)