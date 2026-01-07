"""
Selectors for Chatbot Data Retrieval

This module contains selector classes for retrieving data from the database
for use by the chatbot. Following the existing selector pattern in the codebase.
"""

from typing import Dict, Any, List, Optional
from django.db.models import Q, Prefetch
from django.core.cache import cache
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class ChatbotSelector:
    """
    Selector class for retrieving chatbot-related data from the database.

    This class provides methods to fetch restaurant information, menu data,
    customer preferences, and conversation history efficiently.
    """

    @staticmethod
    def get_restaurant_context(restaurant_id: int) -> Optional[Dict[str, Any]]:
        """
        Get restaurant information for chatbot context.

        Args:
            restaurant_id: ID of the restaurant

        Returns:
            dict: Restaurant context data or None if not found
        """
        from apps.restaurants.models import Restaurant

        cache_key = f'restaurant:info:{restaurant_id}'

        # Try cache first
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.debug(f"Restaurant info cache hit for restaurant {restaurant_id}")
            return cached_data

        try:
            restaurant = Restaurant.objects.filter(
                id=restaurant_id,
                is_active=True
            ).first()

            if not restaurant:
                logger.warning(f"Restaurant {restaurant_id} not found or inactive")
                return None

            # Prepare context data
            context = {
                'id': restaurant.id,
                'name': restaurant.name,
                'slug': restaurant.slug,
                'description': restaurant.description,
                'phone_number': restaurant.phone_number,
                'email': restaurant.email,
                'address': restaurant.address,
                'city': restaurant.city,
                'district': restaurant.district,
                'ward': restaurant.ward,
                'postal_code': restaurant.postal_code,
                'latitude': str(restaurant.latitude) if restaurant.latitude else None,
                'longitude': str(restaurant.longitude) if restaurant.longitude else None,
                'opening_time': restaurant.opening_time.strftime('%H:%M') if restaurant.opening_time else None,
                'closing_time': restaurant.closing_time.strftime('%H:%M') if restaurant.closing_time else None,
                'is_open': restaurant.is_open,
                'rating': float(restaurant.rating) if restaurant.rating else 0,
                'total_reviews': restaurant.total_reviews,
                'minimum_order': float(restaurant.minimum_order) if restaurant.minimum_order else 0,
                'delivery_fee': float(restaurant.delivery_fee) if restaurant.delivery_fee else 0,
                'delivery_radius': float(restaurant.delivery_radius) if restaurant.delivery_radius else 0,
            }

            # Cache for 24 hours
            cache.set(cache_key, context, timeout=86400)
            logger.debug(f"Retrieved and cached restaurant info for {restaurant_id}")

            return context

        except Exception as e:
            logger.error(f"Error retrieving restaurant context: {str(e)}")
            return None

    @staticmethod
    def get_menu_summary(restaurant_id: int) -> Optional[Dict[str, Any]]:
        """
        Get menu summary for a restaurant.

        For restaurants in a chain, this returns the chain's menu.
        For independent restaurants, this returns the restaurant's menu.

        Args:
            restaurant_id: ID of the restaurant

        Returns:
            dict: Menu summary with categories and featured items
        """
        from apps.dishes.models import Category, MenuItem
        from apps.restaurants.models import Restaurant

        cache_key = f'menu:restaurant:{restaurant_id}'

        # Try cache first
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.debug(f"Menu summary cache hit for restaurant {restaurant_id}")
            return cached_data

        try:
            # Get restaurant to check if it's in a chain
            restaurant = Restaurant.objects.filter(id=restaurant_id).first()
            if not restaurant:
                logger.warning(f"Restaurant {restaurant_id} not found")
                return None

            # Determine if restaurant is in a chain
            chain_id = restaurant.chain_id if restaurant.chain else None

            # Get active categories (from chain if exists, otherwise from restaurant)
            if chain_id:
                categories = Category.objects.filter(
                    chain_id=chain_id,
                    is_active=True
                ).order_by('display_order', 'name').values('id', 'name', 'slug', 'description')
            else:
                categories = Category.objects.filter(
                    restaurant_id=restaurant_id,
                    is_active=True
                ).order_by('display_order', 'name').values('id', 'name', 'slug', 'description')

            category_list = list(categories)

            # Get featured items (from chain if exists, otherwise from restaurant)
            if chain_id:
                featured_items = MenuItem.objects.filter(
                    chain_id=chain_id,
                    is_available=True,
                    is_featured=True
                ).order_by('-rating', '-total_reviews', 'display_order')[:10]
            else:
                featured_items = MenuItem.objects.filter(
                    restaurant_id=restaurant_id,
                    is_available=True,
                    is_featured=True
                ).order_by('-rating', '-total_reviews', 'display_order')[:10]

            featured_list = []
            for item in featured_items:
                featured_list.append({
                    'id': item.id,
                    'name': item.name,
                    'slug': item.slug,
                    'description': item.description,
                    'price': float(item.price),
                    'original_price': float(item.original_price) if item.original_price else None,
                    'category': item.category.name if item.category else None,
                    'calories': item.calories,
                    'preparation_time': item.preparation_time,
                    'rating': float(item.rating) if item.rating else 0,
                    'total_reviews': item.total_reviews,
                    'is_vegetarian': item.is_vegetarian,
                    'is_spicy': item.is_spicy,
                    'is_featured': item.is_featured,
                    'image': item.image.url if item.image else None,
                })

            # Get category item counts
            category_counts = {}
            for category in category_list:
                if chain_id:
                    count = MenuItem.objects.filter(
                        chain_id=chain_id,
                        category_id=category['id'],
                        is_available=True
                    ).count()
                else:
                    count = MenuItem.objects.filter(
                        restaurant_id=restaurant_id,
                        category_id=category['id'],
                        is_available=True
                    ).count()
                category_counts[category['id']] = count

            # Get total items count
            if chain_id:
                total_items = MenuItem.objects.filter(
                    chain_id=chain_id,
                    is_available=True
                ).count()
            else:
                total_items = MenuItem.objects.filter(
                    restaurant_id=restaurant_id,
                    is_available=True
                ).count()

            summary = {
                'categories': [cat['name'] for cat in category_list],
                'category_details': category_list,
                'category_counts': category_counts,
                'featured_items': featured_list,
                'total_items': total_items,
            }

            # Cache for 1 hour
            cache.set(cache_key, summary, timeout=3600)
            logger.debug(f"Retrieved and cached menu summary for restaurant {restaurant_id} (chain: {chain_id})")

            return summary

        except Exception as e:
            logger.error(f"Error retrieving menu summary: {str(e)}")
            return None

    @staticmethod
    def get_customer_preferences(customer_id: int) -> Dict[str, Any]:
        """
        Get customer preferences based on order history.

        Args:
            customer_id: ID of the customer

        Returns:
            dict: Customer preference data
        """
        from apps.users.models import User, CustomerProfile
        from apps.orders.models import Order, OrderItem
        from apps.dishes.models import MenuItem

        cache_key = f'customer:preferences:{customer_id}'

        # Try cache first
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.debug(f"Customer preferences cache hit for customer {customer_id}")
            return cached_data

        try:
            user = User.objects.filter(id=customer_id).first()
            if not user:
                return {}

            # Get customer profile
            customer_profile = CustomerProfile.objects.filter(user_id=customer_id).first()

            # Get order history
            orders = Order.objects.filter(
                customer_id=customer_id
            ).exclude(
                status__in=['cancelled', 'refunded']
            ).prefetch_related('items').order_by('-created_at')[:20]

            # Analyze preferences
            dietary_restrictions = []
            favorite_categories = []
            spice_tolerance = 'medium'  # Default

            total_orders = orders.count()
            total_spent = sum(float(order.total) for order in orders if order.total)
            average_order_value = total_spent / total_orders if total_orders > 0 else 0

            # Get ordered items
            ordered_items = []
            for order in orders:
                for item in order.items.all():
                    menu_item = item.menu_item
                    if menu_item:
                        ordered_items.append(menu_item)

                        # Collect dietary info
                        if menu_item.is_vegetarian and 'vegetarian' not in dietary_restrictions:
                            dietary_restrictions.append('vegetarian')

                        # Get categories
                        if menu_item.category and menu_item.category.name not in favorite_categories:
                            favorite_categories.append(menu_item.category.name)

                        # Determine spice tolerance
                        if menu_item.is_spicy:
                            spicy_count = sum(1 for item in ordered_items if item.is_spicy)
                            total_count = len(ordered_items)
                            if spicy_count / total_count > 0.6:
                                spice_tolerance = 'high'
                            elif spicy_count / total_count > 0.3:
                                spice_tolerance = 'medium'
                            else:
                                spice_tolerance = 'low'

            preferences = {
                'customer_id': customer_id,
                'username': user.username,
                'dietary_restrictions': dietary_restrictions if dietary_restrictions else ['none'],
                'favorite_categories': favorite_categories if favorite_categories else ['various'],
                'spice_tolerance': spice_tolerance,
                'total_orders': total_orders,
                'total_spent': float(total_spent) if total_spent else 0,
                'average_order_value': float(average_order_value) if average_order_value else 0,
                'preferred_language': customer_profile.preferred_language if customer_profile else 'vi',
                'receive_promotions': customer_profile.receive_promotions if customer_profile else True,
            }

            # Cache for 6 hours
            cache.set(cache_key, preferences, timeout=21600)
            logger.debug(f"Retrieved and cached customer preferences for {customer_id}")

            return preferences

        except Exception as e:
            logger.error(f"Error retrieving customer preferences: {str(e)}")
            return {}

    @staticmethod
    def get_conversation_history(room_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent conversation history for context.

        Args:
            room_id: ID of the chat room
            limit: Maximum number of messages to retrieve

        Returns:
            list: List of message dictionaries
        """
        from apps.chat.models import Message

        try:
            messages = Message.objects.filter(
                room_id=room_id
            ).select_related(
                'sender'
            ).order_by('-created_at')[:limit]

            # Reverse to get chronological order
            messages = list(reversed(messages))

            history = []
            for msg in messages:
                history.append({
                    'role': 'assistant' if msg.is_bot_response else 'user',
                    'content': msg.content,
                    'timestamp': msg.created_at.isoformat(),
                })

            logger.debug(f"Retrieved {len(history)} messages for room {room_id}")
            return history

        except Exception as e:
            logger.error(f"Error retrieving conversation history: {str(e)}")
            return []

    @staticmethod
    def get_dish_by_name_or_id(restaurant_id: int, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific dish by name or ID.

        For restaurants in a chain, searches in the chain's menu.
        For independent restaurants, searches in the restaurant's menu.

        Args:
            restaurant_id: ID of the restaurant
            identifier: Dish name or ID

        Returns:
            dict: Dish information or None
        """
        from apps.dishes.models import MenuItem
        from apps.restaurants.models import Restaurant

        try:
            # Get restaurant to check if it's in a chain
            restaurant = Restaurant.objects.filter(id=restaurant_id).first()
            if not restaurant:
                return None

            chain_id = restaurant.chain_id if restaurant.chain else None

            # Try to find by ID first
            if identifier.isdigit():
                if chain_id:
                    dish = MenuItem.objects.filter(
                        id=int(identifier),
                        chain_id=chain_id,
                        is_available=True
                    ).first()
                else:
                    dish = MenuItem.objects.filter(
                        id=int(identifier),
                        restaurant_id=restaurant_id,
                        is_available=True
                    ).first()
            else:
                # Try to find by name (case-insensitive partial match)
                if chain_id:
                    dish = MenuItem.objects.filter(
                        chain_id=chain_id,
                        name__icontains=identifier,
                        is_available=True
                    ).first()
                else:
                    dish = MenuItem.objects.filter(
                        restaurant_id=restaurant_id,
                        name__icontains=identifier,
                        is_available=True
                    ).first()

            if not dish:
                return None

            return {
                'id': dish.id,
                'name': dish.name,
                'slug': dish.slug,
                'description': dish.description,
                'price': float(dish.price),
                'original_price': float(dish.original_price) if dish.original_price else None,
                'category': dish.category.name if dish.category else None,
                'category_id': dish.category_id,
                'calories': dish.calories,
                'preparation_time': dish.preparation_time,
                'rating': float(dish.rating) if dish.rating else 0,
                'total_reviews': dish.total_reviews,
                'is_vegetarian': dish.is_vegetarian,
                'is_spicy': dish.is_spicy,
                'is_featured': dish.is_featured,
                'image': dish.image.url if dish.image else None,
            }

        except Exception as e:
            logger.error(f"Error retrieving dish: {str(e)}")
            return None

    @staticmethod
    def search_menu_items(
        restaurant_id: int,
        query: Optional[str] = None,
        is_vegetarian: Optional[bool] = None,
        is_spicy: Optional[bool] = None,
        category_id: Optional[int] = None,
        max_price: Optional[float] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search menu items with filters.

        For restaurants in a chain, searches in the chain's menu.
        For independent restaurants, searches in the restaurant's menu.

        Args:
            restaurant_id: ID of the restaurant
            query: Search query for dish name or description
            is_vegetarian: Filter by vegetarian status
            is_spicy: Filter by spicy status
            category_id: Filter by category
            max_price: Maximum price
            limit: Maximum results

        Returns:
            list: List of matching dishes
        """
        from apps.dishes.models import MenuItem
        from apps.restaurants.models import Restaurant

        try:
            # Get restaurant to check if it's in a chain
            restaurant = Restaurant.objects.filter(id=restaurant_id).first()
            if not restaurant:
                return []

            chain_id = restaurant.chain_id if restaurant.chain else None

            # Build base queryset
            if chain_id:
                queryset = MenuItem.objects.filter(
                    chain_id=chain_id,
                    is_available=True
                )
            else:
                queryset = MenuItem.objects.filter(
                    restaurant_id=restaurant_id,
                    is_available=True
                )

            # Apply filters
            if query:
                queryset = queryset.filter(
                    Q(name__icontains=query) |
                    Q(description__icontains=query)
                )

            if is_vegetarian is not None:
                queryset = queryset.filter(is_vegetarian=is_vegetarian)

            if is_spicy is not None:
                queryset = queryset.filter(is_spicy=is_spicy)

            if category_id:
                queryset = queryset.filter(category_id=category_id)

            if max_price:
                queryset = queryset.filter(price__lte=max_price)

            # Order by rating and popularity
            queryset = queryset.order_by('-rating', '-total_reviews', 'display_order')[:limit]

            items = []
            for item in queryset:
                items.append({
                    'id': item.id,
                    'name': item.name,
                    'description': item.description,
                    'price': float(item.price),
                    'category': item.category.name if item.category else None,
                    'rating': float(item.rating) if item.rating else 0,
                    'is_vegetarian': item.is_vegetarian,
                    'is_spicy': item.is_spicy,
                    'calories': item.calories,
                })

            logger.debug(f"Found {len(items)} items matching search criteria")
            return items

        except Exception as e:
            logger.error(f"Error searching menu items: {str(e)}")
            return []

    @staticmethod
    def clear_cache(restaurant_id: Optional[int] = None, customer_id: Optional[int] = None):
        """
        Clear relevant caches.

        Args:
            restaurant_id: Restaurant ID to clear caches for
            customer_id: Customer ID to clear caches for
        """
        if restaurant_id:
            cache.delete(f'restaurant:info:{restaurant_id}')
            cache.delete(f'menu:restaurant:{restaurant_id}')
            logger.info(f"Cleared caches for restaurant {restaurant_id}")

        if customer_id:
            cache.delete(f'customer:preferences:{customer_id}')
            logger.info(f"Cleared cache for customer {customer_id}")
