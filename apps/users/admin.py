from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, CustomerProfile, StaffProfile


class CustomerProfileInline(admin.StackedInline):
    """Inline for CustomerProfile"""
    model = CustomerProfile
    can_delete = False
    verbose_name_plural = 'Hồ sơ khách hàng'
    fk_name = 'user'
    fields = (
        'preferred_language',
        'loyalty_points',
        'total_orders',
        'total_spent',
        'receive_promotions',
        'receive_notifications',
    )


class StaffProfileInline(admin.StackedInline):
    """Inline for StaffProfile"""
    model = StaffProfile
    can_delete = False
    verbose_name_plural = 'Hồ sơ nhân viên'
    fk_name = 'user'
    fields = (
        'employee_id',
        'position',
        'hire_date',
        'salary',
        'restaurant',
        'is_active',
    )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin cho User model"""
    list_display = [
        'username', 'email', 'phone_number', 'user_type',
        'is_verified', 'is_active', 'is_staff', 'date_joined'
    ]
    list_filter = [
        'user_type', 'is_verified', 'is_active', 'is_staff',
        'is_superuser', 'date_joined'
    ]
    search_fields = ['username', 'email', 'phone_number', 'first_name', 'last_name']
    readonly_fields = ['date_joined', 'last_login', 'created_at', 'updated_at']

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Thông tin cá nhân', {
            'fields': ('first_name', 'last_name', 'email', 'avatar', 'date_of_birth')
        }),
        ('Thông tin liên hệ', {
            'fields': ('phone_number', 'address', 'city', 'district', 'ward', 'postal_code')
        }),
        ('Tọa độ', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Quyền hạn', {
            'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions')
        }),
        ('Thời gian', {
            'fields': ('date_joined', 'last_login', 'created_at', 'updated_at')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'user_type'),
        }),
    )

    ordering = ['-date_joined']
    filter_horizontal = ['groups', 'user_permissions']

    def get_inlines(self, request, obj=None):
        """Return appropriate inline based on user_type"""
        if not obj:
            return []

        if obj.user_type == 'customer':
            return [CustomerProfileInline]
        elif obj.user_type in ['staff', 'manager', 'admin']:
            return [StaffProfileInline]
        return []

    def get_inline_instances(self, request, obj=None):
        """Override to prevent inlines for new objects"""
        if not obj:
            return []
        return super().get_inline_instances(request, obj)


# Create custom admin models for customers and staff
class CustomerUser(User):
    """Proxy model for customers to display in admin"""
    class Meta:
        proxy = True
        verbose_name = 'Khách hàng'
        verbose_name_plural = 'Khách hàng'


@admin.register(CustomerUser)
class CustomerUserAdmin(BaseUserAdmin):
    """Admin for customers only"""
    list_display = [
        'username', 'email', 'phone_number', 'first_name', 'last_name',
        'is_verified', 'is_active', 'date_joined'
    ]
    list_filter = ['is_verified', 'is_active', 'date_joined', 'city']
    search_fields = ['username', 'email', 'phone_number', 'first_name', 'last_name']
    readonly_fields = ['date_joined', 'last_login', 'created_at', 'updated_at']

    def get_queryset(self, request):
        return super().get_queryset(request).filter(user_type='customer')

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Thông tin cá nhân', {
            'fields': ('first_name', 'last_name', 'email', 'avatar', 'date_of_birth')
        }),
        ('Thông tin liên hệ', {
            'fields': ('phone_number', 'address', 'city', 'district', 'ward', 'postal_code')
        }),
        ('Tọa độ', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Quyền hạn', {
            'fields': ('is_active', 'is_verified')
        }),
        ('Thời gian', {
            'fields': ('date_joined', 'last_login', 'created_at', 'updated_at')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )

    def save_model(self, request, obj, form, change):
        # Ensure user_type is set to customer
        if not change:  # Only for new objects
            obj.user_type = 'customer'
        super().save_model(request, obj, form, change)

    inlines = [CustomerProfileInline]


class StaffUser(User):
    """Proxy model for staff to display in admin"""
    class Meta:
        proxy = True
        verbose_name = 'Nhân viên'
        verbose_name_plural = 'Nhân viên'


@admin.register(StaffUser)
class StaffUserAdmin(BaseUserAdmin):
    """Admin for staff only"""
    list_display = [
        'username', 'email', 'phone_number', 'first_name', 'last_name',
        'user_type', 'is_verified', 'is_active', 'date_joined'
    ]
    list_filter = ['user_type', 'is_verified', 'is_active', 'date_joined', 'city']
    search_fields = ['username', 'email', 'phone_number', 'first_name', 'last_name']
    readonly_fields = ['date_joined', 'last_login', 'created_at', 'updated_at']

    def get_queryset(self, request):
        return super().get_queryset(request).filter(user_type__in=['staff', 'manager', 'admin'])

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Thông tin cá nhân', {
            'fields': ('first_name', 'last_name', 'email', 'avatar', 'date_of_birth')
        }),
        ('Thông tin liên hệ', {
            'fields': ('phone_number', 'address', 'city', 'district', 'ward', 'postal_code')
        }),
        ('Tọa độ', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Quyền hạn', {
            'fields': ('user_type', 'is_active', 'is_staff', 'is_superuser', 'is_verified', 'groups', 'user_permissions')
        }),
        ('Thời gian', {
            'fields': ('date_joined', 'last_login', 'created_at', 'updated_at')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'user_type'),
        }),
    )

    def save_model(self, request, obj, form, change):
        # Ensure user_type is valid for staff
        if not change and obj.user_type not in ['staff', 'manager', 'admin']:
            obj.user_type = 'staff'
        super().save_model(request, obj, form, change)

    inlines = [StaffProfileInline]


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """Admin cho CustomerProfile"""
    list_display = [
        'user', 'email', 'phone_number', 'loyalty_points', 'total_orders',
        'total_spent', 'receive_promotions', 'receive_notifications', 'created_at'
    ]
    list_filter = ['receive_promotions', 'receive_notifications', 'preferred_language', 'created_at']
    search_fields = ['user__username', 'user__email', 'user__phone_number', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']

    def get_queryset(self, request):
        # Filter to show only profiles of customer users
        from django.db.models import Q
        return super().get_queryset(request).filter(user__user_type='customer')

    def email(self, obj):
        return obj.user.email if obj.user else ''
    email.short_description = 'Email'

    def phone_number(self, obj):
        return obj.user.phone_number if obj.user else ''
    phone_number.short_description = 'Số điện thoại'

    fieldsets = (
        ('Người dùng', {'fields': ('user',)}),
        ('Thông tin khách hàng', {
            'fields': ('preferred_language', 'loyalty_points', 'total_orders', 'total_spent')
        }),
        ('Tùy chọn', {
            'fields': ('receive_promotions', 'receive_notifications')
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    """Admin cho StaffProfile"""
    list_display = [
        'user', 'user_type', 'email', 'phone_number', 'employee_id',
        'position', 'restaurant', 'hire_date', 'is_active', 'created_at'
    ]
    list_filter = ['position', 'is_active', 'restaurant', 'hire_date', 'user__user_type']
    search_fields = [
        'user__username', 'user__email', 'user__phone_number', 'employee_id',
        'position', 'restaurant__name'
    ]
    readonly_fields = ['created_at', 'updated_at']

    def get_queryset(self, request):
        # Filter to show only users with staff-related user_types
        from django.db.models import Q
        staff_users = User.objects.filter(user_type__in=['staff', 'manager', 'admin'])
        staff_user_ids = staff_users.values_list('id', flat=True)

        # Get existing staff profiles
        qs = super().get_queryset(request)
        existing_profile_user_ids = qs.values_list('user_id', flat=True)

        # For staff users without profiles, create a placeholder
        missing_ids = set(staff_user_ids) - set(existing_profile_user_ids)
        if missing_ids:
            # Note: In a real implementation, you might want to auto-create profiles
            # For now, we'll only show existing profiles
            pass

        return qs.filter(user_id__in=staff_user_ids)

    def user_type(self, obj):
        return obj.user.get_user_type_display() if obj.user else ''
    user_type.short_description = 'Loại người dùng'

    def email(self, obj):
        return obj.user.email if obj.user else ''
    email.short_description = 'Email'

    def phone_number(self, obj):
        return obj.user.phone_number if obj.user else ''
    phone_number.short_description = 'Số điện thoại'

    fieldsets = (
        ('Người dùng', {'fields': ('user',)}),
        ('Thông tin nhân viên', {
            'fields': ('employee_id', 'position', 'hire_date', 'salary', 'restaurant')
        }),
        ('Trạng thái', {
            'fields': ('is_active',)
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at')
        }),
    )
