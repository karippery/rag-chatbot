from rest_framework import serializers
import logging
from utils.get_client_ip import get_client_ip
from .models import User
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator


logger = logging.getLogger("user_activity")

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "full_name",
            "role",
            "department",
            "is_active",
            "created_at",
            "updated_at",

        )
        extra_kwargs = {"password": {"write_only": True}}

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "email",
            "full_name",
            "role",
            "department",
            "is_active",
        )
        extra_kwargs = {"password": {"write_only": True}}

        def update(self, instance, validated_data):
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            request = self.context.get("request")
            if request:
                ip = get_client_ip(request)
                logger.info(f"User updated: {instance.email} from IP: {ip}")
            return instance
        
class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self, request):
        email = self.validated_data["email"]
        opts = {
            "use_https": request.is_secure(),
            "from_email": settings.DEFAULT_FROM_EMAIL,
            "request": request,
        }
        form = PasswordResetForm(data=self.validated_data)
        if form.is_valid():
            form.save(**opts)

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        uid = attrs["uid"]
        token = attrs["token"]
        new_password = attrs["new_password"]

        try:
            uid = urlsafe_base64_decode(uid).decode()
            user = get_user_model().objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
            raise serializers.ValidationError("Invalid reset link.")

        try:
            validate_password(new_password, user=user)
        except ValidationError as e:
            raise serializers.ValidationError({"new_password": e.messages})

        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError("Invalid or expired token.")

        attrs["user"] = user
        return attrs

    def save(self):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user