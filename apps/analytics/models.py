from django.db import models
from django.core.validators import MinValueValidator
from apps.api.mixins import TimestampMixin


class DashboardMetric(TimestampMixin):
    """
    Metrics cho dashboard
    Lưu trữ các chỉ số thống kê để hiển thị trên dashboard
    """
    METRIC_TYPE_CHOICES = [
        ('daily_revenue', 'Doanh thu theo ngày'),
        ('monthly_revenue', 'Doanh thu theo tháng'),
        ('total_orders', 'Tổng số đơn hàng'),
        ('total_customers', 'Tổng số khách hàng'),
        ('average_order_value', 'Giá trị đơn hàng trung bình'),
        ('popular_items', 'Món ăn phổ biến'),
        ('reservation_stats', 'Thống kê đặt bàn'),
        ('customer_retention', 'Tỷ lệ khách hàng quay lại'),
    ]
    
    restaurant = models.ForeignKey(
        'restaurants.Restaurant',
        on_delete=models.CASCADE,
        related_name='dashboard_metrics',
        help_text="Nhà hàng"
    )
    
    metric_type = models.CharField(
        max_length=50,
        choices=METRIC_TYPE_CHOICES,
        help_text="Loại metric"
    )
    
    # Thời gian
    date = models.DateField(help_text="Ngày")
    
    # Giá trị
    value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Giá trị"
    )
    
    # Dữ liệu bổ sung (JSON)
    metadata = models.JSONField(
        blank=True,
        null=True,
        help_text="Dữ liệu bổ sung"
    )
    
    class Meta:
        db_table = 'dashboard_metrics'
        verbose_name = 'Chỉ số dashboard'
        verbose_name_plural = 'Chỉ số dashboard'
        unique_together = ['restaurant', 'metric_type', 'date']
        ordering = ['-date', 'restaurant']
        indexes = [
            models.Index(fields=['restaurant', 'metric_type', '-date']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.get_metric_type_display()} - {self.date}"


class OrderHistory(TimestampMixin):
    """
    Lịch sử mua hàng của khách hàng
    Lưu trữ để dễ dàng truy vấn và hiển thị
    """
    customer = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='order_history',
        help_text="Khách hàng"
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.CASCADE,
        related_name='history_records',
        help_text="Đơn hàng"
    )
    
    # Thông tin đơn hàng (snapshot tại thời điểm tạo)
    order_number = models.CharField(max_length=50, help_text="Mã đơn hàng")
    restaurant_name = models.CharField(max_length=200, help_text="Tên nhà hàng")
    order_date = models.DateTimeField(help_text="Ngày đặt hàng")
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Tổng tiền"
    )
    status = models.CharField(max_length=20, help_text="Trạng thái")
    
    # Chi tiết món ăn (JSON)
    items_summary = models.JSONField(
        help_text="Tóm tắt món ăn"
    )
    
    class Meta:
        db_table = 'order_history'
        verbose_name = 'Lịch sử mua hàng'
        verbose_name_plural = 'Lịch sử mua hàng'
        ordering = ['-order_date']
        indexes = [
            models.Index(fields=['customer', '-order_date']),
            models.Index(fields=['order_number']),
        ]
    
    def __str__(self):
        return f"{self.customer.username} - {self.order_number}"
