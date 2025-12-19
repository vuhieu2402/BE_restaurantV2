from django.contrib import admin
from django.utils.html import format_html
from .models import Restaurant, RestaurantChain, Table, DeliveryPricingConfig


class TableInline(admin.TabularInline):
    """Inline admin cho Table"""
    model = Table
    extra = 1
    fields = ['table_number', 'capacity', 'floor', 'section', 'status', 'is_active']


class RestaurantInline(admin.TabularInline):
    """Inline admin cho Restaurant (branches) trong Chain"""
    model = Restaurant
    extra = 0
    fields = ['name', 'slug', 'city', 'district', 'is_open', 'is_active']
    readonly_fields = ['name', 'slug']
    can_delete = False
    show_change_link = True
    verbose_name = "Chi nhánh"
    verbose_name_plural = "Các chi nhánh"


@admin.register(RestaurantChain)
class RestaurantChainAdmin(admin.ModelAdmin):
    """Admin cho RestaurantChain"""
    list_display = [
        'name', 'slug', 'total_branches_display', 'enable_auto_assignment', 
        'is_active', 'owner', 'created_at'
    ]
    list_filter = [
        'is_active', 'enable_auto_assignment', 'created_at'
    ]
    search_fields = [
        'name', 'slug', 'description', 'contact_email', 
        'contact_phone', 'owner__username'
    ]
    readonly_fields = ['created_at', 'updated_at', 'logo_preview', 'cover_preview', 'total_branches_display']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('name', 'slug', 'description', 'owner')
        }),
        ('Hình ảnh & Branding', {
            'fields': ('logo', 'logo_preview', 'cover_image', 'cover_preview')
        }),
        ('Thông tin liên hệ', {
            'fields': ('contact_email', 'contact_phone', 'website')
        }),
        ('Cấu hình mặc định', {
            'fields': (
                'default_minimum_order', 
                'default_delivery_fee', 
                'default_delivery_radius'
            ),
            'description': 'Cấu hình mặc định cho các chi nhánh mới'
        }),
        ('Cài đặt', {
            'fields': ('enable_auto_assignment',),
            'description': 'Bật tự động phân đơn hàng cho chi nhánh gần nhất'
        }),
        ('Trạng thái', {
            'fields': ('is_active',)
        }),
        ('Thống kê', {
            'fields': ('total_branches_display',),
            'classes': ('collapse',)
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    inlines = [RestaurantInline]
    
    def total_branches_display(self, obj):
        """Hiển thị tổng số chi nhánh"""
        if obj.pk:
            count = obj.get_total_branches()
            return format_html(
                '<strong style="color: #0066cc;">{} chi nhánh</strong>',
                count
            )
        return "-"
    total_branches_display.short_description = "Tổng số chi nhánh"
    
    def logo_preview(self, obj):
        """Hiển thị preview logo"""
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px; border-radius: 8px;" />',
                obj.logo.url
            )
        return "Chưa có logo"
    logo_preview.short_description = "Preview Logo"
    
    def cover_preview(self, obj):
        """Hiển thị preview cover image"""
        if obj.cover_image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 200px; border-radius: 8px;" />',
                obj.cover_image.url
            )
        return "Chưa có ảnh bìa"
    cover_preview.short_description = "Preview Ảnh Bìa"


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    """Admin cho Restaurant"""
    list_display = [
        'name', 'chain_display', 'city', 'district', 'manager', 'is_open', 
        'is_active', 'rating', 'total_reviews', 'created_at'
    ]
    list_filter = [
        'chain', 'is_open', 'is_active', 'city', 'district', 
        'manager', 'created_at'
    ]
    search_fields = [
        'name', 'slug', 'phone_number', 'email', 
        'address', 'city', 'district', 'manager__username',
        'chain__name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'logo_preview', 'cover_preview']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('chain', 'name', 'slug', 'description', 'manager'),
            'description': 'Chọn chain nếu đây là chi nhánh của chuỗi nhà hàng. Để trống nếu là nhà hàng độc lập.'
        }),
        ('Hình ảnh', {
            'fields': ('logo', 'logo_preview', 'cover_image', 'cover_preview')
        }),
        ('Thông tin liên hệ', {
            'fields': ('phone_number', 'email')
        }),
        ('Địa chỉ', {
            'fields': ('address', 'city', 'district', 'ward', 'postal_code')
        }),
        ('Tọa độ', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Thông tin hoạt động', {
            'fields': ('opening_time', 'closing_time', 'is_open')
        }),
        ('Đánh giá', {
            'fields': ('rating', 'total_reviews')
        }),
        ('Cấu hình', {
            'fields': ('minimum_order', 'delivery_fee', 'delivery_radius')
        }),
        ('Trạng thái', {
            'fields': ('is_active',)
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    inlines = [TableInline]
    
    def chain_display(self, obj):
        """Hiển thị chain name với link"""
        if obj.chain:
            return format_html(
                '<a href="/admin/restaurants/restaurantchain/{}/change/" style="color: #0066cc;">{}</a>',
                obj.chain.id,
                obj.chain.name
            )
        return format_html('<span style="color: #999;">Nhà hàng độc lập</span>')
    chain_display.short_description = "Chuỗi"
    
    def logo_preview(self, obj):
        """Hiển thị preview logo"""
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.logo.url
            )
        return "Chưa có logo"
    logo_preview.short_description = "Preview Logo"
    
    def cover_preview(self, obj):
        """Hiển thị preview cover image"""
        if obj.cover_image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 200px;" />',
                obj.cover_image.url
            )
        return "Chưa có ảnh bìa"
    cover_preview.short_description = "Preview Ảnh Bìa"


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    """Admin cho Table"""
    list_display = [
        'restaurant', 'table_number', 'capacity', 'floor', 
        'section', 'status', 'is_active', 'created_at'
    ]
    list_filter = [
        'restaurant', 'status', 'floor', 'section', 
        'is_active', 'created_at'
    ]
    search_fields = [
        'restaurant__name', 'table_number', 'section'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('restaurant', 'table_number', 'capacity', 'floor', 'section')
        }),
        ('Trạng thái', {
            'fields': ('status', 'is_active')
        }),
        ('Vị trí (cho sơ đồ)', {
            'fields': ('x_position', 'y_position'),
            'classes': ('collapse',)
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(DeliveryPricingConfig)
class DeliveryPricingConfigAdmin(admin.ModelAdmin):
    """Admin cho DeliveryPricingConfig"""
    list_display = [
        'restaurant', 'base_fee', 'per_km_fee', 'free_distance_km',
        'enable_surge_pricing', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'enable_surge_pricing']
    search_fields = ['restaurant__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Nhà hàng', {
            'fields': ('restaurant',)
        }),
        ('Cấu hình phí cơ bản', {
            'fields': ('base_fee', 'per_km_fee', 'free_distance_km')
        }),
        ('Giới hạn phí', {
            'fields': ('minimum_fee', 'maximum_fee')
        }),
        ('Surge Pricing (Giờ cao điểm)', {
            'fields': (
                'enable_surge_pricing', 'surge_multiplier',
                'surge_start_time', 'surge_end_time'
            ),
            'classes': ('collapse',)
        }),
        ('Trạng thái', {
            'fields': ('is_active',)
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at')
        }),
    )
