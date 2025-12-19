from rest_framework import serializers
from decimal import Decimal
from django.db.models import Sum
from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    """
    Serializer cho CartItem - hiển thị thông tin chi tiết
    
    Note: Không bao gồm thông tin delivery. Thông tin đó sẽ được xử lý ở Order level.
    """
    menu_item = serializers.SerializerMethodField()
    subtotal_display = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            'id',
            'menu_item',
            'quantity',
            'special_instructions',
            'subtotal',
            'subtotal_display',
            'created_at',
            'updated_at'
        ]

    def get_menu_item(self, obj):
        """Lấy thông tin chi tiết của menu_item"""
        if obj.menu_item:
            return {
                'id': obj.menu_item.id,
                'name': obj.menu_item.name,
                'slug': obj.menu_item.slug,
                'price': obj.menu_item.price,
                'image': obj.menu_item.image.url if obj.menu_item.image else None,
                'description': obj.menu_item.description,
                'calories': obj.menu_item.calories,
                'preparation_time': obj.menu_item.preparation_time,
                'is_vegetarian': obj.menu_item.is_vegetarian,
                'is_spicy': obj.menu_item.is_spicy,
            }
        return None

    def get_restaurant(self, obj):
        """Lấy thông tin chi tiết của restaurant"""
        if obj.restaurant:
            return {
                'id': obj.restaurant.id,
                'name': obj.restaurant.name,
                'slug': obj.restaurant.slug,
                'address': obj.restaurant.address,
                'phone_number': obj.restaurant.phone_number,
                'is_open': obj.restaurant.is_open,
                'minimum_order': obj.restaurant.minimum_order,
            }
        return None

    def get_subtotal_display(self, obj):
        """Format hiển thị subtotal"""
        return f"{obj.subtotal:,.0f}đ"


class CartItemCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer cho việc thêm/cập nhật item trong giỏ hàng
    
    Note: Chỉ cần menu_item_id, quantity, và special_instructions.
    Thông tin delivery sẽ được nhập khi checkout (tạo Order).
    """
    menu_item_id = serializers.IntegerField(write_only=True)
    quantity = serializers.IntegerField(min_value=1, default=1)

    class Meta:
        model = CartItem
        fields = [
            'menu_item_id',
            'quantity',
            'special_instructions'
        ]

    def validate_menu_item_id(self, value):
        """Validate menu_item_id exists and is available"""
        from apps.dishes.models import MenuItem

        try:
            menu_item = MenuItem.objects.get(
                id=value,
                is_available=True
            )
            return value
        except MenuItem.DoesNotExist:
            raise serializers.ValidationError(
                "Món ăn không tồn tại hoặc không còn bán"
            )


class CartItemListSerializer(serializers.Serializer):
    """
    Serializer cho việc thêm nhiều món vào giỏ hàng
    """
    items = CartItemCreateUpdateSerializer(many=True)

    def validate_items(self, value):
        """Validate danh sách items"""
        if not value:
            raise serializers.ValidationError("Danh sách món không được trống")
        return value


class CartItemRemoveSerializer(serializers.Serializer):
    """
    Serializer cho việc xóa nhiều món
    """
    item_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )

    def validate_item_ids(self, value):
        """Validate danh sách item_ids"""
        if not value:
            raise serializers.ValidationError("Danh sách ID món không được trống")
        return value


class CartSerializer(serializers.ModelSerializer):
    """
    Serializer cho Cart - hiển thị thông tin chi tiết
    
    Note: 
    - Cart chỉ hiển thị giá trị món ăn (subtotal)
    - Không có thông tin về delivery/tax/discount - những thông tin này sẽ được tính khi tạo Order
    - items_grouped_by_restaurant giúp frontend dễ dàng hiển thị theo nhà hàng
    """
    items_grouped_by_restaurant = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    subtotal_display = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            'id',
            'user',
            'subtotal',
            'subtotal_display',
            'notes',
            'items_grouped_by_restaurant',
            'total_items',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['user']

    def get_items_grouped_by_restaurant(self, obj):
        """
        Nhóm các món theo nhà hàng để hiển thị tốt hơn trên UI
        
        Note: Chỉ tính tổng giá món ăn (subtotal), không tính delivery fee.
        Delivery fee sẽ được tính khi tạo Order.
        """
        grouped = {}

        for item in obj.items.all():
            restaurant_id = item.restaurant.id

            if restaurant_id not in grouped:
                grouped[restaurant_id] = {
                    'items': [],
                    'restaurant_subtotal': 0,
                    'item_count': 0
                }

            # Thêm item vào nhóm
            item_data = CartItemSerializer(item).data
            grouped[restaurant_id]['items'].append(item_data)
            grouped[restaurant_id]['restaurant_subtotal'] += float(item.subtotal)
            grouped[restaurant_id]['item_count'] += item.quantity

        # Format các giá trị số
        for restaurant_group in grouped.values():
            restaurant_group['restaurant_subtotal_display'] = f"{restaurant_group['restaurant_subtotal']:,.0f}đ"

        return list(grouped.values())


    def get_total_items(self, obj):
        """Lấy tổng số lượng món trong giỏ hàng"""
        return obj.get_total_items()

    def get_subtotal_display(self, obj):
        """Format hiển thị subtotal"""
        return f"{obj.subtotal:,.0f}đ"


class CartUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer cho việc cập nhật cart
    """
    class Meta:
        model = Cart
        fields = ['notes']


class CartCalculateSerializer(serializers.Serializer):
    """
    Serializer cho việc tính toán lại giỏ hàng
    """
    pass  # Không cần thêm field nào, chỉ cần trigger action


class CartCheckoutSerializer(serializers.Serializer):
    """
    Serializer cho việc checkout giỏ hàng - tạo nhiều orders
    """
    payment_method_id = serializers.IntegerField(required=False, allow_null=True)
    delivery_address = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
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

    def validate(self, attrs):
        """Validate checkout data"""
        # Thêm các validation rules cho checkout ở đây
        # Ví dụ: kiểm tra địa chỉ giao hàng, phương thức thanh toán, v.v.
        return attrs


class CartStatsSerializer(serializers.Serializer):
    """
    Serializer cho thống kê giỏ hàng
    """
    total_carts = serializers.IntegerField()
    active_carts = serializers.IntegerField()
    total_items = serializers.IntegerField()
    total_value = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_items_per_cart = serializers.DecimalField(max_digits=5, decimal_places=2)
    most_popular_items = serializers.ListField()
    restaurant_distribution = serializers.ListField()