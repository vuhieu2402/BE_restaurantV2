from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from apps.api.mixins import TimestampMixin
from config.storage.storage import MinIOMediaStorage


class User(AbstractUser, TimestampMixin):
    """
    User model mở rộng từ AbstractUser
    Hỗ trợ nhiều loại user: Customer, Staff, Manager
    """
    USER_TYPE_CHOICES = [
        ('customer', 'Khách hàng'),
        ('staff', 'Nhân viên'),
        ('manager', 'Quản lý'),
        ('admin', 'Quản trị viên'),
    ]
    
    phone_regex = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Số điện thoại phải có định dạng: '+999999999'. Tối đa 15 số."
    )
    
    # Thông tin cơ bản
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='customer',
        help_text="Loại người dùng"
    )
    phone_number = models.CharField(
        validators=[phone_regex],
        max_length=17,
        blank=True,
        null=True,
        unique=True,
        help_text="Số điện thoại"
    )
    email = models.EmailField(unique=True, blank=True, null=True, help_text="Email")
    avatar = models.ImageField(
        upload_to='avatars/',
        storage=MinIOMediaStorage(),
        blank=True,
        null=True,
        help_text="Ảnh đại diện"
    )
    date_of_birth = models.DateField(
        blank=True,
        null=True,
        help_text="Ngày sinh"
    )
    
    # Địa chỉ
    address = models.TextField(blank=True, null=True, help_text="Địa chỉ")
    city = models.CharField(max_length=100, blank=True, null=True, help_text="Thành phố")
    district = models.CharField(max_length=100, blank=True, null=True, help_text="Quận/Huyện")
    ward = models.CharField(max_length=100, blank=True, null=True, help_text="Phường/Xã")
    postal_code = models.CharField(max_length=10, blank=True, null=True, help_text="Mã bưu điện")
    
    # Tọa độ địa lý (cho tích hợp map)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Vĩ độ"
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="Kinh độ"
    )
    
    # Trạng thái
    is_verified = models.BooleanField(default=False, help_text="Đã xác thực")
    is_active = models.BooleanField(default=True, help_text="Tài khoản đang hoạt động")
    
    
    class Meta:
        db_table = 'users'
        verbose_name = 'Người dùng'
        verbose_name_plural = 'Người dùng'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    @property
    def is_customer(self):
        return self.user_type == 'customer'
    
    @property
    def is_staff_member(self):
        return self.user_type in ['staff', 'manager', 'admin']
    
    @property
    def is_manager(self):
        return self.user_type in ['manager', 'admin']


class CustomerProfile(TimestampMixin):
    """
    Profile chi tiết cho khách hàng
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='customer_profile',
        help_text="Người dùng"
    )
    
    # Thông tin khách hàng
    preferred_language = models.CharField(
        max_length=10,
        default='vi',
        choices=[('vi', 'Tiếng Việt'), ('en', 'English')],
        help_text="Ngôn ngữ ưa thích"
    )
    loyalty_points = models.IntegerField(default=0, help_text="Điểm tích lũy")
    total_orders = models.IntegerField(default=0, help_text="Tổng số đơn hàng")
    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Tổng chi tiêu"
    )
    
    # Tùy chọn
    receive_promotions = models.BooleanField(default=True, help_text="Nhận khuyến mãi")
    receive_notifications = models.BooleanField(default=True, help_text="Nhận thông báo")
    
    class Meta:
        db_table = 'customer_profiles'
        verbose_name = 'Hồ sơ khách hàng'
        verbose_name_plural = 'Hồ sơ khách hàng'
    
    def __str__(self):
        return f"Profile của {self.user.username}"


class StaffProfile(TimestampMixin):
    """
    Profile cho nhân viên và quản lý
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='staff_profile',
        help_text="Người dùng"
    )
    
    # Thông tin nhân viên
    employee_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Mã nhân viên"
    )
    position = models.CharField(
        max_length=100,
        help_text="Chức vụ"
    )
    hire_date = models.DateField(help_text="Ngày vào làm")
    salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Lương"
    )
    
    # Liên kết với nhà hàng
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_members',
        help_text="Nhà hàng làm việc"
    )
    
    # Trạng thái
    is_active = models.BooleanField(default=True, help_text="Đang làm việc")
    
    class Meta:
        db_table = 'staff_profiles'
        verbose_name = 'Hồ sơ nhân viên'
        verbose_name_plural = 'Hồ sơ nhân viên'
    
    def __str__(self):
        return f"{self.user.username} - {self.position}"
