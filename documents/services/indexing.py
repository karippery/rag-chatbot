"""
Orchestrates the full document indexing pipeline:

    MinIO download → text extraction → chunking → embedding → DB persistence

Pipeline stages
---------------
1. **Download** — fetch the raw file from MinIO into a local temp file.
2. **Process**  — extract text and split it into overlapping chunks.
3. **Embed**    — generate a dense vector for each chunk (outside the DB
                  transaction to avoid holding a connection during slow
                  model inference).
4. **Persist**  — atomically write all chunks and update the Document status.

Error contract
--------------
``index_document`` never silently swallows exceptions.  On *any* failure it:

* Sets ``document.status = FAILED`` and records the error message.
* Re-raises the exception so the Celery task can apply retry logic.
* Does **not** delete the MinIO object — the file must remain available for
  retries; the Celery task owns MinIO cleanup after all retries are exhausted.

Temp file cleanup
-----------------
The local temp file is always removed in the ``finally`` block, whether the
pipeline succeeded or failed, to prevent disk leaks on long-running workers.
"""

import logging
import os
import tempfile

from django.db import DatabaseError, transaction

from documents.models import Document, DocumentChunk
from documents.services.document_processor import document_processor
from .embedding import embedding_service
from .storage import MinIOService

logger = logging.getLogger(__name__)


class DocumentIndexingService:
    """
    Stateless service that drives the end-to-end document indexing pipeline.

    A module-level singleton is not provided here because the service holds no
    state — instantiate it wherever needed, or create one at the Django app
    layer and inject it into tasks.
    """

    def __init__(self) -> None:
        self.processor = document_processor

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def index_document(self, document_id: int) -> bool:
        """
        Run the full indexing pipeline for a single document.

        Fetches the ``Document`` record, downloads the file from MinIO,
        extracts and embeds its text, then persists the resulting
        ``DocumentChunk`` rows to the database.

        Args:
            document_id: Primary key of the ``Document`` to index.

        Returns:
            ``True`` on success.

        Raises:
            Document.DoesNotExist: If no document with ``document_id`` exists.
            ValueError:            If the document produces zero chunks (empty
                                   or unreadable file).
            S3Error:               On MinIO download failure.
            DatabaseError:         On DB write failure.
            Exception:             Any other unexpected error; always re-raised
                                   after updating the document status to FAILED.
        """
        logger.info(
            "Indexing pipeline started.",
            extra={"document_id": document_id},
        )

        # ── Fetch document ────────────────────────────────────────────────────
        try:
            document = Document.objects.get(id=document_id)
        except Document.DoesNotExist:
            # Nothing to mark as FAILED — the record doesn't exist.
            logger.error(
                "Document not found — cannot index.",
                extra={"document_id": document_id},
            )
            raise

        document.status = Document.Status.PROCESSING
        document.save(update_fields=["status"])
        logger.debug(
            "Document status set to PROCESSING.",
            extra={"document_id": document_id, "minio_key": document.minio_key},
        )

        tmp_path = None
        try:
            # ── Step 1: Download from MinIO ───────────────────────────────────
            # ``delete=False`` for cross-platform compatibility: Windows locks
            # open file handles, so we close the handle first and let MinIO
            # write to the path directly.
            tmp = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=f".{document.file_type}",
            )
            tmp_path = tmp.name
            tmp.close()

            logger.debug(
                "Downloading document from MinIO.",
                extra={
                    "document_id": document_id,
                    "minio_key": document.minio_key,
                    "tmp_path": tmp_path,
                },
            )
            MinIOService.download_file(
                object_name=document.minio_key,
                file_path=tmp_path,
            )
            logger.debug(
                "MinIO download complete.",
                extra={"document_id": document_id, "tmp_path": tmp_path},
            )

            # ── Step 2: Extract and chunk document content ────────────────────
            logger.debug(
                "Processing document into chunks.",
                extra={"document_id": document_id, "file_type": document.file_type},
            )
            chunks = self.processor.process_document(
                file_path=tmp_path,
                file_type=document.file_type,
            )

            if not chunks:
                raise ValueError(
                    f"Document {document_id} produced zero chunks — "
                    "file may be empty or unreadable."
                )

            logger.debug(
                "Document chunked successfully.",
                extra={"document_id": document_id, "num_chunks": len(chunks)},
            )

            # ── Step 3: Generate embeddings (outside transaction) ─────────────
            # Embedding is the slowest step (model inference).  Running it
            # outside the DB transaction keeps the connection free during that
            # time, reducing lock contention and idle-connection pressure.
            logger.debug(
                "Generating embeddings for chunks.",
                extra={"document_id": document_id, "num_chunks": len(chunks)},
            )
            texts = [chunk["content"] for chunk in chunks]
            embeddings = embedding_service.embed_batch(texts)

            if len(embeddings) != len(chunks):
                # Defensive check — embed_batch should always return one vector
                # per input, but a mismatch here would silently corrupt data.
                raise ValueError(
                    f"Embedding count mismatch: got {len(embeddings)} embeddings "
                    f"for {len(chunks)} chunks (document {document_id})."
                )

            logger.debug(
                "Embeddings generated.",
                extra={
                    "document_id": document_id,
                    "num_embeddings": len(embeddings),
                    "embedding_dim": len(embeddings[0]) if embeddings else 0,
                },
            )

            # ── Step 4: Persist chunks atomically ────────────────────────────
            # All DB writes happen inside a single transaction so a partial
            # failure leaves the document in a consistent (unchunked) state
            # rather than partially indexed.
            logger.debug(
                "Persisting chunks to database.",
                extra={"document_id": document_id, "num_chunks": len(chunks)},
            )
            try:
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

            except DatabaseError as db_err:
                logger.error(
                    "Database write failed during chunk persistence.",
                    extra={"document_id": document_id, "num_chunks": len(chunks)},
                    exc_info=True,
                )
                raise

            logger.info(
                "Document indexed successfully.",
                extra={
                    "document_id": document_id,
                    "num_chunks": len(chunks),
                    "minio_key": document.minio_key,
                },
            )
            return True

        except Exception as exc:
            # ── Failure handler ───────────────────────────────────────────────
            # Record the failure on the document.  Do NOT delete the MinIO
            # file — the Celery task owns that after all retries are exhausted.
            error_message = str(exc)
            document.status = Document.Status.FAILED
            document.error_message = error_message
            document.save(update_fields=["status", "error_message"])

            logger.error(
                "Indexing pipeline failed.",
                extra={
                    "document_id": document_id,
                    "error": error_message,
                    "error_type": type(exc).__name__,
                },
                exc_info=True,
            )
            raise  # Re-raise so the Celery task can apply its retry policy.

        finally:
            # ── Temp file cleanup ─────────────────────────────────────────────
            # Always remove the local copy regardless of success or failure.
            # A missing file (e.g. download failed before writing) is handled
            # by the os.path.exists guard.
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                    logger.debug(
                        "Temp file cleaned up.",
                        extra={"document_id": document_id, "tmp_path": tmp_path},
                    )
                except OSError as cleanup_err:
                    # Non-fatal: log and continue.  The worker will survive; a
                    # disk-full situation will surface on the next write anyway.
                    logger.warning(
                        "Failed to remove temp file — manual cleanup may be required.",
                        extra={
                            "document_id": document_id,
                            "tmp_path": tmp_path,
                            "error": str(cleanup_err),
                        },
                    )