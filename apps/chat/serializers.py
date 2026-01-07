"""
Serializers for Chatbot API

This module contains serializers for chatbot requests and responses,
following Django REST framework patterns.
"""

from rest_framework import serializers
from typing import Dict, Any


class ChatbotMessageSerializer(serializers.Serializer):
    """
    Serializer for sending a message to the chatbot.
    """
    message = serializers.CharField(
        max_length=2000,
        help_text="The user's message to the chatbot",
        required=True,
        allow_blank=False,
    )

    restaurant_id = serializers.IntegerField(
        help_text="ID of the restaurant context",
        required=True,
    )

    context = serializers.DictField(
        help_text="Additional context (weather, location, etc.)",
        required=False,
        child=serializers.CharField(allow_null=True),
        default={},
    )

    def validate_message(self, value):
        """Validate that message is not empty or just whitespace"""
        if not value or not value.strip():
            raise serializers.ValidationError("Message cannot be empty")
        return value.strip()

    def validate_restaurant_id(self, value):
        """Validate restaurant_id is positive"""
        if value <= 0:
            raise serializers.ValidationError("Restaurant ID must be positive")
        return value


class DishSuggestionSerializer(serializers.Serializer):
    """
    Serializer for dish suggestions in bot response.
    """
    item_id = serializers.IntegerField(help_text="ID of the menu item")
    name = serializers.CharField(help_text="Name of the dish")
    price = serializers.CharField(help_text="Price as string")
    reason = serializers.CharField(help_text="Why this dish is recommended", required=False)


class BotMessageSerializer(serializers.Serializer):
    """
    Serializer for bot response message.
    """
    id = serializers.IntegerField(help_text="Message ID", required=False)
    content = serializers.CharField(help_text="Response text content")
    message_type = serializers.ChoiceField(
        choices=['text', 'image', 'file', 'system'],
        default='text',
        help_text="Type of message"
    )
    suggestions = DishSuggestionSerializer(
        many=True,
        help_text="Suggested dishes",
        required=False,
        default=[]
    )


class ChatbotResponseSerializer(serializers.Serializer):
    """
    Serializer for chatbot API response.
    """
    bot_message = BotMessageSerializer(help_text="The bot's response message")
    intent = serializers.CharField(
        help_text="Detected intent of the user message",
        required=False,
        allow_blank=True
    )
    entities = serializers.DictField(
        help_text="Extracted entities from the message",
        required=False,
        default={}
    )
    is_escalated = serializers.BooleanField(
        help_text="Whether the conversation was escalated to human",
        default=False
    )
    confidence_score = serializers.FloatField(
        help_text="Confidence score of the intent classification",
        required=False,
        allow_null=True
    )


class ChatbotContextSerializer(serializers.Serializer):
    """
    Serializer for conversation context.
    """
    room_id = serializers.IntegerField(help_text="Chat room ID")
    user_id = serializers.IntegerField(help_text="User ID", required=False)
    conversation_state = serializers.CharField(
        help_text="Current conversation state",
        required=False,
        allow_blank=True
    )
    last_intent = serializers.CharField(
        help_text="Last detected intent",
        required=False,
        allow_blank=True
    )
    entities = serializers.DictField(
        help_text="Persistent entities",
        required=False,
        default={}
    )
    preferences = serializers.DictField(
        help_text="User preferences learned during conversation",
        required=False,
        default={}
    )


class ChatbotFeedbackSerializer(serializers.Serializer):
    """
    Serializer for submitting feedback on chatbot responses.
    """
    message_id = serializers.IntegerField(help_text="ID of the bot message")
    room_id = serializers.IntegerField(help_text="ID of the chat room")
    rating = serializers.ChoiceField(
        choices=['helpful', 'neutral', 'not_helpful'],
        help_text="Feedback rating"
    )
    comment = serializers.CharField(
        help_text="Optional comment",
        required=False,
        allow_blank=True,
        max_length=500
    )


