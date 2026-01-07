import logging
from typing import Dict, Any, Optional
from rest_framework.views import APIView
from rest_framework import permissions, status, throttling
from rest_framework.decorators import action
from django.utils import timezone
from django.db import transaction

from apps.api.mixins import StandardResponseMixin
from apps.chat.models import ChatRoom, Message
from apps.chat.services import get_chatbot_service
from apps.chat.selectors import ChatbotSelector
from apps.chat.serializers import (
    ChatbotMessageSerializer,
    ChatbotResponseSerializer,
    ChatbotContextSerializer,
    ChatbotFeedbackSerializer,
)
from apps.chat.throttling import (
    ChatbotBurstRateThrottle,
    ChatbotSustainedRateThrottle,
    ChatbotFeedbackThrottle,
    PerRoomRateThrottle,
)

logger = logging.getLogger(__name__)


class ChatbotMessageView(StandardResponseMixin, APIView):
    """
    API View for handling chatbot messages.

    POST /api/chat/chatbot/rooms/{room_id}/message/
    """

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [
        PerRoomRateThrottle,
        ChatbotBurstRateThrottle,
        ChatbotSustainedRateThrottle,
    ]

    def post(self, request, room_id):
        """
        Process a user message and generate a chatbot response.

        Request Body:
        {
            "message": "What do you recommend for lunch?",
            "restaurant_id": 1,
            "context": {
                "weather": {"temp": 28, "condition": "sunny"}
            }
        }

        Response:
        {
            "success": true,
            "data": {
                "bot_message": {...},
                "intent": "recommendation",
                "is_escalated": false
            }
        }
        """
        try:
            # Validate request data
            serializer = ChatbotMessageSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error_response(
                    message="Validation failed",
                    errors=serializer.errors
                )

            validated_data = serializer.validated_data
            user_message = validated_data['message']
            restaurant_id = validated_data['restaurant_id']
            user_context = validated_data.get('context', {})

            # Get chat room
            try:
                room = ChatRoom.objects.get(id=room_id, customer=request.user)
            except ChatRoom.DoesNotExist:
                return self.not_found_response(
                    message="Chat room not found"
                )

            # Save user message (mark as chatbot type)
            user_msg = Message.objects.create(
                room=room,
                sender=request.user,
                message_type='chatbot',
                content=user_message,
            )

            # Process with ChatbotService (Phase 2: GLM-powered)
            chatbot_service = get_chatbot_service()
            result = chatbot_service.process_message(
                user_message=user_message,
                room_id=room_id,
                user_id=request.user.id,
                restaurant_id=restaurant_id,
                additional_context=user_context,
            )

            # Save bot message (mark as chatbot type)
            bot_msg = Message.objects.create(
                room=room,
                sender_id=request.user.id,  # Bot messages use system user
                message_type='chatbot',
                content=result.response_content,
                is_bot_response=True,
                intent=result.intent,
                entities=result.entities,
                confidence_score=result.confidence,
            )

            # Update room's last message time
            room.last_message_at = timezone.now()

            # Update status if escalated
            if result.is_escalated:
                room.status = 'waiting'

            room.save()

            # Prepare response
            response_data = {
                'bot_message': {
                    'id': bot_msg.id,
                    'content': bot_msg.content,
                    'message_type': bot_msg.message_type,
                    'suggestions': result.suggestions,
                },
                'intent': result.intent,
                'entities': result.entities,
                'is_escalated': result.is_escalated,
                'confidence_score': result.confidence,
            }

            return self.success_response(
                data=response_data,
                message="Chatbot response generated"
            )

        except Exception as e:
            logger.error(f"Error processing chatbot message: {str(e)}", exc_info=True)
            return self.error_response(
                message="Failed to process message",
                errors=str(e)
            )


