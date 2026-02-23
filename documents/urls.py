from django.urls import path
from . import views

urlpatterns = [
    path("v1/documents/",                       views.DocumentListView.as_view(),   name="document_list"),
    path("v1/upload/",                views.DocumentUploadView.as_view(), name="document_upload"),
    path("v1/<int:pk>/",              views.DocumentDetailView.as_view(), name="document_detail"),
    path("v1/<int:pk>/download/",     views.DocumentDownloadView.as_view(),
                         name="document_download"),
]