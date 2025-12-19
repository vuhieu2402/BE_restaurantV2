"""
Data access layer for authentication app
- Chỉ query database
- KHÔNG business logic
- KHÔNG validation
- CHỈ có data access logic
- Caching để tăng performance
"""
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.cache import cache
from .models import VerificationCode, RefreshTokenSession

User = get_user_model()

# Cache timeout: 5 minutes
USER_CACHE_TIMEOUT = 300


class UserSelector:
    """Selector cho User model - chỉ query database với caching"""

    @staticmethod
    def get_user_by_email(email):
        """Get user by email với caching"""
        if not email:
            return None
        
        cache_key = f"user_email_{email}"
        user = cache.get(cache_key)
        
        if user is None:
            try:
                user = User.objects.get(email=email)
                cache.set(cache_key, user, USER_CACHE_TIMEOUT)
            except User.DoesNotExist:
                cache.set(cache_key, False, USER_CACHE_TIMEOUT)  # Cache miss để tránh DB lookup
                return None
        
        return user if user else None

    @staticmethod
    def get_user_by_phone(phone_number):
        """Get user by phone number với caching"""
        if not phone_number:
            return None
        
        cache_key = f"user_phone_{phone_number}"
        user = cache.get(cache_key)
        
        if user is None:
            try:
                user = User.objects.get(phone_number=phone_number)
                cache.set(cache_key, user, USER_CACHE_TIMEOUT)
            except User.DoesNotExist:
                cache.set(cache_key, False, USER_CACHE_TIMEOUT)  # Cache miss
                return None
        
        return user if user else None

    @staticmethod
    def get_user_by_identifier(identifier):
        """Get user by email or phone number"""
        if not identifier:
            return None
        
        if '@' in identifier:
            return UserSelector.get_user_by_email(identifier)
        else:
            return UserSelector.get_user_by_phone(identifier)

    @staticmethod
    def check_email_exists(email):
        """Check if email exists với caching"""
        if not email:
            return False
        
        cache_key = f"user_email_exists_{email}"
        exists = cache.get(cache_key)
        
        if exists is None:
            exists = User.objects.filter(email=email).exists()
            cache.set(cache_key, exists, USER_CACHE_TIMEOUT)
        
        return exists

    @staticmethod
    def check_phone_exists(phone_number):
        """Check if phone number exists với caching"""
        if not phone_number:
            return False
        
        cache_key = f"user_phone_exists_{phone_number}"
        exists = cache.get(cache_key)
        
        if exists is None:
            exists = User.objects.filter(phone_number=phone_number).exists()
            cache.set(cache_key, exists, USER_CACHE_TIMEOUT)
        
        return exists

    @staticmethod
    def check_identifier_exists(identifier):
        """Check if email or phone exists"""
        if not identifier:
            return False
        
        if '@' in identifier:
            return UserSelector.check_email_exists(identifier)
        else:
            return UserSelector.check_phone_exists(identifier)

    @staticmethod
    def invalidate_user_cache(user):
        """Invalidate cache khi user được update"""
        if user.email:
            cache.delete(f"user_email_{user.email}")
            cache.delete(f"user_email_exists_{user.email}")
        if user.phone_number:
            cache.delete(f"user_phone_{user.phone_number}")
            cache.delete(f"user_phone_exists_{user.phone_number}")


class VerificationCodeSelector:
    """Selector cho VerificationCode model - chỉ query database"""

    @staticmethod
    def get_active_verification_code(email=None, phone_number=None, verification_type='email'):
        """Get active verification code"""
        return VerificationCode.objects.filter(
            models.Q(email=email) | models.Q(phone_number=phone_number),
            verification_type=verification_type,
            is_verified=False,
            is_used=False,
            expires_at__gt=timezone.now()
        ).first()

    @staticmethod
    def get_verification_by_id(verification_id):
        """Get verification code by ID"""
        try:
            return VerificationCode.objects.get(id=verification_id)
        except VerificationCode.DoesNotExist:
            return None

    @staticmethod
    def get_verification_code_for_verify(code, email=None, phone_number=None, verification_type='email'):
        """Get verification code for verification"""
        try:
            return VerificationCode.objects.get(
                models.Q(email=email) | models.Q(phone_number=phone_number),
                code=code,
                verification_type=verification_type,
                is_used=False
            )
        except VerificationCode.DoesNotExist:
            return None

    @staticmethod
    def get_expired_verification_codes():
        """Get expired verification codes"""
        return VerificationCode.objects.filter(
            models.Q(
                models.Q(expires_at__lt=timezone.now()) |
                models.Q(is_used=True) |
                models.Q(attempts__gte=models.F('max_attempts'))
            )
        )

    @staticmethod
    def deactivate_old_codes(email=None, phone_number=None, verification_type='email'):
        """Deactivate old verification codes"""
        filter_kwargs = {
            'verification_type': verification_type,
            'is_verified': False,
            'is_used': False
        }
        
        if email:
            filter_kwargs['email'] = email
        elif phone_number:
            filter_kwargs['phone_number'] = phone_number
        
        return VerificationCode.objects.filter(**filter_kwargs).update(is_used=True)


class RefreshTokenSessionSelector:
    """Selector cho RefreshTokenSession model - chỉ query database"""

    @staticmethod
    def get_session_by_refresh_token(refresh_token):
        """Get session by refresh token"""
        try:
            return RefreshTokenSession.objects.get(
                refresh_token=refresh_token,
                is_active=True
            )
        except RefreshTokenSession.DoesNotExist:
            return None

    @staticmethod
    def get_active_user_sessions(user):
        """Get all active sessions for user"""
        return RefreshTokenSession.objects.filter(
            user=user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).order_by('-last_used_at')

    @staticmethod
    def get_expired_sessions():
        """Get expired sessions"""
        return RefreshTokenSession.objects.filter(
            expires_at__lt=timezone.now(),
            is_active=True
        )

    @staticmethod
    def revoke_user_sessions(user, exclude_session_id=None):
        """Revoke all sessions for user (except current one)"""
        sessions = RefreshTokenSession.objects.filter(
            user=user,
            is_active=True
        )
        if exclude_session_id:
            sessions = sessions.exclude(id=exclude_session_id)

        return sessions.update(
            is_active=False,
            revoked_at=timezone.now(),
            revoked_reason='security'
        )

    @staticmethod
    def update_session_activity(session_id, user):
        """Update session last_used_at"""
        return RefreshTokenSession.objects.filter(
            id=session_id,
            user=user,
            is_active=True
        ).update(last_used_at=timezone.now())