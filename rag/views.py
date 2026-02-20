from rest_framework import generics, permissions, status
from rest_framework.response import Response

from documents.models import Document
from rag.models import QueryHistory
from .serializers import QueryRequestSerializer, QueryHistorySerializer
from .services import rag_query_service
from rag.services.rag_query_service import rag_query_service

RESPONSE_MODE_MODELS = {
    "quick":    "Qwen/Qwen2-0.5B-Instruct",    # fast, less detail
    "detailed": "Qwen/Qwen2.5-1.5B-Instruct",  # slower, better answers
}


class QueryView(generics.GenericAPIView):
    """
    Main RAG query endpoint.
    Security level is derived from the authenticated user's role — not user input.
    Mode (quick/detailed) selects which LLM model is used.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = QueryRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        mode = serializer.validated_data.get("mode", "quick")
        model_name = RESPONSE_MODE_MODELS[mode]

        try:
            result = rag_query_service.query(
                query_text=serializer.validated_data["query"],
                user=request.user,
                security_level=self._get_security_level(request.user),
                model_name=model_name,
            )

            status_code = status.HTTP_200_OK if result["success"] else status.HTTP_500_INTERNAL_SERVER_ERROR
            return Response(result, status=status_code)

        except Exception as e:
            return Response(
                {"error": "Internal server error", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _get_security_level(self, user) -> str:
        if user.groups.filter(name="admin").exists():
            return Document.SecurityLevel.HIGH
        if user.groups.filter(name="manager").exists():
            return Document.SecurityLevel.MID
        return Document.SecurityLevel.LOW

class QueryHistoryView(generics.ListAPIView):
    """
    Returns the authenticated user's query history.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = QueryHistorySerializer

    def get_queryset(self):
        # Only return history for the logged-in user
        return QueryHistory.objects.filter(user=self.request.user).order_by('-created_at')
    
class QueryDetailView(generics.RetrieveAPIView):
    """
    Retrieve details of a specific query history entry.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = QueryHistorySerializer
    queryset = QueryHistory.objects.all()
    lookup_field = 'id'

    def get_queryset(self):
        # Ensure users can only retrieve their own history
        return QueryHistory.objects.filter(user=self.request.user)