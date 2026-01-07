"""
Views for Reservations app
"""
from rest_framework.views import APIView
from rest_framework import permissions, status
from rest_framework.generics import ListAPIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.utils.decorators import method_decorator
from django.shortcuts import render
import logging

from apps.api.mixins import StandardResponseMixin
from apps.api.response import ApiResponse
from .serializers import (
    ReservationSerializer,
    ReservationListSerializer,
    ReservationCreateSerializer,
    ReservationUpdateStatusSerializer,
    ReservationCancelSerializer,
    ReservationDepositPaymentSerializer,
    TableStatusSerializer,
)
from .services import ReservationService, ReservationDepositService, ReservationSelector

logger = logging.getLogger(__name__)


class ReservationListView(StandardResponseMixin, APIView):
    """
    GET /api/reservations/
    Lấy danh sách reservation của user hiện tại
    """
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.selector = ReservationSelector()

    @extend_schema(
        tags=['Reservations'],
        summary="List customer reservations",
        description="Lấy danh sách đặt bàn của khách hàng đang đăng nhập",
        parameters=[
            OpenApiParameter(
                name='status',
                description='Filter by status (pending, confirmed, completed, cancelled)',
                type=str,
                required=False
            ),
        ],
        responses={200: ReservationListSerializer(many=True)}
    )
    def get(self, request):
        """Get list of customer's reservations"""
        # Get status filter
        status_filter = request.query_params.get('status')

        # Get reservations
        reservations = self.selector.get_customer_reservations(
            user=request.user,
            status=status_filter
        )

        serializer = ReservationListSerializer(reservations, many=True)

        return ApiResponse.success(
            data=serializer.data,
            message="Lấy danh sách đặt bàn thành công"
        )


class ReservationDetailView(StandardResponseMixin, APIView):
    """
    GET /api/reservations/{id}/
    Chi tiết reservation
    """
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.selector = ReservationSelector()

    @extend_schema(
        tags=['Reservations'],
        summary="Get reservation detail",
        description="Lấy chi tiết đặt bàn",
        responses={200: ReservationSerializer}
    )
    def get(self, request, reservation_id):
        """Get reservation detail"""
        reservation = self.selector.get_reservation_by_id(
            reservation_id=reservation_id,
            user=request.user
        )

        if not reservation:
            return ApiResponse.not_found(
                message="Reservation không tồn tại hoặc bạn không có quyền truy cập"
            )

        serializer = ReservationSerializer(reservation)

        return ApiResponse.success(
            data=serializer.data,
            message="Lấy thông tin đặt bàn thành công"
        )


class ReservationCreateView(StandardResponseMixin, APIView):
    """
    POST /api/reservations/
    Tạo reservation mới
    """
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.reservation_service = ReservationService()

    @extend_schema(
        tags=['Reservations'],
        summary="Create reservation",
        description="Tạo đặt bàn mới",
        request=ReservationCreateSerializer,
        responses={201: ReservationSerializer}
    )
    def post(self, request):
        """Create new reservation"""
        # Validate input
        serializer = ReservationCreateSerializer(
            data=request.data
        )

        if not serializer.is_valid():
            return ApiResponse.validation_error(
                message="Dữ liệu không hợp lệ",
                errors=serializer.errors
            )

        # Create reservation
        result = self.reservation_service.create_reservation(
            user=request.user,
            data=serializer.validated_data
        )

        if not result['success']:
            return ApiResponse.error(
                message=result['message']
            )

        # Serialize reservation
        reservation_serializer = ReservationSerializer(result['reservation'])

        return ApiResponse.success(
            data=reservation_serializer.data,
            message=result['message'],
            status_code=status.HTTP_201_CREATED
        )


