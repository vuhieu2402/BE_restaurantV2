from django.db import models
from django.db.models import Q
from .models import Restaurant, RestaurantChain, Table


class RestaurantChainSelector:
    """
    Selector layer for RestaurantChain (SELECT ONLY)
    """
    
    def get_chain_by_id(self, chain_id):
        """Get single chain by ID"""
        try:
            return RestaurantChain.objects.get(id=chain_id, is_active=True)
        except RestaurantChain.DoesNotExist:
            return None
    
    def get_chain_by_slug(self, slug):
        """Get single chain by slug"""
        try:
            return RestaurantChain.objects.get(slug=slug, is_active=True)
        except RestaurantChain.DoesNotExist:
            return None
    
    def get_active_chains(self, filters=None):
        """Get active chains with filters"""
        if filters is None:
            filters = {}
        
        queryset = RestaurantChain.objects.filter(is_active=True)
        
        if filters.get('search'):
            search_term = filters['search']
            queryset = queryset.filter(
                Q(name__icontains=search_term) |
                Q(description__icontains=search_term)
            )
        
        return queryset.order_by('name')
    
    def get_chain_branches(self, chain_id, filters=None):
        """Get all branches of a chain"""
        if filters is None:
            filters = {}
        
        queryset = Restaurant.objects.filter(
            chain_id=chain_id,
            is_active=True
        )
        
        if filters.get('city'):
            queryset = queryset.filter(city__icontains=filters['city'])
        
        if filters.get('is_open'):
            queryset = queryset.filter(is_open=filters['is_open'])
        
        return queryset.order_by('name')
    
    def check_slug_exists(self, slug, exclude_id=None):
        """Check if slug exists"""
        queryset = RestaurantChain.objects.filter(slug=slug, is_active=True)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()


class RestaurantSelector:
    """
    Selector layer - Chịu trách nhiệm truy vấn dữ liệu từ database (SELECT ONLY)
    """

    def get_restaurant_by_id(self, restaurant_id):
        """
        Get single restaurant by ID (SELECT ONLY)
        """
        try:
            return Restaurant.objects.get(id=restaurant_id, is_active=True)
        except Restaurant.DoesNotExist:
            return None

    def get_restaurant_by_slug(self, slug):
        """
        Get single restaurant by slug (SELECT ONLY)
        """
        try:
            return Restaurant.objects.get(slug=slug, is_active=True)
        except Restaurant.DoesNotExist:
            return None

    def get_active_restaurants(self, filters=None):
        """
        Get active restaurants with filters (SELECT ONLY)
        """
        if filters is None:
            filters = {}

        queryset = Restaurant.objects.filter(is_active=True)

        # Apply filters - Data access logic only
        if filters.get('city'):
            queryset = queryset.filter(city__icontains=filters['city'])

        if filters.get('district'):
            queryset = queryset.filter(district__icontains=filters['district'])

        if filters.get('is_open'):
            queryset = queryset.filter(is_open=filters['is_open'])

        if filters.get('min_rating'):
            queryset = queryset.filter(rating__gte=filters['min_rating'])

        if filters.get('search'):
            search_term = filters['search']
            queryset = queryset.filter(
                Q(name__icontains=search_term) |
                Q(description__icontains=search_term) |
                Q(address__icontains=search_term)
            )

        return queryset.order_by('-created_at')

    def get_nearby_restaurants(self, latitude, longitude, radius_km=5):
        """
        Get restaurants within radius from coordinates (SELECT ONLY)
        """
        # Using rough distance calculation for filtering
        lat_delta = radius_km / 111.0  # ~1 degree latitude = 111km
        lon_delta = radius_km / (111.0 * abs(latitude)) if latitude else radius_km / 111.0

        return Restaurant.objects.filter(
            is_active=True,
            is_open=True,
            latitude__gte=float(latitude) - lat_delta,
            latitude__lte=float(latitude) + lat_delta,
            longitude__gte=float(longitude) - lon_delta,
            longitude__lte=float(longitude) + lon_delta
        ).order_by('-rating', '-created_at')

    def get_restaurants_by_manager(self, manager_id):
        """
        Get restaurants managed by specific user (SELECT ONLY)
        """
        return Restaurant.objects.filter(
            manager_id=manager_id,
            is_active=True
        ).order_by('name')

    def check_restaurant_exists(self, name):
        """
        Check if restaurant exists by name (SELECT ONLY)
        """
        return Restaurant.objects.filter(name=name, is_active=True).exists()

    def check_slug_exists(self, slug, exclude_id=None):
        """
        Check if slug exists (SELECT ONLY)
        """
        queryset = Restaurant.objects.filter(slug=slug, is_active=True)
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()

    def count_restaurants(self, filters=None):
        """
        Count restaurants with filters (SELECT ONLY)
        """
        queryset = self.get_active_restaurants(filters)
        return queryset.count()


class TableSelector:
    """
    Selector layer for Table model (SELECT ONLY)
    """

    def get_tables_by_restaurant(self, restaurant_id, filters=None):
        """
        Get tables for a restaurant (SELECT ONLY)
        """
        if filters is None:
            filters = {}

        queryset = Table.objects.filter(
            restaurant_id=restaurant_id,
            is_active=True
        )

        # Apply filters - Data access logic only
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])

        if filters.get('floor'):
            queryset = queryset.filter(floor=filters['floor'])

        if filters.get('section'):
            queryset = queryset.filter(section__icontains=filters['section'])

        if filters.get('min_capacity'):
            queryset = queryset.filter(capacity__gte=filters['min_capacity'])

        return queryset.order_by('floor', 'table_number')

    def get_table_by_id(self, table_id):
        """
        Get single table by ID (SELECT ONLY)
        """
        try:
            return Table.objects.get(id=table_id, is_active=True)
        except Table.DoesNotExist:
            return None

    def get_available_tables(self, restaurant_id, capacity=None):
        """
        Get available tables for restaurant (SELECT ONLY)
        """
        queryset = Table.objects.filter(
            restaurant_id=restaurant_id,
            status='available',
            is_active=True
        )

        if capacity:
            queryset = queryset.filter(capacity__gte=capacity)

        return queryset.order_by('capacity', 'table_number')

    def get_tables_by_numbers(self, restaurant_id, table_numbers):
        """
        Get multiple tables by their numbers (SELECT ONLY)
        """
        return Table.objects.filter(
            restaurant_id=restaurant_id,
            table_number__in=table_numbers,
            is_active=True
        )

    def check_table_number_exists(self, restaurant_id, table_number, exclude_id=None):
        """
        Check if table number exists for restaurant (SELECT ONLY)
        """
        queryset = Table.objects.filter(
            restaurant_id=restaurant_id,
            table_number=table_number,
            is_active=True
        )
        if exclude_id:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()

    def count_tables(self, restaurant_id, filters=None):
        """
        Count tables with filters (SELECT ONLY)
        """
        queryset = Table.objects.filter(
            restaurant_id=restaurant_id,
            is_active=True
        )

        if filters and filters.get('status'):
            queryset = queryset.filter(status=filters['status'])

        return queryset.count()