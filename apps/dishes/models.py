from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Avg, Count
from apps.api.mixins import TimestampMixin
from apps.restaurants.models import Restaurant
from config.storage.storage import MinIOMediaStorage

User = get_user_model()


class Category(TimestampMixin):
    """
    Danh mục món ăn - Thuộc về Chain hoặc Restaurant độc lập
    """
    # Thuộc chuỗi nhà hàng (cho chuỗi)
    chain = models.ForeignKey(
        'restaurants.RestaurantChain',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='categories',
        help_text="Chuỗi nhà hàng (menu chung cho cả chuỗi)"
    )
    
    # Thuộc nhà hàng độc lập (cho nhà hàng không thuộc chuỗi)
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='categories',
        help_text="Nhà hàng độc lập (để trống nếu thuộc chuỗi)"
    )
    
    name = models.CharField(max_length=100, help_text="Tên danh mục")
    slug = models.SlugField(help_text="URL slug")
    description = models.TextField(blank=True, null=True, help_text="Mô tả")
    image = models.ImageField(
        upload_to='categories/',
        storage=MinIOMediaStorage(),
        blank=True,
        null=True,
        help_text="Hình ảnh"
    )
    display_order = models.IntegerField(default=0, help_text="Thứ tự hiển thị")
    
    is_active = models.BooleanField(default=True, help_text="Đang hoạt động")
    
    class Meta:
        db_table = 'categories'
        verbose_name = 'Danh mục'
        verbose_name_plural = 'Danh mục'
        # Không thể unique_together vì có 2 FK nullable, sẽ validate trong clean()
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['chain', 'slug']),
            models.Index(fields=['restaurant', 'slug']),
        ]
    
    def __str__(self):
        if self.chain:
            return f"{self.chain.name} - {self.name}"
        elif self.restaurant:
            return f"{self.restaurant.name} - {self.name}"
        return self.name
    
    def clean(self):
        """Validate: phải thuộc chain HOẶC restaurant, không được cả hai hoặc không có"""
        super().clean()
        
        if self.chain and self.restaurant:
            raise ValidationError(
                'Danh mục chỉ có thể thuộc chuỗi HOẶC nhà hàng độc lập, không thể cả hai.'
            )
        
        if not self.chain and not self.restaurant:
            raise ValidationError(
                'Danh mục phải thuộc chuỗi hoặc nhà hàng độc lập.'
            )
        
        # Kiểm tra slug unique trong cùng chain/restaurant
        if self.chain:
            existing = Category.objects.filter(
                chain=self.chain,
                slug=self.slug
            ).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError({
                    'slug': f'Slug "{self.slug}" đã tồn tại trong chuỗi này.'
                })
        elif self.restaurant:
            existing = Category.objects.filter(
                restaurant=self.restaurant,
                slug=self.slug
            ).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError({
                    'slug': f'Slug "{self.slug}" đã tồn tại trong nhà hàng này.'
                })
    
    def save(self, *args, **kwargs):
        """Chạy validation trước khi save"""
        self.full_clean()
        super().save(*args, **kwargs)


