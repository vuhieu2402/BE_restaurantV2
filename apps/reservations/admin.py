from django.contrib import admin
from .models import Reservation, FIXED_DEPOSIT_AMOUNT


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    """Admin cho Reservation"""
    list_display = [
        'reservation_number',
        'customer',
        'restaurant',
        'table',
        'reservation_date',
        'reservation_time',
        'number_of_guests',
        'status',
        'deposit_status_display',
        'payment_status_display',
        'created_at'
    ]
    list_filter = [
        'status',
        'restaurant',
        'reservation_date',
        'special_occasion',
        'created_at'
    ]
    search_fields = [
        'reservation_number',
        'customer__username',
        'customer__email',
        'contact_name',
        'contact_phone',
        'contact_email',
        'restaurant__name'
    ]
    readonly_fields = [
        'reservation_number',
        'deposit_required',
        'deposit_paid',
        'deposit_remaining',
        'payment_status_display',
        'is_deposit_fully_paid',
        'is_paid',
        'is_upcoming',
        'created_at',
        'updated_at',
        'checked_in_at',
        'completed_at'
    ]
    date_hierarchy = 'reservation_date'

    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': (
                'reservation_number',
                'customer',
                'restaurant',
                'table',
                'status'
            )
        }),
        ('Thông tin đặt bàn', {
            'fields': (
                'reservation_date',
                'reservation_time',
                'number_of_guests'
            )
        }),
        ('Thông tin liên hệ', {
            'fields': (
                'contact_name',
                'contact_phone',
                'contact_email'
            )
        }),
        ('Cọc đặt bàn', {
            'fields': (
                'deposit_required',
                'deposit_paid',
                'deposit_remaining',
                'is_deposit_fully_paid',
                'payment_status_display',
                'is_paid'
            )
        }),
        ('Thông tin bổ sung', {
            'fields': (
                'special_requests',
                'special_occasion',
            ),
            'classes': ('collapse',)
        }),
        ('Ghi chú', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Thời gian', {
            'fields': (
                'checked_in_at',
                'completed_at',
                'is_upcoming',
                'created_at',
                'updated_at'
            )
        }),
    )

    def deposit_status_display(self, obj):
        """Hiển thị trạng thái cọc"""
        return obj.get_payment_status_display()
    deposit_status_display.short_description = 'Trạng thái cọc'

    def payment_status_display(self, obj):
        """Hiển thị trạng thái payment"""
        if obj.is_paid:
            return '<span style="color: green;">Đã thanh toán</span>'
        elif obj.deposit_paid > 0:
            return '<span style="color: orange;">Thanh toán một phần</span>'
        else:
            return '<span style="color: red;">Chưa thanh toán</span>'
    payment_status_display.short_description = 'Trạng thái TT'
    payment_status_display.allow_tags = True

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('customer', 'restaurant', 'table')

    def has_change_permission(self, request, obj=None):
        """Staff có thể thay đổi reservation"""
        if obj and request.user.user_type == 'customer':
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Chỉ admin/staff/manager mới được xóa"""
        if request.user.user_type == 'customer':
            return False
        return super().has_delete_permission(request, obj)
