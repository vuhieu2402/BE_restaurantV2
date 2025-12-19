from django.contrib import admin
from .models import Cart, CartItem


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """
    Admin configuration for Cart model
    
    Note: Cart chỉ lưu thông tin món ăn, không có delivery/tax/discount.
    """
    list_display = [
        'user', 'subtotal', 'total_items', 'restaurant_count', 'created_at'
    ]
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'user__email', 'notes']
    readonly_fields = ['created_at', 'updated_at', 'subtotal']
    ordering = ['-created_at']

    def total_items(self, obj):
        """Display total number of items"""
        return obj.get_total_items()
    total_items.short_description = 'Số lượng món'

    def restaurant_count(self, obj):
        """Display number of restaurants in cart"""
        return obj.get_restaurant_count()
    restaurant_count.short_description = 'Số nhà hàng'

    fieldsets = (
        ('Thông tin người dùng', {
            'fields': ('user',)
        }),
        ('Chi tiết giỏ hàng', {
            'fields': ('subtotal',)
        }),
        ('Thông tin khác', {
            'fields': ('notes',)
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """
    Admin configuration for CartItem model
    
    Note: Không có thông tin delivery. Thông tin đó sẽ được xử lý ở Order level.
    """
    list_display = [
        'cart', 'menu_item', 'restaurant', 'quantity',
        'item_price', 'subtotal', 'created_at'
    ]
    list_filter = [
        'restaurant', 'created_at', 'updated_at'
    ]
    search_fields = [
        'item_name', 'restaurant_name', 'cart__user__username',
        'menu_item__name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'subtotal']
    ordering = ['-created_at']

    fieldsets = (
        ('Thông tin giỏ hàng', {
            'fields': ('cart',)
        }),
        ('Thông tin món ăn', {
            'fields': ('menu_item', 'restaurant', 'chain')
        }),
        ('Snapshot thông tin', {
            'fields': ('item_name', 'item_price', 'item_image', 'restaurant_name')
        }),
        ('Chi tiết', {
            'fields': ('quantity', 'special_instructions', 'subtotal')
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related(
            'cart__user',
            'menu_item',
            'restaurant',
            'chain'
        )