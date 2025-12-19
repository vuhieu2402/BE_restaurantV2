"""
User Management Views - API Layer
- Chỉ nhận HTTP request và validate cơ bản
- Gọi Service layer
- Format response theo chuẩn
- KHÔNG chứa business logic
- KHÔNG query database trực tiếp
- KHÔNG validate business rules
"""
from rest_framework import status, permissions, serializers
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from apps.api.mixins import StandardResponseMixin
from apps.api.response import ApiResponse
from .services import UserService, CustomerProfileService
from .serializers import (
    UserListSerializer, UserCreateSerializer, UserUpdateSerializer,
    CustomerProfileSerializer, StaffProfileSerializer,
    CustomerProfileUpdateSerializer, StaffProfileUpdateSerializer,
    BulkUserOperationSerializer, UserFilterSerializer, LoyaltyInfoSerializer
)
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class CustomPagination(PageNumberPagination):
    """Custom pagination cho user list"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'count': schema,
                'next': schema,
                'previous': schema,
                'results': {
                    'type': 'array',
                    'items': schema
                }
            }
        }


class UserListView(StandardResponseMixin, ListAPIView):
    """
    View cho danh sách users
    Chỉ admin/manager có quyền truy cập
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserListSerializer
    pagination_class = CustomPagination

    @extend_schema(
        summary="List users",
        description="Lấy danh sách người dùng với phân trang và filter",
        parameters=[
            OpenApiParameter(
                name='user_type',
                description='Loại người dùng',
                type=OpenApiTypes.STR,
                enum=['customer', 'staff', 'manager', 'admin']
            ),
            OpenApiParameter(
                name='is_active',
                description='Trạng thái hoạt động',
                type=OpenApiTypes.BOOL
            ),
            OpenApiParameter(
                name='is_verified',
                description='Trạng thái xác thực',
                type=OpenApiTypes.BOOL
            ),
            OpenApiParameter(
                name='search',
                description='Tìm kiếm theo username, email, họ tên',
                type=OpenApiTypes.STR
            ),
            OpenApiParameter(
                name='restaurant_id',
                description='ID nhà hàng (cho staff)',
                type=OpenApiTypes.INT
            ),
            OpenApiParameter(
                name='ordering',
                description='Sắp xếp theo field',
                type=OpenApiTypes.STR,
                enum=['username', '-username', 'created_at', '-created_at', 'user_type']
            ),
        ]
    )
    def get(self, request, *args, **kwargs):
        """GET method - Lấy danh sách users"""
        try:
            # Validate filter parameters
            filter_serializer = UserFilterSerializer(data=request.query_params)
            filter_serializer.is_valid(raise_exception=True)

            # Lấy filters validated
            filters = {}
            for field in ['user_type', 'is_active', 'is_verified', 'search', 'restaurant_id',
                         'created_after', 'created_before']:
                if field in filter_serializer.validated_data:
                    filters[field] = filter_serializer.validated_data[field]

            ordering = filter_serializer.validated_data.get('ordering')
            page = filter_serializer.validated_data.get('page', 1)
            page_size = filter_serializer.validated_data.get('page_size', 20)

            # Gọi service
            user_service = UserService()
            result = user_service.get_user_list(
                user=request.user,
                filters=filters,
                ordering=ordering,
                page=page,
                page_size=page_size
            )

            if result['success']:
                # Format response với pagination
                return ApiResponse.paginated_response(
                    data=result['data']['items'],
                    pagination=result['data']['pagination'],
                    message=result['message']
                )
            else:
                return ApiResponse.forbidden(message=result['message'])

        except Exception as e:
            logger.error(f"User list error: {str(e)}")
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserDetailView(StandardResponseMixin, APIView):
    """
    View cho chi tiết user
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get user details",
        description="Lấy thông tin chi tiết của một người dùng"
    )
    def get(self, request, user_id, *args, **kwargs):
        """GET method - Lấy chi tiết user"""
        try:
            user_service = UserService()
            result = user_service.get_user_detail(request.user, user_id)

            if result['success']:
                # Serialize user data
                user_serializer = UserListSerializer(result['data']['user'])
                response_data = user_serializer.data

                # Add profile data
                if result['data']['profile']:
                    response_data['profile'] = result['data']['profile']

                return ApiResponse.success(
                    data=response_data,
                    message=result['message']
                )
            elif result['error_code'] == 'USER_NOT_FOUND':
                return ApiResponse.not_found(message=result['message'])
            elif result['error_code'] == 'PERMISSION_DENIED':
                return ApiResponse.forbidden(message=result['message'])
            else:
                return ApiResponse.bad_request(message=result['message'])

        except Exception as e:
            logger.error(f"User detail error: {str(e)}")
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserCreateView(StandardResponseMixin, GenericAPIView):
    """
    View cho tạo user mới
    Chỉ admin/manager có quyền tạo user
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserCreateSerializer

    @extend_schema(
        summary="Create user",
        description="Tạo người dùng mới với profile",
        request=UserCreateSerializer,
        responses={201: UserListSerializer}
    )
    def post(self, request, *args, **kwargs):
        """POST method - Tạo user mới"""
        try:
            # Validate request data
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Gọi service
            user_service = UserService()
            result = user_service.create_user(request.user, serializer.validated_data)

            if result['success']:
                # Serialize created user
                user_serializer = UserListSerializer(result['data']['user'])
                return ApiResponse.created(
                    data=user_serializer.data,
                    message=result['message']
                )
            elif result['error_code'] in ['PERMISSION_DENIED', 'EMAIL_EXISTS', 'PHONE_EXISTS', 'VALIDATION_ERROR']:
                return ApiResponse.validation_error(
                    message=result['message'],
                    errors=result.get('errors', {})
                )
            else:
                return ApiResponse.bad_request(message=result['message'])

        except Exception as e:
            logger.error(f"User create error: {str(e)}")
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserUpdateView(StandardResponseMixin, APIView):
    """
    View cho cập nhật user
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Update user",
        description="Cập nhật thông tin người dùng",
        request=UserUpdateSerializer,
        responses={200: UserListSerializer}
    )
    def patch(self, request, user_id, *args, **kwargs):
        """PATCH method - Cập nhật user (partial update)"""
        try:
            # Validate request data (partial cho PATCH)
            serializer = UserUpdateSerializer(data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            # Gọi service
            user_service = UserService()
            result = user_service.update_user(request.user, user_id, serializer.validated_data)

            if result['success']:
                # Serialize updated user
                user_serializer = UserListSerializer(result['data']['user'])
                return ApiResponse.success(
                    data=user_serializer.data,
                    message=result['message']
                )
            elif result['error_code'] == 'USER_NOT_FOUND':
                return ApiResponse.not_found(message=result['message'])
            elif result['error_code'] == 'PERMISSION_DENIED':
                return ApiResponse.forbidden(message=result['message'])
            else:
                return ApiResponse.bad_request(message=result['message'])

        except Exception as e:
            logger.error(f"User update error: {str(e)}")
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserDeleteView(StandardResponseMixin, APIView):
    """
    View cho xóa user
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Delete user",
        description="Xóa người dùng (soft delete)"
    )
    def delete(self, request, user_id, *args, **kwargs):
        """DELETE method - Xóa user"""
        try:
            user_service = UserService()
            result = user_service.delete_user(request.user, user_id)

            if result['success']:
                return ApiResponse.success(
                    data=result['data'],
                    message=result['message']
                )
            elif result['error_code'] == 'USER_NOT_FOUND':
                return ApiResponse.not_found(message=result['message'])
            elif result['error_code'] == 'PERMISSION_DENIED':
                return ApiResponse.forbidden(message=result['message'])
            elif result['error_code'] == 'SELF_DELETE':
                return ApiResponse.bad_request(message=result['message'])
            else:
                return ApiResponse.bad_request(message=result['message'])

        except Exception as e:
            logger.error(f"User delete error: {str(e)}")
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserToggleStatusView(StandardResponseMixin, APIView):
    """
    View cho activate/deactivate user
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Toggle user status",
        description="Activate/Deactivate người dùng",
        parameters=[
            OpenApiParameter(
                name='is_active',
                description='Trạng thái mới (true=active, false=inactive)',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                required=True
            )
        ]
    )
    def patch(self, request, user_id, *args, **kwargs):
        """PATCH method - Toggle user status"""
        try:
            # Get is_active from query params
            is_active_str = request.query_params.get('is_active')
            if is_active_str is None:
                return ApiResponse.validation_error(
                    message='Thiếu parameter is_active'
                )

            is_active = is_active_str.lower() in ['true', '1', 'yes']

            user_service = UserService()
            result = user_service.toggle_user_status(request.user, user_id, is_active)

            if result['success']:
                return ApiResponse.success(
                    data=result['data'],
                    message=result['message']
                )
            elif result['error_code'] == 'USER_NOT_FOUND':
                return ApiResponse.not_found(message=result['message'])
            elif result['error_code'] == 'PERMISSION_DENIED':
                return ApiResponse.forbidden(message=result['message'])
            elif result['error_code'] == 'SELF_MODIFY':
                return ApiResponse.bad_request(message=result['message'])
            else:
                return ApiResponse.bad_request(message=result['message'])

        except Exception as e:
            logger.error(f"User toggle status error: {str(e)}")
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BulkUserOperationView(StandardResponseMixin, GenericAPIView):
    """
    View cho bulk operations
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = BulkUserOperationSerializer

    @extend_schema(
        summary="Bulk user operations",
        description="Thực hiện thao tác hàng loạt trên nhiều user",
        request=BulkUserOperationSerializer
    )
    def post(self, request, *args, **kwargs):
        """POST method - Bulk operations"""
        try:
            # Validate request data
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            user_service = UserService()
            result = user_service.bulk_operations(
                admin_user=request.user,
                user_ids=serializer.validated_data['user_ids'],
                operation=serializer.validated_data['operation'],
                operation_data={'reason': serializer.validated_data.get('reason')}
            )

            if result['success']:
                return ApiResponse.success(
                    data=result['data'],
                    message=result['message']
                )
            elif result['error_code'] == 'PERMISSION_DENIED':
                return ApiResponse.forbidden(message=result['message'])
            else:
                return ApiResponse.bad_request(message=result['message'])

        except Exception as e:
            logger.error(f"Bulk user operation error: {str(e)}")
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CustomerProfileView(StandardResponseMixin, APIView):
    """
    View cho customer profile management
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get customer profile",
        description="Lấy thông tin profile của customer"
    )
    def get(self, request, *args, **kwargs):
        """GET method - Lấy customer profile của user hiện tại"""
        try:
            if not request.user.is_customer:
                return ApiResponse.forbidden(
                    message='Chỉ customer có thể xem profile này'
                )

            customer_service = CustomerProfileService()
            result = customer_service.get_loyalty_info(request.user)

            if result['success']:
                serializer = LoyaltyInfoSerializer(result['data'])
                return ApiResponse.success(
                    data=serializer.data,
                    message=result['message']
                )
            else:
                return ApiResponse.not_found(message=result['message'])

        except Exception as e:
            logger.error(f"Customer profile error: {str(e)}")
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        summary="Update customer preferences",
        description="Cập nhật preferences của customer",
        request=CustomerProfileUpdateSerializer
    )
    def patch(self, request, *args, **kwargs):
        """PATCH method - Cập nhật customer preferences"""
        try:
            if not request.user.is_customer:
                return ApiResponse.forbidden(
                    message='Chỉ customer có thể cập nhật profile này'
                )

            # Validate request data (partial cho PATCH)
            serializer = CustomerProfileUpdateSerializer(
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)

            customer_service = CustomerProfileService()
            result = customer_service.update_customer_preferences(
                request.user,
                serializer.validated_data
            )

            if result['success']:
                # Get updated loyalty info
                loyalty_result = customer_service.get_loyalty_info(request.user)
                if loyalty_result['success']:
                    loyalty_serializer = LoyaltyInfoSerializer(loyalty_result['data'])
                    return ApiResponse.success(
                        data=loyalty_serializer.data,
                        message=result['message']
                    )
                else:
                    profile_serializer = CustomerProfileSerializer(result['data']['profile'])
                    return ApiResponse.success(
                        data=profile_serializer.data,
                        message=result['message']
                    )
            else:
                return ApiResponse.not_found(message=result['message'])

        except Exception as e:
            logger.error(f"Customer preferences update error: {str(e)}")
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserStatsView(StandardResponseMixin, APIView):
    """
    View cho user statistics
    Chỉ admin có quyền truy cập
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="User statistics",
        description="Lấy thống kê về người dùng"
    )
    def get(self, request, *args, **kwargs):
        """GET method - Lấy user statistics"""
        try:
            # Business rule: Chỉ admin có thể xem statistics
            if not (request.user.is_superuser or request.user.user_type == 'admin'):
                return ApiResponse.forbidden(
                    message='Chỉ admin có quyền xem thống kê người dùng'
                )

            from .selectors import UserSelector
            user_selector = UserSelector()

            stats = user_selector.get_user_statistics()
            return ApiResponse.success(
                data=stats,
                message='Lấy thống kê người dùng thành công'
            )

        except Exception as e:
            logger.error(f"User stats error: {str(e)}")
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CustomerAnalyticsView(StandardResponseMixin, APIView):
    """
    View cho customer analytics
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Customer analytics",
        description="Lấy thống kê chi tiết về customers"
    )
    def get(self, request, *args, **kwargs):
        """GET method - Lấy customer analytics"""
        try:
            # Business rule: Manager trở lên có thể xem customer analytics
            if not (request.user.is_superuser or
                     request.user.user_type in ['admin', 'manager']):
                return ApiResponse.forbidden(
                    message='Bạn không có quyền xem analytics khách hàng'
                )

            from .selectors import CustomerProfileSelector
            customer_selector = CustomerProfileSelector()

            analytics = customer_selector.get_customer_analytics()
            return ApiResponse.success(
                data=analytics,
                message='Lấy analytics khách hàng thành công'
            )

        except Exception as e:
            logger.error(f"Customer analytics error: {str(e)}")
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StaffAnalyticsView(StandardResponseMixin, APIView):
    """
    View cho staff analytics
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Staff analytics",
        description="Lấy thống kê chi tiết về staff"
    )
    def get(self, request, *args, **kwargs):
        """GET method - Lấy staff analytics"""
        try:
            # Business rule: Manager trở lên có thể xem staff analytics
            if not (request.user.is_superuser or
                     request.user.user_type in ['admin', 'manager']):
                return ApiResponse.forbidden(
                    message='Bạn không có quyền xem analytics nhân viên'
                )

            from .selectors import StaffProfileSelector
            staff_selector = StaffProfileSelector()

            analytics = staff_selector.get_staff_analytics()
            return ApiResponse.success(
                data=analytics,
                message='Lấy analytics nhân viên thành công'
            )

        except Exception as e:
            logger.error(f"Staff analytics error: {str(e)}")
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )