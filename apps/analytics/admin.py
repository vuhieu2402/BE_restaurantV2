from django.contrib import admin
from .models import DashboardMetric, OrderHistory


@admin.register(DashboardMetric)
class DashboardMetricAdmin(admin.ModelAdmin):
    """Admin cho DashboardMetric"""
    list_display = [
        'restaurant', 'metric_type', 'date', 'value', 'created_at'
    ]
    list_filter = [
        'metric_type', 'restaurant', 'date', 'created_at'
    ]
    search_fields = [
        'restaurant__name', 'metric_type'
    ]
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('restaurant', 'metric_type', 'date', 'value')
        }),
        ('Dữ liệu bổ sung', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(OrderHistory)
class OrderHistoryAdmin(admin.ModelAdmin):
    """Admin cho OrderHistory"""
    list_display = [
        'customer', 'order_number', 'restaurant_name', 
        'order_date', 'total_amount', 'status', 'created_at'
    ]
    list_filter = [
        'status', 'order_date', 'created_at'
    ]
    search_fields = [
        'customer__username', 'customer__email', 'order_number', 
        'restaurant_name', 'order__order_number'
    ]
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'order_date'
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('customer', 'order')
        }),
        ('Thông tin đơn hàng', {
            'fields': (
                'order_number', 'restaurant_name', 'order_date', 
                'total_amount', 'status'
            )
        }),
        ('Chi tiết món ăn', {
            'fields': ('items_summary',),
            'classes': ('collapse',)
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at')
        }),
    )
