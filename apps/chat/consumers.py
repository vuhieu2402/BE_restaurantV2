"""
WebSocket consumers for realtime chat functionality.

Provides WebSocket connections for:
1. Chat rooms - real-time messaging between customers and staff
2. Online presence - track which users are currently online
"""

import json
import logging
from datetime import datetime
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.chat.models import ChatRoom, Message, OnlinePresence

logger = logging.getLogger(__name__)
User = get_user_model()


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for chat room messaging.

    Handles real-time messaging, typing indicators, and read receipts
    for a single chat room.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        try:
            # Get room ID from URL route
            self.room_id = int(self.scope['url_route']['kwargs']['room_id'])
            self.room_group_name = f'chat_{self.room_id}'
            self.user = self.scope.get('user')

            # Check if user is authenticated
            if not self.user or self.user.is_anonymous:
                await self.close(code=4001)
                return

            # Get room and verify access
            self.room = await self.get_room()
            if not self.room:
                await self.close(code=4004)
                return

            # Verify user has access to this room
            has_access = await self.verify_room_access()
            if not has_access:
                await self.close(code=4003)
                return

            # Join room group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            # Accept connection
            await self.accept()

            # Update online presence
            await self.update_presence(is_online=True)

            # Send recent messages to newly connected user
            await self.send_recent_messages()

            logger.info(f"User {self.user.id} connected to chat room {self.room_id}")

        except Exception as e:
            logger.error(f"Error in connect: {str(e)}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        try:
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

            # Update online presence
            await self.update_presence(is_online=False)

            logger.info(f"User {self.user.id} disconnected from chat room {self.room_id}")

        except Exception as e:
            logger.error(f"Error in disconnect: {str(e)}")

    async def receive_json(self, content):
        """Handle incoming JSON messages from WebSocket."""
        try:
            message_type = content.get('type')

            if message_type == 'message':
                await self.handle_message(content)
            elif message_type == 'typing':
                await self.handle_typing(content)
            elif message_type == 'read':
                await self.handle_read_receipt(content)
            else:
                await self.send_error(f"Unknown message type: {message_type}")

        except Exception as e:
            logger.error(f"Error in receive_json: {str(e)}")
            await self.send_error(str(e))

    async def handle_message(self, content):
        """Handle incoming chat message."""
        message_text = content.get('content', '').strip()

        if not message_text:
            await self.send_error("Message content is required")
            return

        # Create message in database
        message = await self.create_message(message_text)

        # Update room's last message time
        await self.update_room_last_message()

        # Get sender info
        sender_data = await self.get_user_data(self.user.id)

        # Broadcast message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': message.id,
                    'content': message.content,
                    'sender': sender_data,
                    'message_type': message.message_type,
                    'is_bot_response': message.is_bot_response,
                    'created_at': message.created_at.isoformat(),
                }
            }
        )

    async def handle_typing(self, content):
        """Handle typing indicator."""
        is_typing = content.get('is_typing', False)

        # Get sender info
        sender_data = await self.get_user_data(self.user.id)

        # Broadcast typing indicator to room
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': self.user.id,
                'username': sender_data.get('username'),
                'is_typing': is_typing
            }
        )

    async def handle_read_receipt(self, content):
        """Handle read receipt."""
        message_id = content.get('message_id')

        if message_id:
            await self.mark_messages_as_read(message_id)

            # Broadcast read receipt to room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'read_receipt',
                    'user_id': self.user.id,
                    'message_id': message_id
                }
            )

    async def chat_message(self, event):
        """Send chat message to WebSocket."""
        # Don't send back to sender
        if event['message']['sender']['id'] == self.user.id:
            return

        await self.send_json({
            'type': 'message',
            'data': event['message']
        })

    async def typing_indicator(self, event):
        """Send typing indicator to WebSocket."""
        # Don't send back to sender
        if event['user_id'] == self.user.id:
            return

        await self.send_json({
            'type': 'typing',
            'data': {
                'user_id': event['user_id'],
                'username': event.get('username'),
                'is_typing': event['is_typing']
            }
        })

    async def read_receipt(self, event):
        """Send read receipt to WebSocket."""
        await self.send_json({
            'type': 'read_receipt',
            'data': {
                'user_id': event['user_id'],
                'message_id': event.get('message_id')
            }
        })

    async def send_recent_messages(self):
        """Send recent messages to newly connected user."""
        messages = await self.get_recent_messages()

        for message in messages:
            await self.send_json({
                'type': 'message',
                'data': {
                    'id': message['id'],
                    'content': message['content'],
                    'sender': message['sender'],
                    'message_type': message['message_type'],
                    'is_bot_response': message.get('is_bot_response', False),
                    'created_at': message['created_at'],
                    'is_read': message.get('is_read', False)
                }
            })

    async def send_error(self, message):
        """Send error message to client."""
        await self.send_json({
            'type': 'error',
            'data': {'message': message}
        })

    # Database operations (sync_to_async wrappers)

    @database_sync_to_async
    def get_room(self):
        """Get chat room from database."""
        try:
            return ChatRoom.objects.get(id=self.room_id)
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def verify_room_access(self):
        """Verify user has access to this room."""
        if self.user.is_staff:
            # Staff can access all rooms
            return True

        # Customers can only access their own rooms
        return ChatRoom.objects.filter(
            id=self.room_id,
            customer=self.user
        ).exists()

    @database_sync_to_async
    def create_message(self, content):
        """Create new message in database."""
        return Message.objects.create(
            room_id=self.room_id,
            sender=self.user,
            content=content,
            message_type='text'
        )

    @database_sync_to_async
    def update_room_last_message(self):
        """Update room's last message timestamp."""
        ChatRoom.objects.filter(id=self.room_id).update(
            last_message_at=timezone.now()
        )

    @database_sync_to_async
    def update_presence(self, is_online):
        """Update user's online presence."""
        OnlinePresence.objects.update_or_create(
            user=self.user,
            room_id=self.room_id,
            defaults={
                'is_online': is_online
            }
        )

        # Clean up old offline presences
        OnlinePresence.objects.filter(
            user=self.user,
            is_online=False
        ).delete()

    @database_sync_to_async
    def get_recent_messages(self):
        """Get recent messages from room."""
        messages = Message.objects.filter(
            room_id=self.room_id
        ).select_related('sender').order_by('-created_at')[:50]

        return list({
            'id': m.id,
            'content': m.content,
            'sender': {
                'id': m.sender.id,
                'username': m.sender.username,
                'first_name': m.sender.first_name,
                'last_name': m.sender.last_name,
            },
            'message_type': m.message_type,
            'is_bot_response': m.is_bot_response,
            'created_at': m.created_at.isoformat(),
            'is_read': m.is_read
        } for m in reversed(messages))

    @database_sync_to_async
    def get_user_data(self, user_id):
        """Get user data for message."""
        try:
            user = User.objects.get(id=user_id)
            return {
                'id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        except User.DoesNotExist:
            return {'id': user_id, 'username': 'Unknown'}

    @database_sync_to_async
    def mark_messages_as_read(self, message_id):
        """Mark messages as read for current user."""
        # Mark all unread messages in this room as read (except own messages)
        Message.objects.filter(
            room_id=self.room_id
        ).exclude(
            sender=self.user
        ).update(
            is_read=True,
            read_at=timezone.now()
        )


class OnlinePresenceConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for tracking online presence.

    Broadcasts when users come online or go offline.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope.get('user')

        # Check if user is authenticated
        if not self.user or self.user.is_anonymous:
            await self.close(code=4001)
            return

        # Join presence group
        self.presence_group_name = 'online_presence'
        await self.channel_layer.group_add(
            self.presence_group_name,
            self.channel_name
        )

        # Accept connection
        await self.accept()

        # Update presence
        await self.update_presence(is_online=True)

        # Broadcast user online
        await self.broadcast_presence(True)

        logger.info(f"User {self.user.id} connected to presence")

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave presence group
        await self.channel_layer.group_discard(
            self.presence_group_name,
            self.channel_name
        )

        # Update presence
        await self.update_presence(is_online=False)

        # Broadcast user offline
        await self.broadcast_presence(False)

        logger.info(f"User {self.user.id} disconnected from presence")

    async def broadcast_presence(self, is_online):
        """Broadcast presence status to all connected users."""
        await self.channel_layer.group_send(
            self.presence_group_name,
            {
                'type': 'presence_update',
                'user_id': self.user.id,
                'username': self.user.username,
                'is_online': is_online
            }
        )

    async def presence_update(self, event):
        """Send presence update to WebSocket."""
        # Don't send back to sender
        if event['user_id'] == self.user.id:
            return

        await self.send_json({
            'type': 'presence',
            'data': {
                'user_id': event['user_id'],
                'username': event.get('username'),
                'is_online': event['is_online']
            }
        })

    @database_sync_to_async
    def update_presence(self, is_online):
        """Update user's online presence in database."""
        OnlinePresence.objects.update_or_create(
            user=self.user,
            defaults={
                'is_online': is_online
            }
        )

        # Clean up old offline presences
        OnlinePresence.objects.filter(
            user=self.user,
            is_online=False
        ).delete()