class ReservationUpdateStatusView(StandardResponseMixin, APIView):
    """
    PATCH /api/reservations/{id}/status/
    Cập nhật trạng thái reservation (dành cho staff)
    """
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.reservation_service = ReservationService()
        self.selector = ReservationSelector()

    @extend_schema(
        tags=['Reservations'],
        summary="Update reservation status",
        description="Cập nhật trạng thái đặt bàn (staff only)",
        request=ReservationUpdateStatusSerializer,
        responses={200: ReservationSerializer}
    )
    def patch(self, request, reservation_id):
        """Update reservation status"""
        # TODO: Add staff permission check
        # if request.user.user_type not in ['staff', 'manager', 'admin']:
        #     return ApiResponse.forbidden(message="Chỉ staff mới có quyền cập nhật trạng thái")

        # Get reservation
        reservation = self.selector.get_reservation_by_id(
            reservation_id=reservation_id
        )

        if not reservation:
            return ApiResponse.not_found(
                message="Reservation không tồn tại"
            )

        # Validate input
        serializer = ReservationUpdateStatusSerializer(
            data=request.data,
            context={'reservation': reservation}
        )

        if not serializer.is_valid():
            return ApiResponse.validation_error(
                message="Dữ liệu không hợp lệ",
                errors=serializer.errors
            )

        # Update status
        result = self.reservation_service.update_reservation_status(
            reservation_id=reservation_id,
            new_status=serializer.validated_data['status'],
            notes=serializer.validated_data.get('notes'),
            staff_user=request.user
        )

        if not result['success']:
            return ApiResponse.error(
                message=result['message']
            )

        # Serialize reservation
        reservation_serializer = ReservationSerializer(result['reservation'])

        return ApiResponse.success(
            data=reservation_serializer.data,
            message=result['message']
        )


class ReservationCancelView(StandardResponseMixin, APIView):
    """
    POST /api/reservations/{id}/cancel/
    Hủy reservation
    """
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.reservation_service = ReservationService()
        self.selector = ReservationSelector()

    @extend_schema(
        tags=['Reservations'],
        summary="Cancel reservation",
        description="Hủy đặt bàn",
        request=ReservationCancelSerializer,
        responses={200: ReservationSerializer}
    )
    def post(self, request, reservation_id):
        """Cancel reservation"""
        # Get reservation
        reservation = self.selector.get_reservation_by_id(
            reservation_id=reservation_id,
            user=request.user
        )

        if not reservation:
            return ApiResponse.not_found(
                message="Reservation không tồn tại hoặc bạn không có quyền"
            )

        # Validate input
        serializer = ReservationCancelSerializer(
            data=request.data,
            context={'reservation': reservation}
        )

        if not serializer.is_valid():
            return ApiResponse.validation_error(
                message="Dữ liệu không hợp lệ",
                errors=serializer.errors
            )

        # Cancel reservation
        result = self.reservation_service.cancel_reservation(
            reservation_id=reservation_id,
            cancel_reason=serializer.validated_data['cancel_reason'],
            user=request.user
        )

        if not result['success']:
            return ApiResponse.error(
                message=result['message']
            )

        # Serialize reservation
        reservation_serializer = ReservationSerializer(result['reservation'])

        return ApiResponse.success(
            data=reservation_serializer.data,
            message=result['message']
        )


