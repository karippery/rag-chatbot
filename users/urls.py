from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

urlpatterns = [
    path("v1/users/", views.UserListCreateView.as_view(), name="user-list-create"),
    path("v1/users/<int:pk>/", views.UserDetailView.as_view(), name="user-detail"),
    # Authentication
    path("v1/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    # refresh token
    path(
        "v1/token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),
    # Password Reset Flow (DRF-style, no templates)
    path(
        "v1/password-reset/",
        views.PasswordResetRequestView.as_view(),
        name="password-reset",
    ),
    path(
        "v1/password-reset-confirm/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "v1/password-reset-confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm_api",
    ),
]