class ChatbotContextView(StandardResponseMixin, APIView):
    """
    API View for managing conversation context.

    GET /api/chat/chatbot/rooms/{room_id}/context/
    PUT /api/chat/chatbot/rooms/{room_id}/context/
    """

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ChatbotBurstRateThrottle]  # Lighter throttling for GET requests

    def get(self, request, room_id):
        """Get conversation context for a room"""
        try:
            room = ChatRoom.objects.get(id=room_id, customer=request.user)

            # Get conversation history
            history = ChatbotSelector.get_conversation_history(room_id, limit=10)

            context_data = {
                'room_id': room.id,
                'user_id': request.user.id,
                'conversation_history': history,
                'room_status': room.status,
                'room_type': room.room_type,
            }

            return self.success_response(
                data=context_data,
                message="Context retrieved successfully"
            )

        except ChatRoom.DoesNotExist:
            return self.not_found_response(message="Chat room not found")

    def put(self, request, room_id):
        """Update conversation context (for future use)"""
        # This will be implemented in Phase 2 with Redis context management
        return self.success_response(
            message="Context update will be available in Phase 2"
        )


class ChatbotFeedbackView(StandardResponseMixin, APIView):
    """
    API View for submitting feedback on chatbot responses.

    POST /api/chat/chatbot/feedback/
    """

    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ChatbotFeedbackThrottle]

    def post(self, request):
        """Submit feedback on a chatbot response"""
        try:
            serializer = ChatbotFeedbackSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error_response(
                    message="Validation failed",
                    errors=serializer.errors
                )

            validated_data = serializer.validated_data

            # For now, just log the feedback
            # In Phase 2, we'll save this to a feedback model
            logger.info(
                f"Chatbot feedback received: "
                f"message_id={validated_data['message_id']}, "
                f"rating={validated_data['rating']}"
            )

            return self.success_response(
                message="Thank you for your feedback!"
            )

        except Exception as e:
            logger.error(f"Error submitting feedback: {str(e)}")
            return self.error_response(
                message="Failed to submit feedback",
                errors=str(e)
            )


# ==================== Live Chat Views ====================

from rest_framework import viewsets, status, pagination
from rest_framework.decorators import action
from django.utils import timezone
from django.db.models import Q, Count, F
from django.shortcuts import get_object_or_404

from apps.chat.serializers import (
    ChatRoomListSerializer,
    ChatRoomDetailSerializer,
    CreateChatRoomSerializer,
    UpdateChatRoomSerializer,
    SendMessageSerializer,
    MarkReadSerializer,
    OnlinePresenceSerializer,
)


