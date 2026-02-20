# documents/services/indexing.py
import tempfile
import os
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

    def index_document(self, document_id: int) -> bool:
        """
        Index a document: download from MinIO, extract chunks, generate
        embeddings, and persist to the database.

        Returns:
            bool: True on success.

        Raises:
            Exception: On any failure. The caller (Celery task) is responsible
                       for retry logic and MinIO cleanup — this method does NOT
                       delete MinIO files on failure.
        """
        document = Document.objects.get(id=document_id)

        document.status = Document.Status.PROCESSING
        document.save(update_fields=["status"])

        tmp_path = None
        try:
            # ── Step 1: Download from MinIO to a temp file ────────────
            # delete=False for cross-platform compatibility (Windows locks
            # open files, preventing MinIO from writing to them by path).
            tmp = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=f".{document.file_type}"
            )
            tmp_path = tmp.name
            tmp.close()  # Release handle so MinIO can write to the path

            MinIOService.download_file(
                object_name=document.minio_key,
                file_path=tmp_path
            )

            # ── Step 2: Extract and chunk document content ────────────
            chunks = self.processor.process_document(
                file_path=tmp_path,
                file_type=document.file_type
            )

            if not chunks:
                raise ValueError(f"Document {document_id} produced zero chunks — file may be empty or unreadable.")

            # ── Step 3: Generate embeddings (outside transaction) ─────
            # embed_batch can be slow (model inference). Keeping it outside
            # the transaction avoids holding a DB connection open during that time.
            texts = [chunk["content"] for chunk in chunks]
            embeddings = embedding_service.embed_batch(texts)

            # ── Step 4: Persist chunks atomically ─────────────────────
            with transaction.atomic():
                chunks_to_create = [
                    DocumentChunk(
                        document=document,
                        chunk_index=chunk["chunk_index"],
                        content=chunk["content"],
                        embedding=embedding,
                        token_count=chunk["token_count"],
                        metadata=chunk["metadata"],
                        security_level=document.security_level,
                    )
                    for chunk, embedding in zip(chunks, embeddings)
                ]

                DocumentChunk.objects.bulk_create(chunks_to_create, batch_size=100)

                document.chunk_count = len(chunks)
                document.status = Document.Status.INDEXED
                document.save(update_fields=["chunk_count", "status"])

            logger.info(
                f"Successfully indexed document {document_id} "
                f"({len(chunks)} chunks)",
                extra={"document_id": document_id, "chunk_count": len(chunks)}
            )
            return True

        except Exception as e:
            # Update document status — do NOT delete MinIO file here.
            # The Celery task handles MinIO cleanup after all retries are
            # exhausted, so the file must remain available for retries.
            document.status = Document.Status.FAILED
            document.error_message = str(e)
            document.save(update_fields=["status", "error_message"])

            logger.error(
                f"Indexing failed for document {document_id}: {str(e)}",
                exc_info=True,
                extra={"document_id": document_id}
            )
            raise  # Re-raise for Celery retry logic

        finally:
            # Always clean up the local temp file, regardless of outcome.
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                    logger.debug(
                        f"Cleaned up temp file: {tmp_path}",
                        extra={"tmp_path": tmp_path}
                    )
                except Exception as cleanup_err:
                    # Non-fatal: log and continue
                    logger.warning(
                        f"Failed to clean up temp file {tmp_path}: {cleanup_err}",
                        extra={"tmp_path": tmp_path}
                    )