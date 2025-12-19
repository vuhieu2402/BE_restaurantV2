from django.contrib import admin
from django.utils.html import format_html
from .models import PaymentMethod, Payment


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """Admin cho PaymentMethod"""
    list_display = [
        'name', 'code', 'is_active', 'requires_online', 
        'display_order', 'icon_preview', 'created_at'
    ]
    list_filter = ['is_active', 'requires_online', 'created_at']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at', 'icon_preview']
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('name', 'code', 'description', 'icon', 'icon_preview')
        }),
        ('Cấu hình', {
            'fields': ('is_active', 'requires_online', 'display_order')
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def icon_preview(self, obj):
        """Hiển thị preview icon"""
        if obj.icon:
            return format_html(
                '<img src="{}" style="max-height: 50px; max-width: 50px;" />',
                obj.icon.url
            )
        return "Chưa có icon"
    icon_preview.short_description = "Preview Icon"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """Admin cho Payment"""
    list_display = [
        'payment_number', 'order', 'customer', 'payment_method', 
        'status', 'amount', 'currency', 'paid_at', 'created_at'
    ]
    list_filter = [
        'status', 'payment_method', 'currency', 
        'created_at', 'paid_at', 'refunded_at'
    ]
    search_fields = [
        'payment_number', 'transaction_id', 'order__order_number', 
        'customer__username', 'customer__email', 'customer__phone_number'
    ]
    readonly_fields = [
        'payment_number', 'created_at', 'updated_at', 
        'paid_at', 'refunded_at', 'is_successful', 'is_pending'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('payment_number', 'order', 'customer', 'payment_method', 'status')
        }),
        ('Số tiền', {
            'fields': ('amount', 'currency')
        }),
        ('Thông tin thanh toán online', {
            'fields': ('transaction_id', 'payment_gateway', 'gateway_response'),
            'classes': ('collapse',)
        }),
        ('Thông tin thẻ', {
            'fields': ('card_last_four', 'card_brand'),
            'classes': ('collapse',)
        }),
        ('Thời gian', {
            'fields': ('paid_at', 'refunded_at', 'created_at', 'updated_at')
        }),
        ('Ghi chú', {
            'fields': ('notes', 'failure_reason'),
            'classes': ('collapse',)
        }),
        ('Trạng thái', {
            'fields': ('is_successful', 'is_pending'),
            'classes': ('collapse',)
        }),
    )