class ChatRoomViewSet(StandardResponseMixin, viewsets.ModelViewSet):
    """
    ViewSet for managing chat rooms.

    - Customers can only see their own rooms
    - Staff can see all rooms
    """
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None  # Use default from REST_FRAMEWORK settings

    @property
    def paginator(self):
        """Override to use custom paginator with our response format."""
        if self.pagination_class is None:
            self.pagination_class = pagination.PageNumberPagination
        return super().paginator

    def get_queryset(self):
        """Return appropriate queryset based on user type."""
        user = self.request.user

        if user.is_staff:
            # Staff can see all rooms, excluding closed ones by default
            queryset = ChatRoom.objects.all().select_related(
                'customer', 'staff'
            ).prefetch_related('messages')
        else:
            # Customers can only see their own rooms
            queryset = ChatRoom.objects.filter(
                customer=user
            ).select_related('staff').prefetch_related('messages')

        # Filter by status if provided
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-last_message_at', '-created_at')

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'create':
            return CreateChatRoomSerializer
        elif self.action == 'update' or self.action == 'partial_update':
            return UpdateChatRoomSerializer
        elif self.action == 'retrieve':
            return ChatRoomDetailSerializer
        return ChatRoomListSerializer

    def perform_create(self, serializer):
        """Set customer as current user when creating room."""
        serializer.save(customer=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        """Get detailed chat room with messages."""
        room = self.get_object()

        # Verify access
        if not request.user.is_staff and room.customer != request.user:
            return self.permission_denied(request)

        serializer = ChatRoomDetailSerializer(room)
        return self.success_response(
            data=serializer.data,
            message="Chat room retrieved successfully"
        )

    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get only active (not closed) chat rooms.

        Query parameters:
        - page: Page number (default: 1)
        - page_size: Items per page (default: 20)
        """
        queryset = self.get_queryset().filter(status__in=['active', 'waiting'])

        # Paginate results using the paginator property
        page = self.paginator.paginate_queryset(queryset, request)

        if page is not None:
            serializer = ChatRoomListSerializer(page, many=True)
            return self.success_response(
                data={
                    'rooms': serializer.data,
                    'total': self.paginator.page.paginator.count,
                    'page': request.query_params.get('page', 1),
                    'page_size': self.paginator.page.paginator.per_page,
                    'total_pages': self.paginator.page.paginator.num_pages
                },
                message="Active rooms retrieved successfully"
            )

        # Fallback if pagination is disabled
        serializer = ChatRoomListSerializer(queryset, many=True)
        return self.success_response(
            data={'rooms': serializer.data, 'total': queryset.count()},
            message="Active rooms retrieved successfully"
        )

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """
        Staff joins a chat room.

        POST /api/chat/rooms/{id}/join/
        """
        room = self.get_object()

        # Only staff can join rooms
        if not request.user.is_staff:
            return self.error_response(
                message="Only staff can join rooms",
                errors={"permission": "Staff access required"}
            )

        # Assign staff to room
        room.staff = request.user
        room.status = 'active'
        room.save()

        # Create system message
        Message.objects.create(
            room=room,
            sender=request.user,
            message_type='system',
            content=f"Staff {request.user.get_full_name() or request.user.username} joined the chat."
        )

        return self.success_response(
            message="Joined room successfully"
        )

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """
        Staff leaves a chat room.

        POST /api/chat/rooms/{id}/leave/
        """
        room = self.get_object()

        # Only staff can leave rooms
        if not request.user.is_staff:
            return self.error_response(
                message="Only staff can leave rooms"
            )

        # Remove staff assignment
        room.staff = None
        room.status = 'waiting'
        room.save()

        # Create system message
        Message.objects.create(
            room=room,
            sender=request.user,
            message_type='system',
            content=f"Staff {request.user.get_full_name() or request.user.username} left the chat."
        )

        return self.success_response(
            message="Left room successfully"
        )

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """
        Close a chat room.

        POST /api/chat/rooms/{id}/close/
        """
        room = self.get_object()

        # Verify access
        if not request.user.is_staff and room.customer != request.user:
            return self.error_response(
                message="You don't have permission to close this room"
            )

        # Close the room
        room.status = 'closed'
        room.closed_at = timezone.now()
        room.save()

        return self.success_response(
            message="Room closed successfully"
        )

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """
        Get messages from a chat room, separated into chatbot and live chat.

        GET /api/chat/rooms/{id}/messages/?limit=50&before=<message_id>

        Classification:
        - chatbot: message_type='chatbot' (from REST API /chatbot/)
        - live_chat: message_type='text' (from WebSocket)
        """
        room = self.get_object()

        # Verify access
        if not request.user.is_staff and room.customer != request.user:
            return self.error_response(
                message="You don't have permission to view messages in this room"
            )

        # Get query parameters
        limit = int(request.query_params.get('limit', 50))
        before_id = request.query_params.get('before')

        # Build base queryset
        queryset = Message.objects.filter(room=room).select_related('sender')

        if before_id:
            queryset = queryset.filter(id__lt=before_id)

        # Separate by message_type
        bot_messages = queryset.filter(
            message_type='chatbot'
        ).order_by('-created_at')[:limit]

        live_messages = queryset.filter(
            message_type='text'
        ).order_by('-created_at')[:limit]

        # Reverse to get chronological order
        bot_messages = list(reversed(bot_messages))
        live_messages = list(reversed(live_messages))

        # Serialize
        from apps.chat.serializers import MessageSerializer
        bot_serializer = MessageSerializer(bot_messages, many=True)
        live_serializer = MessageSerializer(live_messages, many=True)

        return self.success_response(
            data={
                'chatbot_messages': bot_serializer.data,
                'live_chat_messages': live_serializer.data,
                'total_bot_messages': len(bot_serializer.data),
                'total_live_messages': len(live_serializer.data)
            },
            message=f"Retrieved {len(bot_serializer.data)} bot messages and {len(live_serializer.data)} live messages"
        )

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """
        Send a message via REST API (alternative to WebSocket).

        POST /api/chat/rooms/{id}/send_message/
        """
        room = self.get_object()

        # Verify access
        if not request.user.is_staff and room.customer != request.user:
            return self.error_response(
                message="You don't have permission to send messages in this room"
            )

        # Validate request
        serializer = SendMessageSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation failed",
                errors=serializer.errors
            )

        # Create message
        message = Message.objects.create(
            room=room,
            sender=request.user,
            content=serializer.validated_data['content'],
            message_type=serializer.validated_data.get('message_type', 'text')
        )

        # Update room
        room.last_message_at = timezone.now()
        room.save()

        # Return created message
        from apps.chat.serializers import MessageSerializer
        response_serializer = MessageSerializer(message)

        return self.success_response(
            data=response_serializer.data,
            message="Message sent successfully"
        )

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark messages as read.

        POST /api/chat/rooms/{id}/mark_read/
        Body: {"mark_all": true} or {"message_id": 123}
        """
        room = self.get_object()

        # Verify access
        if not request.user.is_staff and room.customer != request.user:
            return self.error_response(
                message="You don't have permission to mark messages in this room"
            )

        # Validate request
        serializer = MarkReadSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation failed",
                errors=serializer.errors
            )

        data = serializer.validated_data

        if data.get('mark_all'):
            # Mark all unread messages as read
            count = Message.objects.filter(
                room=room,
                is_read=False
            ).exclude(sender=request.user).update(
                is_read=True,
                read_at=timezone.now()
            )
            return self.success_response(
                data={'marked_count': count},
                message=f"Marked {count} messages as read"
            )
        elif data.get('message_id'):
            # Mark specific message as read
            try:
                message = Message.objects.get(
                    room=room,
                    id=data['message_id']
                )
                message.mark_as_read()
                return self.success_response(
                    message="Message marked as read"
                )
            except Message.DoesNotExist:
                return self.error_response(
                    message="Message not found"
                )

        return self.error_response(
            message="Either mark_all or message_id is required"
        )