class ReservationDepositPaymentView(StandardResponseMixin, APIView):
    """
    POST /api/reservations/{id}/pay-deposit/
    Tạo payment cho deposit của reservation
    """
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.deposit_service = ReservationDepositService()

    @extend_schema(
        tags=['Reservations'],
        summary="Pay reservation deposit",
        description="Tạo thanh toán cọc cho đặt bàn",
        request=ReservationDepositPaymentSerializer,
        responses={201: ReservationSerializer}
    )
    def post(self, request, reservation_id):
        """Create payment for reservation deposit"""
        # Validate input
        input_data = {
            'reservation_id': reservation_id,
            'payment_method_id': request.data.get('payment_method_id')
        }

        serializer = ReservationDepositPaymentSerializer(
            data=input_data,
            context={'user': request.user}
        )

        if not serializer.is_valid():
            return ApiResponse.validation_error(
                message="Dữ liệu không hợp lệ",
                errors=serializer.errors
            )

        # Create payment
        result = self.deposit_service.create_deposit_payment(
            reservation_id=reservation_id,
            payment_method_id=serializer.validated_data['payment_method_id'],
            user=request.user
        )

        if not result['success']:
            return ApiResponse.error(
                message=result['message']
            )

        # Serialize payment
        from apps.payments.serializers import PaymentSerializer
        payment_serializer = PaymentSerializer(result['payment'])

        response_data = payment_serializer.data

        # Add payment_url nếu có (online payment)
        if result.get('payment_url'):
            response_data['payment_url'] = result['payment_url']

        return ApiResponse.success(
            data=response_data,
            message=result['message'],
            status_code=status.HTTP_201_CREATED
        )


class ReservationPaymentStatusView(StandardResponseMixin, APIView):
    """
    GET /api/reservations/{id}/payment-status/
    Lấy trạng thái thanh toán deposit của reservation
    """
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.deposit_service = ReservationDepositService()

    @extend_schema(
        tags=['Reservations'],
        summary="Get reservation payment status",
        description="Lấy trạng thái thanh toán cọc",
        responses={200: 'dict'}  # Payment info dict
    )
    def get(self, request, reservation_id):
        """Get payment status for reservation"""
        # Get payment
        result = self.deposit_service.get_payment_by_reservation(
            reservation_id=reservation_id,
            user=request.user
        )

        if not result['success']:
            return ApiResponse.error(
                message=result['message']
            )

        if result['payment']:
            from apps.payments.serializers import PaymentSerializer
            payment_serializer = PaymentSerializer(result['payment'])

            return ApiResponse.success(
                data=payment_serializer.data,
                message=result['message']
            )
        else:
            return ApiResponse.success(
                data=None,
                message=result['message']
            )


class ReservationSuccessView(APIView):
    """
    GET /api/reservations/success/
    Render trang success sau khi tạo reservation thành công
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """Render success template"""
        reservation_number = request.query_params.get('reservation_number')
        deposit_amount = request.query_params.get('deposit_amount', '300000')

        context = {
            'reservation_number': reservation_number,
            'deposit_amount': deposit_amount,
        }
        return render(request, 'reservations/reservation_success.html', context)


class ReservationPaymentReturnView(APIView):
    """
    GET /api/reservations/payment/return/
    Redirect URL sau khi khách hàng thanh toán deposit xong
    (Similar to VNPay return but for reservations)
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """
        Xử lý redirect từ payment gateway sau khi khách hàng thanh toán deposit
        """
        # This will be handled by the existing VNPay return flow
        # Just redirect to a success page
        reservation_id = request.query_params.get('reservation_id')
        payment_id = request.query_params.get('payment_id')

        context = {
            'reservation_id': reservation_id,
            'payment_id': payment_id,
        }
        return render(request, 'reservations/deposit_payment_success.html', context)


