"""
WebSocket consumers for order notifications.

Provides WebSocket connections for:
1. Order notifications - real-time notifications for new orders
2. Order updates - real-time updates when order status changes
"""

import json
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class OrderNotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for order notifications.

    Handles real-time notifications for:
    - New orders
    - Order status updates
    - Order assignments

    Staff members automatically subscribe to their restaurant's notifications.
    Admins subscribe to all restaurant notifications.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        try:
            self.user = self.scope.get('user')

            if not self.user or self.user.is_anonymous:
                await self.close(code=4001)
                return

            if not self.user.is_staff_member:
                await self.close(code=4003)
                return

            # Tự động subscribe dựa trên user type
            await self.auto_subscribe()

            await self.accept()

            logger.info(f"User {self.user.id} ({self.user.user_type}) connected to order notifications")

        except Exception as e:
            logger.error(f"Error in connect: {str(e)}")
            await self.close(code=4000)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        try:
            # Unsubscribe từ tất cả các groups
            if hasattr(self, 'restaurant_groups'):
                for group_name in self.restaurant_groups:
                    await self.channel_layer.group_discard(
                        group_name,
                        self.channel_name
                    )

            logger.info(f"User {self.user.id} disconnected from order notifications")

        except Exception as e:
            logger.error(f"Error in disconnect: {str(e)}")

    async def auto_subscribe(self):
        """Tự động subscribe nhân viên vào các restaurant liên quan."""
        self.restaurant_groups = []

        # Admin subscribe vào tất cả restaurants
        if self.user.user_type == 'admin':
            self.restaurant_groups.append('orders_all')
            await self.channel_layer.group_add(
                'orders_all',
                self.channel_name
            )
            logger.info(f"Admin {self.user.id} subscribed to all orders")
        else:
            # Staff/Manager subscribe vào restaurant của họ
            staff_profile = await self.get_staff_profile()
            if staff_profile and staff_profile.restaurant:
                restaurant_id = staff_profile.restaurant.id
                group_name = f'orders_restaurant_{restaurant_id}'
                self.restaurant_groups.append(group_name)
                
                await self.channel_layer.group_add(
                    group_name,
                    self.channel_name
                )
                
                logger.info(f"Staff {self.user.id} subscribed to restaurant {restaurant_id}")
            else:
                # Nếu không có restaurant, subscribe vào all
                self.restaurant_groups.append('orders_all')
                await self.channel_layer.group_add(
                    'orders_all',
                    self.channel_name
                )
                logger.info(f"Staff {self.user.id} (no restaurant) subscribed to all orders")

    async def receive_json(self, content):
        """Handle incoming JSON messages from WebSocket."""
        try:
            message_type = content.get('type')

            if message_type == 'subscribe':
                await self.handle_subscribe(content)
            elif message_type == 'unsubscribe':
                await self.handle_unsubscribe(content)
            else:
                await self.send_error(f"Unknown message type: {message_type}")

        except Exception as e:
            logger.error(f"Error in receive_json: {str(e)}")
            await self.send_error(str(e))

    async def handle_subscribe(self, content):
        """Handle subscription to specific restaurant (cho admin)."""
        if self.user.user_type != 'admin':
            await self.send_error("Only admins can manually subscribe to restaurants")
            return

        restaurant_id = content.get('restaurant_id')

        if restaurant_id:
            new_group_name = f'orders_restaurant_{restaurant_id}'

            if new_group_name not in self.restaurant_groups:
                await self.channel_layer.group_add(
                    new_group_name,
                    self.channel_name
                )

                self.restaurant_groups.append(new_group_name)

                await self.send_json({
                    'type': 'subscribed',
                    'data': {
                        'restaurant_id': restaurant_id
                    }
                })

                logger.info(f"Admin {self.user.id} manually subscribed to restaurant {restaurant_id}")

    async def handle_unsubscribe(self, content):
        """Handle unsubscription from specific restaurant."""
        restaurant_id = content.get('restaurant_id')

        if restaurant_id:
            group_name = f'orders_restaurant_{restaurant_id}'

            if group_name in self.restaurant_groups:
                await self.channel_layer.group_discard(
                    group_name,
                    self.channel_name
                )

                self.restaurant_groups.remove(group_name)

                await self.send_json({
                    'type': 'unsubscribed',
                    'data': {
                        'restaurant_id': restaurant_id
                    }
                })

                logger.info(f"User {self.user.id} unsubscribed from restaurant {restaurant_id}")

    async def new_order(self, event):
        """Send new order notification to WebSocket."""
        await self.send_json({
            'type': 'new_order',
            'data': event['order']
        })

    async def order_updated(self, event):
        """Send order update notification to WebSocket."""
        await self.send_json({
            'type': 'order_updated',
            'data': event['order']
        })

    async def order_assigned(self, event):
        """Send order assignment notification to WebSocket."""
        await self.send_json({
            'type': 'order_assigned',
            'data': event['order']
        })

    async def send_error(self, message):
        """Send error message to client."""
        await self.send_json({
            'type': 'error',
            'data': {'message': message}
        })

    @database_sync_to_async
    def get_staff_profile(self):
        """Get staff profile from database."""
        try:
            return self.user.staff_profile
        except:
            return None
