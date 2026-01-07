"""
Authentication Services - Business Logic Layer
- Xử lý business logic
- Validation business rules
- Điều phối các operation
- Transaction management
- Gọi Selector layer để lấy data
- KHÔNG query database trực tiếp
"""
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework_simplejwt.exceptions import TokenError
import logging
from datetime import timedelta
from django.contrib.auth import get_user_model
from .selectors import UserSelector, VerificationCodeSelector, RefreshTokenSessionSelector
from .models import VerificationCode, RefreshTokenSession
from .sms_service import SMSService
from .tasks import (
    send_email_verification_task,
    send_phone_verification_task,
    send_password_reset_task,
    send_welcome_email_task,
)

User = get_user_model()

logger = logging.getLogger(__name__)


class AuthService:
    """Service cho các thao tác authentication chính"""

    def __init__(self):
        self.user_selector = UserSelector()
        self.verification_selector = VerificationCodeSelector()
        self.session_selector = RefreshTokenSessionSelector()

    @staticmethod
    def generate_device_info(request):
        """Extract device information từ request"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        ip_address = AuthService.get_client_ip(request)

        # Simple device detection
        device_info = {
            'name': 'Unknown Device',
            'browser': 'Unknown',
            'os': 'Unknown',
            'ip_address': ip_address
        }

        # Basic browser detection
        if 'Chrome' in user_agent:
            device_info['browser'] = 'Chrome'
        elif 'Firefox' in user_agent:
            device_info['browser'] = 'Firefox'
        elif 'Safari' in user_agent:
            device_info['browser'] = 'Safari'
        elif 'Edge' in user_agent:
            device_info['browser'] = 'Edge'

        # Basic OS detection
        if 'Windows' in user_agent:
            device_info['os'] = 'Windows'
        elif 'Mac' in user_agent:
            device_info['os'] = 'macOS'
        elif 'Linux' in user_agent:
            device_info['os'] = 'Linux'
        elif 'Android' in user_agent:
            device_info['os'] = 'Android'
        elif 'iOS' in user_agent:
            device_info['os'] = 'iOS'

        # Set device name based on user agent patterns
        if 'Mobile' in user_agent:
            device_info['name'] = f"{device_info['browser']} Mobile"
        else:
            device_info['name'] = f"{device_info['browser']} Desktop"

        return device_info

    @staticmethod
    def get_client_ip(request):
        """Get real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def authenticate_user(self, identifier, password):
        """Authenticate user by email/phone and password"""
        try:
            # Validate business rule: identifier và password phải có
            if not identifier or not password:
                return {
                    'success': False,
                    'message': 'Vui lòng nhập email/số điện thoại và mật khẩu'
                }

            # Get user by identifier
            user = UserSelector.get_user_by_identifier(identifier)

            # Business rule: check if user exists
            if not user:
                return {
                    'success': False,
                    'message': 'Tài khoản không tồn tại'
                }

            # Business rule: check if user is active
            if not user.is_active:
                return {
                    'success': False,
                    'message': 'Tài khoản đã bị khóa'
                }

            # Business rule: check if user is verified
            if not user.is_verified:
                return {
                    'success': False,
                    'message': 'Tài khoản chưa được xác thực. Vui lòng kiểm tra email/SMS.'
                }

            # Check password
            if not user.check_password(password):
                return {
                    'success': False,
                    'message': 'Mật khẩu không đúng'
                }

            return {
                'success': True,
                'message': 'Xác thực thành công',
                'data': {'user': user}
            }

        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return {
                'success': False,
                'message': f'Đăng nhập thất bại: {str(e)}'
            }

    def generate_tokens(self, user, device_info=None):
        """Generate access và refresh tokens với business logic"""
        try:
            with transaction.atomic():
                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)
                access = refresh.access_token

                # Business rule: create session in database
                session = RefreshTokenSession.objects.create(
                    user=user,
                    refresh_token=str(refresh),
                    device_info=device_info or {},
                    ip_address=device_info.get('ip_address') if device_info else None,
                    expires_at=timezone.now() + settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME', timedelta(days=7))
                )

                return {
                    'success': True,
                    'message': 'Tạo token thành công',
                    'data': {
                        'access_token': str(access),
                        'refresh_token': str(refresh),
                        'access_token_expires': access['exp'],
                        'refresh_token_expires': refresh['exp']
                    }
                }

        except Exception as e:
            logger.error(f"Token generation error: {str(e)}")
            return {
                'success': False,
                'message': f'Tạo token thất bại: {str(e)}'
            }

    def refresh_token(self, refresh_token, device_info=None):
        """Refresh access token với business logic"""
        try:
            with transaction.atomic():
                # Business rule: validate refresh token existence
                session = RefreshTokenSessionSelector.get_session_by_refresh_token(refresh_token)
                if not session or session.is_expired:
                    return {
                        'success': False,
                        'message': 'Refresh token không hợp lệ hoặc đã hết hạn'
                    }

                # Update session activity
                session.last_used_at = timezone.now()
                session.save()

                # Revoke old refresh token (business rule: rotate tokens)
                session.revoke('new_device')

                # Generate new tokens
                refresh = RefreshToken.for_user(session.user)
                access = refresh.access_token

                # Create new session
                RefreshTokenSession.objects.create(
                    user=session.user,
                    refresh_token=str(refresh),
                    device_info=device_info or {},
                    ip_address=device_info.get('ip_address') if device_info else None,
                    expires_at=timezone.now() + settings.SIMPLE_JWT.get('REFRESH_TOKEN_LIFETIME', timedelta(days=7))
                )

                return {
                    'success': True,
                    'message': 'Refresh token thành công',
                    'data': {
                        'access_token': str(access),
                        'refresh_token': str(refresh),
                        'access_token_expires': access['exp'],
                        'refresh_token_expires': refresh['exp']
                    }
                }

        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            return {
                'success': False,
                'message': f'Refresh token thất bại: {str(e)}'
            }

    def revoke_refresh_token(self, refresh_token):
        """Revoke refresh token với business logic"""
        try:
            with transaction.atomic():
                session = RefreshTokenSessionSelector.get_session_by_refresh_token(refresh_token)

                if session:
                    session.revoke('logout')
                    return {
                        'success': True,
                        'message': 'Đăng xuất thành công'
                    }

                return {
                    'success': False,
                    'message': 'Không tìm thấy session để đăng xuất'
                }

        except Exception as e:
            logger.error(f"Token revoke error: {str(e)}")
            return {
                'success': False,
                'message': f'Đăng xuất thất bại: {str(e)}'
            }

    def revoke_all_user_sessions(self, user, exclude_session_id=None):
        """Revoke tất cả sessions của user (business logic)"""
        try:
            with transaction.atomic():
                count = RefreshTokenSessionSelector.revoke_user_sessions(
                    user, exclude_session_id
                )

                return {
                    'success': True,
                    'message': f'Đã đăng xuất khỏi {count} thiết bị khác',
                    'data': {'revoked_sessions': count}
                }

        except Exception as e:
            logger.error(f"Revoke all sessions error: {str(e)}")
            return {
                'success': False,
                'message': f'Đăng xuất tất cả thất bại: {str(e)}'
            }

    def revoke_current_session(self, request):
        """Revoke current session based on request"""
        try:
            with transaction.atomic():
                # Get the current session using the refresh token from the request
                refresh_token = self._get_refresh_token_from_request(request)

                if not refresh_token:
                    return {
                        'success': False,
                        'message': 'Không tìm thấy refresh token trong request'
                    }

                # Get and revoke the session
                session = RefreshTokenSessionSelector.get_session_by_refresh_token(refresh_token)

                if session:
                    if not session.is_active:
                        return {
                            'success': False,
                            'message': 'Session đã được đăng xuất trước đó'
                        }

                    session.revoke('logout')
                    return {
                        'success': True,
                        'message': 'Đăng xuất thành công',
                        'data': {
                            'device_name': session.device_info.get('name', 'Unknown Device'),
                            'logged_out_at': timezone.now()
                        }
                    }

                return {
                    'success': False,
                    'message': 'Không tìm thấy session để đăng xuất'
                }

        except Exception as e:
            logger.error(f"Current session revoke error: {str(e)}")
            return {
                'success': False,
                'message': f'Đăng xuất thất bại: {str(e)}'
            }

    def _get_refresh_token_from_request(self, request):
        """Extract refresh token from request (cookies or headers)"""
        # Try to get from cookies first
        refresh_token = request.COOKIES.get('refresh_token')

        if refresh_token:
            return refresh_token

        # Try to get from Authorization header (if using Bearer token)
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            # Note: This would be the access token, not refresh token
            # In most implementations, refresh token should be in cookies or separate header
            pass

        # Try custom header
        refresh_token = request.META.get('HTTP_X_REFRESH_TOKEN')

        return refresh_token

    def get_user_sessions(self, user):
        """Get tất cả active sessions của user"""
        try:
            sessions = RefreshTokenSessionSelector.get_active_user_sessions(user)

            return {
                'success': True,
                'message': 'Lấy danh sách session thành công',
                'data': list(sessions)
            }

        except Exception as e:
            logger.error(f"Get sessions error: {str(e)}")
            return {
                'success': False,
                'message': f'Lấy session thất bại: {str(e)}'
            }


