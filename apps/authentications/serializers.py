from rest_framework import serializers
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from .services import AuthService, VerificationService, PasswordService
from .models import RefreshTokenSession

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer cho User model - Đồng bộ với apps/users/models.py"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, required=False)
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'phone_number', 'password', 'password_confirm', 'user_type', 'user_type_display',
            'address', 'city', 'district', 'ward', 'postal_code',
            'latitude', 'longitude', 'date_of_birth', 'avatar',
            'is_verified', 'is_active', 'date_joined', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'phone_number': {'required': False},
            'email': {'required': False},
            'is_verified': {'read_only': True},
            'date_joined': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
            'avatar': {'required': False}
        }

    def get_full_name(self, obj):
        """Get full name of user"""
        return obj.get_full_name() 

    def validate_password(self, value):
        """Validate password strength"""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        # Additional custom validation
        is_valid, message = PasswordService.validate_password_strength(value)
        if not is_valid:
            raise serializers.ValidationError(message)

        return value

    def validate_email(self, value):
        """Validate email format and uniqueness"""
        if value:
            # Check if user exists and exclude current user for updates
            queryset = User.objects.filter(email=value)
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)

            if queryset.exists():
                raise serializers.ValidationError("Email đã được sử dụng")
        return value

    def validate_phone_number(self, value):
        """Validate phone number format and uniqueness"""
        if value:
            # Check if user exists and exclude current user for updates
            queryset = User.objects.filter(phone_number=value)
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)

            if queryset.exists():
                raise serializers.ValidationError("Số điện thoại đã được sử dụng")
        return value

    def validate_latitude(self, value):
        """Validate latitude range"""
        if value is not None:
            if not -90 <= value <= 90:
                raise serializers.ValidationError("Vĩ độ phải nằm trong khoảng -90 đến 90")
        return value

    def validate_longitude(self, value):
        """Validate longitude range"""
        if value is not None:
            if not -180 <= value <= 180:
                raise serializers.ValidationError("Kinh độ phải nằm trong khoảng -180 đến 180")
        return value

    def validate_date_of_birth(self, value):
        """Validate date of birth"""
        if value:
            if value >= timezone.now().date():
                raise serializers.ValidationError("Ngày sinh phải là ngày trong quá khứ")

            # Check age is reasonable (between 1 and 120 years)
            from datetime import date
            today = date.today()
            age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
            if age < 1 or age > 120:
                raise serializers.ValidationError("Độ tuổi không hợp lệ")
        return value

    def validate(self, attrs):
        """Validate password confirmation and required fields"""
        if 'password_confirm' in attrs and attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError("Mật khẩu xác nhận không khớp")

        # Check if at least one of email or phone is provided for new users
        if not self.instance and not attrs.get('email') and not attrs.get('phone_number'):
            raise serializers.ValidationError("Phải cung cấp email hoặc số điện thoại")

        return attrs

    def create(self, validated_data):
        """Create user with encrypted password"""
        validated_data.pop('password_confirm', None)
        password = validated_data.pop('password')

        user = User.objects.create_user(
            password=password,
            **validated_data
        )
        return user

    def update(self, instance, validated_data):
        """Update user with proper password handling"""
        password = validated_data.pop('password', None)
        password_confirm = validated_data.pop('password_confirm', None)

        # Handle password update for PATCH requests
        if password and password_confirm:
            if password != password_confirm:
                raise serializers.ValidationError("Mật khẩu xác nhận không khớp")
            instance.set_password(password)

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    """Serializer cho login bằng email hoặc phone"""
    identifier = serializers.CharField(
        help_text="Email hoặc số điện thoại"
    )
    password = serializers.CharField(
        write_only=True,
        help_text="Mật khẩu"
    )
    device_info = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Device information"
    )

    def validate(self, attrs):
        """Validate login credentials"""
        identifier = attrs.get('identifier')
        password = attrs.get('password')

        if not identifier or not password:
            raise serializers.ValidationError("Vui lòng nhập email/số điện thoại và mật khẩu")

        # Try to find user by email or phone
        try:
            if '@' in identifier:
                user = User.objects.get(email=identifier)
            else:
                user = User.objects.get(phone_number=identifier)
        except User.DoesNotExist:
            raise serializers.ValidationError("Tài khoản không tồn tại")

        # Authenticate user
        if not user.check_password(password):
            raise serializers.ValidationError("Mật khẩu không đúng")

        if not user.is_active:
            raise serializers.ValidationError("Tài khoản đã bị khóa")

        attrs['user'] = user
        return attrs


