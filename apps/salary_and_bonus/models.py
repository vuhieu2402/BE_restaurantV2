"""
Salary and Bonus Management Models
Hệ thống quản lý lương thưởng cho nhân viên nhà hàng
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from apps.api.mixins import TimestampMixin


class Employee(TimestampMixin):
    """
    Nhân viên - Liên kết User với Restaurant
    Note: Có thể tái sử dụng StaffProfile từ apps/users hoặc tạo mới để có thêm tính năng
    """
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='employee_records',
        help_text="Người dùng"
    )
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='employees',
        help_text="Nhà hàng"
    )
    
    # Thông tin nhân viên
    employee_id = models.CharField(
        max_length=50,
        help_text="Mã nhân viên"
    )
    position = models.CharField(
        max_length=100,
        help_text="Chức vụ (Ví dụ: Phục vụ, Đầu bếp, Quản lý)"
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Bộ phận (Ví dụ: Phục vụ, Bếp, Bar)"
    )
    hire_date = models.DateField(help_text="Ngày vào làm")
    
    # Trạng thái
    STATUS_CHOICES = [
        ('active', 'Đang làm việc'),
        ('on_leave', 'Nghỉ phép'),
        ('suspended', 'Tạm ngưng'),
        ('terminated', 'Đã nghỉ việc'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text="Trạng thái"
    )
    
    # Ngày nghỉ việc (nếu có)
    termination_date = models.DateField(
        blank=True,
        null=True,
        help_text="Ngày nghỉ việc"
    )
    
    class Meta:
        db_table = 'employees'
        verbose_name = 'Nhân viên'
        verbose_name_plural = 'Nhân viên'
        unique_together = ['restaurant', 'employee_id']
        indexes = [
            models.Index(fields=['restaurant', 'status']),
            models.Index(fields=['user', 'restaurant']),
        ]
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.restaurant.name} ({self.position})"
    
    @property
    def is_active(self):
        """Kiểm tra nhân viên có đang làm việc không"""
        return self.status == 'active'


class Shift(TimestampMixin):
    """
    Ca làm việc - Ghi nhận giờ làm của nhân viên
    """
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='shifts',
        help_text="Nhân viên"
    )
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='shifts',
        help_text="Nhà hàng"
    )
    
    # Thông tin ca làm
    date = models.DateField(help_text="Ngày làm việc")
    scheduled_start_time = models.TimeField(
        help_text="Giờ bắt đầu dự kiến"
    )
    scheduled_end_time = models.TimeField(
        help_text="Giờ kết thúc dự kiến"
    )
    
    # Thời gian thực tế
    actual_start_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Thời gian check-in thực tế"
    )
    actual_end_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Thời gian check-out thực tế"
    )
    
    # Nghỉ giữa ca
    break_duration_minutes = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Thời gian nghỉ (phút)"
    )
    
    # Trạng thái
    STATUS_CHOICES = [
        ('scheduled', 'Đã lên lịch'),
        ('checked_in', 'Đã check-in'),
        ('checked_out', 'Đã check-out'),
        ('cancelled', 'Đã hủy'),
        ('no_show', 'Không đến'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled',
        help_text="Trạng thái"
    )
    
    # Ghi chú
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Ghi chú"
    )
    
    # Địa điểm làm việc (nếu nhà hàng có nhiều địa điểm)
    location = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Địa điểm làm việc"
    )
    
    class Meta:
        db_table = 'shifts'
        verbose_name = 'Ca làm việc'
        verbose_name_plural = 'Ca làm việc'
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['restaurant', 'date']),
            models.Index(fields=['status', 'date']),
        ]
        ordering = ['-date', '-scheduled_start_time']
    
    def __str__(self):
        return f"{self.employee.user.get_full_name() or self.employee.user.username} - {self.date} ({self.get_status_display()})"
    
    @property
    def total_hours(self):
        """Tính tổng giờ làm (giờ thực tế)"""
        if not self.actual_start_time or not self.actual_end_time:
            return Decimal('0.00')
        
        duration = self.actual_end_time - self.actual_start_time
        total_minutes = duration.total_seconds() / 60 - self.break_duration_minutes
        return Decimal(str(round(total_minutes / 60, 2)))
    
    @property
    def scheduled_hours(self):
        """Tính giờ làm dự kiến"""
        from datetime import datetime, timedelta
        
        start = datetime.combine(self.date, self.scheduled_start_time)
        end = datetime.combine(self.date, self.scheduled_end_time)
        
        # Nếu giờ kết thúc < giờ bắt đầu, có nghĩa là ca làm qua đêm
        if end < start:
            end += timedelta(days=1)
        
        duration = end - start
        total_minutes = duration.total_seconds() / 60 - self.break_duration_minutes
        return Decimal(str(round(total_minutes / 60, 2)))
    
    @property
    def overtime_hours(self):
        """Tính giờ làm thêm (nếu > 8 giờ/ngày)"""
        total = self.total_hours
        if total > 8:
            return total - 8
        return Decimal('0.00')
    
    @property
    def regular_hours(self):
        """Tính giờ làm thường (<= 8 giờ/ngày)"""
        total = self.total_hours
        if total > 8:
            return Decimal('8.00')
        return total


class SalaryRate(TimestampMixin):
    """
    Mức lương theo giờ - Có thể cấu hình theo position, restaurant, thời gian
    """
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='salary_rates',
        help_text="Nhà hàng (null = áp dụng cho tất cả)"
    )
    
    position = models.CharField(
        max_length=100,
        help_text="Chức vụ (Ví dụ: Phục vụ, Đầu bếp)"
    )
    
    # Mức lương
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Lương theo giờ (VND)"
    )
    
    # Hệ số làm thêm
    overtime_rate_multiplier = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal('1.5'),
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        help_text="Hệ số lương làm thêm (Ví dụ: 1.5 = 150% lương thường)"
    )
    
    # Thời gian áp dụng
    effective_date = models.DateField(
        help_text="Ngày bắt đầu áp dụng"
    )
    expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text="Ngày hết hạn (null = không hết hạn)"
    )
    
    # Trạng thái
    is_active = models.BooleanField(
        default=True,
        help_text="Đang áp dụng"
    )
    
    # Ghi chú
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Ghi chú"
    )
    
    class Meta:
        db_table = 'salary_rates'
        verbose_name = 'Mức lương'
        verbose_name_plural = 'Mức lương'
        indexes = [
            models.Index(fields=['restaurant', 'position', 'is_active']),
            models.Index(fields=['effective_date', 'expiry_date']),
        ]
        ordering = ['-effective_date']
    
    def __str__(self):
        restaurant_name = self.restaurant.name if self.restaurant else "Tất cả"
        return f"{restaurant_name} - {self.position}: {self.hourly_rate:,} VND/giờ"
    
    @property
    def overtime_rate(self):
        """Tính lương làm thêm theo giờ"""
        return self.hourly_rate * self.overtime_rate_multiplier


class BonusRule(TimestampMixin):
    """
    Quy tắc thưởng - Các điều kiện để nhận thưởng
    """
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='bonus_rules',
        help_text="Nhà hàng"
    )
    
    name = models.CharField(
        max_length=200,
        help_text="Tên quy tắc thưởng"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="Mô tả"
    )
    
    # Loại thưởng
    BONUS_TYPE_CHOICES = [
        ('sales_target', 'Đạt doanh số'),
        ('shift_count', 'Số ca làm'),
        ('customer_rating', 'Đánh giá khách hàng'),
        ('attendance', 'Tỷ lệ đi làm'),
        ('custom', 'Tùy chỉnh'),
    ]
    bonus_type = models.CharField(
        max_length=20,
        choices=BONUS_TYPE_CHOICES,
        help_text="Loại thưởng"
    )
    
    # Điều kiện
    condition_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Giá trị điều kiện (doanh số, số ca, rating, tỷ lệ %)"
    )
    
    # Cách tính thưởng
    CALCULATION_TYPE_CHOICES = [
        ('fixed', 'Số tiền cố định'),
        ('percentage', 'Phần trăm lương'),
    ]
    calculation_type = models.CharField(
        max_length=20,
        choices=CALCULATION_TYPE_CHOICES,
        default='fixed',
        help_text="Cách tính thưởng"
    )
    
    # Giá trị thưởng
    bonus_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Số tiền thưởng (nếu calculation_type = fixed) hoặc % (nếu = percentage)"
    )
    
    # Thời gian áp dụng
    effective_date = models.DateField(
        help_text="Ngày bắt đầu áp dụng"
    )
    expiry_date = models.DateField(
        blank=True,
        null=True,
        help_text="Ngày hết hạn"
    )
    
    # Trạng thái
    is_active = models.BooleanField(
        default=True,
        help_text="Đang áp dụng"
    )
    
    class Meta:
        db_table = 'bonus_rules'
        verbose_name = 'Quy tắc thưởng'
        verbose_name_plural = 'Quy tắc thưởng'
        indexes = [
            models.Index(fields=['restaurant', 'is_active']),
            models.Index(fields=['bonus_type', 'is_active']),
        ]
        ordering = ['-effective_date']
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"


class Payroll(TimestampMixin):
    """
    Bảng lương - Tổng hợp lương tháng của nhân viên
    """
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='payrolls',
        help_text="Nhân viên"
    )
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='payrolls',
        help_text="Nhà hàng"
    )
    
    # Kỳ lương
    month = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Tháng"
    )
    year = models.IntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
        help_text="Năm"
    )
    period_start = models.DateField(help_text="Ngày bắt đầu kỳ lương")
    period_end = models.DateField(help_text="Ngày kết thúc kỳ lương")
    
    # Tổng hợp giờ làm
    total_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Tổng giờ làm"
    )
    regular_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Giờ làm thường"
    )
    overtime_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Giờ làm thêm"
    )
    
    # Tổng hợp lương
    base_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Lương cơ bản"
    )
    overtime_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Lương làm thêm"
    )
    total_bonus = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Tổng thưởng"
    )
    total_deductions = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Tổng khấu trừ"
    )
    net_salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Lương thực nhận"
    )
    
    # Trạng thái
    STATUS_CHOICES = [
        ('draft', 'Nháp'),
        ('calculated', 'Đã tính'),
        ('approved', 'Đã duyệt'),
        ('paid', 'Đã trả'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        help_text="Trạng thái"
    )
    
    # Ngày thay đổi trạng thái
    calculated_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Thời gian tính lương"
    )
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Thời gian duyệt"
    )
    approved_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_payrolls',
        help_text="Người duyệt"
    )
    paid_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Thời gian trả lương"
    )
    
    # Ghi chú
    notes = models.TextField(
        blank=True,
        null=True,
        help_text="Ghi chú"
    )
    
    class Meta:
        db_table = 'payrolls'
        verbose_name = 'Bảng lương'
        verbose_name_plural = 'Bảng lương'
        unique_together = ['employee', 'month', 'year']
        indexes = [
            models.Index(fields=['employee', 'year', 'month']),
            models.Index(fields=['restaurant', 'year', 'month']),
            models.Index(fields=['status']),
        ]
        ordering = ['-year', '-month', '-created_at']
    
    def __str__(self):
        return f"{self.employee.user.get_full_name() or self.employee.user.username} - {self.month}/{self.year}"


class PayrollItem(TimestampMixin):
    """
    Chi tiết lương - Các khoản trong bảng lương
    """
    payroll = models.ForeignKey(
        Payroll,
        on_delete=models.CASCADE,
        related_name='items',
        help_text="Bảng lương"
    )
    
    # Loại khoản
    ITEM_TYPE_CHOICES = [
        ('base_salary', 'Lương cơ bản'),
        ('overtime', 'Lương làm thêm'),
        ('bonus', 'Thưởng'),
        ('deduction', 'Khấu trừ'),
        ('allowance', 'Phụ cấp'),
    ]
    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPE_CHOICES,
        help_text="Loại khoản"
    )
    
    # Thông tin
    description = models.CharField(
        max_length=500,
        help_text="Mô tả"
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text="Số lượng (giờ, số ca, v.v.)"
    )
    unit_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Đơn giá (lương/giờ, số tiền thưởng, v.v.)"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Thành tiền"
    )
    
    # Tham chiếu (nếu có)
    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payroll_items',
        help_text="Ca làm việc (nếu áp dụng)"
    )
    bonus_rule = models.ForeignKey(
        BonusRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payroll_items',
        help_text="Quy tắc thưởng (nếu áp dụng)"
    )
    
    class Meta:
        db_table = 'payroll_items'
        verbose_name = 'Chi tiết lương'
        verbose_name_plural = 'Chi tiết lương'
        indexes = [
            models.Index(fields=['payroll', 'item_type']),
        ]
        ordering = ['payroll', 'item_type', 'created_at']
    
    def __str__(self):
        return f"{self.payroll} - {self.get_item_type_display()}: {self.amount:,} VND"
