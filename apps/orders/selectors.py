"""
Selector layer for Orders app
Chỉ xử lý SELECT queries - không modify data
"""
from django.db.models import Q, Prefetch, Count
from .models import Order, OrderItem


class OrderSelector:
    """
    Selector layer - Xử lý các query READ ONLY cho Order
    """
    
    def get_user_orders(self, user, filters=None):
        """
        Lấy danh sách orders của user với filters
        
        Args:
            user: User object
            filters: Dict chứa các filter options {
                'status': str,
                'order_type': str,
                'date_from': date,
                'date_to': date,
                'restaurant_id': int,
            }
        
        Returns:
            QuerySet of Orders
        """
        queryset = Order.objects.filter(customer=user).select_related(
            'restaurant',
            'chain',
            'table',
            'assigned_staff'
        ).prefetch_related(
            'items'
        ).order_by('-created_at')
        
        if not filters:
            return queryset
        
        # Apply filters
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        
        if filters.get('order_type'):
            queryset = queryset.filter(order_type=filters['order_type'])
        
        if filters.get('date_from'):
            queryset = queryset.filter(created_at__gte=filters['date_from'])
        
        if filters.get('date_to'):
            queryset = queryset.filter(created_at__lte=filters['date_to'])
        
        if filters.get('restaurant_id'):
            queryset = queryset.filter(restaurant_id=filters['restaurant_id'])
        
        return queryset
    
    def get_order_by_id(self, order_id, user=None):
        """
        Lấy order detail theo ID
        
        Args:
            order_id: ID của order
            user: User object (optional) - để validate quyền truy cập
        
        Returns:
            Order object hoặc None
        """
        try:
            queryset = Order.objects.select_related(
                'customer',
                'restaurant',
                'chain',
                'table',
                'assigned_staff'
            ).prefetch_related(
                Prefetch(
                    'items',
                    queryset=OrderItem.objects.select_related('menu_item')
                )
            )
            
            if user:
                # Customer chỉ xem được order của mình
                # Staff/admin có thể xem tất cả (check ở view layer)
                order = queryset.get(id=order_id, customer=user)
            else:
                order = queryset.get(id=order_id)
            
            return order
        
        except Order.DoesNotExist:
            return None
    
    def get_order_with_items(self, order_id):
        """
        Lấy order kèm theo tất cả items
        
        Args:
            order_id: ID của order
        
        Returns:
            Order object hoặc None
        """
        try:
            order = Order.objects.select_related(
                'restaurant',
                'customer'
            ).prefetch_related(
                Prefetch(
                    'items',
                    queryset=OrderItem.objects.select_related('menu_item').order_by('created_at')
                )
            ).get(id=order_id)
            
            return order
        
        except Order.DoesNotExist:
            return None
    
    def get_restaurant_orders(self, restaurant_id, filters=None):
        """
        Lấy danh sách orders của restaurant (cho staff/manager)
        
        Args:
            restaurant_id: ID của restaurant
            filters: Dict chứa các filter options
        
        Returns:
            QuerySet of Orders
        """
        queryset = Order.objects.filter(
            restaurant_id=restaurant_id
        ).select_related(
            'customer',
            'table',
            'assigned_staff'
        ).prefetch_related(
            'items'
        ).order_by('-created_at')
        
        if not filters:
            return queryset
        
        # Apply filters
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        
        if filters.get('order_type'):
            queryset = queryset.filter(order_type=filters['order_type'])
        
        if filters.get('date_from'):
            queryset = queryset.filter(created_at__gte=filters['date_from'])
        
        if filters.get('date_to'):
            queryset = queryset.filter(created_at__lte=filters['date_to'])
        
        return queryset
    
    def get_order_stats(self, user=None, restaurant_id=None):
        """
        Lấy thống kê orders
        
        Args:
            user: User object (optional) - stats cho user
            restaurant_id: ID restaurant (optional) - stats cho restaurant
        
        Returns:
            Dict với các thống kê
        """
        queryset = Order.objects.all()
        
        if user:
            queryset = queryset.filter(customer=user)
        
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        
        total_orders = queryset.count()
        
        # Count by status
        status_counts = {}
        for status, label in Order.ORDER_STATUS_CHOICES:
            count = queryset.filter(status=status).count()
            status_counts[status] = {
                'count': count,
                'label': label
            }
        
        # Count by order_type
        type_counts = {}
        for order_type, label in Order.ORDER_TYPE_CHOICES:
            count = queryset.filter(order_type=order_type).count()
            type_counts[order_type] = {
                'count': count,
                'label': label
            }
        
        # Calculate totals
        from django.db.models import Sum
        total_revenue = queryset.filter(
            status='completed'
        ).aggregate(Sum('total'))['total__sum'] or 0
        
        return {
            'total_orders': total_orders,
            'status_counts': status_counts,
            'type_counts': type_counts,
            'total_revenue': float(total_revenue),
        }
    
    def search_orders(self, query, user=None, restaurant_id=None):
        """
        Tìm kiếm orders theo order_number hoặc customer info
        
        Args:
            query: Search query string
            user: User object (optional)
            restaurant_id: ID restaurant (optional)
        
        Returns:
            QuerySet of Orders
        """
        queryset = Order.objects.all()
        
        if user:
            queryset = queryset.filter(customer=user)
        
        if restaurant_id:
            queryset = queryset.filter(restaurant_id=restaurant_id)
        
        # Search by order_number or customer name
        queryset = queryset.filter(
            Q(order_number__icontains=query) |
            Q(customer__username__icontains=query) |
            Q(customer__first_name__icontains=query) |
            Q(customer__last_name__icontains=query) |
            Q(delivery_phone__icontains=query)
        ).select_related(
            'customer',
            'restaurant'
        ).order_by('-created_at')
        
        return queryset
    
    def get_all_orders(self, filters=None):
        """
        Lấy danh sách tất cả orders với filters theo thời gian và các điều kiện khác
        
        Args:
            filters: Dict chứa các filter options {
                'date': str (YYYY-MM-DD) - Filter theo ngày cụ thể
                'week': int - Filter theo tuần trong năm
                'month': int - Filter theo tháng
                'year': int - Filter theo năm
                'date_from': date - Ngày bắt đầu
                'date_to': date - Ngày kết thúc
                'status': str - Filter theo trạng thái
                'order_type': str - Filter theo loại đơn hàng
                'restaurant_id': int - Filter theo chi nhánh
                'chain_id': int - Filter theo chuỗi nhà hàng
                'customer_id': int - Filter theo khách hàng
            }
        
        Returns:
            QuerySet of Orders
        """
        from django.utils import timezone
        from datetime import datetime, timedelta
        
        queryset = Order.objects.select_related(
            'customer',
            'restaurant',
            'chain',
            'table',
            'assigned_staff'
        ).prefetch_related(
            'items'
        ).order_by('-created_at')
        
        if not filters:
            return queryset
        
        # Filter theo thời gian
        if filters.get('date'):
            try:
                date_obj = datetime.strptime(filters['date'], '%Y-%m-%d').date()
                queryset = queryset.filter(
                    created_at__date=date_obj
                )
            except (ValueError, TypeError):
                pass
        
        elif filters.get('week') and filters.get('year'):
            try:
                week = int(filters['week'])
                year = int(filters['year'])
                
                # Tính ngày đầu và cuối của tuần
                start_date = datetime.strptime(f"{year}-W{week-1}-1", "%Y-W%W-%w").date()
                end_date = start_date + timedelta(days=6)
                
                queryset = queryset.filter(
                    created_at__date__gte=start_date,
                    created_at__date__lte=end_date
                )
            except (ValueError, TypeError):
                pass
        
        elif filters.get('month') and filters.get('year'):
            try:
                month = int(filters['month'])
                year = int(filters['year'])
                
                queryset = queryset.filter(
                    created_at__year=year,
                    created_at__month=month
                )
            except (ValueError, TypeError):
                pass
        
        elif filters.get('year'):
            try:
                year = int(filters['year'])
                queryset = queryset.filter(created_at__year=year)
            except (ValueError, TypeError):
                pass
        
        # Filter theo khoảng thời gian
        if filters.get('date_from'):
            queryset = queryset.filter(created_at__gte=filters['date_from'])
        
        if filters.get('date_to'):
            queryset = queryset.filter(created_at__lte=filters['date_to'])
        
        # Filter theo trạng thái
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        
        # Filter theo loại đơn hàng
        if filters.get('order_type'):
            queryset = queryset.filter(order_type=filters['order_type'])
        
        # Filter theo chi nhánh
        if filters.get('restaurant_id'):
            queryset = queryset.filter(restaurant_id=filters['restaurant_id'])
        
        # Filter theo chuỗi nhà hàng
        if filters.get('chain_id'):
            queryset = queryset.filter(chain_id=filters['chain_id'])
        
        # Filter theo khách hàng
        if filters.get('customer_id'):
            queryset = queryset.filter(customer_id=filters['customer_id'])
        
        return queryset
