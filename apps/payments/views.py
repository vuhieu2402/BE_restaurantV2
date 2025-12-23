"""
Views for Payments app
"""
from rest_framework.views import APIView
from rest_framework import permissions, status
from drf_spectacular.utils import extend_schema
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
import logging

from apps.api.mixins import StandardResponseMixin
from apps.api.response import ApiResponse
from .serializers import (
    PaymentMethodSerializer,
    PaymentSerializer,
    PaymentProcessSerializer,
    PaymentConfirmCODSerializer,
)
from .services import PaymentService
from .vnpay_service import vnpay_service
from .selectors import PaymentMethodSelector, PaymentSelector

logger = logging.getLogger(__name__)


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


class VNPayCallbackView(APIView):
    """
    POST /api/payments/vnpay/callback/
    Webhook callback từ VNPay - Server-to-Server
    Note: Public endpoint - không cần authentication
    """
    permission_classes = [permissions.AllowAny]

    def __init__(self):
        super().__init__()
        self.payment_service = PaymentService()

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        """
        Xử lý VNPay callback (server-to-server)

        VNPay gửi callback khi có kết quả thanh toán
        """
        logger.info(f"Received VNPay callback: {request.data}")

        try:
            # Verify and process VNPay callback
            is_valid, callback_data = vnpay_service.verify_callback(request.data)

            if not is_valid:
                logger.warning("Invalid VNPay callback signature")
                return JsonResponse({'status': 'error', 'message': 'Invalid signature'}, status=400)

            # Extract transaction reference
            transaction_ref = callback_data.get('transaction_ref')
            if not transaction_ref:
                logger.error("Missing transaction reference in VNPay callback")
                return JsonResponse({'status': 'error', 'message': 'Missing transaction reference'}, status=400)

            # Find payment by transaction ID
            try:
                payment = self.payment_service._get_payment_by_transaction_id(transaction_ref)
            except Exception:
                payment = None

            if not payment:
                logger.error(f"Payment not found for transaction: {transaction_ref}")
                return JsonResponse({'status': 'error', 'message': 'Payment not found'}, status=404)

            # Process payment result
            result = self.payment_service.process_vnpay_callback(payment, callback_data)

            if result['success']:
                return JsonResponse({'status': 'success', 'message': 'Payment processed successfully'})
            else:
                return JsonResponse({'status': 'error', 'message': result['message']}, status=400)

        except Exception as e:
            logger.error(f"Error processing VNPay callback: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)


class VNPayReturnView(APIView):
    """
    GET /api/payments/vnpay/return/
    Redirect URL sau khi khách hàng thanh toán xong trên VNPay
    """
    permission_classes = [permissions.AllowAny]

    def __init__(self):
        super().__init__()
        self.payment_service = PaymentService()

    def get(self, request):
        """
        Xử lý redirect từ VNPay sau khi khách hàng thanh toán

        Khách hàng sẽ được redirect về đây từ VNPay
        
        Note: Trên localhost, VNPay không thể gọi callback URL (IPN),
        nên ta phải update Payment status tại đây.
        """
        logger.info(f"VNPay return with data: {request.query_params}")

        try:
            # Log the raw callback data for debugging
            logger.info(f"Raw VNPay return data: {dict(request.query_params)}")

            # Verify and process VNPay return
            is_valid, callback_data = vnpay_service.verify_callback(request.query_params.dict())

            logger.info(f"VNPay verification result: {is_valid}")
            if callback_data:
                logger.info(f"Processed callback data: {callback_data}")

            if not is_valid:
                logger.warning("Invalid VNPay return signature")
                context = {
                    'error_message': 'Chữ ký xác thực không hợp lệ. Giao dịch có thể bị giả mạo.',
                    'error_code': 'INVALID_SIGNATURE',
                }
                return render(request, 'payments/payment_failed.html', context, status=400)

            # Extract transaction reference
            transaction_ref = callback_data.get('transaction_ref')
            if not transaction_ref:
                logger.error("Missing transaction reference in VNPay return")
                context = {
                    'error_message': 'Thiếu thông tin giao dịch từ VNPay.',
                    'error_code': 'MISSING_TXN_REF',
                }
                return render(request, 'payments/payment_failed.html', context, status=400)

            # Find payment
            try:
                payment = self.payment_service._get_payment_by_transaction_id(transaction_ref)
            except Exception:
                payment = None

            if not payment:
                logger.error(f"Payment not found for transaction: {transaction_ref}")
                context = {
                    'error_message': 'Không tìm thấy thông tin thanh toán trong hệ thống.',
                    'error_code': 'PAYMENT_NOT_FOUND',
                }
                return render(request, 'payments/payment_failed.html', context, status=404)

            # Get response code
            response_code = callback_data.get('response_code')
            success = response_code == '00'

            logger.info(f"Payment response code: {response_code}, success: {success}")

            # ⭐ UPDATE PAYMENT STATUS (vì callback URL không accessible trên localhost)
            logger.info(f"Processing VNPay callback for payment ID: {payment.id}")
            result = self.payment_service.process_vnpay_callback(payment, callback_data)
            
            logger.info(f"Process result: {result}")
            
            if not result['success']:
                logger.error(f"Failed to process VNPay payment: {result['message']}")

            # Reload payment to get updated status
            payment.refresh_from_db()
            logger.info(f"Payment status after update: {payment.status}")

            # Format amount with thousand separators
            amount_formatted = f"{payment.amount:,.0f}".replace(',', '.')

            if success:
                # Render success template
                context = {
                    'amount': amount_formatted,
                }
                return render(request, 'payments/payment_success.html', context)
            else:
                # Render failed template
                error_message = vnpay_service.get_error_message(response_code)
                context = {
                    'error_message': error_message,
                    'error_code': response_code,
                }
                return render(request, 'payments/payment_failed.html', context)

        except Exception as e:
            logger.error(f"Error processing VNPay return: {str(e)}", exc_info=True)
            context = {
                'error_message': 'Đã xảy ra lỗi khi xử lý thanh toán. Vui lòng liên hệ hỗ trợ.',
                'error_code': 'SYSTEM_ERROR',
            }
            return render(request, 'payments/payment_failed.html', context, status=500)


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
