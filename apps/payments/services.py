"""
Service layer for Payments app
Xử lý business logic cho Payment
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import Payment, PaymentMethod
from apps.orders.models import Order


class PaymentService:
    """
    Service layer - Xử lý business logic cho Payment
    """
    
    @transaction.atomic
    def create_payment_for_order(self, order_id, payment_method_id, user):
        """
        Tạo Payment cho Order
        
        Args:
            order_id: ID của order
            payment_method_id: ID của payment method
            user: User thực hiện thanh toán
        
        Returns:
            dict: {
                'success': bool,
                'payment': Payment object,
                'payment_url': str (nếu là online payment),
                'message': str
            }
        """
        try:
            # Get order
            order = Order.objects.select_related('restaurant').get(
                id=order_id,
                customer=user
            )
        except Order.DoesNotExist:
            return {
                'success': False,
                'message': 'Đơn hàng không tồn tại hoặc bạn không có quyền.'
            }
        
        # Validate order chưa có payment
        if hasattr(order, 'payment') and order.payment:
            return {
                'success': False,
                'message': 'Đơn hàng đã có thanh toán.',
                'payment': order.payment
            }
        
        # Validate order status
        if order.status not in ['pending', 'confirmed']:
            return {
                'success': False,
                'message': f'Không thể thanh toán cho đơn hàng ở trạng thái "{order.get_status_display()}".'
            }
        
        # Get payment method
        try:
            payment_method = PaymentMethod.objects.get(
                id=payment_method_id,
                is_active=True
            )
        except PaymentMethod.DoesNotExist:
            return {
                'success': False,
                'message': 'Phương thức thanh toán không tồn tại hoặc không khả dụng.'
            }
        
        # Create Payment
        payment = Payment.objects.create(
            order=order,
            customer=user,
            payment_method=payment_method,
            amount=order.total,
            currency='VND',
            status='pending'
        )
        
        # Update order payment_method
        order.payment_method = payment_method
        order.save(update_fields=['payment_method'])
        
        result = {
            'success': True,
            'payment': payment,
            'message': 'Tạo thanh toán thành công.'
        }
        
        # Xử lý theo loại payment
        if payment_method.requires_online:
            # Online payment - cần redirect đến gateway
            # TODO: Implement payment gateway integration (VNPay, MoMo, ZaloPay)
            payment_url = self._generate_payment_url(payment, payment_method)
            result['payment_url'] = payment_url
            result['message'] = 'Vui lòng thanh toán qua link.'
        else:
            # COD hoặc thanh toán tại quầy
            # Tự động confirm order (chờ nhận tiền)
            if order.status == 'pending':
                order.status = 'confirmed'
                order.save(update_fields=['status'])
            
            result['message'] = 'Đơn hàng đã được xác nhận. Thanh toán khi nhận hàng.'
        
        return result
    
    def _generate_payment_url(self, payment, payment_method):
        """
        Generate payment URL cho online payment gateway
        
        Args:
            payment: Payment object
            payment_method: PaymentMethod object
        
        Returns:
            str: Payment URL
        
        TODO: Implement integration với các gateway thực tế:
        - VNPay
        - MoMo
        - ZaloPay
        - Stripe
        """
        # Placeholder - cần implement theo từng gateway
        gateway_code = payment_method.code.lower()
        
        if gateway_code == 'vnpay':
            # TODO: Integrate VNPay
            return f"https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?payment_id={payment.id}"
        
        elif gateway_code == 'momo':
            # TODO: Integrate MoMo
            return f"https://test-payment.momo.vn/pay?payment_id={payment.id}"
        
        elif gateway_code == 'zalopay':
            # TODO: Integrate ZaloPay
            return f"https://sbgateway.zalopay.vn/pay?payment_id={payment.id}"
        
        else:
            # Default placeholder
            return f"http://localhost:8000/payment/{payment.payment_number}/process"
    
    def process_payment_callback(self, payment_id, callback_data):
        """
        Xử lý callback từ payment gateway
        
        Args:
            payment_id: ID của payment
            callback_data: Dict chứa data từ gateway
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            payment = Payment.objects.select_related('order').get(id=payment_id)
        except Payment.DoesNotExist:
            return {
                'success': False,
                'message': 'Payment không tồn tại.'
            }
        
        # Validate callback (TODO: verify signature từ gateway)
        # ...
        
        # Update payment status
        is_success = callback_data.get('success', False)
        
        if is_success:
            payment.status = 'completed'
            payment.transaction_id = callback_data.get('transaction_id')
            payment.paid_at = timezone.now()
            payment.gateway_response = callback_data
            payment.save()
            
            # Signal sẽ tự động update Order status
            
            return {
                'success': True,
                'message': 'Thanh toán thành công.',
                'payment': payment
            }
        else:
            payment.status = 'failed'
            payment.failure_reason = callback_data.get('message', 'Thanh toán thất bại')
            payment.gateway_response = callback_data
            payment.save()
            
            return {
                'success': False,
                'message': payment.failure_reason,
                'payment': payment
            }
    
    def confirm_cod_payment(self, payment_id, staff_user, notes=None):
        """
        Xác nhận đã nhận tiền COD (dành cho staff)
        
        Args:
            payment_id: ID của payment
            staff_user: Staff xác nhận
            notes: Ghi chú
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            payment = Payment.objects.select_related('order', 'payment_method').get(
                id=payment_id
            )
        except Payment.DoesNotExist:
            return {
                'success': False,
                'message': 'Payment không tồn tại.'
            }
        
        # Validate là COD
        if payment.payment_method.requires_online:
            return {
                'success': False,
                'message': 'Chỉ xác nhận được thanh toán COD.'
            }
        
        # Validate status
        if payment.status not in ['pending', 'processing']:
            return {
                'success': False,
                'message': f'Không thể xác nhận payment ở trạng thái "{payment.get_status_display()}".'
            }
        
        # Update payment
        payment.status = 'completed'
        payment.paid_at = timezone.now()
        if notes:
            payment.notes = notes
        payment.save()
        
        # Signal sẽ tự động update Order status
        
        return {
            'success': True,
            'message': 'Đã xác nhận nhận tiền thành công.',
            'payment': payment
        }
    
    def refund_payment(self, payment_id, staff_user, reason):
        """
        Hoàn tiền (dành cho staff/admin)
        
        Args:
            payment_id: ID của payment
            staff_user: Staff thực hiện refund
            reason: Lý do hoàn tiền
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            payment = Payment.objects.select_related('order').get(id=payment_id)
        except Payment.DoesNotExist:
            return {
                'success': False,
                'message': 'Payment không tồn tại.'
            }
        
        # Validate payment đã completed
        if payment.status != 'completed':
            return {
                'success': False,
                'message': 'Chỉ có thể hoàn tiền cho payment đã thanh toán.'
            }
        
        # Update payment
        payment.status = 'refunded'
        payment.refunded_at = timezone.now()
        payment.notes = f"Hoàn tiền bởi {staff_user.username}. Lý do: {reason}\n{payment.notes or ''}"
        payment.save()
        
        # Signal sẽ tự động update Order status = 'refunded'
        
        # TODO: Gọi API gateway để hoàn tiền thực tế
        
        return {
            'success': True,
            'message': 'Đã hoàn tiền thành công.',
            'payment': payment
        }
