"""
Views for Payments app
"""
from rest_framework.views import APIView
from rest_framework import permissions, status
from drf_spectacular.utils import extend_schema
from apps.api.mixins import StandardResponseMixin
from apps.api.response import ApiResponse
from .serializers import (
    PaymentMethodSerializer,
    PaymentSerializer,
    PaymentProcessSerializer,
    PaymentConfirmCODSerializer,
)
from .services import PaymentService
from .selectors import PaymentMethodSelector, PaymentSelector


class PaymentMethodListView(StandardResponseMixin, APIView):
    """
    GET /api/payments/methods/
    Lấy danh sách phương thức thanh toán available
    """
    permission_classes = [permissions.AllowAny]
    
    def __init__(self):
        super().__init__()
        self.selector = PaymentMethodSelector()
    
    @extend_schema(
        tags=['Payments'],
        summary="List payment methods",
        description="Lấy danh sách phương thức thanh toán",
        responses={200: PaymentMethodSerializer(many=True)}
    )
    def get(self, request):
        """Get all active payment methods"""
        methods = self.selector.get_active_payment_methods()
        serializer = PaymentMethodSerializer(methods, many=True)
        
        return ApiResponse.success(
            data=serializer.data,
            message="Lấy danh sách phương thức thanh toán thành công"
        )


class PaymentProcessView(StandardResponseMixin, APIView):
    """
    POST /api/payments/process/
    Tạo payment cho order và xử lý thanh toán
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.payment_service = PaymentService()
    
    @extend_schema(
        tags=['Payments'],
        summary="Process payment",
        description="Tạo payment cho order và xử lý thanh toán",
        request=PaymentProcessSerializer,
        responses={201: PaymentSerializer}
    )
    def post(self, request):
        """Process payment for order"""
        # Validate input
        serializer = PaymentProcessSerializer(
            data=request.data,
            context={'user': request.user}
        )
        
        if not serializer.is_valid():
            return ApiResponse.validation_error(
                message="Dữ liệu không hợp lệ",
                errors=serializer.errors
            )
        
        # Create and process payment
        result = self.payment_service.create_payment_for_order(
            order_id=serializer.validated_data['order_id'],
            payment_method_id=serializer.validated_data['payment_method_id'],
            user=request.user
        )
        
        if not result['success']:
            return ApiResponse.validation_error(
                message=result['message']
            )
        
        # Serialize payment
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


class PaymentDetailView(StandardResponseMixin, APIView):
    """
    GET /api/payments/{payment_id}/
    Chi tiết payment
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.selector = PaymentSelector()
    
    @extend_schema(
        tags=['Payments'],
        summary="Get payment detail",
        description="Lấy chi tiết payment",
        responses={200: PaymentSerializer}
    )
    def get(self, request, payment_id):
        """Get payment detail"""
        payment = self.selector.get_payment_by_id(payment_id, user=request.user)
        
        if not payment:
            return ApiResponse.not_found(
                message="Payment không tồn tại"
            )
        
        serializer = PaymentSerializer(payment)
        
        return ApiResponse.success(
            data=serializer.data,
            message="Lấy thông tin payment thành công"
        )


class PaymentConfirmCODView(StandardResponseMixin, APIView):
    """
    POST /api/payments/{payment_id}/confirm-cod/
    Xác nhận đã nhận tiền COD (dành cho staff)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def __init__(self):
        super().__init__()
        self.payment_service = PaymentService()
    
    @extend_schema(
        tags=['Payments'],
        summary="Confirm COD payment",
        description="Xác nhận đã nhận tiền COD (staff)",
        request=PaymentConfirmCODSerializer,
        responses={200: PaymentSerializer}
    )
    def post(self, request, payment_id):
        """Confirm COD payment received"""
        # TODO: Add staff permission check
        # if not request.user.is_staff:
        #     return ApiResponse.forbidden(message="Chỉ staff mới có quyền xác nhận")
        
        # Validate input
        serializer = PaymentConfirmCODSerializer(data=request.data)
        
        if not serializer.is_valid():
            return ApiResponse.validation_error(
                message="Dữ liệu không hợp lệ",
                errors=serializer.errors
            )
        
        # Confirm COD
        result = self.payment_service.confirm_cod_payment(
            payment_id=payment_id,
            staff_user=request.user,
            notes=serializer.validated_data.get('notes')
        )
        
        if not result['success']:
            return ApiResponse.error(
                message=result['message']
            )
        
        # Return payment
        payment_serializer = PaymentSerializer(result['payment'])
        
        return ApiResponse.success(
            data=payment_serializer.data,
            message=result['message']
        )


class PaymentCallbackView(APIView):
    """
    POST /api/payments/callback/{gateway}/
    Webhook callback từ payment gateway (VNPay, MoMo, etc.)
    
    Note: Public endpoint - không cần authentication
    """
    permission_classes = [permissions.AllowAny]
    
    def __init__(self):
        super().__init__()
        self.payment_service = PaymentService()
    
    def post(self, request, gateway):
        """
        Process payment gateway callback
        
        TODO: Implement theo từng gateway:
        - Verify signature
        - Parse callback data
        - Update payment status
        """
        # Get payment_id từ callback
        payment_id = request.data.get('payment_id') or request.query_params.get('payment_id')
        
        if not payment_id:
            return ApiResponse.validation_error(
                message="Missing payment_id"
            )
        
        # Process callback
        result = self.payment_service.process_payment_callback(
            payment_id=payment_id,
            callback_data=request.data
        )
        
        if result['success']:
            return ApiResponse.success(
                message=result['message']
            )
        else:
            return ApiResponse.error(
                message=result['message']
            )
