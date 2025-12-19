from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from apps.users.models import User
from apps.restaurants.models import Restaurant, RestaurantChain
from apps.dishes.models import MenuItem


class Cart(models.Model):
    """
    Giỏ hàng của người dùng - Một người dùng chỉ có một giỏ hàng
    có thể chứa món từ nhiều nhà hàng khác nhau
    
    Note: Cart chỉ lưu thông tin các món ăn và tổng giá trị món ăn.
    Thông tin delivery (phí ship, địa chỉ, thuế, discount) sẽ được xử lý ở Order level.
    """
    id = models.BigAutoField(primary_key=True)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart',
        verbose_name="Người dùng"
    )

    # Tổng giá trị giỏ hàng (chỉ tính giá món ăn)
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Tổng giá trị món ăn",
        help_text="Tổng giá trị các món trong giỏ (chưa bao gồm phí ship, thuế, discount)"
    )

    # Ghi chú chung cho giỏ hàng (optional)
    notes = models.TextField(
        blank=True,
        verbose_name="Ghi chú"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ngày tạo"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Ngày cập nhật"
    )

    class Meta:
        db_table = 'carts'
        verbose_name = "Giỏ hàng"
        verbose_name_plural = "Giỏ hàng"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Giỏ hàng của {self.user.get_full_name() or self.user.username}"

    def calculate_totals(self):
        """
        Tính toán lại tổng giá trị giỏ hàng
        
        Note: Chỉ tính tổng giá món ăn, không tính delivery/tax/discount.
        Các thông tin đó sẽ được tính khi tạo Order.
        """
        items = self.items.all()

        # Tính tổng giá trị món ăn
        self.subtotal = sum(
            item.subtotal for item in items
        ) or Decimal('0.00')

        self.save(update_fields=['subtotal'])

    def get_restaurant_count(self):
        """Lấy số lượng nhà hàng trong giỏ hàng"""
        return self.items.values('restaurant').distinct().count()

    def get_total_items(self):
        """Lấy tổng số lượng món trong giỏ hàng"""
        total = self.items.aggregate(
            total=models.Sum('quantity')
        )['total'] or 0
        return total
    
    def get_cart_restaurant(self):
        """
        Lấy restaurant hiện tại trong cart
        
        Returns:
            Restaurant object hoặc None nếu cart trống
        """
        first_item = self.items.first()
        return first_item.restaurant if first_item else None
    
    def validate_single_restaurant(self, new_restaurant_id):
        """
        Validate cart items phải cùng chain (nếu thuộc chain) hoặc cùng restaurant (nếu độc lập)
        
        Args:
            new_restaurant_id: ID của restaurant muốn thêm món
        
        Raises:
            ValidationError nếu không match với items hiện tại
        """
        first_item = self.items.select_related('chain', 'restaurant').first()
        
        if not first_item:
            return  # Cart trống, cho phép thêm
        
        try:
            new_restaurant = Restaurant.objects.select_related('chain').get(id=new_restaurant_id)
        except Restaurant.DoesNotExist:
            raise ValidationError({
                'restaurant': 'Chi nhánh không tồn tại.'
            })
        
        # Nếu items hiện tại thuộc chain
        if first_item.chain:
            # Cho phép thêm món từ bất kỳ restaurant nào trong cùng chain
            if not new_restaurant.chain or new_restaurant.chain_id != first_item.chain_id:
                raise ValidationError({
                    'restaurant': f'Giỏ hàng đã có món từ chuỗi "{first_item.chain.name}". '
                                 f'Vui lòng chọn món từ cùng chuỗi nhà hàng.'
                })
        else:
            # Items từ restaurant độc lập - phải match chính xác restaurant
            if new_restaurant.id != first_item.restaurant_id:
                raise ValidationError({
                    'restaurant': f'Giỏ hàng đã có món từ "{first_item.restaurant.name}". '
                                 f'Vui lòng xóa các món hiện tại để thêm món từ nhà hàng khác.'
                })
    
    def clear_items(self):
        """Xóa tất cả items trong cart"""
        self.items.all().delete()
        self.subtotal = Decimal('0.00')
        self.save()


