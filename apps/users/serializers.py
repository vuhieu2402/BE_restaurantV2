"""
User Management Serializers - API Layer
- Validate input data
- Format output data
- KHÔNG business logic
- KHÔNG database queries
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator, EmailValidator
from django.utils import timezone
from apps.restaurants.serializers import RestaurantSerializer
from apps.restaurants.models import Restaurant
from .models import CustomerProfile, StaffProfile
from .selectors import UserSelector

User = get_user_model()


class BaseUserSerializer(serializers.ModelSerializer):
    """Base serializer cho User model"""
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    password_confirm = serializers.CharField(write_only=True, required=False)
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)
    created_at_formatted = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'password', 'password_confirm', 'user_type', 'user_type_display',
            'address', 'city', 'district', 'ward', 'postal_code',
            'latitude', 'longitude', 'date_of_birth', 'avatar',
            'is_verified', 'is_active', 'date_joined', 'created_at', 'updated_at',
            'created_at_formatted'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'phone_number': {'required': False, 'allow_blank': True},
            'email': {'required': False, 'allow_blank': True},
            'is_verified': {'read_only': True},
            'date_joined': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
            'avatar': {'required': False, 'allow_null': True},
            'date_of_birth': {'required': False, 'allow_null': True},
        }

    def get_full_name(self, obj):
        """Get full name của user"""
        return obj.get_full_name()

    def get_created_at_formatted(self, obj):
        """Format created_at cho display"""
        return obj.created_at.strftime('%d/%m/%Y %H:%M') if obj.created_at else None

    def validate_password(self, value):
        """Validate password strength"""
        if value:
            try:
                validate_password(value)
            except ValidationError as e:
                raise serializers.ValidationError(str(e))
        return value

    def validate_email(self, value):
        """Validate email format và uniqueness cho creating user"""
        if value:
            validator = EmailValidator()
            validator(value)
        return value

    def validate_phone_number(self, value):
        """Validate phone number format"""
        if value:
            phone_regex = RegexValidator(
                regex=r'^\+?1?\d{9,15}$',
                message="Số điện thoại phải có định dạng: '+999999999'. Tối đa 15 số."
            )
            phone_regex(value)
        return value

    def validate_latitude(self, value):
        """Validate latitude"""
        if value is not None:
            if not -90 <= value <= 90:
                raise serializers.ValidationError("Vĩ độ phải nằm trong khoảng -90 đến 90.")
        return value

    def validate_longitude(self, value):
        """Validate longitude"""
        if value is not None:
            if not -180 <= value <= 180:
                raise serializers.ValidationError("Kinh độ phải nằm trong khoảng -180 đến 180.")
        return value

    def validate_date_of_birth(self, value):
        """Validate date of birth"""
        if value:
            if value > timezone.now().date():
                raise serializers.ValidationError("Ngày sinh không thể trong tương lai.")
            # Check if user is at least 13 years old
            min_date = timezone.now().date() - timezone.timedelta(days=13*365)
            if value > min_date:
                raise serializers.ValidationError("Bạn phải ít nhất 13 tuổi.")
        return value


class UserCreateSerializer(BaseUserSerializer):
    """Serializer cho tạo user mới"""
    class Meta(BaseUserSerializer.Meta):
        fields = BaseUserSerializer.Meta.fields + ['password_confirm']
        extra_kwargs = {
            **BaseUserSerializer.Meta.extra_kwargs,
            'password': {'write_only': True, 'required': True},
            'email': {'required': False, 'allow_blank': True},
            'phone_number': {'required': False, 'allow_blank': True},
            'password_confirm': {'write_only': True, 'required': True},
        }

    def validate(self, data):
        """Validate user creation data"""
        errors = {}

        # Kiểm tra email hoặc phone_number phải có
        email = data.get('email')
        phone_number = data.get('phone_number')

        if not email and not phone_number:
            errors['identifier'] = 'Phải cung cấp email hoặc số điện thoại'

        # Kiểm tra password confirmation
        password = data.get('password')
        password_confirm = data.get('password_confirm')

        if password and password_confirm:
            if password != password_confirm:
                errors['password_confirm'] = 'Mật khẩu xác nhận không khớp'

        # Kiểm tra uniqueness cho email và phone
        if email and UserSelector.check_email_exists(email):
            errors['email'] = 'Email đã được sử dụng'

        if phone_number and UserSelector.check_phone_exists(phone_number):
            errors['phone_number'] = 'Số điện thoại đã được sử dụng'

        if errors:
            raise serializers.ValidationError(errors)

        return data


class UserUpdateSerializer(BaseUserSerializer):
    """Serializer cho cập nhật user"""
    class Meta(BaseUserSerializer.Meta):
        extra_kwargs = {
            **BaseUserSerializer.Meta.extra_kwargs,
            'password': {'write_only': True, 'required': False},
            'email': {'required': False, 'allow_blank': True},
            'phone_number': {'required': False, 'allow_blank': True},
            'username': {'required': False},
            'user_type': {'read_only': True},  # Không cho đổi user type qua update
        }

    def validate(self, data):
        """Validate user update data"""
        errors = {}
        instance = self.instance

        # Kiểm tra password confirmation nếu có password mới
        password = data.get('password')
        password_confirm = data.get('password_confirm')

        if password:
            if not password_confirm:
                errors['password_confirm'] = 'Phải xác nhận mật khẩu mới'
            elif password != password_confirm:
                errors['password_confirm'] = 'Mật khẩu xác nhận không khớp'

        # Kiểm tra uniqueness nếu có thay đổi email/phone
        email = data.get('email')
        phone_number = data.get('phone_number')

        if email and email != instance.email:
            if UserSelector.check_email_exists(email):
                errors['email'] = 'Email đã được sử dụng'

        if phone_number and phone_number != instance.phone_number:
            if UserSelector.check_phone_exists(phone_number):
                errors['phone_number'] = 'Số điện thoại đã được sử dụng'

        if errors:
            raise serializers.ValidationError(errors)

        return data


class UserListSerializer(BaseUserSerializer):
    """Serializer cho danh sách users"""
    profile_info = serializers.SerializerMethodField(read_only=True)

    class Meta(BaseUserSerializer.Meta):
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'user_type', 'user_type_display',
            'is_verified', 'is_active', 'date_joined', 'created_at',
            'profile_info'
        ]

    def get_profile_info(self, obj):
        """Get thông tin profile tóm tắt"""
        if obj.user_type == 'customer':
            try:
                from .selectors import CustomerProfileSelector
                profile = CustomerProfileSelector.get_profile_by_user(obj)
                if profile:
                    return {
                        'loyalty_points': profile.loyalty_points,
                        'total_orders': profile.total_orders,
                        'preferred_language': profile.preferred_language,
                    }
            except:
                pass
        elif obj.user_type in ['staff', 'manager']:
            try:
                from .selectors import StaffProfileSelector
                profile = StaffProfileSelector.get_profile_by_user(obj)
                if profile:
                    return {
                        'position': profile.position,
                        'restaurant_id': profile.restaurant_id,
                        'is_active': profile.is_active,
                    }
            except:
                pass
        return None


class CustomerProfileSerializer(serializers.ModelSerializer):
    """Serializer cho CustomerProfile"""
    user_info = serializers.SerializerMethodField(read_only=True)
    loyalty_tier = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = CustomerProfile
        fields = [
            'id', 'user', 'preferred_language', 'loyalty_points', 'total_orders',
            'total_spent', 'receive_promotions', 'receive_notifications',
            'created_at', 'updated_at', 'user_info', 'loyalty_tier'
        ]
        extra_kwargs = {
            'user': {'read_only': True},
            'total_spent': {'decimal_places': 2, 'max_digits': 12},
        }

    def get_user_info(self, obj):
        """Get thông tin cơ bản của user"""
        if obj.user:
            return {
                'username': obj.user.username,
                'email': obj.user.email,
                'phone_number': obj.user.phone_number,
                'full_name': obj.user.get_full_name(),
                'avatar': obj.user.avatar.url if obj.user.avatar else None,
            }
        return None

    def get_loyalty_tier(self, obj):
        """Get loyalty tier của customer"""
        from django.conf import settings

        loyalty_tiers = getattr(settings, 'LOYALTY_TIERS', {
            'bronze': {'min_points': 0, 'name': 'Đồng', 'discount': 0.05},
            'silver': {'min_points': 100, 'name': 'Bạc', 'discount': 0.10},
            'gold': {'min_points': 500, 'name': 'Vàng', 'discount': 0.15},
            'platinum': {'min_points': 1000, 'name': 'Bạch Kim', 'discount': 0.20},
        })

        for tier_name, tier_info in sorted(
            loyalty_tiers.items(),
            key=lambda x: x[1]['min_points'],
            reverse=True
        ):
            if obj.loyalty_points >= tier_info['min_points']:
                return tier_info['name']

        return loyalty_tiers.get('bronze', {}).get('name', 'Không có hạng')


class StaffProfileSerializer(serializers.ModelSerializer):
    """Serializer cho StaffProfile"""
    user_info = serializers.SerializerMethodField(read_only=True)
    restaurant_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = StaffProfile
        fields = [
            'id', 'user', 'employee_id', 'position', 'hire_date', 'salary',
            'restaurant', 'is_active', 'created_at', 'updated_at',
            'user_info', 'restaurant_info'
        ]
        extra_kwargs = {
            'user': {'read_only': True},
            'salary': {'decimal_places': 2, 'max_digits': 10, 'allow_null': True},
            'restaurant': {'allow_null': True},
        }

    def get_user_info(self, obj):
        """Get thông tin cơ bản của user"""
        if obj.user:
            return {
                'username': obj.user.username,
                'email': obj.user.email,
                'phone_number': obj.user.phone_number,
                'full_name': obj.user.get_full_name(),
                'user_type': obj.user.get_user_type_display(),
                'avatar': obj.user.avatar.url if obj.user.avatar else None,
            }
        return None

    def get_restaurant_info(self, obj):
        """Get thông tin cơ bản của restaurant"""
        if obj.restaurant:
            return {
                'id': obj.restaurant.id,
                'name': obj.restaurant.name,
                'slug': obj.restaurant.slug,
            }
        return None


class CustomerProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer cho cập nhật customer profile"""
    class Meta:
        model = CustomerProfile
        fields = [
            'preferred_language', 'receive_promotions', 'receive_notifications'
        ]


class StaffProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer cho cập nhật staff profile"""
    restaurant = serializers.PrimaryKeyRelatedField(
        queryset=Restaurant.objects.filter(is_active=True),
        allow_null=True,
        required=False
    )

    class Meta:
        model = StaffProfile
        fields = [
            'position', 'salary', 'restaurant', 'is_active'
        ]
        extra_kwargs = {
            'salary': {'decimal_places': 2, 'max_digits': 10, 'allow_null': True},
            'restaurant': {'allow_null': True},
        }


class UserCreateWithProfileSerializer(serializers.Serializer):
    """Complex serializer cho tạo user với profile"""
    user = UserCreateSerializer()
    profile = serializers.SerializerMethodField()

    def get_profile(self, obj):
        """Get profile serializer dựa trên user_type"""
        user_type = self.initial_data.get('user', {}).get('user_type', 'customer')
        if user_type == 'customer':
            return CustomerProfileUpdateSerializer()
        elif user_type in ['staff', 'manager']:
            return StaffProfileUpdateSerializer()
        return None

    def create(self, validated_data):
        """Tạo user với profile"""
        user_data = validated_data.pop('user', {})
        profile_data = validated_data.get('profile', {})

        # Tạo user
        user = UserCreateSerializer().create(user_data)

        # Tạo profile
        if user.user_type == 'customer':
            CustomerProfile.objects.create(user=user, **profile_data)
        elif user.user_type in ['staff', 'manager']:
            StaffProfile.objects.create(user=user, **profile_data)

        return user


class BulkUserOperationSerializer(serializers.Serializer):
    """Serializer cho bulk operations"""
    user_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        min_length=1,
        max_length=100
    )
    operation = serializers.ChoiceField(
        choices=['activate', 'deactivate', 'delete'],
        required=True
    )
    reason = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True
    )

    def validate_user_ids(self, value):
        """Validate danh sách user_ids"""
        if len(value) > len(set(value)):
            raise serializers.ValidationError("Không thể thao tác trùng user ID trong cùng một lần.")
        return value


class UserFilterSerializer(serializers.Serializer):
    """Serializer cho filter users"""
    user_type = serializers.ChoiceField(
        choices=[ut[0] for ut in User.USER_TYPE_CHOICES],
        required=False
    )
    is_active = serializers.BooleanField(required=False)
    is_verified = serializers.BooleanField(required=False)
    search = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True
    )
    restaurant_id = serializers.IntegerField(
        min_value=1,
        required=False,
        allow_null=True
    )
    created_after = serializers.DateField(required=False, allow_null=True)
    created_before = serializers.DateField(required=False, allow_null=True)
    ordering = serializers.ChoiceField(
        choices=[
            'username', '-username',
            'email', '-email',
            'created_at', '-created_at',
            'user_type', '-user_type',
            'is_active', '-is_active'
        ],
        required=False
    )
    page = serializers.IntegerField(min_value=1, required=False, default=1)
    page_size = serializers.ChoiceField(
        choices=[10, 20, 50, 100],
        required=False,
        default=20
    )


class LoyaltyInfoSerializer(serializers.Serializer):
    """Serializer cho loyalty information"""
    loyalty_points = serializers.IntegerField(min_value=0)
    total_orders = serializers.IntegerField(min_value=0)
    total_spent = serializers.DecimalField(max_digits=12, decimal_places=2)
    current_tier = serializers.CharField()
    current_discount = serializers.DecimalField(max_digits=3, decimal_places=2)
    next_tier = serializers.CharField(allow_null=True)
    points_to_next_tier = serializers.IntegerField(min_value=0)
    preferred_language = serializers.CharField()
    receive_promotions = serializers.BooleanField()
    receive_notifications = serializers.BooleanField()