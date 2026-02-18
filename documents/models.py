from django.db import models
from django.conf import settings
from pgvector.django import VectorField 


class Document(models.Model):
    """A document uploaded to the system with security classification."""

    class SecurityLevel(models.TextChoices):
        LOW       = "LOW",       "Low"
        MID       = "MID",       "Mid"
        HIGH      = "HIGH",      "High"
        VERY_HIGH = "VERY_HIGH", "Very High"

    class Status(models.TextChoices):
        PENDING    = "PENDING",    "Pending"
        PROCESSING = "PROCESSING", "Processing"
        INDEXED    = "INDEXED",    "Indexed"
        FAILED     = "FAILED",     "Failed"

    title          = models.CharField(max_length=255, unique=True)
    description    = models.TextField(blank=True)
    security_level = models.CharField(
        max_length=10,
        choices=SecurityLevel.choices,
        default=SecurityLevel.LOW,
        db_index=True,
    )
    file_type      = models.CharField(max_length=10)   # pdf, docx, txt
    file_size      = models.PositiveIntegerField(default=0)   # bytes
    minio_key      = models.CharField(max_length=512, unique=True)  # storage path
    original_name  = models.CharField(max_length=255)
    status         = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    uploaded_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_documents",
    )
    chunk_count    = models.PositiveIntegerField(default=0)
    error_message  = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes  = [
            models.Index(fields=["security_level", "status"]),
            models.Index(fields=["uploaded_by", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.title} [{self.security_level}]"
    

class DocumentChunk(models.Model):
    """A single text chunk from a document with its vector embedding."""

    document       = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    chunk_index    = models.PositiveIntegerField()  # position within document
    content        = models.TextField()
    security_level = models.CharField(
        max_length=10,
        choices=Document.SecurityLevel.choices,
        db_index=True,
    )  # Denormalized from Document for fast pre-retrieval filtering
    embedding      = VectorField(dimensions=384)  # all-MiniLM-L6-v2 output dim
    token_count    = models.PositiveIntegerField(default=0)
    
    # Optional: Add metadata fields
    metadata       = models.JSONField(default=dict, blank=True)  # Store additional chunk metadata
    is_active      = models.BooleanField(default=True)  # Soft delete or disable chunks
    
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)  # Add for tracking updates

    class Meta:
        ordering = ["document", "chunk_index"]
        indexes  = [
            models.Index(fields=["security_level"]),
            models.Index(fields=["document", "chunk_index"]),
            # Add composite index for common queries
            models.Index(fields=["security_level", "document"]),
        ]
        # Add unique constraint to prevent duplicate chunks
        unique_together = ['document', 'chunk_index']

    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.document.title}"

