import tempfile
import logging

from django.db import transaction
from documents.models import Document, DocumentChunk
from .storage import MinIOService
from .embedding import embedding_service

from documents.services.document_processor import document_processor




logger = logging.getLogger(__name__)


class DocumentIndexingService:

    def __init__(self):

        self.processor = document_processor


    def index_document(self, document_id: int):

        document = Document.objects.get(id=document_id)

        document.status = Document.Status.PROCESSING
        document.save(update_fields=["status"])


        try:

            # Step 1 download from minio

            with tempfile.NamedTemporaryFile(delete=True) as temp:

                MinIOService.download_file(
                    object_name=document.minio_key,
                    file_path=temp.name
                )

                # Step 2 extract chunks

                chunks = self.processor.process_document(
                    file_path=temp.name,
                    file_type=document.file_type
                )


            # Step 3 save chunks with embeddings

            with transaction.atomic():
                # Option 1: Batch embedding (recommended for performance)
                texts = [chunk["content"] for chunk in chunks]
                embeddings = embedding_service.embed_batch(texts)  # ✅ Use batch version
                
                # Create all chunk objects
                chunks_to_create = []
                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    chunks_to_create.append(
                        DocumentChunk(
                            document=document,
                            chunk_index=chunk["chunk_index"],
                            content=chunk["content"],
                            embedding=embedding,  # Already a list from embed_batch
                            token_count=chunk["token_count"],
                            metadata=chunk["metadata"],
                            security_level=document.security_level,
                        )
                    )
                
                # Bulk insert all at once
                DocumentChunk.objects.bulk_create(chunks_to_create, batch_size=100)

                document.chunk_count = len(chunks)

                document.status = Document.Status.INDEXED

                document.save(update_fields=[
                    "chunk_count",
                    "status"
                ])


            logger.info(f"Indexed document {document.id}")


        except Exception as e:

            document.status = Document.Status.FAILED

            document.error_message = str(e)

            document.save(update_fields=["status", "error_message"])

            # Delete file from MinIO if indexing failed

            try:
                MinIOService.delete_file(document.minio_key)
                logger.warning(f"Deleted orphaned MinIO file {document.minio_key}")
            except Exception as cleanup_error:
                logger.error(f"Failed to delete MinIO file: {cleanup_error}")

            logger.error(str(e))

            raise
