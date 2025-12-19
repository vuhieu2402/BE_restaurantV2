from rest_framework import serializers
from .models import Restaurant, RestaurantChain, Table


class RestaurantChainSerializer(serializers.ModelSerializer):
    """
    Serializer cho RestaurantChain model
    """
    total_branches = serializers.SerializerMethodField()
    
    class Meta:
        model = RestaurantChain
        fields = [
            'id', 'name', 'slug', 'description', 'logo', 'cover_image',
            'contact_email', 'contact_phone', 'website',
            'default_minimum_order', 'default_delivery_fee', 'default_delivery_radius',
            'enable_auto_assignment', 'is_active', 'owner',
            'total_branches', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_branches']
    
    def get_total_branches(self, obj):
        """Get total number of active branches"""
        return obj.get_total_branches()


class RestaurantChainListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer cho chain listing
    """
    total_branches = serializers.SerializerMethodField()
    
    class Meta:
        model = RestaurantChain
        fields = [
            'id', 'name', 'slug', 'logo', 'description',
            'contact_phone', 'enable_auto_assignment',
            'total_branches', 'is_active'
        ]
    
    def get_total_branches(self, obj):
        return obj.get_total_branches()


class RestaurantChainDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer cho chain information với branches
    """
    total_branches = serializers.SerializerMethodField()
    branches = serializers.SerializerMethodField()
    
    class Meta:
        model = RestaurantChain
        fields = [
            'id', 'name', 'slug', 'description', 'logo', 'cover_image',
            'contact_email', 'contact_phone', 'website',
            'default_minimum_order', 'default_delivery_fee', 'default_delivery_radius',
            'enable_auto_assignment', 'is_active', 'owner',
            'total_branches', 'branches', 'created_at', 'updated_at'
        ]
    
    def get_total_branches(self, obj):
        return obj.get_total_branches()
    
    def get_branches(self, obj):
        """Get list of active branches"""
        branches = obj.restaurants.filter(is_active=True)
        return RestaurantListSerializer(branches, many=True, context=self.context).data


class RestaurantChainCreateSerializer(serializers.ModelSerializer):
    """
    Serializer cho creating RestaurantChain
    """
    class Meta:
        model = RestaurantChain
        fields = [
            'name', 'slug', 'description', 'logo', 'cover_image',
            'contact_email', 'contact_phone', 'website',
            'default_minimum_order', 'default_delivery_fee', 'default_delivery_radius',
            'enable_auto_assignment', 'owner'
        ]


class RestaurantChainUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer cho updating RestaurantChain
    """
    class Meta:
        model = RestaurantChain
        fields = [
            'name', 'slug', 'description', 'logo', 'cover_image',
            'contact_email', 'contact_phone', 'website',
            'default_minimum_order', 'default_delivery_fee', 'default_delivery_radius',
            'enable_auto_assignment', 'is_active', 'owner'
        ]


class NearestBranchSerializer(serializers.ModelSerializer):
    """
    Serializer cho nearest branch result
    """
    distance_km = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    
    class Meta:
        model = Restaurant
        fields = [
            'id', 'name', 'slug', 'address', 'city', 'district',
            'latitude', 'longitude', 'phone_number', 'logo',
            'is_open', 'rating', 'delivery_fee', 'delivery_radius',
            'distance_km'
        ]


class RestaurantSerializer(serializers.ModelSerializer):
    """
    Serializer cho Restaurant model
    """
    is_currently_open = serializers.ReadOnlyField()
    chain_info = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            'id', 'chain', 'chain_info', 'name', 'slug', 'description', 'phone_number', 'email',
            'address', 'city', 'district', 'ward', 'postal_code',
            'latitude', 'longitude', 'logo', 'cover_image',
            'opening_time', 'closing_time', 'is_open', 'is_currently_open',
            'rating', 'total_reviews', 'minimum_order', 'delivery_fee', 'delivery_radius',
            'is_active', 'manager', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_currently_open', 'chain_info']
    
    def get_chain_info(self, obj):
        """Get basic chain information if restaurant belongs to a chain"""
        if obj.chain:
            return {
                'id': obj.chain.id,
                'name': obj.chain.name,
                'slug': obj.chain.slug,
                'logo': obj.chain.logo.url if obj.chain.logo else None
            }
        return None


class RestaurantCreateSerializer(serializers.ModelSerializer):
    """
    Serializer cho creating Restaurant
    """
    class Meta:
        model = Restaurant
        fields = [
            'chain', 'name', 'slug', 'description', 'phone_number', 'email',
            'address', 'city', 'district', 'ward', 'postal_code',
            'latitude', 'longitude', 'logo', 'cover_image',
            'opening_time', 'closing_time', 'is_open',
            'minimum_order', 'delivery_fee', 'delivery_radius',
            'manager'
        ]

    def validate_latitude(self, value):
        if value and not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value

    def validate_longitude(self, value):
        if value and not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value

    def validate(self, data):
        opening_time = data.get('opening_time')
        closing_time = data.get('closing_time')

        if opening_time and closing_time and opening_time >= closing_time:
            raise serializers.ValidationError(
                "Opening time must be before closing time"
            )

        return data


class RestaurantUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer cho updating Restaurant
    """
    class Meta:
        model = Restaurant
        fields = [
            'chain', 'name', 'slug', 'description', 'phone_number', 'email',
            'address', 'city', 'district', 'ward', 'postal_code',
            'latitude', 'longitude', 'logo', 'cover_image',
            'opening_time', 'closing_time', 'is_open',
            'minimum_order', 'delivery_fee', 'delivery_radius',
            'manager'
        ]

    def validate_latitude(self, value):
        if value and not -90 <= value <= 90:
            raise serializers.ValidationError("Latitude must be between -90 and 90")
        return value

    def validate_longitude(self, value):
        if value and not -180 <= value <= 180:
            raise serializers.ValidationError("Longitude must be between -180 and 180")
        return value

    def validate(self, data):
        opening_time = data.get('opening_time')
        closing_time = data.get('closing_time')

        if opening_time and closing_time and opening_time >= closing_time:
            raise serializers.ValidationError(
                "Opening time must be before closing time"
            )

        return data


class RestaurantListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer cho restaurant listing
    """
    is_currently_open = serializers.ReadOnlyField()
    chain_name = serializers.CharField(source='chain.name', read_only=True, allow_null=True)

    class Meta:
        model = Restaurant
        fields = [
            'id', 'chain', 'chain_name', 'name', 'slug', 'address', 'city', 'district',
            'latitude', 'longitude', 'phone_number', 'logo',
            'is_open', 'is_currently_open', 'rating', 'total_reviews',
            'delivery_fee', 'delivery_radius'
        ]


class RestaurantDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer cho restaurant information
    """
    is_currently_open = serializers.ReadOnlyField()
    tables_count = serializers.SerializerMethodField()
    chain_info = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            'id', 'chain', 'chain_info', 'name', 'slug', 'description', 'phone_number', 'email',
            'address', 'city', 'district', 'ward', 'postal_code',
            'latitude', 'longitude', 'logo', 'cover_image',
            'opening_time', 'closing_time', 'is_open', 'is_currently_open',
            'rating', 'total_reviews', 'minimum_order', 'delivery_fee', 'delivery_radius',
            'is_active', 'manager', 'tables_count', 'created_at', 'updated_at'
        ]

    def get_tables_count(self, obj):
        """Get total number of active tables for this restaurant"""
        return obj.tables.filter(is_active=True).count()
    
    def get_chain_info(self, obj):
        """Get chain information if restaurant belongs to a chain"""
        if obj.chain:
            return {
                'id': obj.chain.id,
                'name': obj.chain.name,
                'slug': obj.chain.slug,
                'logo': obj.chain.logo.url if obj.chain.logo else None,
                'enable_auto_assignment': obj.chain.enable_auto_assignment
            }
        return None


