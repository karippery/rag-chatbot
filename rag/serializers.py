from rest_framework import serializers
from rag.models import Chat, QueryHistory

class QueryRequestSerializer(serializers.Serializer):
    query = serializers.CharField(
        required=True,
        max_length=2000,
        help_text="Natural language query",
    )
    mode = serializers.ChoiceField(
        choices=["quick", "detailed"],
        required=False,
        default="quick",
        help_text="'quick' uses a smaller/faster model, 'detailed' uses a larger/slower model",
    )

class ChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chat
        fields = ["id", "title", "is_deleted", "created_at", "updated_at"]
        read_only_fields = ["id", "is_deleted", "created_at", "updated_at"]

class QueryHistorySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    sources = serializers.SerializerMethodField()

    class Meta:
        model = QueryHistory
        fields = [
            "id", "query", "response", "response_source",
            "created_at", "security_level", "is_flagged", "username", "sources"
        ]
        read_only_fields = ["id", "created_at"]

    def get_sources(self, obj):
        """
        DRF calls this method to resolve the 'sources' field.
        """
        # Return the raw chunk IDs saved during the query. 
        # (Make sure 'retrieved_chunk_ids' matches the actual field name on your model)
        if hasattr(obj, 'retrieved_chunk_ids') and obj.retrieved_chunk_ids:
            return obj.retrieved_chunk_ids
        return []