class RegistrationService:
    """Service cho user registration"""

    def __init__(self):
        self.user_selector = UserSelector()
        self.verification_service = VerificationService()

    def register_user(self, user_data):
        """Register user với business logic và validation"""
        try:
            with transaction.atomic():
                # Business rule: validate required fields
                email = user_data.get('email')
                phone_number = user_data.get('phone_number')

                if not email and not phone_number:
                    return {
                        'success': False,
                        'message': 'Phải cung cấp email hoặc số điện thoại',
                        'errors': {
                            'identifier': 'Phải cung cấp email hoặc số điện thoại'
                        }
                    }

                # Business rule: check email uniqueness
                if email and UserSelector.check_email_exists(email):
                    return {
                        'success': False,
                        'message': 'Email đã được sử dụng',
                        'errors': {
                            'email': 'Email đã được sử dụng'
                        }
                    }

                # Business rule: check phone uniqueness
                if phone_number and UserSelector.check_phone_exists(phone_number):
                    return {
                        'success': False,
                        'message': 'Số điện thoại đã được sử dụng',
                        'errors': {
                            'phone_number': 'Số điện thoại đã được sử dụng'
                        }
                    }

                # Remove password_confirm from data
                registration_data = user_data.copy()
                registration_data.pop('password_confirm', None)

                # Create user (not active until verification)
                user = User.objects.create_user(
                    is_verified=False,  # Business rule: requires verification
                    **registration_data
                )

                # Send verification code
                if email:
                    success, message = self.verification_service.send_email_verification(email)
                elif phone_number:
                    success, message = self.verification_service.send_phone_verification(phone_number)
                else:
                    success, message = False, "Không thể gửi mã xác thực"

                if not success:
                    # Rollback user creation if verification fails
                    user.delete()
                    return {
                        'success': False,
                        'message': message
                    }

                return {
                    'success': True,
                    'message': 'Đăng ký thành công. Vui lòng kiểm tra email/SMS để xác thực tài khoản.',
                    'data': {
                        'user': user,
                        'verification_sent': True,
                        'verification_target': email or phone_number
                    }
                }

        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return {
                'success': False,
                'message': f'Đăng ký thất bại: {str(e)}'
            }


