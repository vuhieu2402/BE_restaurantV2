"""
Views for Orders app
"""
from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiParameter
from apps.api.mixins import StandardResponseMixin
from apps.api.response import ApiResponse
from .models import Order
from .serializers import (
    OrderSerializer,
    OrderListSerializer,
    OrderCreateSerializer,
    OrderUpdateStatusSerializer,
    DeliveryCalculationSerializer,
    OrderCancelSerializer
)
from .services import OrderService
from .selectors import OrderSelector
from apps.cart.models import Cart


class OrderPagination(PageNumberPagination):
    """Pagination cho orders"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CalculateDeliveryView(StandardResponseMixin, APIView):
    """
    POST /api/orders/calculate-delivery/
    Tính phí vận chuyển preview
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.order_service = OrderService()
    
    @extend_schema(
        tags=['Orders'],
        summary="Calculate delivery fee",
        description="Tính phí vận chuyển và khoảng cách trước khi đặt hàng",
        request=DeliveryCalculationSerializer,
        responses={200: dict}
    )
    def post(self, request):
        """Calculate delivery fee and distance"""
        serializer = DeliveryCalculationSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ApiResponse.validation_error(
                message="Dữ liệu không hợp lệ",
                errors=serializer.errors
            )
        
        # Calculate
        result = self.order_service.calculate_delivery_fee_and_distance(
            restaurant_id=serializer.validated_data['restaurant_id'],
            delivery_latitude=serializer.validated_data['delivery_latitude'],
            delivery_longitude=serializer.validated_data['delivery_longitude']
        )
        
        if not result['success']:
            return ApiResponse.validation_error(
                message=result['message']
            )
        
        # Return result
        response_data = {
            'distance_km': float(result['distance_km']),
            'distance_source': result.get('distance_source', 'Unknown'),
            'delivery_fee': float(result['delivery_fee']),
            'delivery_fee_display': f"{result['delivery_fee']:,.0f}đ",
            'is_in_delivery_radius': result['is_in_delivery_radius'],
            'is_surge_pricing': result.get('is_surge_pricing', False),
            'estimated_time': result['estimated_time'],
            'restaurant': {
                'id': result['restaurant'].id,
                'name': result['restaurant'].name,
                'address': result['restaurant'].address,
                'delivery_radius': float(result['restaurant'].delivery_radius),
            }
        }
        
        return ApiResponse.success(
            data=response_data,
            message=f"Tính toán thành công (sử dụng {result.get('distance_source', 'Unknown')})"
        )


class OrderCheckoutView(StandardResponseMixin, APIView):
    """
    POST /api/orders/checkout/
    Tạo order từ cart
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.order_service = OrderService()
    
    @extend_schema(
        tags=['Orders'],
        summary="Checkout cart to create order",
        description="Tạo đơn hàng từ giỏ hàng",
        request=OrderCreateSerializer,
        responses={201: OrderSerializer}
    )
    def post(self, request):
        """Create order from cart"""
        # Validate input
        serializer = OrderCreateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ApiResponse.validation_error(
                message="Dữ liệu không hợp lệ",
                errors=serializer.errors
            )
        
        # Get cart
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return ApiResponse.validation_error(
                message="Giỏ hàng không tồn tại"
            )
        
        # Create order
        result = self.order_service.create_order_from_cart(
            user=request.user,
            cart=cart,
            order_data=serializer.validated_data
        )
        
        if not result['success']:
            return ApiResponse.validation_error(
                message=result.get('message', 'Lỗi khi tạo đơn hàng'),
                errors=result.get('errors')
            )
        
        # Return order
        order_serializer = OrderSerializer(result['order'])
        
        return ApiResponse.success(
            data=order_serializer.data,
            message=result['message'],
            status_code=status.HTTP_201_CREATED
        )


class OrderListView(StandardResponseMixin, APIView):
    """
    GET /api/orders/
    Lấy danh sách orders của user
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.order_selector = OrderSelector()
    
    @extend_schema(
        tags=['Orders'],
        summary="List user orders",
        description="Lấy danh sách đơn hàng của user với filters",
        parameters=[
            OpenApiParameter(name='status', description='Filter by status', required=False, type=str),
            OpenApiParameter(name='order_type', description='Filter by order type', required=False, type=str),
            OpenApiParameter(name='page', description='Page number', required=False, type=int),
            OpenApiParameter(name='page_size', description='Page size', required=False, type=int),
        ],
        responses={200: OrderListSerializer(many=True)}
    )
    def get(self, request):
        """List orders with filters"""
        # Build filters from query params
        filters = {}
        
        if request.query_params.get('status'):
            filters['status'] = request.query_params.get('status')
        
        if request.query_params.get('order_type'):
            filters['order_type'] = request.query_params.get('order_type')
        
        if request.query_params.get('date_from'):
            filters['date_from'] = request.query_params.get('date_from')
        
        if request.query_params.get('date_to'):
            filters['date_to'] = request.query_params.get('date_to')
        
        # Get orders
        orders = self.order_selector.get_user_orders(
            user=request.user,
            filters=filters
        )
        
        # Paginate
        paginator = OrderPagination()
        paginated_orders = paginator.paginate_queryset(orders, request)
        
        # Serialize
        serializer = OrderListSerializer(paginated_orders, many=True)
        
        return paginator.get_paginated_response(serializer.data)


