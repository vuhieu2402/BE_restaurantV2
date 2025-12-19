from django.contrib import admin
from django.utils.html import format_html
from .models import Category, MenuItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Admin cho Category"""
    list_display = [
        'name', 'owner_display', 'display_order', 
        'is_active', 'image_preview', 'created_at'
    ]
    list_filter = ['chain', 'restaurant', 'is_active', 'created_at']
    search_fields = ['name', 'slug', 'restaurant__name', 'chain__name']
    readonly_fields = ['created_at', 'updated_at', 'image_preview']
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('chain', 'restaurant', 'name', 'slug', 'description'),
            'description': 'Chọn chain (menu chung) HOẶC restaurant (menu riêng). Không thể chọn cả hai.'
        }),
        ('Hình ảnh', {
            'fields': ('image', 'image_preview')
        }),
        ('Hiển thị', {
            'fields': ('display_order', 'is_active')
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def owner_display(self, obj):
        """Hiển thị chain hoặc restaurant"""
        if obj.chain:
            return format_html(
                '<span style="color: #0066cc;">🏢 {}</span>',
                obj.chain.name
            )
        elif obj.restaurant:
            return format_html(
                '<span style="color: #666;">🏪 {}</span>',
                obj.restaurant.name
            )
        return "-"
    owner_display.short_description = "Thuộc về"
    
    def image_preview(self, obj):
        """Hiển thị preview ảnh"""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.image.url
            )
        return "Chưa có ảnh"
    image_preview.short_description = "Preview Ảnh"


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    """Admin cho MenuItem"""
    list_display = [
        'name', 'owner_display', 'category', 'price', 
        'is_available', 'is_featured', 'rating', 'image_preview', 'created_at'
    ]
    list_filter = [
        'chain', 'restaurant', 'category', 'is_available', 'is_featured', 
        'is_vegetarian', 'is_spicy', 'created_at'
    ]
    search_fields = [
        'name', 'slug', 'description', 'restaurant__name', 
        'chain__name', 'category__name'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'image_preview', 
        'is_on_sale', 'discount_percentage'
    ]
    prepopulated_fields = {'slug': ('name',)}
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('chain', 'restaurant', 'category', 'name', 'slug', 'description'),
            'description': 'Chọn chain (menu chung) HOẶC restaurant (menu riêng). Không thể chọn cả hai.'
        }),
        ('Hình ảnh', {
            'fields': ('image', 'image_preview')
        }),
        ('Giá cả', {
            'fields': ('price', 'original_price', 'is_on_sale', 'discount_percentage')
        }),
        ('Thông tin dinh dưỡng', {
            'fields': ('calories', 'preparation_time'),
            'classes': ('collapse',)
        }),
        ('Đánh giá', {
            'fields': ('rating', 'total_reviews')
        }),
        ('Trạng thái', {
            'fields': (
                'is_available', 'is_featured', 'is_vegetarian', 
                'is_spicy', 'display_order'
            )
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def owner_display(self, obj):
        """Hiển thị chain hoặc restaurant"""
        if obj.chain:
            return format_html(
                '<span style="color: #0066cc;">🏢 {}</span>',
                obj.chain.name
            )
        elif obj.restaurant:
            return format_html(
                '<span style="color: #666;">🏪 {}</span>',
                obj.restaurant.name
            )
        return "-"
    owner_display.short_description = "Thuộc về"
    
    def image_preview(self, obj):
        """Hiển thị preview ảnh"""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.image.url
            )
        return "Chưa có ảnh"
    image_preview.short_description = "Preview Ảnh"
