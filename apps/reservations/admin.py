from django.contrib import admin
from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    """Admin cho Reservation"""
    list_display = [
        'reservation_number', 'customer', 'restaurant', 'table', 
        'reservation_date', 'reservation_time', 'number_of_guests', 
        'status', 'created_at'
    ]
    list_filter = [
        'status', 'restaurant', 'reservation_date', 
        'created_at', 'assigned_staff'
    ]
    search_fields = [
        'reservation_number', 'customer__username', 'customer__email', 
        'customer__phone_number', 'restaurant__name', 
        'contact_name', 'contact_phone', 'contact_email'
    ]
    readonly_fields = [
        'reservation_number', 'created_at', 'updated_at', 
        'checked_in_at', 'completed_at', 'is_upcoming'
    ]
    date_hierarchy = 'reservation_date'
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('reservation_number', 'customer', 'restaurant', 'table', 'status')
        }),
        ('Thông tin đặt bàn', {
            'fields': ('reservation_date', 'reservation_time', 'number_of_guests')
        }),
        ('Thông tin liên hệ', {
            'fields': ('contact_name', 'contact_phone', 'contact_email')
        }),
        ('Ghi chú', {
            'fields': ('special_requests', 'notes'),
            'classes': ('collapse',)
        }),
        ('Thời gian', {
            'fields': ('checked_in_at', 'completed_at', 'created_at', 'updated_at')
        }),
        ('Nhân viên', {
            'fields': ('assigned_staff',)
        }),
        ('Thông tin bổ sung', {
            'fields': ('is_upcoming',),
            'classes': ('collapse',)
        }),
    )