class ChatbotConfigSerializer(serializers.Serializer):
    """
    Serializer for chatbot configuration (admin).
    """
    is_enabled = serializers.BooleanField(help_text="Whether chatbot is enabled")
    model_name = serializers.CharField(help_text="GLM model name")
    temperature = serializers.FloatField(help_text="Response temperature (0-1)")
    max_tokens = serializers.IntegerField(help_text="Maximum tokens per response")
    enable_escalation = serializers.BooleanField(
        help_text="Whether to enable escalation to human"
    )
    escalation_keywords = serializers.ListField(
        help_text="Keywords that trigger escalation",
        child=serializers.CharField(),
        required=False
    )
    enable_weather_recommendations = serializers.BooleanField(
        help_text="Whether to use weather for recommendations"
    )
    enable_personalization = serializers.BooleanField(
        help_text="Whether to use personalization"
    )


class FAQRequestSerializer(serializers.Serializer):
    """
    Serializer for FAQ requests.
    """
    question = serializers.CharField(
        max_length=500,
        help_text="The FAQ question"
    )
    restaurant_id = serializers.IntegerField(
        help_text="ID of the restaurant",
        required=False
    )
    category = serializers.ChoiceField(
        choices=['general', 'restaurant', 'menu', 'delivery', 'orders', 'payment'],
        help_text="FAQ category",
        required=False,
        default='general'
    )


class RecommendationRequestSerializer(serializers.Serializer):
    """
    Serializer for recommendation requests.
    """
    restaurant_id = serializers.IntegerField(
        help_text="ID of the restaurant",
        required=True
    )
    dietary_preferences = serializers.ListField(
        help_text="Dietary restrictions (e.g., ['vegetarian', 'gluten-free'])",
        child=serializers.CharField(),
        required=False,
        default=[]
    )
    spice_tolerance = serializers.ChoiceField(
        choices=['none', 'low', 'medium', 'high'],
        help_text="Spice tolerance level",
        required=False,
        default='medium'
    )
    max_price = serializers.FloatField(
        help_text="Maximum price per item",
        required=False,
        allow_null=True
    )
    meal_type = serializers.ChoiceField(
        choices=['breakfast', 'lunch', 'dinner', 'snack', 'any'],
        help_text="Type of meal",
        required=False,
        default='any'
    )
    num_recommendations = serializers.IntegerField(
        help_text="Number of recommendations desired",
        required=False,
        default=3,
        min_value=1,
        max_value=10
    )
    context = serializers.DictField(
        help_text="Additional context (weather, time, etc.)",
        required=False,
        default={}
    )


# ==================== Live Chat Serializers ====================

from apps.chat.models import ChatRoom, Message, OnlinePresence


class SimpleUserSerializer(serializers.Serializer):
    """Simple user serializer for chat responses."""
    id = serializers.IntegerField()
    username = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    avatar = serializers.ImageField(required=False, allow_null=True)


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages."""
    sender = SimpleUserSerializer(read_only=True)
    time_since = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'sender', 'content', 'message_type', 'attachment',
            'is_bot_response', 'is_read', 'read_at', 'created_at',
            'time_since'
        ]

    def get_time_since(self, obj):
        """Get human-readable time since message was created."""
        from django.utils import timezone
        delta = timezone.now() - obj.created_at

        if delta.seconds < 60:
            return f"{delta.seconds}s ago"
        elif delta.seconds < 3600:
            return f"{delta.seconds // 60}m ago"
        elif delta.days < 1:
            return f"{delta.seconds // 3600}h ago"
        elif delta.days < 7:
            return f"{delta.days}d ago"
        else:
            return obj.created_at.strftime('%Y-%m-%d')


class ChatRoomListSerializer(serializers.ModelSerializer):
    """Serializer for chat room list view."""
    customer_name = serializers.SerializerMethodField()
    staff_name = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True)
    last_message_preview = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            'id', 'room_number', 'room_type', 'status', 'subject',
            'customer_name', 'staff_name', 'unread_count',
            'last_message_preview', 'last_message_at',
            'created_at', 'is_active'
        ]

    def get_customer_name(self, obj):
        """Get customer display name."""
        if obj.customer:
            return obj.customer.get_full_name() or obj.customer.username
        return None

    def get_staff_name(self, obj):
        """Get staff display name."""
        if obj.staff:
            return obj.staff.get_full_name() or obj.staff.username
        return None

    def get_last_message_preview(self, obj):
        """Get preview of last message."""
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            content = last_msg.content
            return content[:50] + '...' if len(content) > 50 else content
        return None

    def get_is_active(self, obj):
        """Check if room is still active (not closed)."""
        return obj.status != 'closed'


class ChatRoomDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed chat room view with separated messages."""
    customer = SimpleUserSerializer(read_only=True)
    staff = SimpleUserSerializer(read_only=True)
    chatbot_messages = serializers.SerializerMethodField()
    live_chat_messages = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ChatRoom
        fields = [
            'id', 'room_number', 'room_type', 'status', 'subject',
            'customer', 'staff', 'chatbot_messages', 'live_chat_messages',
            'unread_count', 'order', 'reservation', 'last_message_at',
            'closed_at', 'created_at', 'updated_at'
        ]

    def get_chatbot_messages(self, obj):
        """
        Get chatbot conversation messages.
        Messages sent via chatbot API have message_type='chatbot'.
        """
        from apps.chat.models import Message
        bot_messages = obj.messages.filter(
            message_type='chatbot'
        ).order_by('created_at')
        return MessageSerializer(bot_messages, many=True).data

    def get_live_chat_messages(self, obj):
        """
        Get live chat messages (human-to-human via WebSocket).
        Messages sent via WebSocket have message_type='text'.
        """
        from apps.chat.models import Message
        live_messages = obj.messages.filter(
            message_type='text'
        ).select_related('sender').order_by('created_at')
        return MessageSerializer(live_messages, many=True).data


