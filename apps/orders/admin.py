from django.contrib import admin
from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    """Inline admin cho OrderItem"""
    model = OrderItem
    extra = 0
    fields = ['menu_item', 'item_name', 'item_price', 'quantity', 'subtotal', 'special_instructions']
    readonly_fields = ['subtotal']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Admin cho Order"""
    list_display = [
        'order_number', 'customer', 'restaurant', 'order_type', 
        'status', 'total', 'created_at', 'completed_at'
    ]
    list_filter = [
        'status', 'order_type', 'restaurant', 'created_at', 
        'completed_at', 'assigned_staff'
    ]
    search_fields = [
        'order_number', 'customer__username', 'customer__email', 
        'customer__phone_number', 'restaurant__name', 'delivery_address'
    ]
    readonly_fields = [
        'order_number', 'created_at', 'updated_at', 
        'completed_at', 'calculate_total_display'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('order_number', 'customer', 'restaurant', 'order_type', 'status')
        }),
        ('Địa chỉ giao hàng', {
            'fields': ('delivery_address', 'delivery_latitude', 'delivery_longitude', 'delivery_phone'),
            'classes': ('collapse',)
        }),
        ('Bàn (nếu ăn tại chỗ)', {
            'fields': ('table',),
            'classes': ('collapse',)
        }),
        ('Giá cả', {
            'fields': (
                'subtotal', 'tax', 'delivery_fee', 'discount', 
                'total', 'calculate_total_display'
            )
        }),
        ('Ghi chú', {
            'fields': ('notes', 'customer_notes'),
            'classes': ('collapse',)
        }),
        ('Thời gian', {
            'fields': ('estimated_time', 'completed_at', 'created_at', 'updated_at')
        }),
        ('Nhân viên', {
            'fields': ('assigned_staff',)
        }),
    )
    
    inlines = [OrderItemInline]
    
    def calculate_total_display(self, obj):
        """Hiển thị công thức tính tổng"""
        if obj.pk:
            return f"{obj.subtotal} + {obj.tax} + {obj.delivery_fee} - {obj.discount} = {obj.total}"
        return "Lưu đơn hàng để xem công thức"
    calculate_total_display.short_description = "Công thức tính tổng"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Admin cho OrderItem"""
    list_display = [
        'order', 'item_name', 'item_price', 'quantity', 
        'subtotal', 'created_at'
    ]
    list_filter = ['order__restaurant', 'order__status', 'created_at']
    search_fields = [
        'order__order_number', 'item_name', 'menu_item__name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'subtotal']
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('order', 'menu_item')
        }),
        ('Chi tiết món', {
            'fields': ('item_name', 'item_price', 'quantity', 'subtotal')
        }),
        ('Yêu cầu đặc biệt', {
            'fields': ('special_instructions',)
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at')
        }),
    )
