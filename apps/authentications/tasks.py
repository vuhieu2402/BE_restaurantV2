"""
Celery Tasks for Authentication System
Asynchronous email sending, SMS, and background operations
"""
import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from decouple import config
from .models import VerificationCode, RefreshTokenSession
from .sms_service import SMSService
from .selectors import VerificationCodeSelector
from django.contrib.auth import get_user_model

User = get_user_model()
logger = logging.getLogger(__name__)

# Celery settings for retries and timeouts
MAX_RETRIES = 3
RETRY_DELAY = 60  # seconds
TASK_SOFT_TIME_LIMIT = 300  # 5 minutes


@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    soft_time_limit=TASK_SOFT_TIME_LIMIT,
    queue='auth'
)
def send_email_verification_task(self, verification_id):
    """
    Asynchronous email verification sending task
    Sends verification code via email using Celery

    Args:
        verification_id (str): UUID of the VerificationCode object

    Returns:
        dict: Success/failure status with message
    """
    try:
        # Get verification code from database
        verification = VerificationCodeSelector.get_verification_by_id(verification_id)

        if not verification:
            logger.error(f"Verification code not found: {verification_id}")
            return {
                'success': False,
                'message': 'Verification code not found',
                'verification_id': verification_id
            }

        # Check if verification is still valid
        if verification.is_verified or verification.is_used or verification.is_expired:
            logger.warning(f"Invalid verification attempt: {verification_id} - "
                          f"verified: {verification.is_verified}, used: {verification.is_used}, "
                          f"expired: {verification.is_expired}")
            return {
                'success': False,
                'message': 'Verification code is no longer valid',
                'verification_id': verification_id
            }

        # Compose email
        subject = 'Xác thực Email - Restaurant Management System'

        # Use HTML template for better formatting
        html_message = f"""
        <html>
        <head></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <h2 style="color: #333; text-align: center;">Restaurant Management System</h2>
                <div style="background-color: white; padding: 30px; border-radius: 6px; margin-top: 20px;">
                    <h3 style="color: #007bff;">Xác thực Email</h3>
                    <p>Xin chào,</p>
                    <p>Mã xác thực email của bạn là:</p>
                    <div style="background-color: #e9ecef; padding: 20px; text-align: center;
                               border-radius: 4px; margin: 20px 0;">
                        <span style="font-size: 32px; font-weight: bold; letter-spacing: 3px; color: #007bff;">
                            {verification.code}
                        </span>
                    </div>
                    <p><strong>Lưu ý:</strong></p>
                    <ul>
                        <li>Mã này có hiệu lực trong <strong>10 phút</strong></li>
                        <li>Vui lòng không chia sẻ mã này với người khác</li>
                        <li>Nếu bạn không yêu cầu mã này, vui lòng bỏ qua email này</li>
                    </ul>
                </div>
                <div style="text-align: center; margin-top: 30px; color: #6c757d;">
                    <p>Trân trọng,<br>Restaurant Management System Team</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_message = f"""
        Chào bạn,

        Mã xác thực email của bạn là: {verification.code}

        Mã này có hiệu lực trong 10 phút.
        Vui lòng không chia sẻ mã này với người khác.

        Trân trọng,
        Restaurant Management System Team
        """

        # Send email with retry logic
        try:
            result = send_mail(
                subject=subject,
                message=text_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@restaurant.com'),
                recipient_list=[verification.email],
                html_message=html_message,
                fail_silently=False
            )

            if result == 1:  # Email sent successfully
                logger.info(f"Email verification sent successfully to {verification.email}")

                # Update rate limit counter (this happens in the service layer)
                # Mark as sent (optional - could add a 'sent_at' field to VerificationCode model)

                return {
                    'success': True,
                    'message': 'Email verification sent successfully',
                    'verification_id': str(verification.id),
                    'email': verification.email
                }
            else:
                raise Exception(f"Email sending failed with result: {result}")

        except Exception as email_error:
            logger.error(f"Email sending failed for {verification.email}: {str(email_error)}")

            # Retry with exponential backoff
            if self.request.retries < self.max_retries:
                countdown = RETRY_DELAY * (2 ** self.request.retries)  # Exponential backoff
                logger.info(f"Retrying email verification task in {countdown} seconds (attempt {self.request.retries + 1})")
                raise self.retry(countdown=countdown, exc=email_error)

            # Max retries exceeded
            logger.error(f"Max retries exceeded for email verification to {verification.email}")
            return {
                'success': False,
                'message': f'Failed to send email after {self.max_retries} attempts',
                'verification_id': str(verification.id),
                'email': verification.email,
                'error': str(email_error)
            }

    except Exception as e:
        logger.error(f"Email verification task failed: {str(e)}")
        return {
            'success': False,
            'message': f'Task failed: {str(e)}',
            'verification_id': verification_id
        }


@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    soft_time_limit=TASK_SOFT_TIME_LIMIT,
    queue='auth'
)
def send_phone_verification_task(self, verification_id):
    """
    Asynchronous phone verification sending task
    Sends verification code via SMS using Celery

    Args:
        verification_id (str): UUID of the VerificationCode object

    Returns:
        dict: Success/failure status with message
    """
    try:
        # Get verification code from database
        verification = VerificationCodeSelector.get_verification_by_id(verification_id)

        if not verification:
            logger.error(f"Verification code not found: {verification_id}")
            return {
                'success': False,
                'message': 'Verification code not found',
                'verification_id': verification_id
            }

        # Check if verification is still valid
        if verification.is_verified or verification.is_used or verification.is_expired:
            logger.warning(f"Invalid verification attempt: {verification_id}")
            return {
                'success': False,
                'message': 'Verification code is no longer valid',
                'verification_id': verification_id
            }

        # Get SMS template
        sms_templates = getattr(settings, 'SMS_TEMPLATES', {})
        template = sms_templates.get('verification', 'Ma xac thuc cua ban la: {code}. Hieu luc trong {minutes} phut.')
        message = template.format(code=verification.code, minutes=10)

        # Send SMS via SMS service
        sms_success, sms_message = SMSService.send_sms(
            phone_number=verification.phone_number,
            message=message,
            message_type='verification'
        )

        if not sms_success:
            logger.error(f"SMS verification failed for {verification.phone_number}: {sms_message}")

            # Retry with exponential backoff
            if self.request.retries < self.max_retries:
                countdown = RETRY_DELAY * (2 ** self.request.retries)
                logger.info(f"Retrying SMS verification task in {countdown} seconds (attempt {self.request.retries + 1})")
                raise self.retry(countdown=countdown, exc=Exception(sms_message))

            # Max retries exceeded
            return {
                'success': False,
                'message': f'Failed to send SMS after {self.max_retries} attempts',
                'verification_id': str(verification.id),
                'phone_number': verification.phone_number,
                'error': sms_message
            }

        logger.info(f"SMS verification sent successfully to {verification.phone_number}")
        return {
            'success': True,
            'message': 'SMS verification sent successfully',
            'verification_id': str(verification.id),
            'phone_number': verification.phone_number
        }

    except Exception as e:
        logger.error(f"SMS verification task failed: {str(e)}")
        return {
            'success': False,
            'message': f'Task failed: {str(e)}',
            'verification_id': verification_id
        }


@shared_task(
    bind=True,
    max_retries=MAX_RETRIES,
    soft_time_limit=TASK_SOFT_TIME_LIMIT,
    queue='auth'
)
def send_password_reset_task(self, verification_id):
    """
    Asynchronous password reset email/SMS sending task
    Sends password reset code using Celery

    Args:
        verification_id (str): UUID of the VerificationCode object

    Returns:
        dict: Success/failure status with message
    """
    try:
        # Get verification code from database
        verification = VerificationCodeSelector.get_verification_by_id(verification_id)

        if not verification:
            logger.error(f"Password reset verification not found: {verification_id}")
            return {
                'success': False,
                'message': 'Password reset verification not found',
                'verification_id': verification_id
            }

        # Check if verification is still valid
        if verification.is_verified or verification.is_used or verification.is_expired:
            logger.warning(f"Invalid password reset attempt: {verification_id}")
            return {
                'success': False,
                'message': 'Password reset code is no longer valid',
                'verification_id': verification_id
            }

        # Send via email or SMS
        if verification.email:
            # Send password reset email
            subject = 'Đặt lại Mật khẩu - Restaurant Management System'

            html_message = f"""
            <html>
            <head></head>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                    <h2 style="color: #333; text-align: center;">Restaurant Management System</h2>
                    <div style="background-color: white; padding: 30px; border-radius: 6px; margin-top: 20px;">
                        <h3 style="color: #dc3545;">Đặt lại Mật khẩu</h3>
                        <p>Xin chào,</p>
                        <p>Mã đặt lại mật khẩu của bạn là:</p>
                        <div style="background-color: #f8d7da; padding: 20px; text-align: center;
                                   border-radius: 4px; margin: 20px 0; border: 1px solid #f5c6cb;">
                            <span style="font-size: 32px; font-weight: bold; letter-spacing: 3px; color: #721c24;">
                                {verification.code}
                            </span>
                        </div>
                        <p><strong>Lưu ý quan trọng:</strong></p>
                        <ul>
                            <li>Mã này có hiệu lực trong <strong>10 phút</strong></li>
                            <li>Vui lòng không chia sẻ mã này với người khác</li>
                            <li>Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng liên hệ hỗ trợ</li>
                        </ul>
                    </div>
                    <div style="text-align: center; margin-top: 30px; color: #6c757d;">
                        <p>Trân trọng,<br>Restaurant Management System Team</p>
                    </div>
                </div>
            </body>
            </html>
            """

            text_message = f"""
            Chào bạn,

            Mã đặt lại mật khẩu của bạn là: {verification.code}

            Mã này có hiệu lực trong 10 phút.
            Vui lòng không chia sẻ mã này với người khác.

            Nếu bạn không yêu cầu đặt lại mật khẩu, vui lòng liên hệ hỗ trợ.

            Trân trọng,
            Restaurant Management System Team
            """

            try:
                result = send_mail(
                    subject=subject,
                    message=text_message,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@restaurant.com'),
                    recipient_list=[verification.email],
                    html_message=html_message,
                    fail_silently=False
                )

                if result == 1:
                    logger.info(f"Password reset email sent to {verification.email}")
                    return {
                        'success': True,
                        'message': 'Password reset email sent successfully',
                        'verification_id': str(verification.id),
                        'email': verification.email
                    }
                else:
                    raise Exception(f"Email sending failed with result: {result}")

            except Exception as email_error:
                logger.error(f"Password reset email failed for {verification.email}: {str(email_error)}")

                if self.request.retries < self.max_retries:
                    countdown = RETRY_DELAY * (2 ** self.request.retries)
                    raise self.retry(countdown=countdown, exc=email_error)

                return {
                    'success': False,
                    'message': f'Failed to send password reset email after {self.max_retries} attempts',
                    'verification_id': str(verification.id),
                    'error': str(email_error)
                }

        elif verification.phone_number:
            # Send password reset SMS
            sms_templates = getattr(settings, 'SMS_TEMPLATES', {})
            template = sms_templates.get('password_reset', 'Mat khau moi cua ban la: {code}. Hieu luc trong {minutes} phut.')
            message = template.format(code=verification.code, minutes=10)

            sms_success, sms_message = SMSService.send_sms(
                phone_number=verification.phone_number,
                message=message,
                message_type='password_reset'
            )

            if not sms_success:
                logger.error(f"Password reset SMS failed for {verification.phone_number}: {sms_message}")

                if self.request.retries < self.max_retries:
                    countdown = RETRY_DELAY * (2 ** self.request.retries)
                    raise self.retry(countdown=countdown, exc=Exception(sms_message))

                return {
                    'success': False,
                    'message': f'Failed to send password reset SMS after {self.max_retries} attempts',
                    'verification_id': str(verification.id),
                    'error': sms_message
                }

            logger.info(f"Password reset SMS sent to {verification.phone_number}")
            return {
                'success': True,
                'message': 'Password reset SMS sent successfully',
                'verification_id': str(verification.id),
                'phone_number': verification.phone_number
            }

        else:
            return {
                'success': False,
                'message': 'No email or phone number found for password reset',
                'verification_id': str(verification.id)
            }

    except Exception as e:
        logger.error(f"Password reset task failed: {str(e)}")
        return {
            'success': False,
            'message': f'Task failed: {str(e)}',
            'verification_id': verification_id
        }


@shared_task(
    bind=True,
    soft_time_limit=TASK_SOFT_TIME_LIMIT,
    queue='auth'
)
def cleanup_expired_verification_codes(self):
    """
    Periodic task to clean up expired verification codes
    Runs every 10 minutes via Celery Beat

    Returns:
        dict: Cleanup statistics
    """
    try:
        with transaction.atomic():
            # Get all expired verification codes
            expired_codes = VerificationCodeSelector.get_expired_verification_codes()
            count = expired_codes.count()

            if count > 0:
                # Log what we're deleting for audit purposes
                for code in expired_codes[:10]:  # Log first 10 for debugging
                    logger.debug(f"Deleting expired verification code: {code.id} "
                               f"({code.email or code.phone_number})")

                # Delete expired codes
                expired_codes.delete()
                logger.info(f"Cleaned up {count} expired verification codes")
            else:
                logger.debug("No expired verification codes to clean up")

            return {
                'success': True,
                'message': f'Cleaned up {count} expired verification codes',
                'cleaned_count': count,
                'timestamp': timezone.now().isoformat()
            }

    except Exception as e:
        logger.error(f"Cleanup expired verification codes task failed: {str(e)}")
        return {
            'success': False,
            'message': f'Cleanup failed: {str(e)}',
            'timestamp': timezone.now().isoformat()
        }


@shared_task(
    bind=True,
    soft_time_limit=TASK_SOFT_TIME_LIMIT,
    queue='auth'
)
def cleanup_expired_refresh_tokens(self):
    """
    Periodic task to clean up expired refresh token sessions
    Runs every hour via Celery Beat

    Returns:
        dict: Cleanup statistics
    """
    try:
        with transaction.atomic():
            # Use the model's cleanup method
            count = RefreshTokenSession.cleanup_expired_sessions()

            logger.info(f"Cleaned up {count} expired refresh token sessions")
            return {
                'success': True,
                'message': f'Cleaned up {count} expired refresh token sessions',
                'cleaned_count': count,
                'timestamp': timezone.now().isoformat()
            }

    except Exception as e:
        logger.error(f"Cleanup expired refresh tokens task failed: {str(e)}")
        return {
            'success': False,
            'message': f'Cleanup failed: {str(e)}',
            'timestamp': timezone.now().isoformat()
        }


@shared_task(
    bind=True,
    soft_time_limit=TASK_SOFT_TIME_LIMIT,
    queue='auth'
)
def send_welcome_email_task(self, user_id):
    """
    Send welcome email to newly registered users
    This task is triggered after successful email verification

    Args:
        user_id (int): ID of the user

    Returns:
        dict: Success/failure status
    """
    try:
        # Get user from database
        try:
            user = User.objects.get(id=user_id, is_active=True, is_verified=True)
        except User.DoesNotExist:
            logger.error(f"User not found or not verified: {user_id}")
            return {
                'success': False,
                'message': 'User not found or not verified',
                'user_id': user_id
            }

        # Compose welcome email
        subject = 'Chào mừng đến với Restaurant Management System'

        html_message = f"""
        <html>
        <head></head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <h2 style="color: #333; text-align: center;">Restaurant Management System</h2>
                <div style="background-color: white; padding: 30px; border-radius: 6px; margin-top: 20px;">
                    <h3 style="color: #28a745;">Chào mừng {user.first_name or user.username}!</h3>
                    <p>Tài khoản của bạn đã được xác thực thành công và sẵn sàng sử dụng.</p>
                    <p>Bạn có thể:</p>
                    <ul>
                        <li>🍽️ Đặt món ăn trực tuyến</li>
                        <li>📅 Đặt bàn tại nhà hàng</li>
                        <li>🏪 Quản lý thông tin cá nhân</li>
                        <li>💳 Thanh toán an toàn</li>
                    </ul>
                    <p style="margin-top: 30px;">
                        <a href="#" style="background-color: #007bff; color: white; padding: 12px 24px;
                         text-decoration: none; border-radius: 4px; display: inline-block;">
                            Bắt đầu trải nghiệm
                        </a>
                    </p>
                </div>
                <div style="text-align: center; margin-top: 30px; color: #6c757d;">
                    <p>Cảm ơn bạn đã tin tưởng dịch vụ của chúng tôi!<br>Restaurant Management System Team</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_message = f"""
        Chào mừng {user.first_name or user.username}!

        Tài khoản của bạn đã được xác thực thành công và sẵn sàng sử dụng.

        Bạn có thể:
        - Đặt món ăn trực tuyến
        - Đặt bàn tại nhà hàng
        - Quản lý thông tin cá nhân
        - Thanh toán an toàn

        Cảm ơn bạn đã tin tưởng dịch vụ của chúng tôi!

        Trân trọng,
        Restaurant Management System Team
        """

        # Send welcome email
        try:
            result = send_mail(
                subject=subject,
                message=text_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@restaurant.com'),
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )

            if result == 1:
                logger.info(f"Welcome email sent to {user.email}")
                return {
                    'success': True,
                    'message': 'Welcome email sent successfully',
                    'user_id': user_id,
                    'email': user.email
                }
            else:
                raise Exception(f"Email sending failed with result: {result}")

        except Exception as email_error:
            logger.error(f"Welcome email failed for {user.email}: {str(email_error)}")

            # Retry welcome email (less critical, so fewer retries)
            if self.request.retries < 2:  # Max 2 retries for welcome emails
                countdown = RETRY_DELAY * (2 ** self.request.retries)
                raise self.retry(countdown=countdown, exc=email_error)

            return {
                'success': False,
                'message': 'Failed to send welcome email',
                'user_id': user_id,
                'error': str(email_error)
            }

    except Exception as e:
        logger.error(f"Welcome email task failed: {str(e)}")
        return {
            'success': False,
            'message': f'Welcome email task failed: {str(e)}',
            'user_id': user_id
        }


# Task monitoring utilities
def get_task_status(task_id):
    """
    Get status of a Celery task

    Args:
        task_id (str): Celery task ID

    Returns:
        dict: Task status information
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id)

    return {
        'task_id': task_id,
        'status': result.status,
        'result': result.result if result.ready() else None,
        'traceback': result.traceback if result.failed() else None,
        'date_done': str(result.date_done) if result.ready() else None,
    }


def revoke_task(task_id, terminate=False):
    """
    Revoke a Celery task

    Args:
        task_id (str): Celery task ID
        terminate (bool): Whether to terminate the task if running

    Returns:
        bool: True if task was revoked successfully
    """
    from celery.task.control import revoke

    try:
        revoke(task_id, terminate=terminate)
        logger.info(f"Task {task_id} revoked successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to revoke task {task_id}: {str(e)}")
        return False