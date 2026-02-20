from django.urls import path
from . import views

urlpatterns = [
    path("query/", views.QueryView.as_view(), name="rag_query"),
    path("history/", views.QueryHistoryView.as_view(), name="query_history"),
    path("history/<int:pk>/", views.QueryDetailView.as_view(), name="query_detail"),
]