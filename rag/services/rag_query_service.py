"""
Orchestrates the end-to-end RAG query pipeline:

    embed query → retrieve chunks → build context → generate answer → persist history

Pipeline stages
---------------
1. **Resolve access** — determine which security levels the user may see.
2. **Embed**          — convert the query string into a dense vector.
3. **Retrieve**       — fetch the top-K most similar authorised chunks via
                        pgvector cosine distance.
4. **Build context**  — concatenate chunk texts up to ``max_context_length``
                        characters.
5. **Generate**       — call the LLM (or extractive fallback).
6. **Persist**        — write a ``QueryHistory`` record for analytics and
                        audit, even on failure.

Error handling
--------------
The public ``query`` method never raises.  All exceptions are caught, logged,
and returned as ``{"success": False, "error": "..."}`` dicts so the view layer
always receives a well-typed response.  A ``QueryHistory`` record is written
even for failed queries (``response_source="ERROR"``) so failures are visible
in the admin and analytics dashboards.
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

from django.conf import settings

from documents.models import DocumentChunk
from documents.services.embedding import embedding_service
from rag.models import Chat, QueryHistory
from rag.services.access_control import get_user_allowed_security_levels
from rag.services.llm_service import llm_service

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Configuration from settings.py
# ──────────────────────────────────────────────────────────────────────────────

TOP_K = settings.TOP_K
SIMILARITY_THRESHOLD = settings.SIMILARITY_THRESHOLD
MAX_CONTEXT_LENGTH = settings.RAG_MAX_CONTEXT_LENGTH


class RAGQueryService:
    """
    Stateless orchestrator for the RAG query pipeline.

    Args:
        max_context_length: Maximum character budget for the context string
                            passed to the LLM.  Chunks are added in similarity
                            order until the budget is exhausted.
    """

    def __init__(self, max_context_length: Optional[int] = None) -> None:
        self.max_context_length = max_context_length or MAX_CONTEXT_LENGTH

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def query(
        self,
        query_text: str,
        user=None,
        model_name: Optional[str] = None,
        chat_session: Optional[Chat] = None,
    ) -> Dict:
        """
        Run the full RAG pipeline for a single query.

        Args:
            query_text:    The user's natural-language question.
            user:          Django ``User`` instance used to resolve security
                           clearance.  ``None`` is treated as an unauthenticated
                           guest (access restricted to ``LOW`` security level).
            model_name:    LLM to use for generation.  ``None`` uses the
                           service's ``DEFAULT_MODEL``.
            chat_session:  Optional ``Chat`` to link the QueryHistory
                           record to. If provided, the query will be associated
                           with this chat session.

        Returns:
            A response dict.  Always contains ``"success"`` (bool) and
            ``"latency_ms"`` (int).

            On success::

                {
                    "success":      True,
                    "query_id":     <int>,
                    "answer":       <str>,
                    "source":       "LLM" | "EXTRACTIVE" | "NO_RESULTS",
                    "model":        <str | None>,
                    "chunks_used":  <int>,
                    "latency_ms":   <int>,
                    "token_count":  <int>,
                    "sources":      [{"chunk_id", "document_id",
                                      "document_title", "chunk_index"}, ...],
                }

            On failure::

                {
                    "success":    False,
                    "query_id":   <int | None>,
                    "error":      <str>,
                    "latency_ms": <int>,
                }
        """
        start_time = time.time()
        user_id = user.id if user else None

        logger.info(
            "RAG pipeline started.",
            extra={
                "user_id": user_id,
                "chat_session_id": chat_session.id if chat_session else None,
                "model_name": model_name,
                "query_preview": query_text[:120],
            },
        )

        # Access control is resolved once and reused across all pipeline stages.
        allowed_levels, effective_max_level = get_user_allowed_security_levels(user)
        logger.debug(
            "Access levels resolved.",
            extra={
                "user_id": user_id,
                "effective_max_level": effective_max_level,
                "allowed_levels": allowed_levels,
            },
        )

        try:
            # ── Stage 1: Embed query ──────────────────────────────────────────
            logger.debug("Embedding query.", extra={"user_id": user_id})
            query_embedding = embedding_service.embed_text(query_text)

            # ── Stage 2: Retrieve chunks ──────────────────────────────────────
            logger.debug(
                "Retrieving chunks.",
                extra={
                    "user_id": user_id,
                    "top_k": TOP_K,
                    "allowed_levels": allowed_levels,
                },
            )
            chunks, chunk_ids = self._retrieve_chunks(
                query_embedding=query_embedding,
                allowed_levels=allowed_levels,
            )
            logger.debug(
                "Chunks retrieved.",
                extra={"user_id": user_id, "chunks_found": len(chunks)},
            )

            if not chunks:
                logger.warning(
                    "No chunks retrieved — returning NO_RESULTS.",
                    extra={"user_id": user_id, "allowed_levels": allowed_levels},
                )
                return self._build_no_results_response(
                    user=user,
                    query_text=query_text,
                    query_embedding=query_embedding,
                    effective_max_level=effective_max_level,
                    start_time=start_time,
                    chat_session=chat_session,
                )

            # ── Stage 3: Build context ────────────────────────────────────────
            context = self._build_context(chunks)
            logger.debug(
                "Context assembled.",
                extra={
                    "user_id": user_id,
                    "context_chars": len(context),
                    "chunks_included": len(chunks),
                },
            )

            # ── Stage 4: Generate answer ──────────────────────────────────────
            logger.debug(
                "Generating answer.",
                extra={"user_id": user_id, "model_name": model_name},
            )
            answer, used_llm = llm_service.generate_answer(
                query=query_text,
                context=context,
                model_name=model_name,
            )

            # ── Stage 5: Persist query history ────────────────────────────────
            latency_ms = int((time.time() - start_time) * 1000)
            token_count = len(answer.split())
            response_source = "LLM" if used_llm else "EXTRACTIVE"

            query_history = QueryHistory.objects.create(
                user=user,
                chat=chat_session,
                query=query_text,
                query_embedding=query_embedding,
                retrieved_chunk_count=len(chunks),
                retrieved_chunk_ids=chunk_ids,
                response=answer,
                response_source=response_source,
                latency_ms=latency_ms,
                token_count=token_count,
                security_level=effective_max_level,
                is_flagged=False,
                flag_reason="",
            )

            logger.info(
                "RAG pipeline completed.",
                extra={
                    "user_id": user_id,
                    "query_id": query_history.id,
                    "chat_session_id": chat_session.id if chat_session else None,
                    "source": response_source,
                    "model_name": model_name,
                    "chunks_used": len(chunks),
                    "latency_ms": latency_ms,
                    "token_count": token_count,
                    "effective_max_level": effective_max_level,
                },
            )

            return {
                "success": True,
                "query_id": query_history.id,
                "answer": answer,
                "source": response_source,
                "model": model_name,
                "chunks_used": len(chunks),
                "latency_ms": latency_ms,
                "token_count": token_count,
                "sources": [
                    {
                        "chunk_id": chunk.id,
                        "document_id": chunk.document_id,
                        "document_title": chunk.document.title,
                        "chunk_index": chunk.chunk_index,
                        "similarity_score": round(chunk.similarity, 4),
                    }
                    for chunk in chunks
                ],
            }

        except Exception as exc:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "RAG pipeline failed.",
                extra={
                    "user_id": user_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "latency_ms": latency_ms,
                },
                exc_info=True,
            )

            # Attempt to persist a FAILED history record for audit purposes.
            q_id = self._persist_error_history(
                user=user,
                chat_session=chat_session,
                query_text=query_text,
                exc=exc,
                latency_ms=latency_ms,
                effective_max_level=effective_max_level,
            )

            return {
                "success": False,
                "query_id": q_id,
                "error": str(exc),
                "latency_ms": latency_ms,
            }

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _retrieve_chunks(
        self,
        query_embedding: List[float],
        allowed_levels: List[str],
        similarity_threshold: Optional[float] = None,
    ) -> Tuple[List[DocumentChunk], List[int]]:
        """
        Query pgvector for the top-K most similar active chunks above a
        minimum similarity threshold.

        The threshold prevents low-confidence chunks from being fed to the
        LLM as if they were relevant — a major cause of hallucination when
        the queried concept does not exist in any document.

        Args:
            query_embedding:     Dense query vector.
            allowed_levels:      Security levels the user may access.
            similarity_threshold: Minimum cosine similarity (0–1) a chunk must
                                  score to be included. Chunks below this are
                                  discarded before being passed to the LLM.
                                  Falls back to settings value if not provided.

        Returns:
            ``(chunks, chunk_ids)``
        """
        from pgvector.django import CosineDistance

        threshold = similarity_threshold or SIMILARITY_THRESHOLD

        qs = (
            DocumentChunk.objects
            .filter(is_active=True, security_level__in=allowed_levels)
            .annotate(similarity=1 - CosineDistance("embedding", query_embedding))
            .filter(similarity__gte=threshold)
            .select_related("document")
            .order_by("-similarity")[:TOP_K]
        )

        chunks = list(qs)

        if not chunks:
            logger.info(
                "No chunks met the similarity threshold.",
                extra={
                    "threshold": threshold,
                    "allowed_levels": allowed_levels,
                },
            )
        else:
            scores = [round(c.similarity, 3) for c in chunks]
            logger.debug(
                "Chunks retrieved above threshold.",
                extra={
                    "threshold": threshold,
                    "chunks_returned": len(chunks),
                    "similarity_scores": scores,
                },
            )

        return chunks, [c.id for c in chunks]

    def _build_context(self, chunks: List[DocumentChunk]) -> str:
        """
        Concatenate chunk texts into a single context string.

        Chunks are added in the order provided (highest similarity first)
        until ``max_context_length`` characters would be exceeded.  The
        truncation point is logged at DEBUG level.

        Args:
            chunks: Ordered list of retrieved ``DocumentChunk`` objects.

        Returns:
            A multi-paragraph context string with source attributions.
        """
        parts: List[str] = []
        total_chars = 0

        for i, chunk in enumerate(chunks):
            text = f"[Source {i + 1}: {chunk.document.title}]\n{chunk.content}"
            if total_chars + len(text) > self.max_context_length:
                logger.debug(
                    "Context budget exhausted — truncating.",
                    extra={
                        "chunks_included": i,
                        "chars_used": total_chars,
                        "max_context_length": self.max_context_length,
                    },
                )
                break
            parts.append(text)
            total_chars += len(text)

        return "\n\n".join(parts)

    def _build_no_results_response(
        self,
        user,
        query_text: str,
        query_embedding: List[float],
        effective_max_level: str,
        start_time: float,
        chat_session: Optional[Chat] = None,
    ) -> Dict:
        """
        Build and persist a NO_RESULTS response.

        Args:
            user:               Django user (may be ``None``).
            query_text:         Original query string.
            query_embedding:    Embedded query vector.
            effective_max_level: The user's highest permitted security level.
            start_time:         ``time.time()`` value at pipeline entry.
            chat_session:       Optional chat session to link the record to.

        Returns:
            A success-shaped response dict with ``source="NO_RESULTS"``.
        """
        latency_ms = int((time.time() - start_time) * 1000)
        message = "I could not find any relevant information to answer your question."
        q_id = None

        try:
            qh = QueryHistory.objects.create(
                user=user,
                chat=chat_session,
                query=query_text,
                query_embedding=query_embedding,
                retrieved_chunk_count=0,
                retrieved_chunk_ids=[],
                response=message,
                response_source="NO_RESULTS",
                latency_ms=latency_ms,
                token_count=len(message.split()),
                security_level=effective_max_level,
                is_flagged=False,
                flag_reason="",
            )
            q_id = qh.id
        except Exception as db_exc:
            logger.error(
                "Failed to persist NO_RESULTS query history.",
                extra={"user_id": user.id if user else None, "error": str(db_exc)},
                exc_info=True,
            )

        return {
            "success": True,
            "query_id": q_id,
            "answer": message,
            "source": "NO_RESULTS",
            "model": None,
            "chunks_used": 0,
            "latency_ms": latency_ms,
            "token_count": len(message.split()),
            "sources": [],
        }

    def _persist_error_history(
        self,
        user,
        query_text: str,
        exc: Exception,
        latency_ms: int,
        effective_max_level: str,
        chat_session: Optional[Chat] = None,
    ) -> Optional[int]:
        """
        Write an ERROR ``QueryHistory`` record for a failed pipeline run.

        Failure here is non-fatal — a warning is logged and ``None`` is
        returned so the caller can still send a response to the client.

        Args:
            user:                Django user (may be ``None``).
            query_text:          Original query string.
            exc:                 The exception that caused the failure.
            latency_ms:          Total elapsed time up to the failure point.
            effective_max_level: User's security level at time of query.
            chat_session:        Optional chat session to link the record to.

        Returns:
            The ``QueryHistory.id`` on success, or ``None`` if the DB write
            itself fails.
        """
        try:
            qh = QueryHistory.objects.create(
                user=user,
                chat=chat_session,
                query=query_text,
                response=f"Error: {exc}",
                response_source="ERROR",
                latency_ms=latency_ms,
                security_level=effective_max_level,
                is_flagged=True,
                flag_reason=str(exc),
            )
            return qh.id
        except Exception as db_exc:
            logger.error(
                "Failed to persist ERROR query history — record will be missing from audit log.",
                extra={
                    "user_id": user.id if user else None,
                    "original_error": str(exc),
                    "db_error": str(db_exc),
                },
                exc_info=True,
            )
            return None


# Module-level singleton.
rag_query_service = RAGQueryService()