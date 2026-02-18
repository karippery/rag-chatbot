from .base import *

# Debug
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "web", "0.0.0.0"]

INSTALLED_APPS += [
    "django_extensions",
    "drf_spectacular",
    "silk",
]

# Development middleware
MIDDLEWARE = [
    "silk.middleware.SilkyMiddleware",
] + MIDDLEWARE


# Swagger/OpenAPI settings for development
SPECTACULAR_SETTINGS = {
    "TITLE": env("APP_TITLE", default="RAG API"),
    "DESCRIPTION": env("APP_DESCRIPTION", default="APP documentation for RAG"),
    "VERSION": env("APP_VERSION", default="1.0.0"),
    "SERVE_INCLUDE_SCHEMA": False,
    'COMPONENT_SPLIT_REQUEST': True,
}


REST_FRAMEWORK.update(
    {
        "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
        "DEFAULT_RENDERER_CLASSES": [
            "rest_framework.renderers.JSONRenderer",
            "rest_framework.renderers.BrowsableAPIRenderer",  # Added, not replaced
        ],
    }
)

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Swagger/OpenAPI settings for development
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {"type": "apiKey", "name": "Authorization", "in": "header"}
    },
    "USE_SESSION_AUTH": False,
}

LOGGING["loggers"]["django.db.backends"] = {
    "handlers": ["console"],
    "level": "INFO",
    "propagate": False,
}


SILKY_PYTHON_PROFILER = True
SILKY_IGNORE_PATHS = ["/health/", "/silk/", "/admin/jsi18n/"]

CORS_ALLOWED_ORIGINS = []

# Email configuration for development
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = "localhost"
EMAIL_PORT = 25
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False
DEFAULT_FROM_EMAIL = "noreply@smartskill.local"

# This is important: Django needs a valid site for password reset links
SITE_ID = 1