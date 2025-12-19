from django.db import models
from apps.api.mixins import TimestampMixin
from config.storage.storage import MinIOMediaStorage


class ChatRoom(TimestampMixin):
    """
    Phòng chat giữa khách hàng và nhân viên
    """
    ROOM_TYPE_CHOICES = [
        ('customer_support', 'Hỗ trợ khách hàng'),
        ('order_support', 'Hỗ trợ đơn hàng'),
        ('reservation_support', 'Hỗ trợ đặt bàn'),
        ('general', 'Tổng đài'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Đang hoạt động'),
        ('waiting', 'Chờ phản hồi'),
        ('closed', 'Đã đóng'),
    ]
    
    # Thông tin cơ bản
    room_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Mã phòng chat"
    )
    customer = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='chat_rooms',
        help_text="Khách hàng"
    )
    staff = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_chat_rooms',
        help_text="Nhân viên phụ trách"
    )
    
    # Loại phòng
    room_type = models.CharField(
        max_length=30,
        choices=ROOM_TYPE_CHOICES,
        default='general',
        help_text="Loại phòng"
    )
    
    # Trạng thái
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text="Trạng thái"
    )
    
    # Liên kết với đơn hàng hoặc đặt bàn (nếu có)
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_rooms',
        help_text="Đơn hàng liên quan"
    )
    reservation = models.ForeignKey(
        'reservations.Reservation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_rooms',
        help_text="Đặt bàn liên quan"
    )
    
    # Thông tin
    subject = models.CharField(max_length=200, blank=True, null=True, help_text="Chủ đề")
    last_message_at = models.DateTimeField(blank=True, null=True, help_text="Tin nhắn cuối")
    
    # Thời gian
    closed_at = models.DateTimeField(blank=True, null=True, help_text="Thời gian đóng")
    
    class Meta:
        db_table = 'chat_rooms'
        verbose_name = 'Phòng chat'
        verbose_name_plural = 'Phòng chat'
        ordering = ['-last_message_at', '-created_at']
        indexes = [
            models.Index(fields=['room_number']),
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['staff', 'status']),
        ]
    
    def __str__(self):
        return f"Chat {self.room_number} - {self.customer.username}"
    
    def save(self, *args, **kwargs):
        """Tự động tạo room_number nếu chưa có"""
        if not self.room_number:
            from django.utils import timezone
            import random
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            random_num = random.randint(1000, 9999)
            self.room_number = f"CHAT{timestamp}{random_num}"
        super().save(*args, **kwargs)
    
    @property
    def unread_count(self):
        """Số tin nhắn chưa đọc"""
        return self.messages.filter(is_read=False).exclude(sender=self.customer).count()


class Message(TimestampMixin):
    """
    Tin nhắn trong phòng chat
    """
    MESSAGE_TYPE_CHOICES = [
        ('text', 'Văn bản'),
        ('image', 'Hình ảnh'),
        ('file', 'File'),
        ('system', 'Hệ thống'),
    ]
    
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text="Phòng chat"
    )
    sender = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='sent_messages',
        help_text="Người gửi"
    )
    
    # Nội dung
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default='text',
        help_text="Loại tin nhắn"
    )
    content = models.TextField(help_text="Nội dung")
    attachment = models.FileField(
        upload_to='chat_attachments/',
        storage=MinIOMediaStorage(),
        blank=True,
        null=True,
        help_text="File đính kèm"
    )
    
    # Trạng thái
    is_read = models.BooleanField(default=False, help_text="Đã đọc")
    read_at = models.DateTimeField(blank=True, null=True, help_text="Thời gian đọc")
    
    class Meta:
        db_table = 'messages'
        verbose_name = 'Tin nhắn'
        verbose_name_plural = 'Tin nhắn'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['room', 'created_at']),
            models.Index(fields=['sender', 'is_read']),
        ]
    
    def __str__(self):
        return f"Message từ {self.sender.username} trong {self.room.room_number}"
    
    def mark_as_read(self):
        """Đánh dấu đã đọc"""
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