class MenuItem(TimestampMixin):
    """
    Món ăn trong menu - Thuộc về Chain hoặc Restaurant độc lập
    """
    # Thuộc chuỗi nhà hàng (cho chuỗi)
    chain = models.ForeignKey(
        'restaurants.RestaurantChain',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='menu_items',
        help_text="Chuỗi nhà hàng (menu chung cho cả chuỗi)"
    )
    
    # Thuộc nhà hàng độc lập (cho nhà hàng không thuộc chuỗi)
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='menu_items',
        help_text="Nhà hàng độc lập (để trống nếu thuộc chuỗi)"
    )
    
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='menu_items',
        help_text="Danh mục"
    )
    
    name = models.CharField(max_length=200, help_text="Tên món")
    slug = models.SlugField(help_text="URL slug")
    description = models.TextField(blank=True, null=True, help_text="Mô tả")
    
    # Giá cả
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Giá"
    )
    original_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="Giá gốc (nếu có khuyến mãi)"
    )
    
    # Hình ảnh
    image = models.ImageField(
        upload_to='menu_items/',
        storage=MinIOMediaStorage(),
        blank=True,
        null=True,
        help_text="Hình ảnh"
    )
    
    # Thông tin dinh dưỡng (optional)
    calories = models.IntegerField(blank=True, null=True, help_text="Calories")
    preparation_time = models.IntegerField(
        blank=True,
        null=True,
        help_text="Thời gian chuẩn bị (phút)"
    )
    
    # Đánh giá
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Đánh giá trung bình"
    )
    total_reviews = models.IntegerField(default=0, help_text="Tổng số đánh giá")

    # Enhanced rating analytics
    rating_distribution = models.JSONField(
        default=dict,
        blank=True,
        help_text="Distribution of ratings: {'1_star': count, '2_star': count, ...}"
    )
    last_rated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time this item was rated"
    )
    verified_purchase_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Percentage of ratings from verified purchases"
    )
    
    # Trạng thái
    is_available = models.BooleanField(default=True, help_text="Còn hàng")
    is_featured = models.BooleanField(default=False, help_text="Nổi bật")
    is_vegetarian = models.BooleanField(default=False, help_text="Món chay")
    is_spicy = models.BooleanField(default=False, help_text="Cay")
    
    display_order = models.IntegerField(default=0, help_text="Thứ tự hiển thị")
    
    class Meta:
        db_table = 'menu_items'
        verbose_name = 'Món ăn'
        verbose_name_plural = 'Món ăn'
        ordering = ['category', 'display_order', 'name']
        indexes = [
            models.Index(fields=['chain', 'slug']),
            models.Index(fields=['restaurant', 'slug']),
            models.Index(fields=['chain', 'is_available']),
            models.Index(fields=['restaurant', 'is_available']),
        ]
    
    def __str__(self):
        if self.chain:
            return f"{self.chain.name} - {self.name}"
        elif self.restaurant:
            return f"{self.restaurant.name} - {self.name}"
        return self.name
    
    def clean(self):
        """
        Validate tính nhất quán giữa chain/restaurant và category
        """
        super().clean()
        
        # Rule 1: Phải thuộc chain HOẶC restaurant, không được cả hai hoặc không có
        if self.chain and self.restaurant:
            raise ValidationError(
                'Món ăn chỉ có thể thuộc chuỗi HOẶC nhà hàng độc lập, không thể cả hai.'
            )
        
        if not self.chain and not self.restaurant:
            raise ValidationError(
                'Món ăn phải thuộc chuỗi hoặc nhà hàng độc lập.'
            )
        
        # Rule 2: Nếu có category, phải cùng chain/restaurant
        if self.category:
            if self.chain:
                # MenuItem thuộc chain → category cũng phải thuộc chain
                if self.category.chain_id != self.chain_id:
                    raise ValidationError({
                        'category': 'Danh mục phải thuộc cùng chuỗi với món ăn.'
                    })
            elif self.restaurant:
                # MenuItem thuộc restaurant → category cũng phải thuộc restaurant
                if self.category.restaurant_id != self.restaurant_id:
                    raise ValidationError({
                        'category': 'Danh mục phải thuộc cùng nhà hàng với món ăn.'
                    })
        
        # Rule 3: Kiểm tra slug unique trong cùng chain/restaurant
        if self.chain:
            existing = MenuItem.objects.filter(
                chain=self.chain,
                slug=self.slug
            ).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError({
                    'slug': f'Slug "{self.slug}" đã tồn tại trong chuỗi này.'
                })
        elif self.restaurant:
            existing = MenuItem.objects.filter(
                restaurant=self.restaurant,
                slug=self.slug
            ).exclude(pk=self.pk)
            if existing.exists():
                raise ValidationError({
                    'slug': f'Slug "{self.slug}" đã tồn tại trong nhà hàng này.'
                })
    
    def save(self, *args, **kwargs):
        """
        Tự động đồng bộ chain/restaurant từ category nếu được set
        """
        # Nếu category được set, tự động đồng bộ chain/restaurant
        if self.category_id and not self.chain_id and not self.restaurant_id:
            # Query chain_id và restaurant_id từ category
            category_data = Category.objects.values_list(
                'chain_id', 'restaurant_id'
            ).get(pk=self.category_id)
            
            self.chain_id = category_data[0]
            self.restaurant_id = category_data[1]
        
        # Chạy validation
        self.full_clean()
        
        # Gọi save() của parent class
        super().save(*args, **kwargs)
    
    @property
    def is_on_sale(self):
        """Kiểm tra có đang giảm giá không"""
        return self.original_price and self.original_price > self.price
    
    @property
    def discount_percentage(self):
        """Phần trăm giảm giá"""
        if self.is_on_sale:
            return int(((self.original_price - self.price) / self.original_price) * 100)
        return 0