class VerificationService:
    """Service cho email/SMS verification"""

    def __init__(self):
        self.user_selector = UserSelector()
        self.verification_selector = VerificationCodeSelector()

    def send_email_verification(self, email):
        """Gửi email verification code với business logic using Celery"""
        try:
            with transaction.atomic():
                # Check rate limiting for verification codes
                rate_limit_result = self._check_verification_rate_limit(email, 'email')
                if not rate_limit_result['allowed']:
                    return False, rate_limit_result['message']

                # Tạo verification code (create_verification đã tự động deactivate old codes)
                verification = VerificationCode.create_verification(
                    email=email,
                    verification_type='email'
                )

                # Queue email sending task to Celery (async)
                task_result = send_email_verification_task.delay(str(verification.id))

                # Update rate limit counter
                self._update_verification_rate_limit(email, 'email')

                logger.info(f"Email verification task queued for {email} (task_id: {task_result.id})")
                return True, "Mã xác thực đã được gửi đến email của bạn"

        except Exception as e:
            logger.error(f"Queue email verification error: {str(e)}")
            return False, "Không thể gửi email xác thực. Vui lòng thử lại sau."

    def send_phone_verification(self, phone_number):
        """Gửi SMS verification code với business logic using Celery"""
        try:
            with transaction.atomic():
                # Check rate limiting for verification codes
                rate_limit_result = self._check_verification_rate_limit(phone_number, 'phone')
                if not rate_limit_result['allowed']:
                    return False, rate_limit_result['message']

                # Tạo verification code (create_verification đã tự động deactivate old codes)
                verification = VerificationCode.create_verification(
                    phone_number=phone_number,
                    verification_type='phone'
                )

                # Queue SMS sending task to Celery (async)
                task_result = send_phone_verification_task.delay(str(verification.id))

                # Update rate limit counter
                self._update_verification_rate_limit(phone_number, 'phone')

                logger.info(f"SMS verification task queued for {phone_number} (task_id: {task_result.id})")
                return True, "Mã xác thực đã được gửi đến số điện thoại của bạn"

        except Exception as e:
            logger.error(f"Queue phone verification error: {str(e)}")
            return False, "Không thể gửi SMS xác thực. Vui lòng thử lại sau."

    def verify_code(self, email=None, phone_number=None, code=None, verification_type='email'):
        """Verify email/SMS code với business logic"""
        try:
            with transaction.atomic():
                # Get verification code
                verification = VerificationCodeSelector.get_verification_code_for_verify(
                    code=code,
                    email=email,
                    phone_number=phone_number,
                    verification_type=verification_type
                )

                if not verification:
                    return {
                        'success': False,
                        'message': 'Mã xác thực không tồn tại'
                    }

                # Business validation
                if verification.attempts >= verification.max_attempts:
                    return {
                        'success': False,
                        'message': 'Đã vượt quá số lần thử tối đa'
                    }

                # Check if code is expired
                if verification.is_expired:
                    return {
                        'success': False,
                        'message': 'Mã xác thực không hợp lệ hoặc đã hết hạn'
                    }

                # Increment attempts
                verification.attempts += 1

                if verification.code != code:
                    verification.save()
                    remaining = verification.attempts_remaining
                    return {
                        'success': False,
                        'message': f'Mã xác thực không đúng. Còn {remaining} lần thử'
                    }

                # Mark as verified
                verification.is_verified = True
                verification.verified_at = timezone.now()
                verification.save()

                # Business rule: activate user if this is email/phone verification
                user = None
                if verification_type in ['email', 'phone']:
                    try:
                        if email:
                            user = UserSelector.get_user_by_email(email)
                        else:
                            user = UserSelector.get_user_by_phone(phone_number)

                        if user:
                            user.is_verified = True
                            user.save()
                            logger.info(f"User {user.email or user.phone_number} verified successfully")
                    except Exception:
                        pass  # User không tồn tại

                # Send welcome email after successful verification
                if user and user.is_verified and (email or (user.email and phone_number)):
                    # Send welcome email asynchronously if user has email
                    if user.email:
                        try:
                            send_welcome_email_task.delay(user.id)
                            logger.info(f"Welcome email task queued for user {user.id}")
                        except Exception as e:
                            logger.warning(f"Failed to queue welcome email for user {user.id}: {str(e)}")

                return {
                    'success': True,
                    'message': 'Xác thực thành công'
                }

        except Exception as e:
            logger.error(f"Code verification error: {str(e)}")
            return {
                'success': False,
                'message': f'Xác thực thất bại: {str(e)}'
            }

    def send_password_reset(self, email=None, phone_number=None):
        """Gửi mã reset password với business logic using Celery"""
        try:
            with transaction.atomic():
                # Create password reset code
                verification = VerificationCode.create_verification(
                    email=email,
                    phone_number=phone_number,
                    verification_type='password_reset'
                )

                # Queue password reset task to Celery (async)
                task_result = send_password_reset_task.delay(str(verification.id))

                logger.info(f"Password reset task queued for {email or phone_number} (task_id: {task_result.id})")
                return {
                    'success': True,
                    'message': 'Mã đặt lại mật khẩu đã được gửi'
                }

        except Exception as e:
            logger.error(f"Queue password reset error: {str(e)}")
            return {
                'success': False,
                'message': 'Không thể gửi mã đặt lại mật khẩu'
            }

    def cleanup_expired_codes(self):
        """Clean up expired verification codes"""
        try:
            with transaction.atomic():
                expired_codes = VerificationCodeSelector.get_expired_verification_codes()
                count = expired_codes.count()
                expired_codes.delete()

                logger.info(f"Cleaned up {count} expired verification codes")
                return {
                    'success': True,
                    'message': f'Đã dọn dẹp {count} mã xác thực hết hạn',
                    'data': {'cleaned_count': count}
                }

        except Exception as e:
            logger.error(f"Cleanup expired codes error: {str(e)}")
            return {
                'success': False,
                'message': 'Dọn dẹp mã xác thực thất bại'
            }

    def _check_verification_rate_limit(self, identifier, verification_type='email'):
        """
        Kiểm tra rate limiting cho verification codes
        Returns: {'allowed': bool, 'message': str}
        """
        # Get rate limits from settings
        per_10min = getattr(settings, 'VERIFICATION_RATE_LIMIT_PER_10MIN', 3)
        per_hour = getattr(settings, 'VERIFICATION_RATE_LIMIT_PER_HOUR', 10)
        per_day = getattr(settings, 'VERIFICATION_RATE_LIMIT_PER_DAY', 20)

        now = timezone.now()
        
        # Check per 10 minutes
        ten_min_key = f"verify_rate_{identifier}_{verification_type}_10min_{now.strftime('%Y%m%d%H%M')[:11]}"
        ten_min_count = cache.get(ten_min_key, 0)
        if ten_min_count >= per_10min:
            return {
                'allowed': False,
                'message': 'Quá nhiều yêu cầu mã xác thực. Vui lòng đợi 10 phút trước khi thử lại.'
            }

        # Check per hour
        hour_key = f"verify_rate_{identifier}_{verification_type}_hour_{now.strftime('%Y%m%d%H')}"
        hour_count = cache.get(hour_key, 0)
        if hour_count >= per_hour:
            return {
                'allowed': False,
                'message': 'Quá nhiều yêu cầu trong giờ. Vui lòng thử lại sau.'
            }

        # Check per day
        day_key = f"verify_rate_{identifier}_{verification_type}_day_{now.strftime('%Y%m%d')}"
        day_count = cache.get(day_key, 0)
        if day_count >= per_day:
            return {
                'allowed': False,
                'message': 'Đã đạt giới hạn yêu cầu mã xác thực trong ngày. Vui lòng thử lại ngày mai.'
            }

        return {'allowed': True, 'message': ''}

    def _update_verification_rate_limit(self, identifier, verification_type='email'):
        """Update rate limit counters for verification codes"""
        now = timezone.now()
        
        # Update 10-minute counter
        ten_min_key = f"verify_rate_{identifier}_{verification_type}_10min_{now.strftime('%Y%m%d%H%M')[:11]}"
        cache.set(ten_min_key, cache.get(ten_min_key, 0) + 1, 600)  # Expire in 10 minutes

        # Update hour counter
        hour_key = f"verify_rate_{identifier}_{verification_type}_hour_{now.strftime('%Y%m%d%H')}"
        cache.set(hour_key, cache.get(hour_key, 0) + 1, 3600)  # Expire in 1 hour

        # Update day counter
        day_key = f"verify_rate_{identifier}_{verification_type}_day_{now.strftime('%Y%m%d')}"
        cache.set(day_key, cache.get(day_key, 0) + 1, 86400)  # Expire in 24 hours