class RegisterSerializer(serializers.Serializer):
    """Serializer cho registration - Đồng bộ với User model"""
    # Username không hiển thị trong API - sẽ được tự động generate từ email/phone
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(
        max_length=17,
        required=False,
        allow_blank=True
    )
    password = serializers.CharField(
        write_only=True,
        min_length=8
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True
    )
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    user_type = serializers.ChoiceField(
        choices=User.USER_TYPE_CHOICES,
        default='customer'
    )
    # Address fields
    address = serializers.CharField(required=False, allow_blank=True)
    city = serializers.CharField(required=False, allow_blank=True, max_length=100)
    district = serializers.CharField(required=False, allow_blank=True, max_length=100)
    ward = serializers.CharField(required=False, allow_blank=True, max_length=100)
    postal_code = serializers.CharField(required=False, allow_blank=True, max_length=10)
    # Geographic coordinates
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True
    )
    # Personal info
    date_of_birth = serializers.DateField(required=False, allow_null=True)

    def validate_password(self, value):
        """Validate password strength"""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        is_valid, message = PasswordService.validate_password_strength(value)
        if not is_valid:
            raise serializers.ValidationError(message)

        return value

    def validate_latitude(self, value):
        """Validate latitude range"""
        if value is not None:
            if not -90 <= value <= 90:
                raise serializers.ValidationError("Vĩ độ phải nằm trong khoảng -90 đến 90")
        return value

    def validate_longitude(self, value):
        """Validate longitude range"""
        if value is not None:
            if not -180 <= value <= 180:
                raise serializers.ValidationError("Kinh độ phải nằm trong khoảng -180 đến 180")
        return value

    def validate_date_of_birth(self, value):
        """Validate date of birth"""
        if value:
            if value >= timezone.now().date():
                raise serializers.ValidationError("Ngày sinh phải là ngày trong quá khứ")

            # Check age is reasonable (between 1 and 120 years)
            from datetime import date
            today = date.today()
            age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
            if age < 1 or age > 120:
                raise serializers.ValidationError("Độ tuổi không hợp lệ")
        return value

    def validate(self, attrs):
        """Validate registration data"""
        if not attrs.get('email') and not attrs.get('phone_number'):
            raise serializers.ValidationError("Phải cung cấp email hoặc số điện thoại")

        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError("Mật khẩu xác nhận không khớp")

        # Generate username if not provided
        if not attrs.get('username'):
            email = attrs.get('email')
            phone = attrs.get('phone_number')

            if email:
                # Use email prefix as username
                import re
                username = re.sub(r'[^a-zA-Z0-9_.-]', '', email.split('@')[0])
            elif phone:
                # Use phone number as username
                username = re.sub(r'[^\d]', '', phone)
            else:
                # Generate random username
                import uuid
                username = f"user_{uuid.uuid4().hex[:8]}"

            # Ensure username uniqueness
            original_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{original_username}_{counter}"
                counter += 1

            attrs['username'] = username

        # Check if email or phone already exists
        email = attrs.get('email')
        phone = attrs.get('phone_number')

        if email and User.objects.filter(email=email).exists():
            raise serializers.ValidationError("Email đã được sử dụng")

        if phone and User.objects.filter(phone_number=phone).exists():
            raise serializers.ValidationError("Số điện thoại đã được sử dụng")

        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """Serializer cho email verification request"""
    email = serializers.EmailField()

    def validate_email(self, value):
        """Validate email"""
        if not User.objects.filter(email=value).exists():
            # Cho phép verification cho cả email chưa đăng ký
            pass
        return value


class PhoneVerificationSerializer(serializers.Serializer):
    """Serializer cho phone verification request"""
    phone_number = serializers.CharField(max_length=17)

    def validate_phone_number(self, value):
        """Validate phone number"""
        if not User.objects.filter(phone_number=value).exists():
            # Cho phép verification cho cả phone chưa đăng ký
            pass
        return value


class VerifyCodeSerializer(serializers.Serializer):
    """Serializer cho code verification"""
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(max_length=17, required=False)
    code = serializers.CharField(max_length=6, min_length=6)
    verification_type = serializers.ChoiceField(
        choices=[
            ('email', 'Email Verification'),
            ('phone', 'Phone Verification'),
            ('password_reset', 'Password Reset'),
        ],
        default='email'
    )

    def validate(self, attrs):
        """Validate verification data"""
        if not attrs.get('email') and not attrs.get('phone_number'):
            raise serializers.ValidationError("Phải cung cấp email hoặc số điện thoại")
        return attrs


