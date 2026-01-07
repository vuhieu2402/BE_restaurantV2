"""
Analytics Services - Business Logic Layer
- Handle date range calculations
- Permission validation
- Orchestrate selector calls
- Format response data
"""
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta, datetime
import logging

from .selectors import AnalyticsSelector

User = get_user_model()
logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service cho analytics business logic"""

    # Period preset definitions
    PERIOD_PRESETS = {
        'today': lambda: _get_today_range(),
        'yesterday': lambda: _get_yesterday_range(),
        'this_week': lambda: _get_this_week_range(),
        'last_week': lambda: _get_last_week_range(),
        'this_month': lambda: _get_this_month_range(),
        'last_month': lambda: _get_last_month_range(),
    }

    def __init__(self):
        self.selector = AnalyticsSelector()

    def _check_permission(self, user):
        """
        Check if user has permission to access analytics

        Args:
            user: User object

        Returns:
            dict with 'allowed' bool and 'message' str
        """
        # Superuser has full access
        if user.is_superuser:
            return {'allowed': True, 'message': ''}

        # Admin and Manager can access analytics
        if user.user_type in ['admin', 'manager']:
            return {'allowed': True, 'message': ''}

        return {
            'allowed': False,
            'message': 'Bạn không có quyền truy cập dữ liệu phân tích'
        }

    def _parse_period(self, period):
        """
        Parse period preset to start_date and end_date

        Args:
            period: String key from PERIOD_PRESETS

        Returns:
            tuple of (start_datetime, end_datetime)
        """
        if period not in self.PERIOD_PRESETS:
            return None, None

        return self.PERIOD_PRESETS[period]()

    def _validate_date_range(self, start_date, end_date):
        """
        Validate custom date range

        Args:
            start_date: datetime or date
            end_date: datetime or date

        Returns:
            tuple of (start_datetime, end_datetime) normalized to datetime
        """
        # Convert date to datetime if needed
        if not isinstance(start_date, datetime):
            start_date = timezone.make_aware(
                datetime.combine(start_date, datetime.min.time())
            )
        if not isinstance(end_date, datetime):
            end_date = timezone.make_aware(
                datetime.combine(end_date, datetime.max.time())
            )

        # Ensure timezone-aware
        if timezone.is_naive(start_date):
            start_date = timezone.make_aware(start_date)
        if timezone.is_naive(end_date):
            end_date = timezone.make_aware(end_date)

        return start_date, end_date

    def _resolve_date_range(self, filters):
        """
        Resolve date range from filters (period or custom dates)

        Args:
            filters: dict with 'period', 'start_date', 'end_date'

        Returns:
            tuple of (start_datetime, end_datetime, period_name)
        """
        period = filters.get('period')
        start_date = filters.get('start_date')
        end_date = filters.get('end_date')

        # Use period preset if provided
        if period:
            return self._parse_period(period) + (period,)

        # Use custom dates
        if start_date and end_date:
            start_dt, end_dt = self._validate_date_range(start_date, end_date)
            return start_dt, end_dt, 'custom'

        # Default to today
        return self._parse_period('today') + ('today',)

    def _format_grouped_data(self, data, group_by):
        """
        Format grouped data for API response

        Args:
            data: List of dicts from selector
            group_by: 'day', 'week', or 'month'

        Returns:
            List of formatted dicts with date string
        """
        result = []
        for item in data:
            period_date = item['period']
            result.append({
                'date': period_date.strftime('%Y-%m-%d'),
                **{k: v for k, v in item.items() if k != 'period'}
            })
        return result

    def get_orders_analytics(self, user, filters):
        """
        Get orders analytics with grouping

        Args:
            user: Current user
            filters: dict with period, start_date, end_date, group_by, status

        Returns:
            dict with success, message, data
        """
        try:
            # Check permission
            permission = self._check_permission(user)
            if not permission['allowed']:
                return {
                    'success': False,
                    'message': permission['message'],
                    'error_code': 'PERMISSION_DENIED'
                }

            # Resolve date range
            start_date, end_date, period = self._resolve_date_range(filters)
            group_by = filters.get('group_by', 'day')
            status_filter = filters.get('status')

            # Get summary
            summary = self.selector.get_orders_summary(
                start_date, end_date, status_filter
            )

            # Get grouped data
            grouped_data = self.selector.get_orders_by_date_range(
                start_date, end_date, group_by, status_filter
            )

            # Format response
            return {
                'success': True,
                'message': 'Lấy dữ liệu đơn hàng thành công',
                'data': {
                    'period': period if period != 'custom' else None,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'group_by': group_by,
                    'summary': summary,
                    'orders': self._format_grouped_data(grouped_data, group_by)
                }
            }

        except Exception as e:
            logger.error(f"Get orders analytics error: {str(e)}")
            return {
                'success': False,
                'message': f'Lấy dữ liệu đơn hàng thất bại: {str(e)}',
                'error_code': 'DATABASE_ERROR'
            }

    def get_revenue_analytics(self, user, filters):
        """
        Get revenue analytics with grouping

        Args:
            user: Current user
            filters: dict with period, start_date, end_date, group_by

        Returns:
            dict with success, message, data
        """
        try:
            # Check permission
            permission = self._check_permission(user)
            if not permission['allowed']:
                return {
                    'success': False,
                    'message': permission['message'],
                    'error_code': 'PERMISSION_DENIED'
                }

            # Resolve date range
            start_date, end_date, period = self._resolve_date_range(filters)
            group_by = filters.get('group_by', 'day')

            # Get summary
            summary = self.selector.get_revenue_summary(start_date, end_date)

            # Get grouped data
            grouped_data = self.selector.get_revenue_by_date_range(
                start_date, end_date, group_by
            )

            # Calculate additional metrics
            total_revenue = summary['total_revenue']
            order_count = summary['order_count']

            # Calculate average daily revenue
            days_count = (end_date - start_date).days + 1
            average_daily = total_revenue / days_count if days_count > 0 else 0

            # Calculate growth rate (compare with previous period)
            previous_revenue = self.selector.get_previous_period_revenue(
                start_date, end_date
            )
            growth_rate = 0
            if previous_revenue > 0:
                growth_rate = round(
                    ((total_revenue - previous_revenue) / previous_revenue) * 100, 2
                )

            # Format response
            return {
                'success': True,
                'message': 'Lấy dữ liệu doanh thu thành công',
                'data': {
                    'period': period if period != 'custom' else None,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'group_by': group_by,
                    'summary': {
                        'total_revenue': total_revenue,
                        'average_daily': average_daily,
                        'growth_rate': growth_rate,
                        'order_count': order_count
                    },
                    'breakdown': self._format_grouped_data(grouped_data, group_by)
                }
            }

        except Exception as e:
            logger.error(f"Get revenue analytics error: {str(e)}")
            return {
                'success': False,
                'message': f'Lấy dữ liệu doanh thu thất bại: {str(e)}',
                'error_code': 'DATABASE_ERROR'
            }

    def get_new_customers_analytics(self, user, filters):
        """
        Get new customers analytics with grouping

        Args:
            user: Current user
            filters: dict with period, start_date, end_date, group_by

        Returns:
            dict with success, message, data
        """
        try:
            # Check permission
            permission = self._check_permission(user)
            if not permission['allowed']:
                return {
                    'success': False,
                    'message': permission['message'],
                    'error_code': 'PERMISSION_DENIED'
                }

            # Resolve date range
            start_date, end_date, period = self._resolve_date_range(filters)
            group_by = filters.get('group_by', 'day')

            # Get summary
            summary = self.selector.get_new_customers_summary(
                start_date, end_date
            )

            # Get grouped data
            grouped_data = self.selector.get_new_customers_by_date_range(
                start_date, end_date, group_by
            )

            # Format response
            return {
                'success': True,
                'message': 'Lấy dữ liệu khách hàng mới thành công',
                'data': {
                    'period': period if period != 'custom' else None,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'group_by': group_by,
                    'summary': summary,
                    'breakdown': self._format_grouped_data(grouped_data, group_by)
                }
            }

        except Exception as e:
            logger.error(f"Get new customers analytics error: {str(e)}")
            return {
                'success': False,
                'message': f'Lấy dữ liệu khách hàng mới thất bại: {str(e)}',
                'error_code': 'DATABASE_ERROR'
            }

    def get_reservations_analytics(self, user, filters):
        """
        Get reservations analytics with grouping

        Args:
            user: Current user
            filters: dict with period, start_date, end_date, group_by, status

        Returns:
            dict with success, message, data
        """
        try:
            # Check permission
            permission = self._check_permission(user)
            if not permission['allowed']:
                return {
                    'success': False,
                    'message': permission['message'],
                    'error_code': 'PERMISSION_DENIED'
                }

            # Resolve date range
            start_date, end_date, period = self._resolve_date_range(filters)
            group_by = filters.get('group_by', 'day')
            status_filter = filters.get('status')

            # Get summary
            summary = self.selector.get_reservation_summary(start_date, end_date)

            # Get grouped data
            grouped_data = self.selector.get_reservations_by_date_range(
                start_date, end_date, group_by, status_filter
            )

            # Get additional breakdown data
            status_breakdown = self.selector.get_reservation_status_breakdown(
                start_date, end_date
            )
            occasion_breakdown = self.selector.get_occasion_breakdown(
                start_date, end_date
            )

            # Format response
            return {
                'success': True,
                'message': 'Lấy dữ liệu đặt bàn thành công',
                'data': {
                    'period': period if period != 'custom' else None,
                    'start_date': start_date.strftime('%Y-%m-%d'),
                    'end_date': end_date.strftime('%Y-%m-%d'),
                    'group_by': group_by,
                    'summary': summary,
                    'breakdown': self._format_grouped_data(grouped_data, group_by),
                    'status_breakdown': status_breakdown,
                    'occasion_breakdown': occasion_breakdown
                }
            }

        except Exception as e:
            logger.error(f"Get reservations analytics error: {str(e)}")
            return {
                'success': False,
                'message': f'Lấy dữ liệu đặt bàn thất bại: {str(e)}',
                'error_code': 'DATABASE_ERROR'
            }


# Helper functions for date range calculations

def _get_today_range():
    """Get today's date range (start of day to end of day)"""
    now = timezone.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end


