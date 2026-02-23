from django.urls import path
from . import views

urlpatterns = [
    path("v1/query/", views.QueryView.as_view(), name="rag_query"),
    path("v1/history/", views.QueryHistoryView.as_view(), name="query_history"),
    path("v1/history/<int:pk>/", views.QueryDetailView.as_view(), name="query_detail"),
]