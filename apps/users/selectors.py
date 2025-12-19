"""
User Management Selectors - Data Access Layer
- Chỉ query database
- KHÔNG business logic
- KHÔNG validation
- Chỉ có data access logic
- Caching để tăng performance
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.core.cache import cache
from .models import CustomerProfile, StaffProfile
from apps.restaurants.models import Restaurant

User = get_user_model()

# Cache timeout: 5 minutes for users, 15 minutes for lists
USER_CACHE_TIMEOUT = 300
LIST_CACHE_TIMEOUT = 900


class UserSelector:
    """Selector cho User model - chỉ query database với caching"""

    @staticmethod
    def get_user_by_id(user_id):
        """Get user by ID với caching"""
        if not user_id:
            return None

        cache_key = f"user_id_{user_id}"
        user = cache.get(cache_key)

        if user is None:
            try:
                user = User.objects.get(id=user_id, is_active=True)
                cache.set(cache_key, user, USER_CACHE_TIMEOUT)
            except User.DoesNotExist:
                cache.set(cache_key, False, USER_CACHE_TIMEOUT)  # Cache miss
                return None

        return user if user else None

    @staticmethod
    def get_user_by_email(email):
        """Get user by email với caching"""
        if not email:
            return None

        cache_key = f"user_email_{email}"
        user = cache.get(cache_key)

        if user is None:
            try:
                user = User.objects.get(email=email, is_active=True)
                cache.set(cache_key, user, USER_CACHE_TIMEOUT)
            except User.DoesNotExist:
                cache.set(cache_key, False, USER_CACHE_TIMEOUT)
                return None

        return user if user else None

    @staticmethod
    def get_user_by_phone(phone_number):
        """Get user by phone number với caching"""
        if not phone_number:
            return None

        cache_key = f"user_phone_{phone_number}"
        user = cache.get(cache_key)

        if user is None:
            try:
                user = User.objects.get(phone_number=phone_number, is_active=True)
                cache.set(cache_key, user, USER_CACHE_TIMEOUT)
            except User.DoesNotExist:
                cache.set(cache_key, False, USER_CACHE_TIMEOUT)
                return None

        return user if user else None

    @staticmethod
    def get_users_paginated(filters=None, ordering=None, page=1, page_size=20):
        """Get danh sách users với phân trang và filters"""
        queryset = User.objects.select_related(
            'customer_profile',
            'staff_profile__restaurant'
        ).all()

        # Apply filters
        if filters:
            if 'user_type' in filters:
                queryset = queryset.filter(user_type=filters['user_type'])

            if 'is_active' in filters:
                queryset = queryset.filter(is_active=filters['is_active'])

            if 'is_verified' in filters:
                queryset = queryset.filter(is_verified=filters['is_verified'])

            if 'restaurant_id' in filters:
                queryset = queryset.filter(
                    models.Q(staff_profile__restaurant_id=filters['restaurant_id']) |
                    models.Q(staff_profile__restaurant_id__in=filters.get('restaurant_id__in', []))
                )

            if 'search' in filters:
                search_term = filters['search']
                queryset = queryset.filter(
                    models.Q(username__icontains=search_term) |
                    models.Q(email__icontains=search_term) |
                    models.Q(first_name__icontains=search_term) |
                    models.Q(last_name__icontains=search_term) |
                    models.Q(phone_number__icontains=search_term)
                )

            if 'created_after' in filters:
                queryset = queryset.filter(created_at__gte=filters['created_after'])

            if 'created_before' in filters:
                queryset = queryset.filter(created_at__lte=filters['created_before'])

        # Apply ordering
        if ordering:
            valid_orderings = ['username', 'email', 'created_at', 'user_type', 'is_active']
            if ordering.lstrip('-') in valid_orderings:
                queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by('-created_at')

        # Pagination
        total_count = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size

        page_count = (total_count + page_size - 1) // page_size
        has_next = page < page_count
        has_previous = page > 1

        return {
            'items': queryset[start:end],
            'pagination': {
                'current_page': page,
                'page_size': page_size,
                'total_count': total_count,
                'page_count': page_count,
                'has_next': has_next,
                'has_previous': has_previous,
            }
        }

    @staticmethod
    def get_users_by_type(user_type, limit=100):
        """Get users theo type với limit"""
        cache_key = f"users_by_type_{user_type}_{limit}"
        users = cache.get(cache_key)

        if users is None:
            users = list(
                User.objects.filter(
                    user_type=user_type,
                    is_active=True
                ).order_by('-created_at')[:limit]
            )
            cache.set(cache_key, users, LIST_CACHE_TIMEOUT)

        return users

    @staticmethod
    def check_email_exists(email):
        """Check if email exists với caching"""
        if not email:
            return False

        cache_key = f"user_email_exists_{email}"
        exists = cache.get(cache_key)

        if exists is None:
            exists = User.objects.filter(email=email).exists()
            cache.set(cache_key, exists, USER_CACHE_TIMEOUT)

        return exists

    @staticmethod
    def check_phone_exists(phone_number):
        """Check if phone number exists với caching"""
        if not phone_number:
            return False

        cache_key = f"user_phone_exists_{phone_number}"
        exists = cache.get(cache_key)

        if exists is None:
            exists = User.objects.filter(phone_number=phone_number).exists()
            cache.set(cache_key, exists, USER_CACHE_TIMEOUT)

        return exists

    @staticmethod
    def get_user_statistics():
        """Get thống kê users"""
        cache_key = "user_statistics"
        stats = cache.get(cache_key)

        if stats is None:
            from django.utils import timezone
            from datetime import timedelta

            now = timezone.now()
            month_ago = now - timedelta(days=30)
            week_ago = now - timedelta(days=7)

            stats = {
                'total_users': User.objects.count(),
                'active_users': User.objects.filter(is_active=True).count(),
                'verified_users': User.objects.filter(is_verified=True).count(),
                'by_user_type': {
                    ut: User.objects.filter(user_type=ut).count()
                    for ut, _ in User.USER_TYPE_CHOICES
                },
                'created_this_month': User.objects.filter(created_at__gte=month_ago).count(),
                'created_this_week': User.objects.filter(created_at__gte=week_ago).count(),
                'updated_this_month': User.objects.filter(
                    updated_at__gte=month_ago
                ).count(),
            }
            cache.set(cache_key, stats, LIST_CACHE_TIMEOUT)

        return stats

    @staticmethod
    def invalidate_user_cache(user):
        """Invalidate cache cho user khi được update"""
        if user.id:
            cache.delete(f"user_id_{user.id}")
        if user.email:
            cache.delete(f"user_email_{user.email}")
            cache.delete(f"user_email_exists_{user.email}")
        if user.phone_number:
            cache.delete(f"user_phone_{user.phone_number}")
            cache.delete(f"user_phone_exists_{user.phone_number}")

        # Invalidate list caches
        cache.delete("user_statistics")
        cache.delete_many([
            f"users_by_type_{ut}_{100}"
            for ut, _ in User.USER_TYPE_CHOICES
        ])


class CustomerProfileSelector:
    """Selector cho CustomerProfile model"""

    @staticmethod
    def get_profile_by_user(user):
        """Get customer profile theo user với caching"""
        if not user or user.user_type != 'customer':
            return None

        cache_key = f"customer_profile_{user.id}"
        profile = cache.get(cache_key)

        if profile is None:
            try:
                profile = CustomerProfile.objects.get(user=user)
                cache.set(cache_key, profile, USER_CACHE_TIMEOUT)
            except CustomerProfile.DoesNotExist:
                cache.set(cache_key, False, USER_CACHE_TIMEOUT)
                return None

        return profile if profile else None

    @staticmethod
    def get_top_loyalty_customers(limit=50):
        """Get top customers theo loyalty points"""
        cache_key = f"top_loyalty_customers_{limit}"
        customers = cache.get(cache_key)

        if customers is None:
            customers = list(
                CustomerProfile.objects.select_related('user').filter(
                    user__is_active=True
                ).order_by('-loyalty_points', '-total_spent')[:limit]
            )
            cache.set(cache_key, customers, LIST_CACHE_TIMEOUT)

        return customers

    @staticmethod
    def get_customers_by_orders_count(min_orders=1, limit=100):
        """Get customers theo số lượng orders"""
        cache_key = f"customers_by_orders_{min_orders}_{limit}"
        customers = cache.get(cache_key)

        if customers is None:
            customers = list(
                CustomerProfile.objects.select_related('user').filter(
                    total_orders__gte=min_orders,
                    user__is_active=True
                ).order_by('-total_orders')[:limit]
            )
            cache.set(cache_key, customers, LIST_CACHE_TIMEOUT)

        return customers

    @staticmethod
    def get_customer_analytics():
        """Get thống kê customer analytics"""
        cache_key = "customer_analytics"
        analytics = cache.get(cache_key)

        if analytics is None:
            from django.db.models import Avg, Sum, Count, Q
            from django.utils import timezone
            from datetime import timedelta

            month_ago = timezone.now() - timedelta(days=30)

            analytics = {
                'total_customers': CustomerProfile.objects.count(),
                'active_customers': CustomerProfile.objects.filter(
                    user__is_active=True
                ).count(),
                'loyalty_stats': {
                    'total_points': CustomerProfile.objects.aggregate(
                        total=Sum('loyalty_points')
                    )['total'] or 0,
                    'average_points': CustomerProfile.objects.aggregate(
                        avg=Avg('loyalty_points')
                    )['avg'] or 0,
                    'customers_with_points': CustomerProfile.objects.filter(
                        loyalty_points__gt=0
                    ).count(),
                },
                'orders_stats': {
                    'total_orders': CustomerProfile.objects.aggregate(
                        total=Sum('total_orders')
                    )['total'] or 0,
                    'average_orders': CustomerProfile.objects.aggregate(
                        avg=Avg('total_orders')
                    )['avg'] or 0,
                    'customers_with_orders': CustomerProfile.objects.filter(
                        total_orders__gt=0
                    ).count(),
                },
                'spending_stats': {
                    'total_spent': CustomerProfile.objects.aggregate(
                        total=Sum('total_spent')
                    )['total'] or 0,
                    'average_spent': CustomerProfile.objects.aggregate(
                        avg=Avg('total_spent')
                    )['avg'] or 0,
                    'customers_with_spending': CustomerProfile.objects.filter(
                        total_spent__gt=0
                    ).count(),
                },
                'new_customers_this_month': CustomerProfile.objects.filter(
                    created_at__gte=month_ago
                ).count(),
            }
            cache.set(cache_key, analytics, LIST_CACHE_TIMEOUT)

        return analytics

    @staticmethod
    def invalidate_customer_cache(user):
        """Invalidate cache cho customer profile"""
        if user.id:
            cache.delete(f"customer_profile_{user.id}")
        cache.delete_many([
            "top_loyalty_customers_50",
            "customers_by_orders_1_100",
            "customer_analytics"
        ])


class StaffProfileSelector:
    """Selector cho StaffProfile model"""

    @staticmethod
    def get_profile_by_user(user):
        """Get staff profile theo user với caching"""
        if not user or user.user_type not in ['staff', 'manager']:
            return None

        cache_key = f"staff_profile_{user.id}"
        profile = cache.get(cache_key)

        if profile is None:
            try:
                profile = StaffProfile.objects.select_related('restaurant').get(user=user)
                cache.set(cache_key, profile, USER_CACHE_TIMEOUT)
            except StaffProfile.DoesNotExist:
                cache.set(cache_key, False, USER_CACHE_TIMEOUT)
                return None

        return profile if profile else None

    @staticmethod
    def get_staff_by_restaurant(restaurant_id, include_inactive=False):
        """Get danh sách staff theo restaurant"""
        cache_key = f"staff_by_restaurant_{restaurant_id}_{include_inactive}"
        staff = cache.get(cache_key)

        if staff is None:
            queryset = StaffProfile.objects.select_related(
                'user', 'restaurant'
            ).filter(restaurant_id=restaurant_id)

            if not include_inactive:
                queryset = queryset.filter(is_active=True)

            staff = list(queryset.order_by('position', 'hire_date'))
            cache.set(cache_key, staff, USER_CACHE_TIMEOUT)

        return staff

    @staticmethod
    def get_managers_by_restaurant(restaurant_id):
        """Get danh sách managers theo restaurant"""
        cache_key = f"managers_by_restaurant_{restaurant_id}"
        managers = cache.get(cache_key)

        if managers is None:
            managers = list(
                StaffProfile.objects.select_related('user', 'restaurant').filter(
                    restaurant_id=restaurant_id,
                    user__user_type='manager',
                    is_active=True
                ).order_by('position', 'hire_date')
            )
            cache.set(cache_key, managers, USER_CACHE_TIMEOUT)

        return managers

    @staticmethod
    def get_staff_by_position(position, limit=50):
        """Get staff theo position"""
        cache_key = f"staff_by_position_{position}_{limit}"
        staff = cache.get(cache_key)

        if staff is None:
            staff = list(
                StaffProfile.objects.select_related('user', 'restaurant').filter(
                    position__icontains=position,
                    is_active=True
                ).order_by('restaurant__name', 'position')[:limit]
            )
            cache.set(cache_key, staff, USER_CACHE_TIMEOUT)

        return staff

    @staticmethod
    def get_staff_analytics():
        """Get thống kê staff analytics"""
        cache_key = "staff_analytics"
        analytics = cache.get(cache_key)

        if analytics is None:
            from django.db.models import Avg, Sum, Count, Q
            from django.utils import timezone
            from datetime import timedelta

            month_ago = timezone.now() - timedelta(days=30)

            analytics = {
                'total_staff': StaffProfile.objects.count(),
                'active_staff': StaffProfile.objects.filter(
                    is_active=True
                ).count(),
                'by_user_type': {
                    'staff': StaffProfile.objects.filter(
                        user__user_type='staff'
                    ).count(),
                    'manager': StaffProfile.objects.filter(
                        user__user_type='manager'
                    ).count(),
                },
                'salary_stats': {
                    'total_salary_budget': StaffProfile.objects.aggregate(
                        total=Sum('salary')
                    )['total'] or 0,
                    'average_salary': StaffProfile.objects.aggregate(
                        avg=Avg('salary')
                    )['avg'] or 0,
                },
                'by_restaurant': {
                    restaurant['name']: StaffProfile.objects.filter(
                        restaurant=restaurant['id']
                    ).count()
                    for restaurant in Restaurant.objects.values('id', 'name')
                },
                'new_staff_this_month': StaffProfile.objects.filter(
                    created_at__gte=month_ago
                ).count(),
                'staff_by_position': {},
            }

            # Get staff count by position
            positions = StaffProfile.objects.values(
                'position'
            ).annotate(count=Count('id')).order_by('-count')[:10]

            analytics['staff_by_position'] = {
                pos['position']: pos['count'] for pos in positions
            }

            cache.set(cache_key, analytics, LIST_CACHE_TIMEOUT)

        return analytics

    @staticmethod
    def invalidate_staff_cache(user):
        """Invalidate cache cho staff profile"""
        if user.id:
            cache.delete(f"staff_profile_{user.id}")
        # Invalidate staff lists - could be optimized with better keys
        cache.delete_many([
            f"staff_by_restaurant_*_{False}",
            f"managers_by_restaurant_*",
            "staff_analytics"
        ])