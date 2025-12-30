from django.db import models
from django.core.validators import MinValueValidator
from apps.api.mixins import TimestampMixin
from config.storage.storage import MinIOMediaStorage


class PaymentMethod(TimestampMixin):
    """
    Phương thức thanh toán
    """
    name = models.CharField(max_length=100, unique=True, help_text="Tên phương thức")
    code = models.CharField(max_length=50, unique=True, help_text="Mã phương thức")
    description = models.TextField(blank=True, null=True, help_text="Mô tả")
    icon = models.ImageField(
        upload_to='payment_methods/',
        storage=MinIOMediaStorage(),
        blank=True,
        null=True,
        help_text="Icon"
    )
    
    # Cấu hình
    is_active = models.BooleanField(default=True, help_text="Đang hoạt động")
    requires_online = models.BooleanField(default=False, help_text="Yêu cầu thanh toán online")
    
    # Thứ tự hiển thị
    display_order = models.IntegerField(default=0, help_text="Thứ tự hiển thị")
    
    class Meta:
        db_table = 'payment_methods'
        verbose_name = 'Phương thức thanh toán'
        verbose_name_plural = 'Phương thức thanh toán'
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return self.name


class Payment(TimestampMixin):
    """
    Thanh toán
    """
    STATUS_CHOICES = [
        ('pending', 'Chờ thanh toán'),
        ('processing', 'Đang xử lý'),
        ('completed', 'Đã thanh toán'),
        ('failed', 'Thất bại'),
        ('refunded', 'Đã hoàn tiền'),
        ('cancelled', 'Đã hủy'),
    ]
    
    # Thông tin cơ bản
    payment_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Mã thanh toán"
    )
    order = models.OneToOneField(
        'orders.Order',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payment',
        help_text="Đơn hàng"
    )
    reservation = models.OneToOneField(
        'reservations.Reservation',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payment',
        help_text="Đặt bàn (payment là cọc cho reservation)"
    )
    customer = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='payments',
        help_text="Khách hàng"
    )
    
    # Phương thức thanh toán
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        related_name='payments',
        help_text="Phương thức thanh toán"
    )
    
    # Trạng thái
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Trạng thái"
    )
    
    # Số tiền
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Số tiền"
    )
    currency = models.CharField(
        max_length=3,
        default='VND',
        help_text="Đơn vị tiền tệ"
    )
    
    # Thông tin thanh toán online (nếu có)
    transaction_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        unique=True,
        help_text="Mã giao dịch"
    )
    payment_gateway = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Cổng thanh toán"
    )
    gateway_response = models.JSONField(
        blank=True,
        null=True,
        help_text="Phản hồi từ gateway"
    )
    
    # Thông tin thẻ (nếu thanh toán bằng thẻ)
    card_last_four = models.CharField(
        max_length=4,
        blank=True,
        null=True,
        help_text="4 số cuối thẻ"
    )
    card_brand = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Loại thẻ"
    )
    
    # Thời gian
    paid_at = models.DateTimeField(blank=True, null=True, help_text="Thời gian thanh toán")
    refunded_at = models.DateTimeField(blank=True, null=True, help_text="Thời gian hoàn tiền")
    
    # Ghi chú
    notes = models.TextField(blank=True, null=True, help_text="Ghi chú")
    failure_reason = models.TextField(blank=True, null=True, help_text="Lý do thất bại")

    def clean(self):
        """
        Validate rằng payment liên kết với order HOẶC reservation (không cả hai, không không có)
        """
        from django.core.exceptions import ValidationError

        has_order = bool(self.order_id)
        has_reservation = bool(self.reservation_id)

        if not has_order and not has_reservation:
            raise ValidationError({
                '__all__': 'Payment phải liên kết với Order hoặc Reservation.'
            })

        if has_order and has_reservation:
            raise ValidationError({
                '__all__': 'Payment không thể liên kết với cả Order và Reservation cùng lúc.'
            })

    class Meta:
        db_table = 'payments'
        verbose_name = 'Thanh toán'
        verbose_name_plural = 'Thanh toán'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_number']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['customer', '-created_at']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Thanh toán {self.payment_number} - {self.amount} {self.currency}"
    
    def save(self, *args, **kwargs):
        """Tự động tạo payment_number nếu chưa có"""
        # Validate before saving
        self.full_clean()
        if not self.payment_number:
            from django.utils import timezone
            import random
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            random_num = random.randint(1000, 9999)
            self.payment_number = f"PAY{timestamp}{random_num}"
        super().save(*args, **kwargs)

    @property
    def payment_type(self):
        """Loại payment: 'order' hoặc 'reservation'"""
        if self.order_id:
            return 'order'
        elif self.reservation_id:
            return 'reservation'
        return None

    @property
    def is_successful(self):
        """Kiểm tra thanh toán thành công"""
        return self.status == 'completed'

    @property
    def is_pending(self):
        """Kiểm tra đang chờ thanh toán"""
        return self.status in ['pending', 'processing']
