"""
Admin configuration for Salary and Bonus models
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Employee, Shift, SalaryRate, BonusRule, Payroll, PayrollItem


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'user', 'restaurant', 'position', 'status', 'hire_date', 'created_at']
    list_filter = ['status', 'position', 'restaurant', 'hire_date']
    search_fields = ['employee_id', 'user__username', 'user__email', 'user__first_name', 'user__last_name', 'position']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['user', 'restaurant']
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('user', 'restaurant', 'employee_id', 'position', 'department')
        }),
        ('Ngày tháng', {
            'fields': ('hire_date', 'termination_date')
        }),
        ('Trạng thái', {
            'fields': ('status',)
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ['id', 'employee', 'restaurant', 'date', 'status', 'scheduled_hours_display', 'total_hours_display', 'created_at']
    list_filter = ['status', 'date', 'restaurant', 'created_at']
    search_fields = ['employee__user__username', 'employee__employee_id', 'restaurant__name', 'notes']
    readonly_fields = ['created_at', 'updated_at', 'total_hours', 'scheduled_hours', 'overtime_hours', 'regular_hours']
    raw_id_fields = ['employee', 'restaurant']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Thông tin ca làm', {
            'fields': ('employee', 'restaurant', 'date', 'location')
        }),
        ('Lịch trình', {
            'fields': ('scheduled_start_time', 'scheduled_end_time', 'break_duration_minutes')
        }),
        ('Thực tế', {
            'fields': ('actual_start_time', 'actual_end_time')
        }),
        ('Tính toán', {
            'fields': ('scheduled_hours', 'total_hours', 'regular_hours', 'overtime_hours'),
            'classes': ('collapse',)
        }),
        ('Trạng thái', {
            'fields': ('status', 'notes')
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def scheduled_hours_display(self, obj):
        return f"{obj.scheduled_hours} giờ"
    scheduled_hours_display.short_description = 'Giờ dự kiến'
    
    def total_hours_display(self, obj):
        if obj.status == 'checked_out':
            return f"{obj.total_hours} giờ"
        return "-"
    total_hours_display.short_description = 'Giờ thực tế'


@admin.register(SalaryRate)
class SalaryRateAdmin(admin.ModelAdmin):
    list_display = ['id', 'restaurant', 'position', 'hourly_rate_display', 'overtime_rate_multiplier', 'effective_date', 'is_active']
    list_filter = ['is_active', 'position', 'restaurant', 'effective_date']
    search_fields = ['position', 'restaurant__name', 'notes']
    readonly_fields = ['created_at', 'updated_at', 'overtime_rate']
    raw_id_fields = ['restaurant']
    
    fieldsets = (
        ('Thông tin', {
            'fields': ('restaurant', 'position', 'notes')
        }),
        ('Mức lương', {
            'fields': ('hourly_rate', 'overtime_rate_multiplier', 'overtime_rate')
        }),
        ('Thời gian áp dụng', {
            'fields': ('effective_date', 'expiry_date', 'is_active')
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def hourly_rate_display(self, obj):
        return f"{obj.hourly_rate:,.0f} VND/giờ"
    hourly_rate_display.short_description = 'Lương/giờ'


@admin.register(BonusRule)
class BonusRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'restaurant', 'bonus_type', 'condition_value', 'calculation_type', 'bonus_amount_display', 'is_active']
    list_filter = ['bonus_type', 'calculation_type', 'is_active', 'restaurant', 'effective_date']
    search_fields = ['name', 'description', 'restaurant__name']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['restaurant']
    
    fieldsets = (
        ('Thông tin', {
            'fields': ('restaurant', 'name', 'description')
        }),
        ('Quy tắc', {
            'fields': ('bonus_type', 'condition_value')
        }),
        ('Cách tính', {
            'fields': ('calculation_type', 'bonus_amount')
        }),
        ('Thời gian áp dụng', {
            'fields': ('effective_date', 'expiry_date', 'is_active')
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def bonus_amount_display(self, obj):
        if obj.calculation_type == 'fixed':
            return f"{obj.bonus_amount:,.0f} VND"
        return f"{obj.bonus_amount}%"
    bonus_amount_display.short_description = 'Giá trị thưởng'


class PayrollItemInline(admin.TabularInline):
    model = PayrollItem
    extra = 0
    readonly_fields = ['item_type', 'description', 'quantity', 'unit_rate', 'amount', 'shift', 'bonus_rule']
    can_delete = False
    fields = ['item_type', 'description', 'quantity', 'unit_rate', 'amount']


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['id', 'employee', 'restaurant', 'month_year', 'total_hours', 'net_salary_display', 'status', 'created_at']
    list_filter = ['status', 'month', 'year', 'restaurant', 'created_at']
    search_fields = ['employee__user__username', 'employee__employee_id', 'restaurant__name']
    readonly_fields = [
        'created_at', 'updated_at', 'calculated_at', 'approved_at', 'paid_at',
        'total_hours', 'regular_hours', 'overtime_hours',
        'base_salary', 'overtime_salary', 'total_bonus', 'total_deductions', 'net_salary'
    ]
    raw_id_fields = ['employee', 'restaurant', 'approved_by']
    inlines = [PayrollItemInline]
    date_hierarchy = 'period_start'
    
    fieldsets = (
        ('Thông tin', {
            'fields': ('employee', 'restaurant', 'notes')
        }),
        ('Kỳ lương', {
            'fields': ('month', 'year', 'period_start', 'period_end')
        }),
        ('Giờ làm', {
            'fields': ('total_hours', 'regular_hours', 'overtime_hours'),
            'classes': ('collapse',)
        }),
        ('Lương', {
            'fields': ('base_salary', 'overtime_salary', 'total_bonus', 'total_deductions', 'net_salary')
        }),
        ('Trạng thái', {
            'fields': ('status', 'calculated_at', 'approved_at', 'approved_by', 'paid_at')
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def month_year(self, obj):
        return f"{obj.month}/{obj.year}"
    month_year.short_description = 'Kỳ lương'
    
    def net_salary_display(self, obj):
        return f"{obj.net_salary:,.0f} VND"
    net_salary_display.short_description = 'Lương thực nhận'
    
    actions = ['approve_payrolls', 'mark_as_paid']
    
    def approve_payrolls(self, request, queryset):
        """Duyệt các bảng lương"""
        from django.utils import timezone
        count = 0
        for payroll in queryset.filter(status='calculated'):
            payroll.status = 'approved'
            payroll.approved_at = timezone.now()
            payroll.approved_by = request.user
            payroll.save()
            count += 1
        self.message_user(request, f"Đã duyệt {count} bảng lương.")
    approve_payrolls.short_description = "Duyệt bảng lương đã chọn"
    
    def mark_as_paid(self, request, queryset):
        """Đánh dấu đã trả lương"""
        from django.utils import timezone
        count = 0
        for payroll in queryset.filter(status='approved'):
            payroll.status = 'paid'
            payroll.paid_at = timezone.now()
            payroll.save()
            count += 1
        self.message_user(request, f"Đã đánh dấu {count} bảng lương là đã trả.")
    mark_as_paid.short_description = "Đánh dấu đã trả lương"


@admin.register(PayrollItem)
class PayrollItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'payroll', 'item_type', 'description', 'quantity', 'unit_rate', 'amount_display']
    list_filter = ['item_type', 'payroll__month', 'payroll__year']
    search_fields = ['description', 'payroll__employee__user__username']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['payroll', 'shift', 'bonus_rule']
    
    def amount_display(self, obj):
        return f"{obj.amount:,.0f} VND"
    amount_display.short_description = 'Thành tiền'
