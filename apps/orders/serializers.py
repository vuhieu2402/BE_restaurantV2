from rest_framework import serializers
from decimal import Decimal
from .models import Order, OrderItem
from apps.restaurants.models import Restaurant, Table


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer cho OrderItem - hiển thị chi tiết món trong order
    """
    menu_item_info = serializers.SerializerMethodField()
    subtotal_display = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderItem
        fields = [
            'id',
            'menu_item',
            'menu_item_info',
            'item_name',
            'item_price',
            'quantity',
            'special_instructions',
            'subtotal',
            'subtotal_display',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'subtotal']
    
    def get_menu_item_info(self, obj):
        """Lấy thông tin snapshot của menu item"""
        if obj.menu_item:
            return {
                'id': obj.menu_item.id,
                'name': obj.menu_item.name,
                'slug': obj.menu_item.slug,
                'image': obj.menu_item.image.url if obj.menu_item.image else None,
            }
        return None
    
    def get_subtotal_display(self, obj):
        """Format hiển thị subtotal"""
        return f"{obj.subtotal:,.0f}đ"


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer đầy đủ cho Order - hiển thị tất cả thông tin
    """
    items = OrderItemSerializer(many=True, read_only=True)
    customer_info = serializers.SerializerMethodField()
    restaurant_info = serializers.SerializerMethodField()
    table_info = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    payment_status = serializers.SerializerMethodField()
    is_paid = serializers.SerializerMethodField()
    
    # Display fields
    subtotal_display = serializers.SerializerMethodField()
    tax_display = serializers.SerializerMethodField()
    delivery_fee_display = serializers.SerializerMethodField()
    discount_display = serializers.SerializerMethodField()
    total_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'customer',
            'customer_info',
            'chain',
            'restaurant',
            'restaurant_info',
            'table',
            'table_info',
            'order_type',
            'order_type_display',
            'status',
            'status_display',
            'assignment_method',
            'assignment_distance',
            'delivery_address',
            'delivery_latitude',
            'delivery_longitude',
            'delivery_phone',
            'subtotal',
            'subtotal_display',
            'tax',
            'tax_display',
            'delivery_fee',
            'delivery_fee_display',
            'discount',
            'discount_display',
            'total',
            'total_display',
            'notes',
            'customer_notes',
            'estimated_time',
            'completed_at',
            'assigned_staff',
            'payment_method',
            'payment_status',
            'is_paid',
            'items',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id', 'order_number', 'created_at', 'updated_at',
            'assignment_distance', 'delivery_fee', 'subtotal', 'total'
        ]
    
    def get_customer_info(self, obj):
        """Lấy thông tin khách hàng"""
        if obj.customer:
            return {
                'id': obj.customer.id,
                'username': obj.customer.username,
                'full_name': obj.customer.get_full_name(),
                'email': obj.customer.email,
                'phone': obj.customer.phone_number if hasattr(obj.customer, 'phone_number') else None,
            }
        return None
    
    def get_restaurant_info(self, obj):
        """Lấy thông tin chi nhánh"""
        return obj.get_restaurant_info()
    
    def get_table_info(self, obj):
        """Lấy thông tin bàn"""
        if obj.table:
            return {
                'id': obj.table.id,
                'table_number': obj.table.table_number,
                'floor': obj.table.floor,
                'capacity': obj.table.capacity,
            }
        return None
    
    def get_subtotal_display(self, obj):
        return f"{obj.subtotal:,.0f}đ"
    
    def get_tax_display(self, obj):
        return f"{obj.tax:,.0f}đ"
    
    def get_delivery_fee_display(self, obj):
        return f"{obj.delivery_fee:,.0f}đ"
    
    def get_discount_display(self, obj):
        return f"{obj.discount:,.0f}đ"
    
    def get_total_display(self, obj):
        return f"{obj.total:,.0f}đ"
    
    def get_payment_status(self, obj):
        """Lấy trạng thái thanh toán"""
        return obj.get_payment_status()
    
    def get_is_paid(self, obj):
        """Kiểm tra đã thanh toán chưa"""
        return obj.is_paid()


class OrderListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer cho list view - chỉ hiển thị thông tin cơ bản
    """
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    order_type_display = serializers.CharField(source='get_order_type_display', read_only=True)
    total_display = serializers.SerializerMethodField()
    items_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'restaurant_name',
            'order_type',
            'order_type_display',
            'status',
            'status_display',
            'total',
            'total_display',
            'items_count',
            'created_at',
        ]
    
    def get_total_display(self, obj):
        return f"{obj.total:,.0f}đ"
    
    def get_items_count(self, obj):
        """Tổng số món trong đơn"""
        return obj.items.count()


class OrderCreateSerializer(serializers.Serializer):
    """
    Serializer cho việc tạo order từ cart
    Validate tất cả input và business rules
    """
    restaurant_id = serializers.IntegerField(required=True)
    order_type = serializers.ChoiceField(
        choices=Order.ORDER_TYPE_CHOICES,
        required=True
    )
    
    # Delivery fields
    delivery_address = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=500
    )
    delivery_latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True
    )
    delivery_longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True
    )
    delivery_phone = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=20
    )
    
    # Dine-in fields
    table_id = serializers.IntegerField(required=False, allow_null=True)
    
    # Optional fields
    customer_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000
    )
    tax = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        default=0
    )
    discount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        default=0
    )
    
    def validate_restaurant_id(self, value):
        """Validate restaurant exists and is active"""
        try:
            restaurant = Restaurant.objects.get(id=value, is_active=True)
            return value
        except Restaurant.DoesNotExist:
            raise serializers.ValidationError("Chi nhánh không tồn tại hoặc không hoạt động.")
    
    def validate_table_id(self, value):
        """Validate table exists and available"""
        if value:
            try:
                table = Table.objects.get(id=value, is_active=True)
                if table.status not in ['available', 'reserved']:
                    raise serializers.ValidationError("Bàn không khả dụng.")
                return value
            except Table.DoesNotExist:
                raise serializers.ValidationError("Bàn không tồn tại.")
        return value
    
    def validate(self, attrs):
        """Validate theo order_type"""
        order_type = attrs.get('order_type')
        
        if order_type == 'delivery':
            # Delivery phải có đầy đủ thông tin địa chỉ
            required_fields = ['delivery_address', 'delivery_latitude', 'delivery_longitude', 'delivery_phone']
            missing_fields = [field for field in required_fields if not attrs.get(field)]
            
            if missing_fields:
                raise serializers.ValidationError({
                    'delivery': f"Thiếu thông tin: {', '.join(missing_fields)}"
                })
        
        elif order_type == 'dine_in':
            # Dine-in phải có table_id
            if not attrs.get('table_id'):
                raise serializers.ValidationError({
                    'table_id': 'Vui lòng chọn bàn cho đơn ăn tại chỗ.'
                })
            
            # Validate table thuộc restaurant
            restaurant_id = attrs.get('restaurant_id')
            table_id = attrs.get('table_id')
            if restaurant_id and table_id:
                try:
                    table = Table.objects.get(id=table_id)
                    if table.restaurant_id != restaurant_id:
                        raise serializers.ValidationError({
                            'table_id': 'Bàn không thuộc chi nhánh đã chọn.'
                        })
                except Table.DoesNotExist:
                    pass
        
        return attrs


class OrderUpdateStatusSerializer(serializers.Serializer):
    """
    Serializer cho việc cập nhật trạng thái order
    """
    status = serializers.ChoiceField(
        choices=Order.ORDER_STATUS_CHOICES,
        required=True
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000
    )
    
    def validate_status(self, value):
        """Validate status transition"""
        order = self.context.get('order')
        if not order:
            return value
        
        current_status = order.status
        
        # Không cho phép update nếu đã completed/cancelled/refunded
        if current_status in ['completed', 'cancelled', 'refunded']:
            raise serializers.ValidationError(
                f"Không thể thay đổi trạng thái từ '{order.get_status_display()}'"
            )
        
        # Validate luồng status hợp lệ
        valid_transitions = {
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['delivering', 'cancelled'],
            'delivering': ['completed', 'cancelled'],
        }
        
        if current_status in valid_transitions:
            if value not in valid_transitions[current_status]:
                raise serializers.ValidationError(
                    f"Không thể chuyển từ '{order.get_status_display()}' sang '{dict(Order.ORDER_STATUS_CHOICES).get(value)}'"
                )
        
        return value


class DeliveryCalculationSerializer(serializers.Serializer):
    """
    Serializer cho việc tính phí vận chuyển
    Input: restaurant + tọa độ
    Output: distance, fee, estimated_time
    """
    restaurant_id = serializers.IntegerField(required=True)
    delivery_latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=True
    )
    delivery_longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=True
    )
    
    def validate_restaurant_id(self, value):
        """Validate restaurant exists and is active"""
        try:
            restaurant = Restaurant.objects.get(
                id=value,
                is_active=True,
                latitude__isnull=False,
                longitude__isnull=False
            )
            return value
        except Restaurant.DoesNotExist:
            raise serializers.ValidationError(
                "Chi nhánh không tồn tại hoặc không có thông tin tọa độ."
            )


class OrderCancelSerializer(serializers.Serializer):
    """
    Serializer cho việc hủy order
    """
    cancel_reason = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=500
    )
    
    def validate(self, attrs):
        """Validate có thể hủy order không"""
        order = self.context.get('order')
        if not order:
            return attrs
        
        # Chỉ cho phép hủy nếu status là pending hoặc confirmed
        if order.status not in ['pending', 'confirmed']:
            raise serializers.ValidationError(
                f"Không thể hủy đơn hàng ở trạng thái '{order.get_status_display()}'"
            )
        
        return attrs
