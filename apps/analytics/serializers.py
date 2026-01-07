"""
Analytics Serializers - Request Validation and Response Formatting
- Validate incoming query parameters
- Format outgoing response data
"""
from rest_framework import serializers
from apps.orders.models import Order


# Period choices for dropdown validation
PERIOD_CHOICES = [
    ('today', 'Today'),
    ('yesterday', 'Yesterday'),
    ('this_week', 'This Week'),
    ('last_week', 'Last Week'),
    ('this_month', 'This Month'),
    ('last_month', 'Last Month'),
]

# Group by choices
GROUP_BY_CHOICES = [
    ('day', 'Day'),
    ('week', 'Week'),
    ('month', 'Month'),
]

# Order status choices for filtering
ORDER_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('confirmed', 'Confirmed'),
    ('delivering', 'Delivering'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
    ('refunded', 'Refunded'),
]


class AnalyticsFilterSerializer(serializers.Serializer):
    """
    Common serializer for analytics filter validation
    Validates period, date range, and group_by parameters
    """
    period = serializers.ChoiceField(
        choices=PERIOD_CHOICES,
        required=False,
        allow_null=True,
        help_text="Preset time period"
    )
    start_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Custom start date (YYYY-MM-DD)"
    )
    end_date = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="Custom end date (YYYY-MM-DD)"
    )
    group_by = serializers.ChoiceField(
        choices=GROUP_BY_CHOICES,
        default='day',
        help_text="Group results by day, week, or month"
    )

    def validate(self, attrs):
        """
        Validate that either period OR start_date+end_date are provided
        """
        period = attrs.get('period')
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')

        # If neither period nor custom dates are provided, default to today
        if not period and not start_date:
            attrs['period'] = 'today'
            return attrs

        # If both period and custom dates are provided, prioritize custom dates
        if period and (start_date or end_date):
            # Clear period to use custom dates
            attrs['period'] = None

        # Validate custom date range
        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError({
                    'start_date': 'Start date must be before or equal to end date'
                })

        return attrs


class OrdersFilterSerializer(AnalyticsFilterSerializer):
    """
    Filter serializer for orders analytics
    Adds optional status filtering
    """
    status = serializers.ChoiceField(
        choices=ORDER_STATUS_CHOICES,
        required=False,
        allow_null=True,
        help_text="Filter by order status"
    )


class OrderPeriodSerializer(serializers.Serializer):
    """Serializer for a single order period in response"""
    date = serializers.DateField(help_text="Date of the period")
    count = serializers.IntegerField(help_text="Number of orders")
    revenue = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Total revenue for period"
    )


class OrdersAnalyticsResponseSerializer(serializers.Serializer):
    """Response serializer for orders analytics"""
    period = serializers.CharField(required=False, help_text="Period preset used")
    start_date = serializers.DateField(help_text="Start date of range")
    end_date = serializers.DateField(help_text="End date of range")
    group_by = serializers.CharField(help_text="Grouping method")
    summary = serializers.DictField(help_text="Summary statistics")
    orders = OrderPeriodSerializer(many=True, help_text="Orders grouped by period")


class RevenuePeriodSerializer(serializers.Serializer):
    """Serializer for a single revenue period in response"""
    date = serializers.DateField(help_text="Date of the period")
    revenue = serializers.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Total revenue for period"
    )
    order_count = serializers.IntegerField(help_text="Number of orders")


class RevenueAnalyticsResponseSerializer(serializers.Serializer):
    """Response serializer for revenue analytics"""
    period = serializers.CharField(required=False, help_text="Period preset used")
    start_date = serializers.DateField(help_text="Start date of range")
    end_date = serializers.DateField(help_text="End date of range")
    group_by = serializers.CharField(help_text="Grouping method")
    summary = serializers.DictField(help_text="Summary statistics")
    breakdown = RevenuePeriodSerializer(many=True, help_text="Revenue grouped by period")


class CustomerPeriodSerializer(serializers.Serializer):
    """Serializer for a single customer period in response"""
    date = serializers.DateField(help_text="Date of the period")
    count = serializers.IntegerField(help_text="Number of new customers")


class NewCustomersResponseSerializer(serializers.Serializer):
    """Response serializer for new customers analytics"""
    period = serializers.CharField(required=False, help_text="Period preset used")
    start_date = serializers.DateField(help_text="Start date of range")
    end_date = serializers.DateField(help_text="End date of range")
    group_by = serializers.CharField(help_text="Grouping method")
    summary = serializers.DictField(help_text="Summary statistics")
    breakdown = CustomerPeriodSerializer(many=True, help_text="Customers grouped by period")


# ==================== RESERVATION ANALYTICS SERIALIZERS ====================

# Reservation status choices for filtering
RESERVATION_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('confirmed', 'Confirmed'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]


class ReservationsFilterSerializer(AnalyticsFilterSerializer):
    """
    Filter serializer for reservations analytics
    Adds optional status filtering
    """
    status = serializers.ChoiceField(
        choices=RESERVATION_STATUS_CHOICES,
        required=False,
        allow_null=True,
        help_text="Filter by reservation status"
    )


class ReservationPeriodSerializer(serializers.Serializer):
    """Serializer for a single reservation period in response"""
    date = serializers.DateField(help_text="Date of the period")
    count = serializers.IntegerField(help_text="Number of reservations")
    total_guests = serializers.IntegerField(help_text="Total number of guests")


class ReservationsAnalyticsResponseSerializer(serializers.Serializer):
    """Response serializer for reservations analytics"""
    period = serializers.CharField(required=False, help_text="Period preset used")
    start_date = serializers.DateField(help_text="Start date of range")
    end_date = serializers.DateField(help_text="End date of range")
    group_by = serializers.CharField(help_text="Grouping method")
    summary = serializers.DictField(help_text="Summary statistics")
    breakdown = ReservationPeriodSerializer(many=True, help_text="Reservations grouped by period")
    status_breakdown = serializers.DictField(required=False, help_text="Count by status")
    occasion_breakdown = serializers.DictField(required=False, help_text="Count by occasion")
