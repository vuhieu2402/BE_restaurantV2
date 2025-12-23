from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from apps.api.mixins import TimestampMixin


class Order(TimestampMixin):
    """
    Đơn hàng
    """
    ORDER_STATUS_CHOICES = [
        ('pending', 'Chờ xử lý'),
        ('confirmed', 'Đã xác nhận'),
        ('delivering', 'Đang giao hàng'),
        ('completed', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
        ('refunded', 'Đã hoàn tiền'),
    ]
    
    ORDER_TYPE_CHOICES = [
        ('dine_in', 'Ăn tại chỗ'),
        ('takeaway', 'Mang đi'),
        ('delivery', 'Giao hàng'),
    ]
    
    # Thông tin cơ bản
    order_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Mã đơn hàng"
    )
    customer = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='orders',
        help_text="Khách hàng"
    )
    
    # Chuỗi nhà hàng (nếu đặt từ chuỗi)
    chain = models.ForeignKey(
        'restaurants.RestaurantChain',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='orders',
        help_text="Chuỗi nhà hàng"
    )
    
    # Chi nhánh xử lý đơn hàng
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='orders',
        help_text="Chi nhánh xử lý đơn hàng"
    )
    
    # Ghi chú về auto-assignment
    assignment_method = models.CharField(
        max_length=20,
        choices=[
            ('manual', 'Thủ công'),
            ('auto', 'Tự động'),
            ('customer', 'Khách chọn'),
        ],
        default='manual',
        help_text="Phương thức phân chi nhánh"
    )
    assignment_distance = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Khoảng cách đến chi nhánh (km)"
    )
    
    # Loại đơn hàng
    order_type = models.CharField(
        max_length=20,
        choices=ORDER_TYPE_CHOICES,
        default='dine_in',
        help_text="Loại đơn hàng"
    )
    
    # Trạng thái
    status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS_CHOICES,
        default='pending',
        help_text="Trạng thái"
    )
    
    # Thông tin địa chỉ giao hàng (nếu là delivery)
    delivery_address = models.TextField(blank=True, null=True, help_text="Địa chỉ giao hàng")
    delivery_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Vĩ độ địa chỉ giao hàng"
    )
    delivery_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Kinh độ địa chỉ giao hàng"
    )
    delivery_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Số điện thoại giao hàng"
    )
    
    # Bàn (nếu là dine_in)
    table = models.ForeignKey(
        'restaurants.Table',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        help_text="Bàn"
    )
    
    # Giá cả
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Tổng tiền món ăn"
    )
    tax = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Thuế"
    )
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Phí giao hàng"
    )
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Giảm giá"
    )
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Tổng cộng"
    )
    
    # Thanh toán
    payment_method = models.ForeignKey(
        'payments.PaymentMethod',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        help_text="Phương thức thanh toán"
    )
    
    # Ghi chú
    notes = models.TextField(blank=True, null=True, help_text="Ghi chú")
    customer_notes = models.TextField(blank=True, null=True, help_text="Ghi chú từ khách hàng")
    
    # Thời gian
    estimated_time = models.IntegerField(
        blank=True,
        null=True,
        help_text="Thời gian dự kiến (phút)"
    )
    completed_at = models.DateTimeField(blank=True, null=True, help_text="Thời gian hoàn thành")
    
    # Nhân viên xử lý
    assigned_staff = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_orders',
        help_text="Nhân viên được giao"
    )
    
    class Meta:
        db_table = 'orders'
        verbose_name = 'Đơn hàng'
        verbose_name_plural = 'Đơn hàng'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['restaurant', 'status']),
        ]
    
    def __str__(self):
        return f"Đơn hàng {self.order_number}"
    
    def clean(self):
        """Validate order data"""
        super().clean()
        
        # Restaurant là bắt buộc
        if not self.restaurant:
            raise ValidationError({
                'restaurant': 'Vui lòng chọn chi nhánh nhà hàng.'
            })
        
        # Nếu có cả chain và restaurant, restaurant phải thuộc chain
        if self.chain and self.restaurant:
            if self.restaurant.chain_id != self.chain_id:
                raise ValidationError({
                    'restaurant': 'Chi nhánh phải thuộc chuỗi đã chọn.'
                })
        
        # Validation theo order_type
        if self.order_type == 'delivery':
            # Delivery phải có địa chỉ và tọa độ
            if not self.delivery_address:
                raise ValidationError({
                    'delivery_address': 'Địa chỉ giao hàng là bắt buộc cho đơn giao hàng.'
                })
            if not self.delivery_latitude or not self.delivery_longitude:
                raise ValidationError({
                    'delivery_latitude': 'Vui lòng cung cấp tọa độ địa chỉ giao hàng.',
                    'delivery_longitude': 'Vui lòng cung cấp tọa độ địa chỉ giao hàng.'
                })
            if not self.delivery_phone:
                raise ValidationError({
                    'delivery_phone': 'Số điện thoại là bắt buộc cho đơn giao hàng.'
                })
            
            # Validate địa chỉ trong delivery_radius
            if self.assignment_distance and self.restaurant:
                if float(self.assignment_distance) > float(self.restaurant.delivery_radius):
                    raise ValidationError({
                        'delivery_address': f'Địa chỉ giao hàng nằm ngoài bán kính phục vụ ({self.restaurant.delivery_radius}km).'
                    })
        
        elif self.order_type == 'dine_in':
            # Dine-in phải có bàn
            if not self.table:
                raise ValidationError({
                    'table': 'Vui lòng chọn bàn cho đơn ăn tại chỗ.'
                })
            # Validate bàn thuộc restaurant
            if self.table and self.restaurant:
                if self.table.restaurant_id != self.restaurant.id:
                    raise ValidationError({
                        'table': 'Bàn phải thuộc chi nhánh đã chọn.'
                    })
    
    def calculate_distance_to_restaurant(self):
        """
        Tính khoảng cách từ địa chỉ giao hàng đến restaurant
        
        Returns:
            Decimal: Khoảng cách (km) hoặc None nếu không đủ thông tin
        """
        if not self.restaurant or not self.delivery_latitude or not self.delivery_longitude:
            return None
        
        if not self.restaurant.latitude or not self.restaurant.longitude:
            return None
        
        from apps.restaurants.utils import calculate_distance
        from decimal import Decimal
        
        distance = calculate_distance(
            float(self.delivery_latitude),
            float(self.delivery_longitude),
            float(self.restaurant.latitude),
            float(self.restaurant.longitude)
        )
        
        return Decimal(str(distance))
    
    def calculate_delivery_fee(self):
        """
        Tính phí giao hàng theo công thức: Base Fee + (Distance × Per KM Fee)
        
        Công thức: delivery_fee = base_fee + (distance × per_km_fee)
        
        Returns:
            Decimal: Phí giao hàng
        """
        from decimal import Decimal
        
        # Nếu không phải delivery, phí = 0
        if self.order_type != 'delivery':
            return Decimal('0.00')
        
        # Phải có restaurant và khoảng cách
        if not self.restaurant or not self.assignment_distance:
            return Decimal('0.00')
        
        # Lấy config từ DeliveryPricingConfig hoặc dùng default
        try:
            config = self.restaurant.delivery_pricing_config
            base_fee = config.base_fee
            per_km_fee = config.per_km_fee
            free_distance = config.free_distance_km
        except:
            # Fallback: dùng restaurant.delivery_fee làm base_fee
            base_fee = self.restaurant.delivery_fee
            per_km_fee = Decimal('5000.00')  # 5,000đ/km
            free_distance = Decimal('0.00')
        
        distance = Decimal(str(self.assignment_distance))
        
        # Tính phí: base_fee + (distance vượt quá free_distance × per_km_fee)
        chargeable_distance = max(Decimal('0.00'), distance - free_distance)
        delivery_fee = base_fee + (chargeable_distance * per_km_fee)
        
        return delivery_fee.quantize(Decimal('0.01'))
    
    def save(self, *args, **kwargs):
        """
        Tự động tạo order_number
        
        Note: 
        - Distance và delivery_fee KHÔNG tự động tính nữa
        - Phải được tính qua API /api/orders/calculate-delivery/ trước
        - Và truyền vào khi tạo Order
        """
        # Tạo order_number
        if not self.order_number:
            from django.utils import timezone
            import random
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            random_num = random.randint(1000, 9999)
            self.order_number = f"ORD{timestamp}{random_num}"
        
        # Set delivery_fee = 0 cho dine_in/takeaway
        if self.order_type in ['dine_in', 'takeaway']:
            self.delivery_fee = 0
            self.assignment_distance = None
        
        # Validate
        self.full_clean()
        
        super().save(*args, **kwargs)
    
    def calculate_total(self):
        """Tính tổng tiền"""
        self.total = self.subtotal + self.tax + self.delivery_fee - self.discount
        return self.total
    
    def get_restaurant_info(self):
        """Lấy thông tin chi nhánh xử lý"""
        if self.restaurant:
            return {
                'name': self.restaurant.name,
                'address': self.restaurant.address,
                'phone': self.restaurant.phone_number,
                'distance': float(self.assignment_distance) if self.assignment_distance else None,
            }
        return None
    
    def get_payment_status(self):
        """
        Lấy trạng thái thanh toán
        
        Returns:
            str: Payment status hoặc None nếu chưa có payment
        """
        if hasattr(self, 'payment') and self.payment:
            return self.payment.status
        return None
    
    def is_paid(self):
        """Kiểm tra đã thanh toán chưa"""
        return self.get_payment_status() == 'completed'


