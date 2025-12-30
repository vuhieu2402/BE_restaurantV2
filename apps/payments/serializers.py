"""
Serializers for Payments app
"""
from rest_framework import serializers
from .models import Payment, PaymentMethod


class PaymentMethodSerializer(serializers.ModelSerializer):
    """
    Serializer cho PaymentMethod - hiển thị danh sách phương thức thanh toán
    """
    icon_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id',
            'name',
            'code',
            'description',
            'icon',
            'icon_url',
            'requires_online',
            'is_active',
        ]
    
    def get_icon_url(self, obj):
        """Lấy URL icon"""
        if obj.icon:
            return obj.icon.url
        return None


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer đầy đủ cho Payment
    """
    payment_method_info = serializers.SerializerMethodField()
    order_info = serializers.SerializerMethodField()
    reservation_info = serializers.SerializerMethodField()
    payment_type = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    amount_display = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id',
            'payment_number',
            'payment_type',
            'order',
            'order_info',
            'reservation',
            'reservation_info',
            'customer',
            'payment_method',
            'payment_method_info',
            'status',
            'status_display',
            'amount',
            'amount_display',
            'currency',
            'transaction_id',
            'payment_gateway',
            'card_last_four',
            'card_brand',
            'paid_at',
            'refunded_at',
            'notes',
            'failure_reason',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'payment_number', 'created_at', 'updated_at',
            'paid_at', 'refunded_at'
        ]

    def get_payment_type(self, obj):
        """Loại payment: 'order' hoặc 'reservation'"""
        return obj.payment_type

    def get_payment_method_info(self, obj):
        """Lấy thông tin payment method"""
        if obj.payment_method:
            return {
                'id': obj.payment_method.id,
                'name': obj.payment_method.name,
                'code': obj.payment_method.code,
                'requires_online': obj.payment_method.requires_online,
            }
        return None

    def get_order_info(self, obj):
        """Lấy thông tin order"""
        if obj.order:
            return {
                'id': obj.order.id,
                'order_number': obj.order.order_number,
                'order_type': obj.order.order_type,
                'status': obj.order.status,
            }
        return None

    def get_reservation_info(self, obj):
        """Lấy thông tin reservation"""
        if obj.reservation:
            return {
                'id': obj.reservation.id,
                'reservation_number': obj.reservation.reservation_number,
                'reservation_date': str(obj.reservation.reservation_date),
                'reservation_time': str(obj.reservation.reservation_time),
                'number_of_guests': obj.reservation.number_of_guests,
                'status': obj.reservation.status,
            }
        return None

    def get_amount_display(self, obj):
        """Format hiển thị amount"""
        return f"{obj.amount:,.0f}đ"


class PaymentProcessSerializer(serializers.Serializer):
    """
    Serializer cho việc process payment
    Input: order_id + payment_method_id
    """
    order_id = serializers.IntegerField(required=True)
    payment_method_id = serializers.IntegerField(required=True)
    
    def validate_order_id(self, value):
        """Validate order exists và thuộc về user"""
        from apps.orders.models import Order
        
        user = self.context.get('user')
        try:
            order = Order.objects.get(id=value, customer=user)
            
            # Validate order chưa có payment
            if hasattr(order, 'payment') and order.payment:
                raise serializers.ValidationError(
                    "Đơn hàng đã có thanh toán. Không thể tạo payment mới."
                )
            
            # Validate order status
            if order.status not in ['pending', 'confirmed']:
                raise serializers.ValidationError(
                    f"Không thể thanh toán cho đơn hàng ở trạng thái '{order.get_status_display()}'."
                )
            
            return value
        except Order.DoesNotExist:
            raise serializers.ValidationError("Đơn hàng không tồn tại.")
    
    def validate_payment_method_id(self, value):
        """Validate payment method exists và active"""
        try:
            payment_method = PaymentMethod.objects.get(id=value, is_active=True)
            return value
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError(
                "Phương thức thanh toán không tồn tại hoặc không khả dụng."
            )


class PaymentUpdateStatusSerializer(serializers.Serializer):
    """
    Serializer cho việc cập nhật payment status (webhook callback)
    """
    status = serializers.ChoiceField(
        choices=Payment.STATUS_CHOICES,
        required=True
    )
    transaction_id = serializers.CharField(required=False, allow_blank=True)
    gateway_response = serializers.JSONField(required=False)
    failure_reason = serializers.CharField(required=False, allow_blank=True)


class PaymentConfirmCODSerializer(serializers.Serializer):
    """
    Serializer cho việc confirm thanh toán COD (staff xác nhận đã nhận tiền)
    """
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500
    )
