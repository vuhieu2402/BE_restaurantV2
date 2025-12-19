from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Category, MenuItem

User = get_user_model()


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializer cho Category model
    """
    owner_type = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'chain', 'restaurant', 'owner_type', 'owner_name',
            'name', 'slug', 'description', 'image',
            'display_order', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'owner_type', 'owner_name']
    
    def get_owner_type(self, obj):
        """Get whether this belongs to chain or restaurant"""
        if obj.chain:
            return 'chain'
        elif obj.restaurant:
            return 'restaurant'
        return None
    
    def get_owner_name(self, obj):
        """Get chain or restaurant name"""
        if obj.chain:
            return obj.chain.name
        elif obj.restaurant:
            return obj.restaurant.name
        return None


class CategoryCreateSerializer(serializers.ModelSerializer):
    """
    Serializer cho creating Category
    """
    class Meta:
        model = Category
        fields = [
            'chain', 'restaurant', 'name', 'slug', 'description', 'image',
            'display_order'
        ]

    def validate_display_order(self, value):
        if value < 0:
            raise serializers.ValidationError("Display order must be non-negative")
        return value
    
    def validate(self, data):
        """Validate that category has either chain or restaurant"""
        if not data.get('chain') and not data.get('restaurant'):
            raise serializers.ValidationError(
                "Category must belong to either a chain or a restaurant"
            )
        if data.get('chain') and data.get('restaurant'):
            raise serializers.ValidationError(
                "Category cannot belong to both chain and restaurant"
            )
        return data


class CategoryUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer cho updating Category
    """
    class Meta:
        model = Category
        fields = [
            'name', 'slug', 'description', 'image',
            'display_order', 'is_active'
        ]
        # Don't allow updating chain/restaurant after creation

    def validate_display_order(self, value):
        if value < 0:
            raise serializers.ValidationError("Display order must be non-negative")
        return value


class CategoryListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer cho category listing
    """
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'image',
            'display_order', 'item_count'
        ]

    def get_item_count(self, obj):
        """Get count of available items in this category"""
        return obj.menu_items.filter(is_available=True).count()


class CategoryWithItemsSerializer(serializers.ModelSerializer):
    """
    Serializer cho category with items
    """
    items = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'image',
            'display_order', 'is_active', 'items'
        ]

    def get_items(self, obj):
        """Get items in this category"""
        items = obj.menu_items.filter(
            is_available=True,
            is_active=True
        ).order_by('display_order', 'name')
        return MenuItemListSerializer(items, many=True, context=self.context).data


class MenuItemSerializer(serializers.ModelSerializer):
    """
    Serializer cho MenuItem model
    """
    is_on_sale = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    owner_type = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            'id', 'chain', 'restaurant', 'owner_type', 'owner_name',
            'category', 'name', 'slug', 'description',
            'price', 'original_price', 'image', 'calories', 'preparation_time',
            'rating', 'total_reviews', 'rating_distribution', 'last_rated_at',
            'verified_purchase_percentage', 'is_available', 'is_featured',
            'is_vegetarian', 'is_spicy', 'display_order',
            'is_on_sale', 'discount_percentage', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_on_sale', 'discount_percentage', 'owner_type', 'owner_name']
    
    def get_owner_type(self, obj):
        """Get whether this belongs to chain or restaurant"""
        if obj.chain:
            return 'chain'
        elif obj.restaurant:
            return 'restaurant'
        return None
    
    def get_owner_name(self, obj):
        """Get chain or restaurant name"""
        if obj.chain:
            return obj.chain.name
        elif obj.restaurant:
            return obj.restaurant.name
        return None


class MenuItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer cho creating MenuItem
    """
    class Meta:
        model = MenuItem
        fields = [
            'chain', 'restaurant', 'category', 'name', 'slug', 'description',
            'price', 'original_price', 'image', 'calories',
            'preparation_time', 'is_available', 'is_featured',
            'is_vegetarian', 'is_spicy', 'display_order'
        ]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price must be non-negative")
        return value

    def validate_original_price(self, value):
        if value is not None and value <= self.initial_data.get('price', 0):
            raise serializers.ValidationError("Original price must be greater than current price")
        return value

    def validate_calories(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Calories must be non-negative")
        return value

    def validate_preparation_time(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Preparation time must be non-negative")
        return value

    def validate_rating(self, value):
        if value is not None and not 0 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 0 and 5")
        return value

    def validate_display_order(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Display order must be non-negative")
        return value if value is not None else 0

    def validate(self, data):
        # Validate price logic
        price = data.get('price', 0)
        original_price = data.get('original_price')

        if original_price is not None and original_price <= price:
            raise serializers.ValidationError(
                "Original price must be greater than current price"
            )
        
        # Validate chain/restaurant logic
        if not data.get('chain') and not data.get('restaurant'):
            raise serializers.ValidationError(
                "Menu item must belong to either a chain or a restaurant"
            )
        if data.get('chain') and data.get('restaurant'):
            raise serializers.ValidationError(
                "Menu item cannot belong to both chain and restaurant"
            )

        return data


class MenuItemUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer cho updating MenuItem
    """
    class Meta:
        model = MenuItem
        fields = [
            'category', 'name', 'slug', 'description',
            'price', 'original_price', 'image', 'calories',
            'preparation_time', 'rating', 'is_available',
            'is_featured', 'is_vegetarian', 'is_spicy',
            'display_order'
        ]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price must be non-negative")
        return value

    def validate_original_price(self, value):
        if value is not None:
            price = self.instance.price if self.instance else 0
            if value <= price:
                raise serializers.ValidationError("Original price must be greater than current price")
        return value

    def validate_calories(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Calories must be non-negative")
        return value

    def validate_preparation_time(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Preparation time must be non-negative")
        return value

    def validate_rating(self, value):
        if value is not None and not 0 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 0 and 5")
        return value

    def validate_display_order(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Display order must be non-negative")
        return value if value is not None else 0

    def validate(self, data):
        price = data.get('price', self.instance.price if self.instance else 0)
        original_price = data.get('original_price')

        if original_price is not None and original_price <= price:
            raise serializers.ValidationError(
                "Original price must be greater than current price"
            )

        return data


class MenuItemListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer cho menu item listing
    """
    is_on_sale = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    category_name = serializers.SerializerMethodField()
    category_slug = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'slug', 'price', 'description', 'original_price',
            'image', 'rating', 'total_reviews', 'verified_purchase_percentage',
            'is_available', 'is_featured', 'is_vegetarian', 'is_spicy',
            'display_order', 'is_on_sale', 'discount_percentage',
            'category_name', 'category_slug'
        ]

    def get_category_name(self, obj):
        """Get category name"""
        return obj.category.name if obj.category else None

    def get_category_slug(self, obj):
        """Get category slug"""
        return obj.category.slug if obj.category else None


class MenuItemDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer cho menu item information
    """
    is_on_sale = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()
    category_name = serializers.SerializerMethodField()
    category_slug = serializers.SerializerMethodField()
    formatted_price = serializers.SerializerMethodField()
    formatted_original_price = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'original_price',
            'image', 'calories', 'preparation_time', 'rating',
            'total_reviews', 'rating_distribution', 'last_rated_at',
            'verified_purchase_percentage', 'is_available', 'is_featured',
            'is_vegetarian', 'is_spicy', 'display_order',
            'is_on_sale', 'discount_percentage', 'category_name',
            'category_slug', 'formatted_price', 'formatted_original_price',
            'created_at', 'updated_at'
        ]

    def get_category_name(self, obj):
        """Get category name"""
        return obj.category.name if obj.category else None

    def get_category_slug(self, obj):
        """Get category slug"""
        return obj.category.slug if obj.category else None

    def get_formatted_price(self, obj):
        """Get formatted price"""
        return f"{int(obj.price):,} VND"

    def get_formatted_original_price(self, obj):
        """Get formatted original price"""
        if obj.original_price:
            return f"{int(obj.original_price):,} VND"
        return None


class FeaturedMenuItemSerializer(serializers.ModelSerializer):
    """
    Serializer cho featured menu items
    """
    category_name = serializers.SerializerMethodField()
    formatted_price = serializers.SerializerMethodField()
    is_on_sale = serializers.ReadOnlyField()
    discount_percentage = serializers.ReadOnlyField()

    class Meta:
        model = MenuItem
        fields = [
            'id', 'name', 'slug', 'price', 'original_price',
            'image', 'rating', 'total_reviews', 'is_available',
            'is_vegetarian', 'is_spicy', 'is_on_sale',
            'discount_percentage', 'category_name', 'formatted_price'
        ]

    def get_category_name(self, obj):
        """Get category name"""
        return obj.category.name if obj.category else None

    def get_formatted_price(self, obj):
        """Get formatted price"""
        return f"{int(obj.price):,} VND"


class MenuItemSearchSerializer(serializers.Serializer):
    """
    Serializer cho menu item search parameters
    """
    search = serializers.CharField(required=False, allow_blank=True)
    category_id = serializers.IntegerField(required=False, min_value=1)
    is_available = serializers.BooleanField(required=False)
    is_featured = serializers.BooleanField(required=False)
    is_vegetarian = serializers.BooleanField(required=False)
    is_spicy = serializers.BooleanField(required=False)
    min_price = serializers.DecimalField(
        required=False, max_digits=10, decimal_places=2, min_value=0
    )
    max_price = serializers.DecimalField(
        required=False, max_digits=10, decimal_places=2, min_value=0
    )
    price_range = serializers.ChoiceField(
        required=False,
        choices=['budget', 'mid', 'premium', 'luxury']
    )


class CategorySearchSerializer(serializers.Serializer):
    """
    Serializer cho category search parameters
    """
    search = serializers.CharField(required=False, allow_blank=True)


class CategoryReorderSerializer(serializers.Serializer):
    """
    Serializer cho category reordering
    """
    id = serializers.IntegerField(min_value=1)
    display_order = serializers.IntegerField(min_value=0)


class MenuItemPriceUpdateSerializer(serializers.Serializer):
    """
    Serializer cho menu item price updates
    """
    id = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0
    )
    original_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False
    )

    def validate(self, data):
        price = data.get('price', 0)
        original_price = data.get('original_price')

        if original_price is not None and original_price <= price:
            raise serializers.ValidationError(
                "Original price must be greater than current price"
            )

        return data


class BulkPriceUpdateSerializer(serializers.Serializer):
    """
    Serializer cho bulk price updates
    """
    price_updates = serializers.ListField(
        child=MenuItemPriceUpdateSerializer(),
        min_length=1
    )


class MenuItemToggleSerializer(serializers.Serializer):
    """
    Serializer cho menu item toggle operations
    """
    item_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1
    )


class CategoryReorderBulkSerializer(serializers.Serializer):
    """
    Serializer cho bulk category reordering
    """
    categories = serializers.ListField(
        child=CategoryReorderSerializer(),
        min_length=1
    )


class MenuAnalyticsSerializer(serializers.Serializer):
    """
    Serializer cho menu analytics
    """
    overview = serializers.JSONField()
    price_distribution = serializers.JSONField()


class MenuSummarySerializer(serializers.Serializer):
    """
    Serializer cho menu summary
    """
    total_categories = serializers.IntegerField(min_value=0)
    total_items = serializers.IntegerField(min_value=0)
    available_items = serializers.IntegerField(min_value=0)
    featured_items = serializers.IntegerField(min_value=0)
    vegetarian_items = serializers.IntegerField(min_value=0)
    avg_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class DietaryPreferenceSerializer(serializers.Serializer):
    """
    Serializer cho dietary preferences
    """
    is_vegetarian = serializers.BooleanField(required=False)
    is_spicy = serializers.BooleanField(required=False)
    max_calories = serializers.IntegerField(
        required=False, min_value=0
    )
    max_preparation_time = serializers.IntegerField(
        required=False, min_value=0
    )


class MenuItemBulkCreateSerializer(serializers.Serializer):
    """
    Serializer cho bulk menu item creation
    """
    items = serializers.ListField(
        child=MenuItemCreateSerializer(),
        min_length=1
    )


class CategoryBulkCreateSerializer(serializers.Serializer):
    """
    Serializer cho bulk category creation
    """
    categories = serializers.ListField(
        child=CategoryCreateSerializer(),
        min_length=1
    )