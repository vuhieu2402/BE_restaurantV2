"""
Analytics Selectors - Data Access Layer
- Query database for orders, revenue, customer, and reservation analytics
- Use Django ORM aggregation with date truncation
- No business logic, no caching (real-time data)
"""
from datetime import timedelta
from django.db import models
from django.db.models import Sum, Count, Q, F, DecimalField, Avg
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.contrib.auth import get_user_model
from apps.orders.models import Order
from apps.reservations.models import Reservation

User = get_user_model()


class AnalyticsSelector:
    """Selector cho analytics - database queries only"""

    @staticmethod
    def get_orders_by_date_range(start_date, end_date, group_by='day', status_filter=None):
        """
        Get orders grouped by date within range

        Args:
            start_date: datetime start of range
            end_date: datetime end of range
            group_by: 'day', 'week', or 'month'
            status_filter: optional order status to filter

        Returns:
            QuerySet with annotated date, count, and revenue per period
        """
        # Determine trunc function based on group_by
        trunc_func = {
            'day': TruncDay('created_at'),
            'week': TruncWeek('created_at'),
            'month': TruncMonth('created_at'),
        }.get(group_by, TruncDay('created_at'))

        # Build base queryset
        queryset = Order.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )

        # Apply status filter if provided
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Annotate with date period and aggregate
        queryset = queryset.annotate(
            period=trunc_func
        ).values(
            'period'
        ).annotate(
            count=Count('id'),
            revenue=Sum(F('total'), output_field=DecimalField())
        ).order_by('period')

        return list(queryset)

    @staticmethod
    def get_revenue_by_date_range(start_date, end_date, group_by='day'):
        """
        Get revenue grouped by date within range

        Args:
            start_date: datetime start of range
            end_date: datetime end of range
            group_by: 'day', 'week', or 'month'

        Returns:
            QuerySet with annotated date, revenue, and order count per period
        """
        # Determine trunc function based on group_by
        trunc_func = {
            'day': TruncDay('created_at'),
            'week': TruncWeek('created_at'),
            'month': TruncMonth('created_at'),
        }.get(group_by, TruncDay('created_at'))

        # Only include completed orders for revenue
        queryset = Order.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date,
            status__in=['completed', 'confirmed']  # Only count confirmed/completed revenue
        )

        # Annotate with date period and aggregate
        queryset = queryset.annotate(
            period=trunc_func
        ).values(
            'period'
        ).annotate(
            revenue=Sum(F('total'), output_field=DecimalField()),
            order_count=Count('id')
        ).order_by('period')

        return list(queryset)

    @staticmethod
    def get_new_customers_by_date_range(start_date, end_date, group_by='day'):
        """
        Get new customer registrations grouped by date within range

        Args:
            start_date: datetime start of range
            end_date: datetime end of range
            group_by: 'day', 'week', or 'month'

        Returns:
            QuerySet with annotated date and count per period
        """
        # Determine trunc function based on group_by
        trunc_func = {
            'day': TruncDay('created_at'),
            'week': TruncWeek('created_at'),
            'month': TruncMonth('created_at'),
        }.get(group_by, TruncDay('created_at'))

        # Filter for customers only
        queryset = User.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date,
            user_type='customer'
        )

        # Annotate with date period and aggregate
        queryset = queryset.annotate(
            period=trunc_func
        ).values(
            'period'
        ).annotate(
            count=Count('id')
        ).order_by('period')

        return list(queryset)

    @staticmethod
    def get_orders_summary(start_date, end_date, status_filter=None):
        """
        Get summary statistics for orders within range

        Args:
            start_date: datetime start of range
            end_date: datetime end of range
            status_filter: optional order status

        Returns:
            Dict with total_orders and total_revenue
        """
        queryset = Order.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        result = queryset.aggregate(
            total_orders=Count('id'),
            total_revenue=Sum(F('total'), output_field=DecimalField())
        )

        return {
            'total_orders': result['total_orders'] or 0,
            'total_revenue': result['total_revenue'] or 0
        }

    @staticmethod
    def get_revenue_summary(start_date, end_date):
        """
        Get summary statistics for revenue within range

        Args:
            start_date: datetime start of range
            end_date: datetime end of range

        Returns:
            Dict with total_revenue and order_count
        """
        result = Order.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date,
            status__in=['completed', 'confirmed']
        ).aggregate(
            total_revenue=Sum(F('total'), output_field=DecimalField()),
            order_count=Count('id')
        )

        return {
            'total_revenue': result['total_revenue'] or 0,
            'order_count': result['order_count'] or 0
        }

    @staticmethod
    def get_new_customers_summary(start_date, end_date):
        """
        Get summary statistics for new customers within range

        Args:
            start_date: datetime start of range
            end_date: datetime end of range

        Returns:
            Dict with total_new_customers
        """
        count = User.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date,
            user_type='customer'
        ).count()

        return {'total_new_customers': count}

    @staticmethod
    def get_previous_period_revenue(start_date, end_date):
        """
        Get revenue for previous period (for growth rate calculation)

        Args:
            start_date: datetime start of current range
            end_date: datetime end of current range

        Returns:
            Total revenue for previous period of same duration
        """
        days_diff = (end_date - start_date).days + 1
        prev_end = start_date - timedelta(days=1)
        prev_start = prev_end - timedelta(days=days_diff - 1)

        result = Order.objects.filter(
            created_at__gte=prev_start,
            created_at__lte=prev_end,
            status__in=['completed', 'confirmed']
        ).aggregate(
            total_revenue=Sum(F('total'), output_field=DecimalField())
        )

        return result['total_revenue'] or 0

    # ==================== RESERVATION ANALYTICS ====================

    @staticmethod
    def get_reservations_by_date_range(start_date, end_date, group_by='day', status_filter=None):
        """
        Get reservations grouped by date within range

        Args:
            start_date: datetime start of range
            end_date: datetime end of range
            group_by: 'day', 'week', or 'month'
            status_filter: optional reservation status

        Returns:
            List with date, count, total_guests per period
        """
        # For reservations, we use reservation_date (not created_at)
        # So we need to filter differently and convert to datetime for comparison
        start_date_only = start_date.date() if hasattr(start_date, 'date') else start_date
        end_date_only = end_date.date() if hasattr(end_date, 'date') else end_date

        # Build base queryset - filter by reservation_date
        queryset = Reservation.objects.filter(
            reservation_date__gte=start_date_only,
            reservation_date__lte=end_date_only
        )

        # Apply status filter if provided
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Group by reservation_date (not created_at)
        # For week/month grouping on date field, we need to use Cast or annotate differently
        # For simplicity, let's use database-specific date extraction

        if group_by == 'day':
            # Group by reservation_date directly
            result = queryset.values('reservation_date').annotate(
                count=Count('id'),
                total_guests=Sum('number_of_guests')
            ).order_by('reservation_date')

            # Convert to expected format with 'period' key
            return [
                {
                    'period': item['reservation_date'],
                    'count': item['count'],
                    'total_guests': item['total_guests'] or 0
                }
                for item in result
            ]

        elif group_by == 'week':
            # Group by week - extract year and week number
            result = queryset.annotate(
                period=models.functions.TruncWeek('reservation_date')
            ).values('period').annotate(
                count=Count('id'),
                total_guests=Sum('number_of_guests')
            ).order_by('period')

            return list(result)

        else:  # month
            # Group by month
            result = queryset.annotate(
                period=models.functions.TruncMonth('reservation_date')
            ).values('period').annotate(
                count=Count('id'),
                total_guests=Sum('number_of_guests')
            ).order_by('period')

            return list(result)

    @staticmethod
    def get_reservation_summary(start_date, end_date):
        """
        Get summary statistics for reservations within range

        Args:
            start_date: datetime start of range
            end_date: datetime end of range

        Returns:
            Dict with total_reservations, total_guests, average_guests
        """
        start_date_only = start_date.date() if hasattr(start_date, 'date') else start_date
        end_date_only = end_date.date() if hasattr(end_date, 'date') else end_date

        result = Reservation.objects.filter(
            reservation_date__gte=start_date_only,
            reservation_date__lte=end_date_only
        ).aggregate(
            total_reservations=Count('id'),
            total_guests=Sum('number_of_guests'),
            average_guests=Avg('number_of_guests')
        )

        return {
            'total_reservations': result['total_reservations'] or 0,
            'total_guests': result['total_guests'] or 0,
            'average_guests': round(result['average_guests'], 1) if result['average_guests'] else 0
        }

    @staticmethod
    def get_reservation_status_breakdown(start_date, end_date):
        """
        Get reservation count by status within range

        Args:
            start_date: datetime start of range
            end_date: datetime end of range

        Returns:
            Dict with counts per status
        """
        start_date_only = start_date.date() if hasattr(start_date, 'date') else start_date
        end_date_only = end_date.date() if hasattr(end_date, 'date') else end_date

        result = Reservation.objects.filter(
            reservation_date__gte=start_date_only,
            reservation_date__lte=end_date_only
        ).values('status').annotate(
            count=Count('id')
        )

        return {
            item['status']: item['count']
            for item in result
        }

    @staticmethod
    def get_deposit_summary(start_date, end_date):
        """
        Get deposit statistics for reservations within range

        Args:
            start_date: datetime start of range
            end_date: datetime end of range

        Returns:
            Dict with deposit_required, deposit_paid, deposit_pending
        """
        start_date_only = start_date.date() if hasattr(start_date, 'date') else start_date
        end_date_only = end_date.date() if hasattr(end_date, 'date') else end_date

        result = Reservation.objects.filter(
            reservation_date__gte=start_date_only,
            reservation_date__lte=end_date_only
        ).aggregate(
            total_deposit_required=Sum('deposit_required'),
            total_deposit_paid=Sum('deposit_paid'),
            total_reservations=Count('id')
        )

        total_required = result['total_deposit_required'] or 0
        total_paid = result['total_deposit_paid'] or 0

        return {
            'total_deposit_required': total_required,
            'total_deposit_paid': total_paid,
            'total_deposit_pending': max(0, total_required - total_paid),
            'payment_completion_rate': round((total_paid / total_required * 100), 1) if total_required > 0 else 0
        }

    @staticmethod
    def get_occasion_breakdown(start_date, end_date):
        """
        Get reservation count by occasion type within range

        Args:
            start_date: datetime start of range
            end_date: datetime end of range

        Returns:
            Dict with counts per occasion
        """
        start_date_only = start_date.date() if hasattr(start_date, 'date') else start_date
        end_date_only = end_date.date() if hasattr(end_date, 'date') else end_date

        result = Reservation.objects.filter(
            reservation_date__gte=start_date_only,
            reservation_date__lte=end_date_only
        ).values('special_occasion').annotate(
            count=Count('id')
        ).exclude(special_occasion__isnull=True).exclude(special_occasion='')

        return {
            item['special_occasion']: item['count']
            for item in result
        }