class TableStatusView(StandardResponseMixin, APIView):
    """
    GET /api/reservations/tables/status/
    Check trạng thái của các bàn theo thời gian ngày hiện tại
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Reservations'],
        summary="Check table status by time",
        description="Kiểm tra trạng thái của các bàn theo thời gian ngày hiện tại",
        parameters=[
            OpenApiParameter(
                name='restaurant_id',
                description='ID nhà hàng (required)',
                type=int,
                required=True
            ),
            OpenApiParameter(
                name='date',
                description='Ngày cần check (YYYY-MM-DD, default: today)',
                type=str,
                required=False
            ),
            OpenApiParameter(
                name='time',
                description='Giờ cần check (HH:MM, default: current time)',
                type=str,
                required=False
            ),
        ],
        responses={200: TableStatusSerializer(many=True)}
    )
    def get(self, request):
        """Check table status by time"""
        from django.utils import timezone
        from datetime import datetime, timedelta
        from apps.restaurants.models import Table, Restaurant

        # Get parameters
        restaurant_id = request.query_params.get('restaurant_id')
        date_str = request.query_params.get('date')
        time_str = request.query_params.get('time')

        # Validate restaurant_id
        if not restaurant_id:
            return ApiResponse.validation_error(
                message="Thiếu restaurant_id"
            )

        try:
            restaurant = Restaurant.objects.get(id=restaurant_id, is_active=True)
        except Restaurant.DoesNotExist:
            return ApiResponse.not_found(
                message="Nhà hàng không tồn tại hoặc không hoạt động"
            )

        # Parse date
        if date_str:
            try:
                check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return ApiResponse.validation_error(
                    message="Định dạng ngày không hợp lệ (YYYY-MM-DD)"
                )
        else:
            check_date = timezone.now().date()

        # Parse time
        if time_str:
            try:
                check_time = datetime.strptime(time_str, '%H:%M').time()
            except ValueError:
                return ApiResponse.validation_error(
                    message="Định dạng giờ không hợp lệ (HH:MM)"
                )
        else:
            check_time = timezone.now().time()

        # Combine to datetime
        check_datetime = timezone.make_aware(
            datetime.combine(check_date, check_time)
        )

        # Get all tables for the restaurant
        tables = Table.objects.filter(
            restaurant=restaurant,
            is_active=True
        ).order_by('floor', 'table_number')

        # Get reservations for the date
        from .models import Reservation

        reservations = Reservation.objects.filter(
            restaurant=restaurant,
            reservation_date=check_date,
            status__in=['pending', 'confirmed']
        ).select_related('table')

        table_status_list = []

        for table in tables:
            # Find reservations for this table
            table_reservations = reservations.filter(table=table)

            # Determine current status based on reservations
            current_status = 'available'
            is_available = True

            # Check if table is in maintenance (from table.status)
            if table.status == 'maintenance':
                current_status = 'maintenance'
                is_available = False
            else:
                # Check if table is reserved at the check time
                for reservation in table_reservations:
                    reservation_datetime = timezone.make_aware(
                        datetime.combine(reservation.reservation_date, reservation.reservation_time)
                    )

                    # Assume reservation lasts 2 hours
                    reservation_end = reservation_datetime + timedelta(hours=2)

                    if reservation_datetime <= check_datetime <= reservation_end:
                        current_status = 'reserved'
                        is_available = False
                        break

            # Build reservation info
            reservation_info = []
            for reservation in table_reservations:
                reservation_datetime = timezone.make_aware(
                    datetime.combine(reservation.reservation_date, reservation.reservation_time)
                )
                reservation_end = reservation_datetime + timedelta(hours=2)

                reservation_info.append({
                    'reservation_id': reservation.id,
                    'reservation_number': reservation.reservation_number,
                    'reservation_time': reservation.reservation_time.strftime('%H:%M'),
                    'reservation_end': reservation_end.time().strftime('%H:%M'),
                    'number_of_guests': reservation.number_of_guests,
                    'status': reservation.status,
                    'status_display': reservation.get_status_display(),
                    'contact_name': reservation.contact_name,
                    'contact_phone': reservation.contact_phone,
                })

            table_status_list.append({
                'table_id': table.id,
                'table_number': table.table_number,
                'floor': table.floor,
                'section': table.section,
                'capacity': table.capacity,
                'current_status': current_status,
                'status_display': dict(Table.STATUS_CHOICES).get(current_status, current_status),
                'is_available': is_available,
                'reservations': reservation_info,
                'x_position': table.x_position,
                'y_position': table.y_position,
            })

        serializer = TableStatusSerializer(table_status_list, many=True)

        return ApiResponse.success(
            data=serializer.data,
            message=f"Lấy trạng thái bàn thành công cho ngày {check_date} lúc {check_time}"
        )
