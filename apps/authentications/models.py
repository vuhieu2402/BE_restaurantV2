from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import uuid
import random
import string


class VerificationCode(models.Model):
    """
    Model để quản lý mã xác thực (email/SMS)
    """
    VERIFICATION_TYPES = [
        ('email', 'Email Verification'),
        ('phone', 'Phone Verification'),
        ('password_reset', 'Password Reset'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(null=True, blank=True, help_text="Email để xác thực")
    phone_number = models.CharField(
        max_length=17,
        null=True,
        blank=True,
        help_text="Số điện thoại để xác thực"
    )
    code = models.CharField(max_length=6, help_text="Mã xác thực 6 số")
    verification_type = models.CharField(
        max_length=20,
        choices=VERIFICATION_TYPES,
        help_text="Loại xác thực"
    )
    attempts = models.IntegerField(default=0, help_text="Số lần thử sai")
    max_attempts = models.IntegerField(default=3, help_text="Số lần thử tối đa")

    is_verified = models.BooleanField(default=False, help_text="Đã xác thực")
    is_used = models.BooleanField(default=False, help_text="Đã sử dụng")

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="Thời gian hết hạn")
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'verification_codes'
        verbose_name = 'Mã xác thực'
        verbose_name_plural = 'Mã xác thực'
        indexes = [
            models.Index(fields=['email', 'verification_type']),
            models.Index(fields=['phone_number', 'verification_type']),
            models.Index(fields=['code', 'expires_at']),
            models.Index(fields=['is_verified', 'is_used']),
        ]
        # Chỉ cho phép 1 mã active (is_used=False) tại một thời điểm
        # Cho phép nhiều mã đã dùng (is_used=True)
        constraints = [
            models.UniqueConstraint(
                fields=['email', 'verification_type'],
                condition=models.Q(is_used=False),
                name='unique_active_email_verification'
            ),
            models.UniqueConstraint(
                fields=['phone_number', 'verification_type'],
                condition=models.Q(is_used=False),
                name='unique_active_phone_verification'
            ),
        ]

    def __str__(self):
        identifier = self.email or self.phone_number
        return f"{self.get_verification_type_display()} - {identifier} - {self.code}"

    @classmethod
    def generate_code(cls):
        """Tạo mã xác thực 6 số"""
        return ''.join(random.choices(string.digits, k=6))

    @classmethod
    def create_verification(cls, email=None, phone_number=None, verification_type='email'):
        """Tạo mã xác thực mới"""
        # Hủy mã cũ chưa xác thực - chỉ filter theo email hoặc phone_number tương ứng
        filter_kwargs = {
            'verification_type': verification_type,
            'is_verified': False,
            'is_used': False
        }
        
        if email:
            filter_kwargs['email'] = email
        elif phone_number:
            filter_kwargs['phone_number'] = phone_number
        
        cls.objects.filter(**filter_kwargs).update(is_used=True)

        return cls.objects.create(
            email=email,
            phone_number=phone_number,
            code=cls.generate_code(),
            verification_type=verification_type,
            expires_at=timezone.now() + timedelta(minutes=10)  # Hết hạn sau 10 phút
        )

    @property
    def is_expired(self):
        """Kiểm tra mã đã hết hạn chưa"""
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Kiểm tra mã còn hiệu lực không"""
        return not self.is_expired and not self.is_used and not self.is_verified

    @property
    def attempts_remaining(self):
        """Số lần thử còn lại"""
        return max(0, self.max_attempts - self.attempts)

    def verify(self, code):
        """Xác thực mã"""
        if not self.is_valid:
            return False, "Mã xác thực không hợp lệ hoặc đã hết hạn"

        if self.attempts >= self.max_attempts:
            return False, "Đã vượt quá số lần thử tối đa"

        self.attempts += 1

        if self.code != code:
            self.save()
            remaining = self.attempts_remaining
            return False, f"Mã xác thực không đúng. Còn {remaining} lần thử"

        self.is_verified = True
        self.verified_at = timezone.now()
        self.save()
        return True, "Xác thực thành công"

    def mark_as_used(self):
        """Đánh dấu là đã sử dụng"""
        self.is_used = True
        self.save()


class RefreshTokenSession(models.Model):
    """
    Stateful management cho refresh tokens - Hybrid approach
    Lưu refresh tokens trong DB để có thể revoke và track sessions
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='refresh_sessions'
    )
    refresh_token = models.TextField(help_text="Mã hóa refresh token")
    device_info = models.JSONField(default=dict, help_text="Thông tin device/browser")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="Thời gian hết hạn refresh token")
    last_used_at = models.DateTimeField(auto_now=True)
    
    is_active = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=100, blank=True, 
                                    choices=[
                                        ('logout', 'User Logout'),
                                        ('expired', 'Token Expired'),
                                        ('security', 'Security Revoke'),
                                        ('new_device', 'New Device Login'),
                                    ])
    
    class Meta:
        db_table = 'refresh_token_sessions'
        verbose_name = 'Refresh Token Session'
        verbose_name_plural = 'Refresh Token Sessions'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['refresh_token']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['ip_address', 'created_at']),
        ]
        
    def __str__(self):
        return f"{self.user.username} - {self.device_info.get('name', 'Unknown')} - {self.created_at}"
    
    def revoke(self, reason='logout'):
        """Revoke refresh token session"""
        self.is_active = False
        self.revoked_at = timezone.now()
        self.revoked_reason = reason
        self.save()
    
    @property
    def is_expired(self):
        """Check if token session is expired"""
        return timezone.now() > self.expires_at
    
    @classmethod
    def cleanup_expired_sessions(cls):
        """Clean up expired refresh token sessions"""
        expired_sessions = cls.objects.filter(
            expires_at__lt=timezone.now(),
            is_active=True
        )
        count = expired_sessions.count()
        expired_sessions.update(
            is_active=False,
            revoked_at=timezone.now(),
            revoked_reason='expired'
        )
        return count
    
    @classmethod
    def revoke_all_user_sessions(cls, user, exclude_session_id=None):
        """Revoke all active sessions for a user (except current one)"""
        sessions = cls.objects.filter(user=user, is_active=True)
        if exclude_session_id:
            sessions = sessions.exclude(id=exclude_session_id)
        
        return sessions.update(
            is_active=False,
            revoked_at=timezone.now(),
            revoked_reason='security'
        )

