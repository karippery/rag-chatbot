from django.urls import path
from . import views

urlpatterns = [

    # List all chats (GET) or Create a new chat (POST)
    path("v1/chats/", views.ChatListCreateView.as_view(), name="chat_list_create"),
    
    # Soft delete a chat (DELETE)
    path("v1/chats/<int:id>/", views.ChatDestroyView.as_view(), name="chat_destroy"),
    
    # View chat history (GET)
    path("v1/chats/<int:id>/messages/", views.ChatMessageView.as_view(), name="chat_message"),
    

    path("v1/query/", views.QueryView.as_view(), name="rag_query"),
    path("v1/history/", views.QueryHistoryView.as_view(), name="query_history"),
    path("v1/history/<int:pk>/", views.QueryDetailView.as_view(), name="query_detail"),
]