from django.db import models
from django.db.models import Q
from .models import Category, MenuItem


class CategorySelector:
    """
    Selector layer - Chịu trách nhiệm truy vấn dữ liệu từ database (SELECT ONLY)
    """

    def get_category_by_id(self, category_id):
        """
        Get single category by ID (SELECT ONLY)
        """
        try:
            return Category.objects.get(id=category_id, is_active=True)
        except Category.DoesNotExist:
            return None

    def get_category_by_slug(self, restaurant_id, slug):
        """
        Get single category by restaurant and slug (SELECT ONLY)
        """
        try:
            return Category.objects.get(
                restaurant_id=restaurant_id,
                slug=slug,
                is_active=True
            )
        except Category.DoesNotExist:
            return None

    def get_categories_by_restaurant(self, restaurant_id, filters=None):
        """
        Get categories for a restaurant (SELECT ONLY)
        """
        if filters is None:
            filters = {}

        queryset = Category.objects.filter(
            restaurant_id=restaurant_id,
            is_active=True
        )

        # Apply filters - Data access logic only
        if filters.get('search'):
            search_term = filters['search']
            queryset = queryset.filter(
                Q(name__icontains=search_term) |
                Q(description__icontains=search_term)
            )

        return queryset.order_by('display_order', 'name')
    
    def get_categories_by_chain(self, chain_id, filters=None):
        """
        Get categories for a chain (SELECT ONLY)
        """
        if filters is None:
            filters = {}

        queryset = Category.objects.filter(
            chain_id=chain_id,
            is_active=True
        )

        # Apply filters
        if filters.get('search'):
            search_term = filters['search']
            queryset = queryset.filter(
                Q(name__icontains=search_term) |
                Q(description__icontains=search_term)
            )

        return queryset.order_by('display_order', 'name')
    
    def get_category_by_slug_and_chain(self, chain_id, slug):
        """
        Get single category by chain and slug (SELECT ONLY)
        """
        try:
            return Category.objects.get(
                chain_id=chain_id,
                slug=slug,
                is_active=True
            )
        except Category.DoesNotExist:
            return None

    def get_categories_with_item_count(self, restaurant_id, filters=None):
        """
        Get categories with item count (SELECT ONLY)
        """
        queryset = self.get_categories_by_restaurant(restaurant_id, filters)

        # Annotate with item count
        categories = queryset.annotate(
            item_count=models.Count('menu_items', filter=models.Q(menu_items__is_available=True))
        )

        return categories

    def check_category_name_exists(self, restaurant_id, name, exclude_id=None):
        """
        Check if category name exists for restaurant (SELECT ONLY)
        """
        queryset = Category.objects.filter(
            restaurant_id=restaurant_id,
            name=name,
            is_active=True
        )
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()

    def check_category_slug_exists(self, restaurant_id, slug, exclude_id=None):
        """
        Check if category slug exists for restaurant (SELECT ONLY)
        """
        queryset = Category.objects.filter(
            restaurant_id=restaurant_id,
            slug=slug,
            is_active=True
        )
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()

    def check_category_name_exists_by_chain(self, chain_id, name, exclude_id=None):
        """
        Check if category name exists for chain (SELECT ONLY)
        """
        queryset = Category.objects.filter(
            chain_id=chain_id,
            name=name,
            is_active=True
        )
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()

    def check_category_slug_exists_by_chain(self, chain_id, slug, exclude_id=None):
        """
        Check if category slug exists for chain (SELECT ONLY)
        """
        queryset = Category.objects.filter(
            chain_id=chain_id,
            slug=slug,
            is_active=True
        )
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()

    def count_categories(self, restaurant_id):
        """
        Count categories for restaurant (SELECT ONLY)
        """
        return Category.objects.filter(
            restaurant_id=restaurant_id,
            is_active=True
        ).count()


