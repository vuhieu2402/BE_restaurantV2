from django.db import models
from django.core.validators import MinValueValidator
from apps.api.mixins import TimestampMixin


class Reservation(TimestampMixin):
    """
    Đặt bàn
    """
    STATUS_CHOICES = [
        ('pending', 'Chờ xác nhận'),
        ('confirmed', 'Đã xác nhận'),
        ('checked_in', 'Đã check-in'),
        ('completed', 'Hoàn thành'),
        ('cancelled', 'Đã hủy'),
        ('no_show', 'Không đến'),
    ]
    
    # Thông tin cơ bản
    reservation_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Mã đặt bàn"
    )
    customer = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='reservations',
        help_text="Khách hàng"
    )
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='reservations',
        help_text="Nhà hàng"
    )
    table = models.ForeignKey(
        'restaurants.Table',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservations',
        help_text="Bàn"
    )
    
    # Thông tin đặt bàn
    reservation_date = models.DateField(help_text="Ngày đặt")
    reservation_time = models.TimeField(help_text="Giờ đặt")
    number_of_guests = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Số lượng khách"
    )
    
    # Trạng thái
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Trạng thái"
    )
    
    # Thông tin liên hệ
    contact_name = models.CharField(max_length=200, help_text="Tên người đặt")
    contact_phone = models.CharField(max_length=20, help_text="Số điện thoại")
    contact_email = models.EmailField(blank=True, null=True, help_text="Email")
    
    # Ghi chú
    special_requests = models.TextField(blank=True, null=True, help_text="Yêu cầu đặc biệt")
    notes = models.TextField(blank=True, null=True, help_text="Ghi chú nội bộ")
    
    # Thời gian
    checked_in_at = models.DateTimeField(blank=True, null=True, help_text="Thời gian check-in")
    completed_at = models.DateTimeField(blank=True, null=True, help_text="Thời gian hoàn thành")
    
    # Nhân viên xử lý
    assigned_staff = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_reservations',
        help_text="Nhân viên được giao"
    )
    
    class Meta:
        db_table = 'reservations'
        verbose_name = 'Đặt bàn'
        verbose_name_plural = 'Đặt bàn'
        ordering = ['reservation_date', 'reservation_time']
        indexes = [
            models.Index(fields=['reservation_number']),
            models.Index(fields=['restaurant', 'reservation_date', 'reservation_time']),
            models.Index(fields=['customer', '-created_at']),
        ]
    
    def __str__(self):
        return f"Đặt bàn {self.reservation_number} - {self.restaurant.name}"
    
    def save(self, *args, **kwargs):
        """Tự động tạo reservation_number nếu chưa có"""
        if not self.reservation_number:
            from django.utils import timezone
            import random
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            random_num = random.randint(1000, 9999)
            self.reservation_number = f"RES{timestamp}{random_num}"
        super().save(*args, **kwargs)
    
    @property
    def is_upcoming(self):
        """Kiểm tra đặt bàn có sắp tới không"""
        from django.utils import timezone
        from datetime import datetime, date
        now = timezone.now()
        reservation_datetime = timezone.make_aware(
            datetime.combine(self.reservation_date, self.reservation_time)
        )
        return reservation_datetime > now and self.status in ['pending', 'confirmed']
