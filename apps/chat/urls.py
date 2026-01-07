"""
URL configuration for chat app

This module defines URL patterns for chat and chatbot-related endpoints.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.chat import views

app_name = 'chat'

# Create router for ViewSet
router = DefaultRouter()
router.register(r'rooms', views.ChatRoomViewSet, basename='chatroom')

urlpatterns = [
    # ==================== Chatbot endpoints ====================
    path('chatbot/rooms/<int:room_id>/message/',
         views.ChatbotMessageView.as_view(),
         name='chatbot-message'),

    path('chatbot/rooms/<int:room_id>/context/',
         views.ChatbotContextView.as_view(),
         name='chatbot-context'),

    path('chatbot/feedback/',
         views.ChatbotFeedbackView.as_view(),
         name='chatbot-feedback'),

    # ==================== Live Chat endpoints ====================
    # Online staff
    path('online-staff/',
         views.OnlineStaffView.as_view(),
         name='online-staff'),

    # Active rooms for staff dashboard
    path('active-rooms/',
         views.ActiveRoomsView.as_view(),
         name='active-rooms'),

    # Include router endpoints (rooms CRUD)
    path('', include(router.urls)),
]