class PasswordResetSerializer(serializers.Serializer):
    """Serializer cho password reset request"""
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(max_length=17, required=False)

    def validate(self, attrs):
        """Validate password reset request"""
        if not attrs.get('email') and not attrs.get('phone_number'):
            raise serializers.ValidationError("Phải cung cấp email hoặc số điện thoại")
        return attrs


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer cho password reset confirmation"""
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(max_length=17, required=False)
    code = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(min_length=8)
    new_password_confirm = serializers.CharField(required=False)

    def validate_new_password(self, value):
        """Validate new password strength"""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        is_valid, message = PasswordService.validate_password_strength(value)
        if not is_valid:
            raise serializers.ValidationError(message)

        return value

    def validate(self, attrs):
        """Validate password reset confirmation"""
        if not attrs.get('email') and not attrs.get('phone_number'):
            raise serializers.ValidationError("Phải cung cấp email hoặc số điện thoại")

        if attrs.get('new_password') != attrs.get('new_password_confirm'):
            raise serializers.ValidationError("Mật khẩu xác nhận không khớp")

        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer cho change password"""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, required=False)

    def validate_new_password(self, value):
        """Validate new password strength"""
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

        is_valid, message = PasswordService.validate_password_strength(value)
        if not is_valid:
            raise serializers.ValidationError(message)

        return value

    def validate(self, attrs):
        """Validate password change"""
        if attrs.get('new_password') != attrs.get('new_password_confirm'):
            raise serializers.ValidationError("Mật khẩu xác nhận không khớp")
        return attrs


class RefreshTokenSerializer(serializers.Serializer):
    """Serializer cho refresh token"""
    refresh_token = serializers.CharField()
    device_info = serializers.JSONField(required=False, default=dict)


class RevokeTokenSerializer(serializers.Serializer):
    """Serializer cho revoke token"""
    refresh_token = serializers.CharField()


class SessionSerializer(serializers.ModelSerializer):
    """Serializer cho user session info"""
    device_name = serializers.SerializerMethodField()
    is_current = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = RefreshTokenSession
        fields = [
            'id', 'device_name', 'ip_address', 'created_at',
            'last_used_at', 'expires_at', 'is_current', 'is_expired'
        ]

    def get_device_name(self, obj):
        """Get device name from device_info"""
        return obj.device_info.get('name', 'Unknown Device') if obj.device_info else 'Unknown Device'
    
    def get_is_current(self, obj):
        """Check if this is the current session"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            # Compare refresh token from request with session refresh token
            # This is a simplified check - you might need to adjust based on your implementation
            return False  # Default to False, can be enhanced if needed
        return False
    
    def get_is_expired(self, obj):
        """Check if session is expired"""
        return obj.is_expired


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile information"""
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)
    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'full_name', 'email', 'phone_number',
            'user_type', 'user_type_display', 'address', 'city', 'district',
            'ward', 'postal_code', 'latitude', 'longitude', 'date_of_birth',
            'avatar', 'is_verified', 'date_joined', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'user_type': {'read_only': True},  # User type changes should be restricted
            'is_verified': {'read_only': True},
            'date_joined': {'read_only': True},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True},
            'email': {'required': False},
            'phone_number': {'required': False},
        }

    def get_full_name(self, obj):
        """Get full name of user"""
        return obj.get_full_name() or obj.username

    def validate_email(self, value):
        """Validate email format and uniqueness"""
        if value:
            # Check if user exists and exclude current user for updates
            queryset = User.objects.filter(email=value)
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)

            if queryset.exists():
                raise serializers.ValidationError("Email đã được sử dụng")
        return value

    def validate_phone_number(self, value):
        """Validate phone number format and uniqueness"""
        if value:
            # Check if user exists and exclude current user for updates
            queryset = User.objects.filter(phone_number=value)
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)

            if queryset.exists():
                raise serializers.ValidationError("Số điện thoại đã được sử dụng")
        return value

    def validate_latitude(self, value):
        """Validate latitude range"""
        if value is not None:
            if not -90 <= value <= 90:
                raise serializers.ValidationError("Vĩ độ phải nằm trong khoảng -90 đến 90")
        return value

    def validate_longitude(self, value):
        """Validate longitude range"""
        if value is not None:
            if not -180 <= value <= 180:
                raise serializers.ValidationError("Kinh độ phải nằm trong khoảng -180 đến 180")
        return value

    def validate_date_of_birth(self, value):
        """Validate date of birth"""
        if value:
            if value >= timezone.now().date():
                raise serializers.ValidationError("Ngày sinh phải là ngày trong quá khứ")

            # Check age is reasonable (between 1 and 120 years)
            from datetime import date
            today = date.today()
            age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
            if age < 1 or age > 120:
                raise serializers.ValidationError("Độ tuổi không hợp lệ")
        return value


class AuthResponseSerializer(serializers.Serializer):
    """Serializer cho authentication response"""
    user = UserSerializer(read_only=True)
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)
    access_token_expires = serializers.IntegerField(read_only=True)
    refresh_token_expires = serializers.IntegerField(read_only=True)
    sessions = serializers.ListField(
        child=SessionSerializer(),
        read_only=True,
        required=False
    )