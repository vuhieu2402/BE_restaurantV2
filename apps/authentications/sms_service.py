"""
SMS Service - Hỗ trợ nhiều SMS providers
- local_sms: Mock SMS cho development (log ra console/file)
- twilio: Twilio SMS service
- vonage: Vonage (Nexmo) SMS service
"""
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class SMSService:
    """Service để gửi SMS với nhiều providers"""

    @staticmethod
    def send_sms(phone_number, message, message_type='verification'):
        """
        Gửi SMS với provider được config
        
        Args:
            phone_number: Số điện thoại nhận
            message: Nội dung tin nhắn
            message_type: Loại tin nhắn (verification, password_reset, etc.)
        
        Returns:
            tuple: (success: bool, message: str)
        """
        provider = getattr(settings, 'SMS_PROVIDER', 'local_sms')
        sms_enabled = getattr(settings, 'SMS_ENABLED', False)

        # Check rate limiting
        rate_limit_result = SMSService._check_rate_limit(phone_number, message_type)
        if not rate_limit_result['allowed']:
            return False, rate_limit_result['message']

        # Route to appropriate provider
        if provider == 'local_sms':
            return SMSService._send_local_sms(phone_number, message, message_type)
        elif provider == 'twilio':
            if not sms_enabled:
                return False, "SMS service is disabled"
            return SMSService._send_twilio_sms(phone_number, message)
        elif provider == 'vonage':
            if not sms_enabled:
                return False, "SMS service is disabled"
            return SMSService._send_vonage_sms(phone_number, message)
        else:
            logger.warning(f"Unknown SMS provider: {provider}, falling back to local_sms")
            return SMSService._send_local_sms(phone_number, message, message_type)

    @staticmethod
    def _send_local_sms(phone_number, message, message_type='verification'):
        """
        Local SMS - Mock SMS cho development
        Log ra console/file thay vì gửi thật
        """
        log_to_console = getattr(settings, 'LOCAL_SMS_LOG_TO_CONSOLE', True)
        local_sms_debug = getattr(settings, 'LOCAL_SMS_DEBUG', True)

        # Format message for logging
        log_message = f"""
{'='*60}
[SMS - LOCAL MODE]
To: {phone_number}
Type: {message_type}
Message: {message}
Time: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*60}
        """

        # Log to console if enabled
        if log_to_console:
            print(log_message)
            logger.info(f"Local SMS sent to {phone_number}: {message}")

        # TODO: Có thể lưu vào database hoặc file nếu cần
        # if local_sms_debug:
        #     LocalSMSLog.objects.create(
        #         phone_number=phone_number,
        #         message=message,
        #         message_type=message_type
        #     )

        # Update rate limit counter
        SMSService._update_rate_limit(phone_number, message_type)

        return True, "SMS đã được gửi (local mode - check console/logs)"

    @staticmethod
    def _send_twilio_sms(phone_number, message):
        """Gửi SMS qua Twilio"""
        try:
            from twilio.rest import Client

            account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
            auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
            from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None)

            if not all([account_sid, auth_token, from_number]):
                logger.error("Twilio credentials not configured")
                return False, "Twilio SMS service không được cấu hình"

            client = Client(account_sid, auth_token)
            message_obj = client.messages.create(
                body=message,
                from_=from_number,
                to=phone_number
            )

            logger.info(f"Twilio SMS sent to {phone_number}: {message_obj.sid}")
            SMSService._update_rate_limit(phone_number, 'verification')
            return True, "SMS đã được gửi qua Twilio"

        except ImportError:
            logger.error("twilio package not installed")
            return False, "Twilio package chưa được cài đặt"
        except Exception as e:
            logger.error(f"Twilio SMS error: {str(e)}")
            return False, f"Lỗi gửi SMS qua Twilio: {str(e)}"

    @staticmethod
    def _send_vonage_sms(phone_number, message):
        """Gửi SMS qua Vonage (Nexmo)"""
        try:
            import vonage

            api_key = getattr(settings, 'VONAGE_API_KEY', None)
            api_secret = getattr(settings, 'VONAGE_API_SECRET', None)
            from_number = getattr(settings, 'VONAGE_FROM_NUMBER', None)

            if not all([api_key, api_secret, from_number]):
                logger.error("Vonage credentials not configured")
                return False, "Vonage SMS service không được cấu hình"

            client = vonage.Client(key=api_key, secret=api_secret)
            sms = vonage.Sms(client)

            response_data = sms.send_message({
                'from': from_number,
                'to': phone_number,
                'text': message
            })

            if response_data['messages'][0]['status'] == '0':
                logger.info(f"Vonage SMS sent to {phone_number}")
                SMSService._update_rate_limit(phone_number, 'verification')
                return True, "SMS đã được gửi qua Vonage"
            else:
                error_msg = response_data['messages'][0]['error-text']
                logger.error(f"Vonage SMS error: {error_msg}")
                return False, f"Lỗi gửi SMS qua Vonage: {error_msg}"

        except ImportError:
            logger.error("vonage package not installed")
            return False, "Vonage package chưa được cài đặt"
        except Exception as e:
            logger.error(f"Vonage SMS error: {str(e)}")
            return False, f"Lỗi gửi SMS qua Vonage: {str(e)}"

    @staticmethod
    def _check_rate_limit(phone_number, message_type='verification'):
        """
        Kiểm tra rate limiting cho SMS
        Returns: {'allowed': bool, 'message': str}
        """
        # Get rate limit settings
        per_minute = getattr(settings, 'SMS_RATE_LIMIT_PER_MINUTE', 5)
        per_hour = getattr(settings, 'SMS_RATE_LIMIT_PER_HOUR', 50)
        per_day = getattr(settings, 'SMS_RATE_LIMIT_PER_DAY', 200)

        now = timezone.now()
        
        # Check per minute
        minute_key = f"sms_rate_{phone_number}_minute_{now.strftime('%Y%m%d%H%M')}"
        minute_count = cache.get(minute_key, 0)
        if minute_count >= per_minute:
            return {
                'allowed': False,
                'message': f'Quá nhiều yêu cầu. Vui lòng thử lại sau 1 phút.'
            }

        # Check per hour
        hour_key = f"sms_rate_{phone_number}_hour_{now.strftime('%Y%m%d%H')}"
        hour_count = cache.get(hour_key, 0)
        if hour_count >= per_hour:
            return {
                'allowed': False,
                'message': f'Quá nhiều yêu cầu trong giờ. Vui lòng thử lại sau.'
            }

        # Check per day
        day_key = f"sms_rate_{phone_number}_day_{now.strftime('%Y%m%d')}"
        day_count = cache.get(day_key, 0)
        if day_count >= per_day:
            return {
                'allowed': False,
                'message': f'Đã đạt giới hạn SMS trong ngày. Vui lòng thử lại ngày mai.'
            }

        return {'allowed': True, 'message': ''}

    @staticmethod
    def _update_rate_limit(phone_number, message_type='verification'):
        """Update rate limit counters"""
        now = timezone.now()
        
        # Update minute counter
        minute_key = f"sms_rate_{phone_number}_minute_{now.strftime('%Y%m%d%H%M')}"
        cache.set(minute_key, cache.get(minute_key, 0) + 1, 60)  # Expire in 60 seconds

        # Update hour counter
        hour_key = f"sms_rate_{phone_number}_hour_{now.strftime('%Y%m%d%H')}"
        cache.set(hour_key, cache.get(hour_key, 0) + 1, 3600)  # Expire in 1 hour

        # Update day counter
        day_key = f"sms_rate_{phone_number}_day_{now.strftime('%Y%m%d')}"
        cache.set(day_key, cache.get(day_key, 0) + 1, 86400)  # Expire in 24 hours