def _get_yesterday_range():
    """Get yesterday's date range"""
    now = timezone.now()
    yesterday = now - timedelta(days=1)
    start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
    end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end


def _get_this_week_range():
    """Get this week's date range (Monday to Sunday)"""
    now = timezone.now()
    # Get Monday of this week
    start = now - timedelta(days=now.weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    # Get Sunday of this week
    end = start + timedelta(days=6)
    end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end


def _get_last_week_range():
    """Get last week's date range (Monday to Sunday)"""
    now = timezone.now()
    # Get Monday of last week
    start = now - timedelta(days=now.weekday() + 7)
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    # Get Sunday of last week
    end = start + timedelta(days=6)
    end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end


def _get_this_month_range():
    """Get this month's date range (1st to last day)"""
    now = timezone.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Get last day of current month
    if now.month == 12:
        next_month = now.replace(year=now.year + 1, month=1, day=1)
    else:
        next_month = now.replace(month=now.month + 1, day=1)
    end = next_month - timedelta(days=1)
    end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end


def _get_last_month_range():
    """Get last month's date range (1st to last day)"""
    now = timezone.now()
    # Get first day of last month
    if now.month == 1:
        last_month = now.replace(year=now.year - 1, month=12, day=1)
    else:
        last_month = now.replace(month=now.month - 1, day=1)
    start = last_month.replace(hour=0, minute=0, second=0, microsecond=0)
    # Get last day of last month
    # Move to first day of this month, then go back 1 day
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = this_month_start - timedelta(days=1)
    end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start, end
