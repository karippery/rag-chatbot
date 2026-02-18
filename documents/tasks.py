# documents/tasks.py
from datetime import timedelta, timezone
from celery import shared_task
import logging
from django.core.cache import cache

from documents.services.indexing import DocumentIndexingService


logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def index_document_task(self, document_id):
    """
    Celery task to index a document asynchronously.
    """
    logger.info(f"Starting indexing task for document {document_id}")
    
    try:
        # Update task progress (optional)
        self.update_state(
            state='PROGRESS',
            meta={'current': 1, 'total': 100, 'status': 'Starting indexing...'}
        )
        
        # Call your indexing service
        service = DocumentIndexingService()
        success = service.index_document(document_id)
        
        if success:
            logger.info(f"Successfully indexed document {document_id}")
            return {
                'document_id': document_id,
                'status': 'completed',
                'message': 'Document indexed successfully'
            }
        else:
            logger.error(f"Failed to index document {document_id}")
            raise self.retry(
                exc=Exception("Indexing failed"),
                countdown=60  # Retry after 60 seconds
            )
            
    except Exception as e:
        logger.exception(f"Error indexing document {document_id}: {str(e)}")
        
        # Retry up to 3 times
        try:
            self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        except self.MaxRetriesExceededError:
            # Update document status to failed
            from .models import Document
            Document.objects.filter(id=document_id).update(
                status=Document.Status.FAILED,
                error_message=f"Indexing failed after 3 retries: {str(e)}"
            )
            return {
                'document_id': document_id,
                'status': 'failed',
                'error': str(e)
            }

@shared_task
def cleanup_failed_indexing_task():
    """
    Optional: Periodic task to clean up or retry failed indexing jobs.
    """
    from .models import Document
    failed_docs = Document.objects.filter(status=Document.Status.FAILED)
    
    for doc in failed_docs:
        # Retry documents that failed less than 1 hour ago
        if doc.updated_at > timezone.now() - timedelta(hours=1):
            index_document_task.delay(doc.id)
    
    return f"Retried {failed_docs.count()} failed documents"