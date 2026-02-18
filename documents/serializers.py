from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.ReadOnlyField(source="uploaded_by.email")
    uploaded_by_role  = serializers.ReadOnlyField(source="uploaded_by.role")

    class Meta:
        model  = Document
        fields = [
            "id", "title", "description", "security_level", "file_type",
            "file_size", "original_name", "status", "chunk_count",
            "error_message", "uploaded_by_email", "uploaded_by_role",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "file_type", "file_size", "original_name", "status",
            "chunk_count", "error_message", "uploaded_by_email",
            "uploaded_by_role", "created_at", "updated_at",
        ]

class DocumentUploadSerializer(serializers.Serializer):
    # Input fields
    file = serializers.FileField(write_only=True)
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    security_level = serializers.ChoiceField(choices=Document.SecurityLevel.choices)

    # Output fields (read_only)
    id = serializers.IntegerField(read_only=True)
    minio_key = serializers.CharField(read_only=True)
    file_type = serializers.CharField(read_only=True)
    file_size = serializers.IntegerField(read_only=True)
    original_name = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    uploaded_at = serializers.DateTimeField(read_only=True)

    def validate_file(self, value):
        """Validate file type and size."""
        allowed_types = {"pdf", "docx", "txt", "doc"}
        ext = value.name.rsplit(".", 1)[-1].lower() if "." in value.name else ""
        
        if ext not in allowed_types:
            raise serializers.ValidationError(
                f"Unsupported file type '{ext}'. Allowed: {', '.join(allowed_types)}"
            )
        
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File too large. Max size is 50MB, got {value.size / 1024 / 1024:.1f}MB"
            )
        
        # Store the extension in validated_data for later use
        self.context['file_extension'] = ext
        return value
    
    def validate_title(self, value):
        """Validate that the title is unique."""
        if Document.objects.filter(title=value).exists():
            raise serializers.ValidationError(
                f"A document with title '{value}' already exists."
            )
        return value

    def create(self, validated_data, **kwargs):
        """
        Create Document instance with data from validated_data and kwargs.
        """

        # Create the database record by merging validated_data and kwargs
        document = Document.objects.create(
            # From validated_data (user-provided)
            title=validated_data['title'],  # Use [] since it's required
            description=validated_data.get('description', ''),
            security_level=validated_data['security_level'],
            
            # From kwargs (system-generated) - these should all be present
            minio_key=validated_data['minio_key'],  # Now accessed from validated_data
            file_type=validated_data['file_type'],
            file_size=validated_data['file_size'],
            original_name=validated_data['original_name'],
            uploaded_by=validated_data.get('uploaded_by'),
            status=validated_data.get('status', Document.Status.PENDING),
        )
        return document