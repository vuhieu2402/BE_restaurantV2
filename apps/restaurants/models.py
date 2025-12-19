from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.api.mixins import TimestampMixin
from config.storage.storage import MinIOMediaStorage


class RestaurantChain(TimestampMixin):
    """
    Chuỗi nhà hàng - Quản lý nhiều chi nhánh với menu chung
    """
    name = models.CharField(max_length=200, help_text="Tên chuỗi nhà hàng")
    slug = models.SlugField(unique=True, help_text="URL slug")
    description = models.TextField(blank=True, null=True, help_text="Mô tả")
    
    # Logo và branding chung
    logo = models.ImageField(
        upload_to='chains/logos/',
        storage=MinIOMediaStorage(),
        blank=True,
        null=True,
        help_text="Logo chuỗi"
    )
    cover_image = models.ImageField(
        upload_to='chains/covers/',
        storage=MinIOMediaStorage(),
        blank=True,
        null=True,
        help_text="Ảnh bìa chuỗi"
    )
    
    # Thông tin liên hệ chung
    contact_email = models.EmailField(blank=True, null=True, help_text="Email liên hệ")
    contact_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Hotline")
    website = models.URLField(blank=True, null=True, help_text="Website")
    
    # Cấu hình chung cho toàn chuỗi
    default_minimum_order = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Đơn hàng tối thiểu mặc định"
    )
    default_delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Phí giao hàng mặc định"
    )
    default_delivery_radius = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=5,
        help_text="Bán kính giao hàng mặc định (km)"
    )
    
    # Auto-assignment settings
    enable_auto_assignment = models.BooleanField(
        default=True,
        help_text="Tự động phân đơn hàng cho chi nhánh gần nhất"
    )
    
    # Trạng thái
    is_active = models.BooleanField(default=True, help_text="Đang hoạt động")
    
    # Quản lý chuỗi
    owner = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_chains',
        help_text="Chủ chuỗi"
    )
    
    class Meta:
        db_table = 'restaurant_chains'
        verbose_name = 'Chuỗi nhà hàng'
        verbose_name_plural = 'Chuỗi nhà hàng'
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_total_branches(self):
        """Tổng số chi nhánh"""
        return self.restaurants.filter(is_active=True).count()
    
    def get_nearest_restaurant(self, latitude, longitude, max_distance=None):
        """
        Tìm chi nhánh gần nhất dựa trên tọa độ
        
        Args:
            latitude: Vĩ độ khách hàng
            longitude: Kinh độ khách hàng
            max_distance: Khoảng cách tối đa (km), None = không giới hạn
        
        Returns:
            Restaurant object hoặc None
        """
        from .utils import calculate_distance
        
        available_restaurants = self.restaurants.filter(
            is_active=True,
            is_open=True,
            latitude__isnull=False,
            longitude__isnull=False
        )
        
        if not available_restaurants.exists():
            return None
        
        # Tính khoảng cách cho từng chi nhánh
        restaurants_with_distance = []
        for restaurant in available_restaurants:
            distance = calculate_distance(
                latitude, longitude,
                float(restaurant.latitude), float(restaurant.longitude)
            )
            
            # Kiểm tra trong bán kính phục vụ
            if max_distance and distance > max_distance:
                continue
            if distance > float(restaurant.delivery_radius):
                continue
            
            restaurants_with_distance.append((restaurant, distance))
        
        if not restaurants_with_distance:
            return None
        
        # Sắp xếp theo khoảng cách và trả về chi nhánh gần nhất
        restaurants_with_distance.sort(key=lambda x: x[1])
        return restaurants_with_distance[0][0]


class Restaurant(TimestampMixin):
    """
    Model nhà hàng (Chi nhánh)
    """
    # Chuỗi nhà hàng (NULL = nhà hàng độc lập)
    chain = models.ForeignKey(
        RestaurantChain,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='restaurants',
        help_text="Chuỗi nhà hàng (để trống nếu là nhà hàng độc lập)"
    )
    
    name = models.CharField(max_length=200, help_text="Tên chi nhánh/nhà hàng")
    slug = models.SlugField(unique=True, help_text="URL slug")
    description = models.TextField(blank=True, null=True, help_text="Mô tả")
    
    # Thông tin liên hệ
    phone_number = models.CharField(max_length=20, help_text="Số điện thoại")
    email = models.EmailField(blank=True, null=True, help_text="Email")
    
    # Địa chỉ
    address = models.TextField(help_text="Địa chỉ")
    city = models.CharField(max_length=100, help_text="Thành phố")
    district = models.CharField(max_length=100, help_text="Quận/Huyện")
    ward = models.CharField(max_length=100, blank=True, null=True, help_text="Phường/Xã")
    postal_code = models.CharField(max_length=10, blank=True, null=True, help_text="Mã bưu điện")
    
    # Tọa độ địa lý (cho tích hợp map)
    latitude = models.DecimalField(
        blank=True,
        null=True,
        max_digits=9,
        decimal_places=6,
        help_text="Vĩ độ"
    )
    longitude = models.DecimalField(
        blank=True,
        null=True,
        max_digits=9,
        decimal_places=6,
        help_text="Kinh độ"
    )
    
    # Hình ảnh
    logo = models.ImageField(
        upload_to='restaurants/logos/',
        storage=MinIOMediaStorage(),
        blank=True,
        null=True,
        help_text="Logo"
    )
    cover_image = models.ImageField(
        upload_to='restaurants/covers/',
        storage=MinIOMediaStorage(),
        blank=True,
        null=True,
        help_text="Ảnh bìa"
    )
    
    # Thông tin hoạt động
    opening_time = models.TimeField(help_text="Giờ mở cửa")
    closing_time = models.TimeField(help_text="Giờ đóng cửa")
    is_open = models.BooleanField(default=True, help_text="Đang mở cửa")
    
    # Đánh giá
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Đánh giá trung bình"
    )
    total_reviews = models.IntegerField(default=0, help_text="Tổng số đánh giá")
    
    # Cấu hình
    minimum_order = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Đơn hàng tối thiểu"
    )
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Phí giao hàng"
    )
    delivery_radius = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=5,
        help_text="Bán kính giao hàng (km)"
    )
    
    # Trạng thái
    is_active = models.BooleanField(default=True, help_text="Đang hoạt động")
    
    # Quản lý
    manager = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_restaurants',
        help_text="Quản lý"
    )
    
    class Meta:
        db_table = 'restaurants'
        verbose_name = 'Nhà hàng'
        verbose_name_plural = 'Nhà hàng'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def is_currently_open(self):
        """Kiểm tra nhà hàng có đang mở cửa không"""
        from django.utils import timezone
        now = timezone.now().time()
        return self.is_open and self.opening_time <= now <= self.closing_time