class OrderDetailView(StandardResponseMixin, APIView):
    """
    GET /api/orders/{order_id}/
    Chi tiết order
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.order_selector = OrderSelector()
    
    @extend_schema(
        tags=['Orders'],
        summary="Get order detail",
        description="Lấy chi tiết đơn hàng",
        responses={200: OrderSerializer}
    )
    def get(self, request, order_id):
        """Get order detail"""
        order = self.order_selector.get_order_by_id(order_id, user=request.user)
        
        if not order:
            return ApiResponse.not_found(
                message="Đơn hàng không tồn tại"
            )
        
        serializer = OrderSerializer(order)
        
        return ApiResponse.success(
            data=serializer.data,
            message="Lấy thông tin đơn hàng thành công"
        )


class OrderUpdateStatusView(StandardResponseMixin, APIView):
    """
    PATCH /api/orders/{order_id}/status/
    Cập nhật trạng thái order (cho staff/admin)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.order_service = OrderService()
        self.order_selector = OrderSelector()
    
    @extend_schema(
        tags=['Orders'],
        summary="Update order status",
        description="Cập nhật trạng thái đơn hàng (staff/admin)",
        request=OrderUpdateStatusSerializer,
        responses={200: OrderSerializer}
    )
    def patch(self, request, order_id):
        """Update order status"""
        # Get order
        order = self.order_selector.get_order_with_items(order_id)
        
        if not order:
            return ApiResponse.not_found(
                message="Đơn hàng không tồn tại"
            )
        
        # TODO: Add permission check (staff/admin only)
        # if not request.user.is_staff:
        #     return ApiResponse.forbidden(message="Bạn không có quyền cập nhật trạng thái")
        
        # Validate input
        serializer = OrderUpdateStatusSerializer(
            data=request.data,
            context={'order': order}
        )
        
        if not serializer.is_valid():
            return ApiResponse.validation_error(
                message="Dữ liệu không hợp lệ",
                errors=serializer.errors
            )
        
        # Update status
        result = self.order_service.update_order_status(
            order=order,
            new_status=serializer.validated_data['status'],
            staff_user=request.user,
            notes=serializer.validated_data.get('notes')
        )
        
        if not result['success']:
            return ApiResponse.error(
                message=result['message']
            )
        
        # Return updated order
        order_serializer = OrderSerializer(order)
        
        return ApiResponse.success(
            data=order_serializer.data,
            message=result['message']
        )


class OrderCancelView(StandardResponseMixin, APIView):
    """
    POST /api/orders/{order_id}/cancel/
    Hủy order (cho customer)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.order_service = OrderService()
        self.order_selector = OrderSelector()
    
    @extend_schema(
        tags=['Orders'],
        summary="Cancel order",
        description="Hủy đơn hàng (customer)",
        request=OrderCancelSerializer,
        responses={200: OrderSerializer}
    )
    def post(self, request, order_id):
        """Cancel order"""
        # Get order
        order = self.order_selector.get_order_by_id(order_id, user=request.user)
        
        if not order:
            return ApiResponse.not_found(
                message="Đơn hàng không tồn tại"
            )
        
        # Validate input
        serializer = OrderCancelSerializer(
            data=request.data,
            context={'order': order}
        )
        
        if not serializer.is_valid():
            return ApiResponse.validation_error(
                message="Dữ liệu không hợp lệ",
                errors=serializer.errors
            )
        
        # Cancel order
        result = self.order_service.cancel_order(
            order=order,
            user=request.user,
            reason=serializer.validated_data['cancel_reason']
        )
        
        if not result['success']:
            return ApiResponse.error(
                message=result['message']
            )
        
        # Return cancelled order
        order_serializer = OrderSerializer(order)
        
        return ApiResponse.success(
            data=order_serializer.data,
            message=result['message']
        )