class OnlineStaffView(StandardResponseMixin, APIView):
    """
    API View for getting online staff members.

    GET /api/chat/online-staff/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get list of online staff members."""
        from apps.users.models import User

        # Get staff users who are online
        online_staff = User.objects.filter(
            is_staff=True,
            online_presences__is_online=True
        ).distinct().select_related('online_presences')

        # Prepare response
        staff_data = []
        for staff in online_staff:
            # Get active rooms for this staff
            active_rooms = ChatRoom.objects.filter(
                Q(staff=staff) | Q(status__in=['active', 'waiting']),
                status__in=['active', 'waiting']
            ).count()

            staff_data.append({
                'id': staff.id,
                'username': staff.username,
                'first_name': staff.first_name,
                'last_name': staff.last_name,
                'full_name': staff.get_full_name(),
                'avatar': staff.avatar.url if staff.avatar else None,
                'active_chats': active_rooms
            })

        return self.success_response(
            data=staff_data,
            message="Online staff retrieved successfully"
        )


class ActiveRoomsView(StandardResponseMixin, APIView):
    """
    API View for staff to see all active rooms.

    GET /api/chat/active-rooms/
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """
        Get all active chat rooms (for staff dashboard).

        Query parameters:
        - status: Filter by status (active, waiting, closed)
        - room_type: Filter by room type
        """
        # Only staff can access
        if not request.user.is_staff:
            return self.error_response(
                message="Only staff can view all active rooms"
            )

        # Build queryset
        queryset = ChatRoom.objects.all().select_related(
            'customer', 'staff'
        ).prefetch_related('messages')

        # Apply filters
        status_filter = request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        else:
            # Exclude closed by default
            queryset = queryset.filter(status__in=['active', 'waiting'])

        room_type = request.query_params.get('room_type')
        if room_type:
            queryset = queryset.filter(room_type=room_type)

        # Annotate with unread count for staff
        queryset = queryset.annotate(
            unread_count=Count('messages', filter=Q(messages__is_read=False))
        )

        # Order by last message, then by created date
        queryset = queryset.order_by('-last_message_at', '-created_at')

        # Paginate
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))

        start = (page - 1) * page_size
        end = start + page_size

        rooms = queryset[start:end]
        total = queryset.count()

        # Serialize
        serializer = ChatRoomListSerializer(rooms, many=True)

        return self.success_response(
            data={
                'rooms': serializer.data,
                'total': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size
            },
            message="Active rooms retrieved successfully"
        )