class Table(TimestampMixin):
    """
    Bàn trong nhà hàng
    """
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='tables',
        help_text="Nhà hàng"
    )
    
    table_number = models.CharField(max_length=50, help_text="Số bàn")
    capacity = models.IntegerField(
        validators=[MinValueValidator(1)],
        help_text="Sức chứa (số người)"
    )
    floor = models.IntegerField(default=1, help_text="Tầng")
    section = models.CharField(max_length=100, blank=True, null=True, help_text="Khu vực")
    
    # Trạng thái
    STATUS_CHOICES = [
        ('available', 'Trống'),
        ('reserved', 'Đã đặt'),
        ('occupied', 'Đang sử dụng'),
        ('maintenance', 'Bảo trì'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available',
        help_text="Trạng thái"
    )
    
    # Tọa độ trong nhà hàng (cho sơ đồ bàn)
    x_position = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Vị trí X"
    )
    y_position = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Vị trí Y"
    )
    
    is_active = models.BooleanField(default=True, help_text="Đang hoạt động")
    
    class Meta:
        db_table = 'tables'
        verbose_name = 'Bàn'
        verbose_name_plural = 'Bàn'
        unique_together = ['restaurant', 'table_number']
        ordering = ['restaurant', 'floor', 'table_number']
    
    def __str__(self):
        return f"{self.restaurant.name} - Bàn {self.table_number}"


class DeliveryPricingConfig(TimestampMixin):
    """
    Cấu hình giá vận chuyển cho từng restaurant
    Cho phép tùy chỉnh công thức tính phí giao hàng
    """
    restaurant = models.OneToOneField(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='delivery_pricing_config',
        help_text="Nhà hàng"
    )
    
    # Phí cơ bản
    base_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=15000,
        validators=[MinValueValidator(0)],
        help_text="Phí giao hàng cơ bản (đ)"
    )
    
    # Phí theo km
    per_km_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=5000,
        validators=[MinValueValidator(0)],
        help_text="Phí mỗi km (đ/km)"
    )
    
    # Khoảng cách miễn phí
    free_distance_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Số km miễn phí (km)"
    )
    
    # Phí tối thiểu
    minimum_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Phí giao hàng tối thiểu (đ)"
    )
    
    # Phí tối đa
    maximum_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Phí giao hàng tối đa (đ) - để trống nếu không giới hạn"
    )
    
    # Surge pricing (giờ cao điểm)
    enable_surge_pricing = models.BooleanField(
        default=False,
        help_text="Bật tính năng tăng giá giờ cao điểm"
    )
    surge_multiplier = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=1.5,
        validators=[MinValueValidator(1.0), MaxValueValidator(3.0)],
        help_text="Hệ số nhân giá giờ cao điểm (1.0 - 3.0)"
    )
    
    # Thời gian giờ cao điểm
    surge_start_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Giờ bắt đầu cao điểm (VD: 11:00)"
    )
    surge_end_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Giờ kết thúc cao điểm (VD: 13:00)"
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Đang sử dụng config này"
    )
    
    class Meta:
        db_table = 'delivery_pricing_configs'
        verbose_name = 'Cấu hình giá vận chuyển'
        verbose_name_plural = 'Cấu hình giá vận chuyển'
    
    def __str__(self):
        return f"Config giá ship - {self.restaurant.name}"
    
    def is_surge_time(self):
        """Kiểm tra có phải giờ cao điểm không"""
        if not self.enable_surge_pricing or not self.surge_start_time or not self.surge_end_time:
            return False
        
        from django.utils import timezone
        now = timezone.now().time()
        return self.surge_start_time <= now <= self.surge_end_time



