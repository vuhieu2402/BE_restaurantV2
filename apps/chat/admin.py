from django.contrib import admin
from .models import ChatRoom, Message


class MessageInline(admin.TabularInline):
    """Inline admin cho Message"""
    model = Message
    extra = 0
    fields = ['sender', 'message_type', 'content', 'is_read', 'created_at']
    readonly_fields = ['created_at']


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    """Admin cho ChatRoom"""
    list_display = [
        'room_number', 'customer', 'staff', 'room_type', 
        'status', 'last_message_at', 'created_at'
    ]
    list_filter = [
        'room_type', 'status', 'staff', 'created_at', 'last_message_at'
    ]
    search_fields = [
        'room_number', 'customer__username', 'customer__email', 
        'staff__username', 'subject', 'order__order_number', 
        'reservation__reservation_number'
    ]
    readonly_fields = [
        'room_number', 'created_at', 'updated_at', 
        'last_message_at', 'closed_at', 'unread_count'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('room_number', 'customer', 'staff', 'room_type', 'status', 'subject')
        }),
        ('Liên kết', {
            'fields': ('order', 'reservation'),
            'classes': ('collapse',)
        }),
        ('Thời gian', {
            'fields': ('last_message_at', 'closed_at', 'created_at', 'updated_at')
        }),
        ('Thông tin bổ sung', {
            'fields': ('unread_count',),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [MessageInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin cho Message"""
    list_display = [
        'room', 'sender', 'message_type', 'content_preview', 
        'is_read', 'read_at', 'created_at'
    ]
    list_filter = [
        'message_type', 'is_read', 'room__room_type', 
        'created_at', 'read_at'
    ]
    search_fields = [
        'room__room_number', 'sender__username', 'content'
    ]
    readonly_fields = ['created_at', 'updated_at', 'read_at', 'content_preview']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('room', 'sender', 'message_type')
        }),
        ('Nội dung', {
            'fields': ('content', 'content_preview', 'attachment')
        }),
        ('Trạng thái', {
            'fields': ('is_read', 'read_at')
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def content_preview(self, obj):
        """Hiển thị preview nội dung"""
        if len(obj.content) > 100:
            return obj.content[:100] + "..."
        return obj.content
    content_preview.short_description = "Preview Nội dung"
