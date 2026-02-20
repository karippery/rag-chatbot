# documents/tasks.py
from celery import shared_task
import logging

from documents.services.indexing import DocumentIndexingService
from documents.services.storage import MinIOService

logger = logging.getLogger(__name__)

PERMANENT_FAILURE_PREFIX = "PERMANENT_FAILURE:"


@shared_task(bind=True, max_retries=3)
def index_document_task(self, document_id: int):
    """
    Celery task to index a document asynchronously.

    Retry Policy:
    - Retries up to 3 times with exponential backoff (60s, 120s, 180s)
    - MinIO file is deleted ONLY after all retries are exhausted
    - Raises on permanent failure so Celery marks task as FAILURE (not SUCCESS)
    """
    logger.info(
        f"Starting indexing task for document {document_id}",
        extra={"document_id": document_id, "attempt": self.request.retries + 1}
    )

    try:
        self.update_state(
            state="PROGRESS",
            meta={"current": 1, "total": 100, "status": "Starting indexing..."}
        )

        service = DocumentIndexingService()
        success = service.index_document(document_id)

        if success:
            logger.info(f"Successfully indexed document {document_id}")
            return {
                "document_id": document_id,
                "status": "completed",
                "message": "Document indexed successfully",
            }
        else:
            raise Exception("Indexing service returned failure")

    except Exception as e:
        logger.exception(
            f"Error indexing document {document_id}: {str(e)}",
            extra={"document_id": document_id, "attempt": self.request.retries + 1}
        )

        # ── All retries exhausted → permanent failure ─────────────────
        if self.request.retries >= self.max_retries:
            logger.warning(
                f"Document {document_id} permanently failed after {self.max_retries} retries.",
                extra={"document_id": document_id}
            )

            from documents.models import Document

            permanent_error_msg = (
                f"{PERMANENT_FAILURE_PREFIX} Indexing failed after "
                f"{self.max_retries} retries: {str(e)}"
            )

            # ── Fetch once, update status, then clean up MinIO ────────
            try:
                doc = Document.objects.only("minio_key", "original_name").get(id=document_id)
                doc.status = Document.Status.FAILED
                doc.error_message = permanent_error_msg
                doc.save(update_fields=["status", "error_message"])

                if doc.minio_key:
                    MinIOService.delete_file(doc.minio_key)
                    logger.info(
                        f"Deleted MinIO file after final failure: {doc.minio_key}",
                        extra={"document_id": document_id, "original_name": doc.original_name}
                    )
            except Exception as cleanup_err:
                logger.error(
                    f"Cleanup failed for document {document_id}: {cleanup_err}",
                    exc_info=True,
                    extra={"document_id": document_id}
                )

            # Raise so Celery marks this task as FAILURE, not SUCCESS
            raise Exception(
                f"Document {document_id} permanently failed after "
                f"{self.max_retries} retries: {str(e)}"
            ) from e

        # ── Retry with exponential backoff ────────────────────────────
        countdown = 60 * (self.request.retries + 1)
        logger.info(
            f"Retrying document {document_id} in {countdown}s "
            f"(attempt {self.request.retries + 1}/{self.max_retries})",
            extra={"document_id": document_id, "countdown": countdown}
        )
        raise self.retry(exc=e, countdown=countdown)