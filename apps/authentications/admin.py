from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import RefreshTokenSession, VerificationCode


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = [
        'identifier', 'verification_type', 'code', 'is_verified',
        'is_used', 'attempts', 'expires_at', 'created_at'
    ]
    list_filter = [
        'verification_type', 'is_verified', 'is_used',
        'created_at', 'expires_at'
    ]
    search_fields = ['email', 'phone_number', 'code']
    readonly_fields = [
        'id', 'code', 'created_at', 'verified_at', 'is_expired'
    ]

    def identifier(self, obj):
        """Display email or phone number"""
        return obj.email or obj.phone_number
    identifier.short_description = 'Identifier'

    def is_expired(self, obj):
        """Check if code is expired"""
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = 'Expired'

    fieldsets = (
        (None, {
            'fields': ('email', 'phone_number', 'verification_type')
        }),
        ('Verification Details', {
            'fields': ('code', 'is_verified', 'is_used', 'attempts'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'verified_at', 'expires_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_as_used', 'cleanup_expired']

    def mark_as_used(self, request, queryset):
        """Mark selected codes as used"""
        count = queryset.filter(is_used=False).update(is_used=True)
        self.message_user(
            request,
            f'Successfully marked {count} codes as used.'
        )
    mark_as_used.short_description = 'Mark selected codes as used'

    def cleanup_expired(self, request, queryset):
        """Clean up expired codes"""
        expired_codes = queryset.filter(
            expires_at__lt=timezone.now(),
            is_used=False
        )
        count = expired_codes.count()
        expired_codes.update(is_used=True)

        self.message_user(
            request,
            f'Successfully cleaned up {count} expired codes.'
        )
    cleanup_expired.short_description = 'Clean up expired codes'


@admin.register(RefreshTokenSession)
class RefreshTokenSessionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'device_name', 'ip_address', 'is_active', 
        'created_at', 'last_used_at', 'expires_at', 'is_expired'
    ]
    list_filter = [
        'is_active', 'created_at', 'last_used_at', 'expires_at', 
        'revoked_reason'
    ]
    search_fields = ['user__username', 'user__email', 'ip_address', 'user_agent']
    readonly_fields = [
        'id', 'refresh_token', 'created_at', 'last_used_at', 
        'revoked_at', 'device_info_display'
    ]
    
    def device_name(self, obj):
        """Extract device name from device_info"""
        return obj.device_info.get('name', 'Unknown Device')
    device_name.short_description = 'Device'
    
    def is_expired(self, obj):
        """Check if session is expired"""
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = 'Expired'
    
    def device_info_display(self, obj):
        """Format device info for display"""
        info = obj.device_info
        return format_html(
            '<strong>Device:</strong> {}<br>'
            '<strong>Browser:</strong> {}<br>'
            '<strong>OS:</strong> {}',
            info.get('name', 'Unknown'),
            info.get('browser', 'Unknown'),
            info.get('os', 'Unknown')
        )
    device_info_display.short_description = 'Device Information'
    
    fieldsets = (
        (None, {
            'fields': ('user', 'is_active', 'revoked_reason')
        }),
        ('Session Details', {
            'fields': ('id', 'device_info_display', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Token Information', {
            'fields': ('refresh_token',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_used_at', 'expires_at', 'revoked_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['revoke_sessions', 'cleanup_expired_sessions']
    
    def revoke_sessions(self, request, queryset):
        """Admin action to revoke selected sessions"""
        active_sessions = queryset.filter(is_active=True)
        count = 0
        for session in active_sessions:
            session.revoke('admin_revoke')
            count += 1
        
        self.message_user(
            request,
            f'Successfully revoked {count} active sessions.'
        )
    revoke_sessions.short_description = 'Revoke selected sessions'
    
    def cleanup_expired_sessions(self, request, queryset):
        """Admin action to cleanup expired sessions"""
        expired_sessions = queryset.filter(
            expires_at__lt=timezone.now(),
            is_active=True
        )
        count = expired_sessions.count()
        expired_sessions.update(
            is_active=False,
            revoked_at=timezone.now(),
            revoked_reason='expired'
        )
        
        self.message_user(
            request,
            f'Successfully cleaned up {count} expired sessions.'
        )
    cleanup_expired_sessions.short_description = 'Cleanup expired sessions'
