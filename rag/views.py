import logging

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.conf import settings
from rag.models import Chat, QueryHistory
from rag.services.rag_query_service import rag_query_service

from .serializers import ChatSerializer, QueryRequestSerializer, QueryHistorySerializer

logger = logging.getLogger(__name__)
RESPONSE_MODE_MODELS = settings.RESPONSE_MODE_MODELS

# Maps the user-facing ``mode`` value to the underlying model identifier.
# Add entries here when new models are registered in LLMService.
# ──────────────────────────────────────────────────────────────────────────────
# Chat Management Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(summary="List all chats", tags=["RAG Chats"]),
    create=extend_schema(summary="Create a new chat", tags=["RAG Chats"])
)
class ChatListCreateView(generics.ListCreateAPIView):
    """
    List user's active conversations or create a new empty chat.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatSerializer

    def get_queryset(self):
        # Enforce access control and hide soft-deleted chats
        return Chat.objects.filter(user=self.request.user, is_deleted=False)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    destroy=extend_schema(summary="Delete a chat (Soft delete)", tags=["RAG Chats"])
)
class ChatDestroyView(generics.DestroyAPIView):
    """
    Soft-delete a chat session. Hides it from the user but keeps DB records for audit.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChatSerializer
    lookup_field = "id"

    def get_queryset(self):
        return Chat.objects.filter(user=self.request.user, is_deleted=False)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save()


# ──────────────────────────────────────────────────────────────────────────────
# Chat Message (RAG Trigger) Endpoints
# ──────────────────────────────────────────────────────────────────────────────

