"""
Analytics Views - API Layer
- Handle HTTP requests
- Validate query parameters
- Call service layer for business logic
- Format standardized responses
- NO business logic, NO direct database queries
"""
from rest_framework import status, permissions
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from apps.api.response import ApiResponse
from .services import AnalyticsService
from .serializers import (
    OrdersFilterSerializer,
    OrdersAnalyticsResponseSerializer,
    RevenueAnalyticsResponseSerializer,
    NewCustomersResponseSerializer,
    ReservationsFilterSerializer,
    ReservationsAnalyticsResponseSerializer
)
import logging

logger = logging.getLogger(__name__)


class OrdersAnalyticsView(APIView):
    """
    API endpoint for orders analytics
    Returns orders grouped by day/week within a date range
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Orders Analytics",
        description="Lấy thống kê đơn hàng theo khoảng thời gian",
        parameters=[
            OpenApiParameter(
                name='period',
                description='Khoảng thời gian preset',
                type=OpenApiTypes.STR,
                enum=['today', 'yesterday', 'this_week', 'last_week', 'this_month', 'last_month'],
                required=False
            ),
            OpenApiParameter(
                name='start_date',
                description='Ngày bắt đầu (YYYY-MM-DD)',
                type=OpenApiTypes.DATE,
                required=False
            ),
            OpenApiParameter(
                name='end_date',
                description='Ngày kết thúc (YYYY-MM-DD)',
                type=OpenApiTypes.DATE,
                required=False
            ),
            OpenApiParameter(
                name='group_by',
                description='Nhóm theo',
                type=OpenApiTypes.STR,
                enum=['day', 'week', 'month'],
                required=False
            ),
            OpenApiParameter(
                name='status',
                description='Lọc theo trạng thái đơn hàng',
                type=OpenApiTypes.STR,
                enum=['pending', 'confirmed', 'delivering', 'completed', 'cancelled', 'refunded'],
                required=False
            ),
        ],
        responses={200: OrdersAnalyticsResponseSerializer},
        tags=['analytics']
    )
    def get(self, request, *args, **kwargs):
        """GET method - Lấy thống kê đơn hàng"""
        try:
            # Validate query parameters
            filter_serializer = OrdersFilterSerializer(data=request.query_params)
            filter_serializer.is_valid(raise_exception=True)

            # Get validated filters
            filters = filter_serializer.validated_data

            # Call service
            service = AnalyticsService()
            result = service.get_orders_analytics(
                user=request.user,
                filters=filters
            )

            if result['success']:
                return ApiResponse.success(
                    data=result['data'],
                    message=result['message']
                )
            else:
                # Handle permission denied
                if result.get('error_code') == 'PERMISSION_DENIED':
                    return ApiResponse.forbidden(message=result['message'])
                # Handle other errors
                return ApiResponse.error(
                    message=result['message'],
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Orders analytics view error: {str(e)}")
            return ApiResponse.error(
                message=f"Lỗi server: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RevenueAnalyticsView(APIView):
    """
    API endpoint for revenue analytics
    Returns revenue grouped by day/week/month within a date range
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Revenue Analytics",
        description="Lấy thống kê doanh thu theo khoảng thời gian",
        parameters=[
            OpenApiParameter(
                name='period',
                description='Khoảng thời gian preset',
                type=OpenApiTypes.STR,
                enum=['today', 'yesterday', 'this_week', 'last_week', 'this_month', 'last_month'],
                required=False
            ),
            OpenApiParameter(
                name='start_date',
                description='Ngày bắt đầu (YYYY-MM-DD)',
                type=OpenApiTypes.DATE,
                required=False
            ),
            OpenApiParameter(
                name='end_date',
                description='Ngày kết thúc (YYYY-MM-DD)',
                type=OpenApiTypes.DATE,
                required=False
            ),
            OpenApiParameter(
                name='group_by',
                description='Nhóm theo',
                type=OpenApiTypes.STR,
                enum=['day', 'week', 'month'],
                required=False
            ),
        ],
        responses={200: RevenueAnalyticsResponseSerializer},
        tags=['analytics']
    )
    def get(self, request, *args, **kwargs):
        """GET method - Lấy thống kê doanh thu"""
        try:
            # Validate query parameters
            from .serializers import AnalyticsFilterSerializer
            filter_serializer = AnalyticsFilterSerializer(data=request.query_params)
            filter_serializer.is_valid(raise_exception=True)

            # Get validated filters
            filters = filter_serializer.validated_data

            # Call service
            service = AnalyticsService()
            result = service.get_revenue_analytics(
                user=request.user,
                filters=filters
            )

            if result['success']:
                return ApiResponse.success(
                    data=result['data'],
                    message=result['message']
                )
            else:
                # Handle permission denied
                if result.get('error_code') == 'PERMISSION_DENIED':
                    return ApiResponse.forbidden(message=result['message'])
                # Handle other errors
                return ApiResponse.error(
                    message=result['message'],
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Revenue analytics view error: {str(e)}")
            return ApiResponse.error(
                message=f"Lỗi server: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NewCustomersAnalyticsView(APIView):
    """
    API endpoint for new customers analytics
    Returns new customer registrations grouped by day/week/month
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="New Customers Analytics",
        description="Lấy thống kê khách hàng mới theo khoảng thời gian",
        parameters=[
            OpenApiParameter(
                name='period',
                description='Khoảng thời gian preset',
                type=OpenApiTypes.STR,
                enum=['today', 'yesterday', 'this_week', 'last_week', 'this_month', 'last_month'],
                required=False
            ),
            OpenApiParameter(
                name='start_date',
                description='Ngày bắt đầu (YYYY-MM-DD)',
                type=OpenApiTypes.DATE,
                required=False
            ),
            OpenApiParameter(
                name='end_date',
                description='Ngày kết thúc (YYYY-MM-DD)',
                type=OpenApiTypes.DATE,
                required=False
            ),
            OpenApiParameter(
                name='group_by',
                description='Nhóm theo',
                type=OpenApiTypes.STR,
                enum=['day', 'week', 'month'],
                required=False
            ),
        ],
        responses={200: NewCustomersResponseSerializer},
        tags=['analytics']
    )
    def get(self, request, *args, **kwargs):
        """GET method - Lấy thống kê khách hàng mới"""
        try:
            # Validate query parameters
            from .serializers import AnalyticsFilterSerializer
            filter_serializer = AnalyticsFilterSerializer(data=request.query_params)
            filter_serializer.is_valid(raise_exception=True)

            # Get validated filters
            filters = filter_serializer.validated_data

            # Call service
            service = AnalyticsService()
            result = service.get_new_customers_analytics(
                user=request.user,
                filters=filters
            )

            if result['success']:
                return ApiResponse.success(
                    data=result['data'],
                    message=result['message']
                )
            else:
                # Handle permission denied
                if result.get('error_code') == 'PERMISSION_DENIED':
                    return ApiResponse.forbidden(message=result['message'])
                # Handle other errors
                return ApiResponse.error(
                    message=result['message'],
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"New customers analytics view error: {str(e)}")
            return ApiResponse.error(
                message=f"Lỗi server: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReservationsAnalyticsView(APIView):
    """
    API endpoint for reservations analytics
    Returns reservations grouped by day/week within a date range
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Reservations Analytics",
        description="Lấy thống kê đặt bàn theo khoảng thời gian",
        parameters=[
            OpenApiParameter(
                name='period',
                description='Khoảng thời gian preset',
                type=OpenApiTypes.STR,
                enum=['today', 'yesterday', 'this_week', 'last_week', 'this_month', 'last_month'],
                required=False
            ),
            OpenApiParameter(
                name='start_date',
                description='Ngày bắt đầu (YYYY-MM-DD)',
                type=OpenApiTypes.DATE,
                required=False
            ),
            OpenApiParameter(
                name='end_date',
                description='Ngày kết thúc (YYYY-MM-DD)',
                type=OpenApiTypes.DATE,
                required=False
            ),
            OpenApiParameter(
                name='group_by',
                description='Nhóm theo',
                type=OpenApiTypes.STR,
                enum=['day', 'week', 'month'],
                required=False
            ),
            OpenApiParameter(
                name='status',
                description='Lọc theo trạng thái đặt bàn',
                type=OpenApiTypes.STR,
                enum=['pending', 'confirmed', 'completed', 'cancelled'],
                required=False
            ),
        ],
        responses={200: ReservationsAnalyticsResponseSerializer},
        tags=['analytics']
    )
    def get(self, request, *args, **kwargs):
        """GET method - Lấy thống kê đặt bàn"""
        try:
            # Validate query parameters
            filter_serializer = ReservationsFilterSerializer(data=request.query_params)
            filter_serializer.is_valid(raise_exception=True)

            # Get validated filters
            filters = filter_serializer.validated_data

            # Call service
            service = AnalyticsService()
            result = service.get_reservations_analytics(
                user=request.user,
                filters=filters
            )

            if result['success']:
                return ApiResponse.success(
                    data=result['data'],
                    message=result['message']
                )
            else:
                # Handle permission denied
                if result.get('error_code') == 'PERMISSION_DENIED':
                    return ApiResponse.forbidden(message=result['message'])
                # Handle other errors
                return ApiResponse.error(
                    message=result['message'],
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Reservations analytics view error: {str(e)}")
            return ApiResponse.error(
                message=f"Lỗi server: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
