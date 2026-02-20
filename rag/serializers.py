from rest_framework import serializers
from documents.models import Document
from rag.models import QueryHistory



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