@extend_schema_view(
    get=extend_schema(summary="View Chat History", tags=["RAG Messages"]),
    post=extend_schema(summary="Ask a Question (Triggers RAG)", tags=["RAG Messages"])
)
class ChatMessageView(generics.GenericAPIView):
    """
    Handle viewing messages and submitting new RAG queries for a specific chat.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return QueryRequestSerializer
        return QueryHistorySerializer

    def get_chat_object(self):
        """Securely fetch the chat session"""
        chat_id = self.kwargs.get("id") or self.kwargs.get("chat_id")
        
        if not chat_id:
            logger.error("No chat_id found in URL kwargs")
            raise Exception("chat_id not provided in URL")
        
        logger.debug(
            "Fetching chat.",
            extra={
                "user_id": self.request.user.id,
                "chat_id": chat_id,
            }
        )
        
        return get_object_or_404(
            Chat,
            id=chat_id,
            user=self.request.user,
            is_deleted=False   
        )

    def get(self, request, *args, **kwargs):
        """View History: Returns list of Q&A pairs for this chat."""
        chat = self.get_chat_object()
        
        messages = QueryHistory.objects.filter(
            chat=chat 
        ).order_by("created_at")
        
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        """Ask a Question: Runs secure RAG pipeline and saves to this chat."""
        chat = self.get_chat_object()
        
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Query validation failed.",
                extra={"user_id": request.user.id, "errors": serializer.errors}
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated = serializer.validated_data
        query_text = validated["query"]
        mode = validated.get("mode", "quick")
        model_name = RESPONSE_MODE_MODELS.get(mode, settings.LLM_DEFAULT_MODEL)

        # Auto-update chat title if it's the first message
        if not chat.title:
            chat.title = query_text[:50].strip()
            chat.save(update_fields=["title"])

        try:
            result = rag_query_service.query(
                query_text=query_text,
                user=request.user,
                model_name=model_name,
                chat_session=chat  # ← Must match service parameter name
            )
        except Exception as exc:
            logger.error(
                "Unhandled exception in rag_query_service.query.",
                extra={
                    "user_id": request.user.id,
                    "chat_id": chat.id,
                    "error": str(exc)
                },
                exc_info=True,
            )
            return Response(
                {"error": "Internal server error", "details": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Update chat timestamp
        if result.get("success"):
            chat.save(update_fields=["updated_at"])

        http_status = (
            status.HTTP_200_OK 
            if result.get("success") 
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        return Response(result, status=http_status)
    
# ──────────────────────────────────────────────────────────────────────────────
# Query endpoint
# ──────────────────────────────────────────────────────────────────────────────

class QueryView(generics.GenericAPIView):
    """
    Submit a natural-language question to the RAG pipeline.

    The service embeds the query, retrieves the most relevant document chunks
    the user is authorised to access, and generates a grounded answer using
    the selected LLM.  Falls back to extractive summarisation if the LLM is
    unavailable.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = QueryRequestSerializer

    @extend_schema(
        summary="Submit a RAG query",
        description=(
            "Embeds the query, retrieves relevant document chunks within the "
            "user's security clearance, and returns a generated answer. "
            "Use `mode=quick` (default) for the smaller, faster model or "
            "`mode=detailed` for the larger, more thorough model."
        ),
        responses={
            200: OpenApiResponse(
                description="Query processed successfully (answer may be extractive if LLM unavailable).",
                examples=[
                    OpenApiExample(
                        "LLM answer",
                        value={
                            "success": True,
                            "query_id": 42,
                            "answer": "The Q3 revenue was $4.2 million.",
                            "source": "LLM",
                            "model": "Qwen/Qwen2-0.5B-Instruct",
                            "chunks_used": 3,
                            "latency_ms": 812,
                            "token_count": 11,
                            "sources": [
                                {
                                    "chunk_id": 7,
                                    "document_id": 2,
                                    "document_title": "Q3 Financial Report",
                                    "chunk_index": 4,
                                }
                            ],
                        },
                    ),
                    OpenApiExample(
                        "No results",
                        value={
                            "success": True,
                            "query_id": 43,
                            "answer": "I could not find any relevant information to answer your question.",
                            "source": "NO_RESULTS",
                            "model": None,
                            "chunks_used": 0,
                            "latency_ms": 54,
                            "sources": [],
                        },
                    ),
                ],
            ),
            400: OpenApiResponse(description="Invalid request body (validation error)."),
            401: OpenApiResponse(description="Authentication credentials not provided."),
            500: OpenApiResponse(
                description="Unexpected server error.",
                examples=[
                    OpenApiExample(
                        "Internal error",
                        value={"error": "Internal server error", "details": "..."},
                    )
                ],
            ),
        },
        tags=["RAG"],
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Query request validation failed.",
                extra={
                    "user_id": request.user.id,
                    "errors": serializer.errors,
                },
            )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated = serializer.validated_data
        query_text = validated["query"]
        mode = validated.get("mode", "quick")
        model_name = RESPONSE_MODE_MODELS.get(mode, RESPONSE_MODE_MODELS["quick"])

        logger.info(
            "RAG query received.",
            extra={
                "user_id": request.user.id,
                "mode": mode,
                "model_name": model_name,
                "query_preview": query_text[:100],
            },
        )

        try:
            result = rag_query_service.query(
                query_text=query_text,
                user=request.user,
                model_name=model_name,
            )
        except Exception as exc:
            # The service should not raise (it returns success=False on errors),
            # but guard here so an unexpected bug never leaks a 500 without a log.
            logger.error(
                "Unhandled exception in rag_query_service.query.",
                extra={"user_id": request.user.id, "error": str(exc)},
                exc_info=True,
            )
            return Response(
                {"error": "Internal server error", "details": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        http_status = (
            status.HTTP_200_OK
            if result.get("success")
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        logger.info(
            "RAG query response dispatched.",
            extra={
                "user_id": request.user.id,
                "query_id": result.get("query_id"),
                "success": result.get("success"),
                "source": result.get("source"),
                "latency_ms": result.get("latency_ms"),
                "http_status": http_status,
            },
        )
        return Response(result, status=http_status)


# ──────────────────────────────────────────────────────────────────────────────
# Query history endpoints
# ──────────────────────────────────────────────────────────────────────────────

@extend_schema_view(
    list=extend_schema(
        summary="List query history",
        description=(
            "Returns all RAG queries submitted by the authenticated user, "
            "ordered by most recent first."
        ),
        responses={
            200: QueryHistorySerializer(many=True),
            401: OpenApiResponse(description="Authentication credentials not provided."),
        },
        tags=["RAG"],
    )
)
class QueryHistoryView(generics.ListAPIView):
    """
    List the authenticated user's RAG query history.

    Results are ordered by ``created_at`` descending (most recent first).
    Only the requesting user's own records are ever returned — there is no
    way to access another user's history through this endpoint.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = QueryHistorySerializer

    def get_queryset(self):
        logger.debug(
            "Fetching query history.",
            extra={"user_id": self.request.user.id},
        )
        return (
            QueryHistory.objects
            .filter(user=self.request.user)
            .order_by("-created_at")
        )


@extend_schema_view(
    retrieve=extend_schema(
        summary="Retrieve a single query history entry",
        description=(
            "Fetch a specific query history record by its ``id``. "
            "Returns 404 if the record does not exist or belongs to another user."
        ),
        responses={
            200: QueryHistorySerializer,
            401: OpenApiResponse(description="Authentication credentials not provided."),
            404: OpenApiResponse(description="Query history entry not found."),
        },
        tags=["RAG"],
    )
)
class QueryDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single query history entry.

    Users can only access their own records.  Attempting to fetch another
    user's record returns a 404 (not a 403) to avoid leaking the existence
    of other users' queries.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = QueryHistorySerializer
    lookup_field = "id"

    def get_queryset(self):
        logger.debug(
            "Fetching single query history entry.",
            extra={
                "user_id": self.request.user.id,
                "query_id": self.kwargs.get("id"),
            },
        )
        return QueryHistory.objects.filter(user=self.request.user)