class CreateChatRoomSerializer(serializers.ModelSerializer):
    """Serializer for creating a new chat room."""
    room_type = serializers.ChoiceField(
        choices=ChatRoom.ROOM_TYPE_CHOICES,
        default='general'
    )
    subject = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True
    )
    order_id = serializers.IntegerField(
        write_only=True,
        required=False,
        allow_null=True
    )
    reservation_id = serializers.IntegerField(
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = ChatRoom
        fields = [
            'room_type', 'subject', 'order_id', 'reservation_id'
        ]

    def create(self, validated_data):
        """Create a new chat room for the current user."""
        from apps.orders.models import Order
        from apps.reservations.models import Reservation

        request = self.context.get('request')
        # customer is already in validated_data from perform_create() in views.py
        customer = validated_data.pop('customer', request.user)

        # Extract related objects
        order_id = validated_data.pop('order_id', None)
        reservation_id = validated_data.pop('reservation_id', None)

        # Create chat room
        room = ChatRoom.objects.create(
            customer=customer,
            **validated_data
        )

        # Link order if provided
        if order_id:
            try:
                room.order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                pass

        # Link reservation if provided
        if reservation_id:
            try:
                room.reservation = Reservation.objects.get(id=reservation_id)
            except Reservation.DoesNotExist:
                pass

        room.save()
        return room


class UpdateChatRoomSerializer(serializers.ModelSerializer):
    """Serializer for updating chat room (status, staff assignment)."""

    class Meta:
        model = ChatRoom
        fields = ['status', 'staff', 'subject']

    def validate_status(self, value):
        """Validate status transition."""
        if value == 'closed':
            # Allow closing any room
            return value
        return value


class SendMessageSerializer(serializers.Serializer):
    """Serializer for sending a message via REST API."""
    content = serializers.CharField(
        max_length=5000,
        required=True,
        allow_blank=False
    )
    message_type = serializers.ChoiceField(
        choices=Message.MESSAGE_TYPE_CHOICES,
        default='text'
    )


class MarkReadSerializer(serializers.Serializer):
    """Serializer for marking messages as read."""
    message_id = serializers.IntegerField(required=False)
    mark_all = serializers.BooleanField(default=False)


class OnlinePresenceSerializer(serializers.ModelSerializer):
    """Serializer for online presence."""
    user = SimpleUserSerializer(read_only=True)
    room_id = serializers.IntegerField(source='room.id', read_only=True)

    class Meta:
        model = OnlinePresence
        fields = ['user', 'room_id', 'is_online', 'last_seen']