class CartItem(models.Model):
    """
    Món trong giỏ hàng
    """
    id = models.BigAutoField(primary_key=True)
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Giỏ hàng"
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        verbose_name="Món ăn"
    )

    # Thông tin nhà hàng cho từng món
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        verbose_name="Nhà hàng"
    )
    chain = models.ForeignKey(
        RestaurantChain,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="Chuỗi nhà hàng"
    )

    # Snapshot thông tin món (để handle thay đổi giá/menu)
    item_name = models.CharField(
        max_length=200,
        verbose_name="Tên món"
    )
    item_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Giá món"
    )
    item_image = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Hình ảnh món"
    )
    restaurant_name = models.CharField(
        max_length=200,
        verbose_name="Tên nhà hàng"
    )

    # Số lượng và tùy chỉnh
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Số lượng"
    )
    special_instructions = models.TextField(
        blank=True,
        verbose_name="Yêu cầu đặc biệt cho món ăn",
        help_text="VD: Ít cay, không hành, v.v."
    )

    # Trường tính toán - Giá trị món (chưa bao gồm phí ship/thuế)
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Thành tiền",
        help_text="Giá món x Số lượng"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ngày tạo"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Ngày cập nhật"
    )

    class Meta:
        db_table = 'cart_items'
        verbose_name = "Món trong giỏ hàng"
        verbose_name_plural = "Các món trong giỏ hàng"
        unique_together = ['cart', 'menu_item']
        indexes = [
            models.Index(fields=['cart', 'created_at']),
            models.Index(fields=['restaurant']),
            models.Index(fields=['menu_item']),
            models.Index(fields=['cart', 'restaurant']),
        ]

    def __str__(self):
        return f"{self.quantity}x {self.item_name} trong giỏ hàng {self.cart.user.username}"
    
    def clean(self):
        """Validate CartItem data"""
        super().clean()
        
        # Validate: items trong cart phải cùng chain (nếu thuộc chain) hoặc cùng restaurant (nếu độc lập)
        if self.cart and self.restaurant:
            # Check items hiện tại (exclude item đang được save)
            existing_items = self.cart.items.exclude(id=self.id).select_related(
                'restaurant', 'chain'
            )
            
            if existing_items.exists():
                first_item = existing_items.first()
                
                # Nếu items hiện tại thuộc chain
                if first_item.chain:
                    # Cho phép thêm món từ bất kỳ restaurant nào trong cùng chain
                    if not self.chain or self.chain_id != first_item.chain_id:
                        raise ValidationError({
                            'restaurant': f'Giỏ hàng đã có món từ chuỗi "{first_item.chain.name}". '
                                        f'Vui lòng chọn món từ cùng chuỗi nhà hàng.'
                        })
                else:
                    # Items từ restaurant độc lập - phải match chính xác
                    if self.restaurant_id != first_item.restaurant_id:
                        raise ValidationError({
                            'restaurant': f'Giỏ hàng đã có món từ "{first_item.restaurant.name}". '
                                        f'Vui lòng xóa các món hiện tại để thêm món từ nhà hàng khác.'
                        })
    
    def save(self, *args, **kwargs):
        """Override save để validate và tính subtotal"""
        # Validate trước khi save
        self.full_clean()
        
        # Tính subtotal
        self.subtotal = (self.item_price * self.quantity).quantize(Decimal('0.01'))
        
        super().save(*args, **kwargs)
        
        # Cập nhật lại tổng giỏ hàng
        self.cart.calculate_totals()
    
    def calculate_subtotal(self):
        """Tính thành tiền cho món"""
        self.subtotal = (self.item_price * self.quantity).quantize(Decimal('0.01'))
        self.save(update_fields=['subtotal'])

        # Cập nhật lại tổng giỏ hàng
        self.cart.calculate_totals()