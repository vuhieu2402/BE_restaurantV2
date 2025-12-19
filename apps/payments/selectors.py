"""
Selector layer for Payments app
Chỉ xử lý SELECT queries
"""
from .models import Payment, PaymentMethod


class PaymentMethodSelector:
    """
    Selector cho PaymentMethod
    """
    
    def get_active_payment_methods(self):
        """
        Lấy danh sách payment methods đang active
        
        Returns:
            QuerySet of PaymentMethod
        """
        return PaymentMethod.objects.filter(
            is_active=True
        ).order_by('display_order', 'name')
    
    def get_payment_method_by_id(self, method_id):
        """
        Lấy payment method theo ID
        
        Returns:
            PaymentMethod object hoặc None
        """
        try:
            return PaymentMethod.objects.get(id=method_id, is_active=True)
        except PaymentMethod.DoesNotExist:
            return None
    
    def get_payment_method_by_code(self, code):
        """
        Lấy payment method theo code
        
        Returns:
            PaymentMethod object hoặc None
        """
        try:
            return PaymentMethod.objects.get(code=code, is_active=True)
        except PaymentMethod.DoesNotExist:
            return None


class PaymentSelector:
    """
    Selector cho Payment
    """
    
    def get_payment_by_id(self, payment_id, user=None):
        """
        Lấy payment theo ID
        
        Args:
            payment_id: ID của payment
            user: User (optional) để validate ownership
        
        Returns:
            Payment object hoặc None
        """
        try:
            queryset = Payment.objects.select_related(
                'order',
                'customer',
                'payment_method'
            )
            
            if user:
                payment = queryset.get(id=payment_id, customer=user)
            else:
                payment = queryset.get(id=payment_id)
            
            return payment
        except Payment.DoesNotExist:
            return None
    
    def get_payment_by_order(self, order_id):
        """
        Lấy payment của order
        
        Returns:
            Payment object hoặc None
        """
        try:
            return Payment.objects.select_related(
                'payment_method'
            ).get(order_id=order_id)
        except Payment.DoesNotExist:
            return None
    
    def get_user_payments(self, user, filters=None):
        """
        Lấy danh sách payments của user
        
        Args:
            user: User object
            filters: Dict filter options
        
        Returns:
            QuerySet of Payments
        """
        queryset = Payment.objects.filter(
            customer=user
        ).select_related(
            'order',
            'payment_method'
        ).order_by('-created_at')
        
        if not filters:
            return queryset
        
        # Apply filters
        if filters.get('status'):
            queryset = queryset.filter(status=filters['status'])
        
        if filters.get('payment_method_id'):
            queryset = queryset.filter(payment_method_id=filters['payment_method_id'])
        
        if filters.get('date_from'):
            queryset = queryset.filter(created_at__gte=filters['date_from'])
        
        if filters.get('date_to'):
            queryset = queryset.filter(created_at__lte=filters['date_to'])
        
        return queryset
