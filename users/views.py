import logging
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    CreateAPIView,
)
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated

from utils.get_client_ip import get_client_ip
from .models import User
from .serializers import (
    UserSerializer,
    UserUpdateSerializer,
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
)
from common.pagination import DefaultPagination
from django.conf import settings
from .permissions import IsAdminOrManager
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

logger = logging.getLogger("user_activity")



class UserListCreateView(ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = DefaultPagination
    permission_classes = [IsAuthenticated, IsAdminOrManager]
    ordering = ["-created_at"]

    def get_permissions(self):
        if self.request.method == "POST":
            return [AllowAny()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save()
        ip = get_client_ip(self.request)
        logger.info(f"New user created: {serializer.instance.email} from IP: {ip}")


class UserDetailView(RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return UserUpdateSerializer
        return UserSerializer

class PasswordResetRequestView(CreateAPIView):
    serializer_class = PasswordResetSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)  # ← DRF standard
        serializer.save(request=request)
        response_data = {"detail": "Password reset email sent."}
        if settings.DEBUG:
            email = serializer.validated_data.get("email")
            if email:
                try:
                    user = User.objects.get(email=email)
                    if user.is_active:
                        uid = urlsafe_base64_encode(force_bytes(user.pk))
                        token = default_token_generator.make_token(user)
                        # Use your actual frontend dev URL, or Django's default
                        reset_url = (
                            f"http://127.0.0.1:8000/api/users/v1/"
                            f"password-reset-confirm/{uid}/{token}/"
                        )
                        logger.info(f"[DEV] Password reset link: {reset_url}")
                        response_data.update(
                            {
                                "uid": uid,
                                "token": token,
                                "reset_url": reset_url,  # optional, for convenience
                            }
                        )
                except User.DoesNotExist:
                    pass  # Silent failure — never confirm email existence

        return Response(response_data, status=status.HTTP_200_OK)


class PasswordResetConfirmView(CreateAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"detail": "Password has been reset."}, status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)