class OrderItem(TimestampMixin):
    """
    Chi tiết món ăn trong đơn hàng
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Đơn hàng"
    )
    menu_item = models.ForeignKey(
        'dishes.MenuItem',
        on_delete=models.SET_NULL,
        null=True,
        related_name='order_items',
        help_text="Món ăn"
    )
    
    # Thông tin tại thời điểm đặt hàng (để lưu lại giá gốc)
    item_name = models.CharField(max_length=200, help_text="Tên món")
    item_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Giá tại thời điểm đặt"
    )
    
    quantity = models.IntegerField(
        validators=[MinValueValidator(1)],
        default=1,
        help_text="Số lượng"
    )
    
    # Tùy chọn (nếu có)
    special_instructions = models.TextField(blank=True, null=True, help_text="Yêu cầu đặc biệt")
    
    # Giá
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Tổng tiền"
    )
    
    class Meta:
        db_table = 'order_items'
        verbose_name = 'Chi tiết đơn hàng'
        verbose_name_plural = 'Chi tiết đơn hàng'
        ordering = ['order', 'created_at']
    
    def __str__(self):
        return f"{self.order.order_number} - {self.item_name} x{self.quantity}"
    
    def save(self, *args, **kwargs):
        """Tự động tính subtotal"""
        if self.menu_item and not self.item_name:
            self.item_name = self.menu_item.name
        if self.menu_item and not self.item_price:
            self.item_price = self.menu_item.price
        self.subtotal = self.item_price * self.quantity
        super().save(*args, **kwargs)
        
        # Cập nhật tổng tiền đơn hàng
        if self.order:
            self.order.subtotal = sum(item.subtotal for item in self.order.items.all())
            self.order.calculate_total()
            self.order.save()
