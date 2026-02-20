import logging
import time
from typing import List, Optional, Tuple, Dict

from documents.models import Document, DocumentChunk
from documents.services.embedding import embedding_service
from rag.models import QueryHistory
from rag.services.llm_service import llm_service


logger = logging.getLogger(__name__)

SECURITY_LEVEL_ACCESS = {
    Document.SecurityLevel.LOW:  [Document.SecurityLevel.LOW],
    Document.SecurityLevel.MID:  [Document.SecurityLevel.LOW, Document.SecurityLevel.MID],
    Document.SecurityLevel.HIGH: [Document.SecurityLevel.LOW, Document.SecurityLevel.MID, Document.SecurityLevel.HIGH],
}

TOP_K = 5


class RAGQueryService:
    def __init__(self, max_context_length: int = 2000):
        self.max_context_length = max_context_length

    def query(
        self,
        query_text: str,
        user=None,
        security_level: Optional[str] = None,
        model_name: Optional[str] = None,  # passed from view based on mode
    ) -> Dict:
        start_time = time.time()

        try:
            query_embedding = embedding_service.embed_text(query_text)

            chunks, chunk_ids = self._retrieve_chunks(
                query_embedding=query_embedding,
                security_level=security_level or Document.SecurityLevel.LOW,
            )

            if not chunks:
                return self._build_no_results_response(
                    user=user,
                    query_text=query_text,
                    query_embedding=query_embedding,
                    security_level=security_level,
                    start_time=start_time,
                )

            context = self._build_context(chunks)

            answer, used_llm = llm_service.generate_answer(
                query=query_text,
                context=context,
                model_name=model_name,
            )

            latency_ms = int((time.time() - start_time) * 1000)
            token_count = len(answer.split())
            response_source = "LLM" if used_llm else "EXTRACTIVE"

            query_history = QueryHistory.objects.create(
                user=user,
                query=query_text,
                query_embedding=query_embedding,
                retrieved_chunk_count=len(chunks),
                retrieved_chunk_ids=chunk_ids,
                response=answer,
                response_source=response_source,
                latency_ms=latency_ms,
                token_count=token_count,
                security_level=security_level or QueryHistory.SecurityLevel.LOW,
                is_flagged=False,
                flag_reason="",
            )

            logger.info(
                "RAG query completed in %dms | source=%s | model=%s | chunks=%d",
                latency_ms, response_source, model_name, len(chunks),
                extra={"query_id": query_history.id, "user_id": user.id if user else None},
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
                    }
                    for chunk in chunks
                ],
            }

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.error("RAG query failed: %s", e, exc_info=True)

            try:
                qh = QueryHistory.objects.create(
                    user=user,
                    query=query_text,
                    response=f"Error: {e}",
                    response_source="ERROR",
                    latency_ms=latency_ms,
                    security_level=security_level or QueryHistory.SecurityLevel.LOW,
                    is_flagged=True,
                    flag_reason=str(e),
                )
                q_id = qh.id
            except Exception as db_err:
                logger.error("Failed to log error query: %s", db_err)
                q_id = None

            return {
                "success": False,
                "query_id": q_id,
                "error": str(e),
                "latency_ms": latency_ms,
            }

    def _retrieve_chunks(
        self,
        query_embedding: List[float],
        security_level: str,
    ) -> Tuple[List[DocumentChunk], List[int]]:
        from pgvector.django import CosineDistance

        allowed_levels = SECURITY_LEVEL_ACCESS.get(
            security_level, [Document.SecurityLevel.LOW]
        )

        qs = (
            DocumentChunk.objects
            .filter(is_active=True, security_level__in=allowed_levels)
            .annotate(similarity=1 - CosineDistance("embedding", query_embedding))
            .select_related("document")
            .order_by("-similarity")[:TOP_K]
        )

        chunks = list(qs)
        return chunks, [c.id for c in chunks]

    def _build_context(self, chunks: List[DocumentChunk]) -> str:
        parts = []
        total = 0
        for i, chunk in enumerate(chunks):
            text = f"[Source {i+1}: {chunk.document.title}]\n{chunk.content}"
            if total + len(text) > self.max_context_length:
                logger.debug("Context truncated at %d chars (limit %d).", total, self.max_context_length)
                break
            parts.append(text)
            total += len(text)
        return "\n\n".join(parts)

    def _build_no_results_response(
        self,
        user,
        query_text: str,
        query_embedding: List[float],
        security_level: Optional[str],
        start_time: float,
    ) -> Dict:
        latency_ms = int((time.time() - start_time) * 1000)
        message = "I could not find any relevant information to answer your question."
        logger.warning("No chunks retrieved for query: %s", query_text)

        try:
            qh = QueryHistory.objects.create(
                user=user,
                query=query_text,
                query_embedding=query_embedding,
                retrieved_chunk_count=0,
                retrieved_chunk_ids=[],
                response=message,
                response_source="NO_RESULTS",
                latency_ms=latency_ms,
                token_count=len(message.split()),
                security_level=security_level or QueryHistory.SecurityLevel.LOW,
                is_flagged=False,
                flag_reason="",
            )
            q_id = qh.id
        except Exception as db_err:
            logger.error("Failed to log no-results query: %s", db_err)
            q_id = None

        return {
            "success": True,
            "query_id": q_id,
            "answer": message,
            "source": "NO_RESULTS",
            "model": None,
            "chunks_used": 0,
            "latency_ms": latency_ms,
            "sources": [],
        }


# Singleton
rag_query_service = RAGQueryService()