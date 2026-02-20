from rest_framework import generics, permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from django.db import transaction
import logging

from .serializers import DocumentSerializer, DocumentUploadSerializer
from .models import Document
from .services.storage import MinIOService
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from .tasks import index_document_task

logger = logging.getLogger("document_activity")


class DocumentUploadView(generics.CreateAPIView):
    """
    Upload a document to MinIO.
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]
    serializer_class = DocumentUploadSerializer

    @extend_schema(
        request=DocumentUploadSerializer,
        responses={201: DocumentUploadSerializer},
        tags=["Documents"],
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)
    
    @transaction.atomic
    def perform_create(self, serializer):
        """
        Handle document upload workflow:
        1. Extract metadata
        2. Upload to MinIO
        3. Save to database
        4. Schedule async indexing (only after DB commit)
        
        Wrapped in @transaction.atomic to ensure consistency.
        """
        file = serializer.validated_data["file"]
        security_level = serializer.validated_data["security_level"]
        object_name = None
        
        try:
            # ── 1. Process File Metadata ──────────────────────────────
            file_name = file.name
            file_extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else "bin"
            
            # ── 2. Upload to MinIO ────────────────────────────────────
            object_name = MinIOService.generate_object_key(
                title=serializer.validated_data['title'],
                security_level=security_level,
                file_extension=file_extension,
            )
            MinIOService.upload_file(
                file_object=file,
                object_name=object_name,
                content_type=file.content_type,
            )

            # ── 3. Save to Database ───────────────────────────────────
            document = serializer.save(
                minio_key=object_name,
                file_type=file_extension,
                file_size=file.size,
                original_name=file_name,
                uploaded_by=self.request.user if self.request.user.is_authenticated else None,
                status=Document.Status.PENDING,
            )

            logger.info(
                "Document uploaded to MinIO and DB",
                extra={
                    "document_id": document.id,
                    "minio_key": object_name,
                    "user_id": getattr(self.request.user, 'id', None),
                }
            )

            # ── 4. Schedule Async Indexing (Post-Commit) ─────────────
            # ✅ Task runs ONLY if the DB transaction succeeds
            transaction.on_commit(lambda: index_document_task.delay(document.id))

        except Exception as e:
            # ── 5. Cleanup on Failure ─────────────────────────────────
            if object_name:
                logger.warning(
                    f"DB save failed. Cleaning up orphaned MinIO file: {object_name}",
                    extra={"error": str(e)}
                )
                try:
                    MinIOService.delete_file(object_name)
                except Exception as cleanup_err:
                    logger.error(
                        f"Failed to clean up MinIO file {object_name}: {cleanup_err}",
                        exc_info=True
                    )
            
            logger.error(
                f"Document upload failed: {str(e)}",
                exc_info=True,
                extra={
                    "file_name": file_name,
                    "user_id": getattr(self.request.user, 'id', None),
                }
            )
            raise  # Re-raise for DRF to handle and return error response
        
    def create(self, request, *args, **kwargs):
        """
        Simplified create method - delegates to perform_create for business logic.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        return Response(
            {
                "message": "Document uploaded successfully. Indexing in progress.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


class DocumentDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [AllowAny]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        user = self.request.user
        return Document.objects.all()

    def perform_destroy(self, instance):
        user = self.request.user

        instance.delete()
        logger.info(f"Document deleted successfully: {instance.minio_key}")


class DocumentListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = DocumentSerializer

    def get_queryset(self):
        return Document.objects.all().order_by("-created_at")

class DocumentDownloadView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = DocumentSerializer
    lookup_field = "id"

    def get_queryset(self):
        queryset = Document.objects.all()
            
        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            url = MinIOService.get_presigned_url(
                    instance.minio_key, 
                    expires_seconds=settings.MINIO_PRESIGNED_URL_EXPIRY
                )
            return Response({
                "download_url": url, 
                "expires_in": settings.MINIO_PRESIGNED_URL_EXPIRY,
                "file_name": instance.original_name
            })
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            