class PasswordService:
    """Service cho password management"""

    @staticmethod
    def validate_password_strength(password):
        """Validate password strength - returns (is_valid, message)"""
        errors = []

        if len(password) < 8:
            errors.append('Mật khẩu phải có ít nhất 8 ký tự')

        if not any(c.isupper() for c in password):
            errors.append('Mật khẩu phải có ít nhất 1 chữ hoa')

        if not any(c.islower() for c in password):
            errors.append('Mật khẩu phải có ít nhất 1 chữ thường')

        if not any(c.isdigit() for c in password):
            errors.append('Mật khẩu phải có ít nhất 1 số')

        if errors:
            message = '; '.join(errors)
            return False, message

        return True, 'Mật khẩu hợp lệ'

    def reset_password(self, email=None, phone_number=None, code=None, new_password=None):
        """Reset password với verification code"""
        try:
            with transaction.atomic():
                # Verify reset code
                verification_service = VerificationService()
                verify_result = verification_service.verify_code(
                    email=email,
                    phone_number=phone_number,
                    code=code,
                    verification_type='password_reset'
                )

                if not verify_result['success']:
                    return verify_result

                # Get user
                if email:
                    user = UserSelector.get_user_by_email(email)
                else:
                    user = UserSelector.get_user_by_phone(phone_number)

                if not user:
                    return {
                        'success': False,
                        'message': 'Tài khoản không tồn tại'
                    }

                # Reset password
                user.set_password(new_password)
                user.save()

                # Revoke all sessions of this user
                auth_service = AuthService()
                auth_service.revoke_all_user_sessions(user)

                return {
                    'success': True,
                    'message': 'Đặt lại mật khẩu thành công. Vui lòng đăng nhập lại.'
                }

        except Exception as e:
            logger.error(f"Password reset error: {str(e)}")
            return {
                'success': False,
                'message': f'Đặt lại mật khẩu thất bại: {str(e)}'
            }

    def change_password(self, user, old_password=None, new_password=None):
        """Change password cho authenticated user"""
        try:
            with transaction.atomic():
                # Business rule: verify old password
                if not user.check_password(old_password):
                    return {
                        'success': False,
                        'message': 'Mật khẩu cũ không đúng'
                    }

                # Change password
                user.set_password(new_password)
                user.save()

                # Revoke all sessions except current
                auth_service = AuthService()
                auth_service.revoke_all_user_sessions(user)

                return {
                    'success': True,
                    'message': 'Đổi mật khẩu thành công. Vui lòng đăng nhập lại.'
                }

        except Exception as e:
            logger.error(f"Change password error: {str(e)}")
            return {
                'success': False,
                'message': f'Đổi mật khẩu thất bại: {str(e)}'
            }

    @staticmethod
    def generate_secure_password(length=12):
        """Generate random secure password"""
        import random
        import string

        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        while True:
            password = ''.join(random.choices(characters, k=length))
            # Check if password meets all criteria
            is_valid, _ = PasswordService.validate_password_strength(password)
            if is_valid:
                return password