class MenuItemSelector:
    """
    Selector layer for MenuItem model (SELECT ONLY)
    """

    def get_menu_item_by_id(self, item_id):
        """
        Get single menu item by ID (SELECT ONLY)
        """
        try:
            return MenuItem.objects.get(id=item_id)
        except MenuItem.DoesNotExist:
            return None

    def get_menu_item_by_slug(self, restaurant_id, slug):
        """
        Get single menu item by restaurant and slug (SELECT ONLY)
        """
        try:
            return MenuItem.objects.get(
                restaurant_id=restaurant_id,
                slug=slug,
                is_available=True
            )
        except MenuItem.DoesNotExist:
            return None

    def get_menu_items_by_restaurant(self, restaurant_id, filters=None):
        """
        Get menu items for a restaurant (SELECT ONLY)
        """
        if filters is None:
            filters = {}

        queryset = MenuItem.objects.filter(
            restaurant_id=restaurant_id,
            is_available=True
        )

        # Apply filters - Data access logic only
        if filters.get('category_id'):
            queryset = queryset.filter(category_id=filters['category_id'])

        if filters.get('is_available'):
            queryset = queryset.filter(is_available=filters['is_available'])

        if filters.get('is_featured'):
            queryset = queryset.filter(is_featured=filters['is_featured'])

        if filters.get('is_vegetarian'):
            queryset = queryset.filter(is_vegetarian=filters['is_vegetarian'])

        if filters.get('is_spicy'):
            queryset = queryset.filter(is_spicy=filters['is_spicy'])

        if filters.get('min_price'):
            queryset = queryset.filter(price__gte=filters['min_price'])

        if filters.get('max_price'):
            queryset = queryset.filter(price__lte=filters['max_price'])

        if filters.get('price_range'):
            # Filter by price range categories
            price_ranges = {
                'budget': (0, 100000),
                'mid': (100000, 300000),
                'premium': (300000, 1000000),
                'luxury': (1000000, float('inf'))
            }
            range_key = filters['price_range']
            if range_key in price_ranges:
                min_price, max_price = price_ranges[range_key]
                queryset = queryset.filter(
                    price__gte=min_price,
                    price__lt=max_price
                )

        if filters.get('search'):
            search_term = filters['search']
            queryset = queryset.filter(
                Q(name__icontains=search_term) |
                Q(description__icontains=search_term)
            )

        return queryset.order_by('category__display_order', 'display_order', 'name')
    
    def get_menu_items_by_chain(self, chain_id, filters=None):
        """
        Get menu items for a chain (SELECT ONLY)
        """
        if filters is None:
            filters = {}

        queryset = MenuItem.objects.filter(
            chain_id=chain_id,
            is_available=True
        )

        # Apply filters - same as restaurant
        if filters.get('category_id'):
            queryset = queryset.filter(category_id=filters['category_id'])

        if filters.get('is_available'):
            queryset = queryset.filter(is_available=filters['is_available'])

        if filters.get('is_featured'):
            queryset = queryset.filter(is_featured=filters['is_featured'])

        if filters.get('is_vegetarian'):
            queryset = queryset.filter(is_vegetarian=filters['is_vegetarian'])

        if filters.get('is_spicy'):
            queryset = queryset.filter(is_spicy=filters['is_spicy'])

        if filters.get('min_price'):
            queryset = queryset.filter(price__gte=filters['min_price'])

        if filters.get('max_price'):
            queryset = queryset.filter(price__lte=filters['max_price'])

        if filters.get('price_range'):
            price_ranges = {
                'budget': (0, 100000),
                'mid': (100000, 300000),
                'premium': (300000, 1000000),
                'luxury': (1000000, float('inf'))
            }
            range_key = filters['price_range']
            if range_key in price_ranges:
                min_price, max_price = price_ranges[range_key]
                queryset = queryset.filter(
                    price__gte=min_price,
                    price__lt=max_price
                )

        if filters.get('search'):
            search_term = filters['search']
            queryset = queryset.filter(
                Q(name__icontains=search_term) |
                Q(description__icontains=search_term)
            )

        return queryset.order_by('category__display_order', 'display_order', 'name')
    
    def get_menu_items_by_category_and_chain(self, chain_id, category_id, filters=None):
        """
        Get menu items by category for a chain (SELECT ONLY)
        """
        if filters is None:
            filters = {}

        queryset = MenuItem.objects.filter(
            chain_id=chain_id,
            category_id=category_id,
            is_available=True
        )

        # Apply other filters
        if filters.get('is_featured'):
            queryset = queryset.filter(is_featured=filters['is_featured'])

        if filters.get('is_vegetarian'):
            queryset = queryset.filter(is_vegetarian=filters['is_vegetarian'])

        if filters.get('is_spicy'):
            queryset = queryset.filter(is_spicy=filters['is_spicy'])

        if filters.get('min_price'):
            queryset = queryset.filter(price__gte=filters['min_price'])

        if filters.get('max_price'):
            queryset = queryset.filter(price__lte=filters['max_price'])

        if filters.get('search'):
            search_term = filters['search']
            queryset = queryset.filter(
                Q(name__icontains=search_term) |
                Q(description__icontains=search_term)
            )

        return queryset.order_by('display_order', 'name')

    def get_available_menu_items(self, restaurant_id, filters=None):
        """
        Get available menu items for restaurant (SELECT ONLY)
        """
        if filters is None:
            filters = {}
        filters['is_available'] = True
        return self.get_menu_items_by_restaurant(restaurant_id, filters)

    def get_featured_menu_items(self, restaurant_id, limit=None):
        """
        Get featured menu items for restaurant (SELECT ONLY)
        """
        queryset = MenuItem.objects.filter(
            restaurant_id=restaurant_id,
            is_featured=True,
            is_available=True
        ).order_by('-rating', '-total_reviews')

        if limit:
            queryset = queryset[:limit]

        return queryset

    def get_menu_items_by_category(self, restaurant_id, category_id, filters=None):
        """
        Get menu items by category (SELECT ONLY)
        """
        if filters is None:
            filters = {}
        filters['category_id'] = category_id
        return self.get_menu_items_by_restaurant(restaurant_id, filters)

    def get_vegetarian_menu_items(self, restaurant_id, filters=None):
        """
        Get vegetarian menu items (SELECT ONLY)
        """
        if filters is None:
            filters = {}
        filters['is_vegetarian'] = True
        return self.get_menu_items_by_restaurant(restaurant_id, filters)

    def search_menu_items(self, restaurant_id, search_term, filters=None):
        """
        Search menu items (SELECT ONLY)
        """
        if filters is None:
            filters = {}
        filters['search'] = search_term
        return self.get_menu_items_by_restaurant(restaurant_id, filters)

    def get_popular_menu_items(self, restaurant_id, limit=10):
        """
        Get popular menu items based on rating and review count (SELECT ONLY)
        """
        return MenuItem.objects.filter(
            restaurant_id=restaurant_id,
            is_available=True
        ).filter(
            rating__gte=4.0,
            total_reviews__gte=5
        ).order_by('-rating', '-total_reviews')[:limit]

    def get_menu_items_on_sale(self, restaurant_id):
        """
        Get menu items that are currently on sale (SELECT ONLY)
        """
        return MenuItem.objects.filter(
            restaurant_id=restaurant_id,
            original_price__isnull=False,
            original_price__gt=models.F('price'),
            is_available=True
        ).order_by('price')

    def get_menu_items_by_price_range(self, restaurant_id, min_price, max_price):
        """
        Get menu items within price range (SELECT ONLY)
        """
        return MenuItem.objects.filter(
            restaurant_id=restaurant_id,
            price__gte=min_price,
            price__lte=max_price,
            is_available=True
        ).order_by('price')

    def get_menu_items_with_categories(self, restaurant_id, filters=None):
        """
        Get menu items grouped by categories (SELECT ONLY)
        """
        items = self.get_menu_items_by_restaurant(restaurant_id, filters)

        # Group items by category
        grouped_items = {}
        for item in items.select_related('category'):
            category_name = item.category.name if item.category else 'Uncategorized'
            if category_name not in grouped_items:
                grouped_items[category_name] = []
            grouped_items[category_name].append(item)

        return grouped_items

    def check_menu_item_name_exists(self, restaurant_id, name, exclude_id=None):
        """
        Check if menu item name exists for restaurant (SELECT ONLY)
        """
        queryset = MenuItem.objects.filter(
            restaurant_id=restaurant_id,
            name=name,
            is_available=True
        )
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()

    def check_menu_item_slug_exists(self, restaurant_id, slug, exclude_id=None):
        """
        Check if menu item slug exists for restaurant (SELECT ONLY)
        """
        queryset = MenuItem.objects.filter(
            restaurant_id=restaurant_id,
            slug=slug,
            is_available=True
        )
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()

    def check_menu_item_name_exists_by_chain(self, chain_id, name, exclude_id=None):
        """
        Check if menu item name exists for chain (SELECT ONLY)
        """
        queryset = MenuItem.objects.filter(
            chain_id=chain_id,
            name=name,
            is_available=True
        )
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()

    def check_menu_item_slug_exists_by_chain(self, chain_id, slug, exclude_id=None):
        """
        Check if menu item slug exists for chain (SELECT ONLY)
        """
        queryset = MenuItem.objects.filter(
            chain_id=chain_id,
            slug=slug,
            is_available=True
        )
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()

    def count_menu_items(self, restaurant_id, filters=None):
        """
        Count menu items for restaurant (SELECT ONLY)
        """
        queryset = MenuItem.objects.filter(
            restaurant_id=restaurant_id,
            is_available=True
        )

        if filters:
            if filters.get('is_available'):
                queryset = queryset.filter(is_available=filters['is_available'])

            if filters.get('is_featured'):
                queryset = queryset.filter(is_featured=filters['is_featured'])

            if filters.get('category_id'):
                queryset = queryset.filter(category_id=filters['category_id'])

        return queryset.count()

    def get_menu_item_stats(self, restaurant_id):
        """
        Get menu item statistics for restaurant (SELECT ONLY)
        """
        from django.db.models import Avg, Sum, Count, Min, Max

        stats = MenuItem.objects.filter(
            restaurant_id=restaurant_id,
            is_available=True
        ).aggregate(
            total_items=Count('id'),
            available_items=Count('id', filter=models.Q(is_available=True)),
            featured_items=Count('id', filter=models.Q(is_featured=True)),
            vegetarian_items=Count('id', filter=models.Q(is_vegetarian=True)),
            spicy_items=Count('id', filter=models.Q(is_spicy=True)),
            avg_price=Avg('price'),
            min_price=Min('price'),
            max_price=Max('price'),
            avg_rating=Avg('rating'),
            total_reviews=Sum('total_reviews')
        )

        return stats

    def get_price_distribution(self, restaurant_id):
        """
        Get price distribution for menu items (SELECT ONLY)
        """
        price_ranges = [
            ('budget', 0, 100000),
            ('mid', 100000, 300000),
            ('premium', 300000, 1000000),
            ('luxury', 1000000, float('inf'))
        ]

        distribution = {}
        total_count = MenuItem.objects.filter(
            restaurant_id=restaurant_id,
            is_available=True
        ).count()

        for range_name, min_price, max_price in price_ranges:
            count = MenuItem.objects.filter(
                restaurant_id=restaurant_id,
                price__gte=min_price,
                price__lt=max_price,
                is_available=True
            ).count()

            distribution[range_name] = {
                'count': count,
                'percentage': round((count / total_count * 100), 2) if total_count > 0 else 0
            }

        return distribution

    def get_menu_items_by_preparation_time(self, restaurant_id, max_minutes=None):
        """
        Get menu items by preparation time (SELECT ONLY)
        """
        queryset = MenuItem.objects.filter(
            restaurant_id=restaurant_id,
            preparation_time__isnull=False,
            is_available=True
        ).order_by('preparation_time')

        if max_minutes:
            queryset = queryset.filter(preparation_time__lte=max_minutes)

        return queryset

    def get_menu_items_by_calories(self, restaurant_id, max_calories=None):
        """
        Get menu items by calories (SELECT ONLY)
        """
        queryset = MenuItem.objects.filter(
            restaurant_id=restaurant_id,
            calories__isnull=False,
            is_available=True
        ).order_by('calories')

        if max_calories:
            queryset = queryset.filter(calories__lte=max_calories)

        return queryset