class NearbyRestaurantSerializer(serializers.ModelSerializer):
    """
    Serializer cho nearby restaurants with distance calculation
    """
    distance_km = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            'id', 'name', 'slug', 'address', 'latitude', 'longitude',
            'phone_number', 'logo', 'is_open', 'is_currently_open',
            'rating', 'delivery_fee', 'distance_km'
        ]

    def get_distance_km(self, obj):
        """Calculate distance from user coordinates"""
        request = self.context.get('request')
        if not request or not hasattr(request, 'query_params'):
            return None

        user_lat = request.query_params.get('latitude')
        user_lon = request.query_params.get('longitude')

        if user_lat and user_lon:
            try:
                # Simple distance calculation (for production, use haversine formula)
                lat_diff = (float(obj.latitude) - float(user_lat)) * 111
                lon_diff = (float(obj.longitude) - float(user_lon)) * 111 * abs(float(obj.latitude))
                distance = (lat_diff ** 2 + lon_diff ** 2) ** 0.5
                return round(distance, 2)
            except (ValueError, TypeError):
                pass

        return None


class TableSerializer(serializers.ModelSerializer):
    """
    Serializer cho Table model
    """
    class Meta:
        model = Table
        fields = [
            'id', 'restaurant', 'table_number', 'capacity', 'floor', 'section',
            'status', 'x_position', 'y_position', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TableCreateSerializer(serializers.ModelSerializer):
    """
    Serializer cho creating Table
    """
    class Meta:
        model = Table
        fields = [
            'table_number', 'capacity', 'floor', 'section',
            'status', 'x_position', 'y_position'
        ]

    def validate_capacity(self, value):
        if value < 1:
            raise serializers.ValidationError("Capacity must be at least 1")
        if value > 50:
            raise serializers.ValidationError("Capacity cannot exceed 50")
        return value

    def validate_floor(self, value):
        if value < 1 or value > 99:
            raise serializers.ValidationError("Floor must be between 1 and 99")
        return value

    def validate_x_position(self, value):
        if value is not None and (value < 0 or value > 10000):
            raise serializers.ValidationError("X position must be between 0 and 10000")
        return value

    def validate_y_position(self, value):
        if value is not None and (value < 0 or value > 10000):
            raise serializers.ValidationError("Y position must be between 0 and 10000")
        return value


class TableUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer cho updating Table
    """
    class Meta:
        model = Table
        fields = [
            'table_number', 'capacity', 'floor', 'section',
            'status', 'x_position', 'y_position', 'is_active'
        ]

    def validate_capacity(self, value):
        if value < 1:
            raise serializers.ValidationError("Capacity must be at least 1")
        if value > 50:
            raise serializers.ValidationError("Capacity cannot exceed 50")
        return value

    def validate_floor(self, value):
        if value < 1 or value > 99:
            raise serializers.ValidationError("Floor must be between 1 and 99")
        return value

    def validate_x_position(self, value):
        if value is not None and (value < 0 or value > 10000):
            raise serializers.ValidationError("X position must be between 0 and 10000")
        return value

    def validate_y_position(self, value):
        if value is not None and (value < 0 or value > 10000):
            raise serializers.ValidationError("Y position must be between 0 and 10000")
        return value


class TableListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer cho table listing
    """
    class Meta:
        model = Table
        fields = [
            'id', 'table_number', 'capacity', 'floor', 'section',
            'status', 'x_position', 'y_position'
        ]


class TableLayoutSerializer(serializers.ModelSerializer):
    """
    Serializer cho restaurant table layout
    """
    class Meta:
        model = Table
        fields = [
            'id', 'table_number', 'capacity', 'floor', 'section',
            'status', 'x_position', 'y_position'
        ]


class AvailableTableSerializer(serializers.ModelSerializer):
    """
    Serializer cho available tables
    """
    class Meta:
        model = Table
        fields = [
            'id', 'table_number', 'capacity', 'floor', 'section',
            'x_position', 'y_position'
        ]


class RestaurantSearchSerializer(serializers.Serializer):
    """
    Serializer cho restaurant search parameters
    """
    search = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True)
    district = serializers.CharField(required=False, allow_blank=True)
    is_open = serializers.BooleanField(required=False)
    min_rating = serializers.DecimalField(
        max_digits=3, decimal_places=2, required=False,
        min_value=0, max_value=5
    )
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False,
        min_value=-90, max_value=90
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6, required=False,
        min_value=-180, max_value=180
    )
    radius = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False,
        min_value=0.1, max_value=100
    )


class TableSearchSerializer(serializers.Serializer):
    """
    Serializer cho table search parameters
    """
    status = serializers.ChoiceField(
        choices=Table.STATUS_CHOICES, required=False
    )
    floor = serializers.IntegerField(required=False, min_value=1, max_value=99)
    section = serializers.CharField(required=False, allow_blank=True)
    min_capacity = serializers.IntegerField(required=False, min_value=1)


class BulkTableOperationSerializer(serializers.Serializer):
    """
    Serializer cho bulk table operations
    """
    action = serializers.ChoiceField(choices=[
        'update_status', 'delete', 'update_floor'
    ])
    table_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1
    )
    data = serializers.JSONField(required=False)  # Additional data for specific operations