from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils import timezone
from django.core.cache import cache
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch, MagicMock
from .models import VerificationCode, RefreshTokenSession
from .services import AuthService, VerificationService, PasswordService
from .selectors import UserSelector
from .sms_service import SMSService

User = get_user_model()


class VerificationCodeModelTests(TestCase):
    """Test cho VerificationCode model"""

    def test_generate_code(self):
        """Test tạo mã xác thực"""
        code = VerificationCode.generate_code()
        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_create_verification(self):
        """Test tạo mã xác thực mới"""
        email = "test@example.com"
        verification = VerificationCode.create_verification(email=email)

        self.assertEqual(verification.email, email)
        self.assertEqual(verification.verification_type, 'email')
        self.assertEqual(len(verification.code), 6)
        self.assertFalse(verification.is_verified)
        self.assertFalse(verification.is_used)

    def test_verify_code_success(self):
        """Test xác thực mã thành công"""
        email = "test@example.com"
        verification = VerificationCode.create_verification(email=email)

        success, message = verification.verify(verification.code)

        self.assertTrue(success)
        self.assertTrue(verification.is_verified)
        self.assertIsNotNone(verification.verified_at)

    def test_verify_code_wrong(self):
        """Test xác thực mã sai"""
        email = "test@example.com"
        verification = VerificationCode.create_verification(email=email)

        success, message = verification.verify("000000")

        self.assertFalse(success)
        self.assertFalse(verification.is_verified)
        self.assertEqual(verification.attempts, 1)

    def test_is_expired(self):
        """Test kiểm tra mã hết hạn"""
        # Tạo mã đã hết hạn
        past_time = timezone.now() - timezone.timedelta(hours=1)
        verification = VerificationCode.objects.create(
            email="test@example.com",
            code="123456",
            expires_at=past_time
        )

        self.assertTrue(verification.is_expired)
        self.assertFalse(verification.is_valid)

    def test_max_attempts(self):
        """Test vượt quá số lần thử"""
        email = "test@example.com"
        verification = VerificationCode.create_verification(email=email)
        verification.max_attempts = 2

        # Thử sai 2 lần
        verification.verify("000000")
        success, message = verification.verify("000000")

        self.assertFalse(success)
        self.assertIn("vượt quá số lần thử", message)


class AuthServiceTests(TransactionTestCase):
    """Test cho AuthService"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
            is_verified=True
        )

    def test_generate_tokens(self):
        """Test tạo JWT tokens"""
        device_info = {'name': 'Test Device'}
        tokens = AuthService.generate_tokens(self.user, device_info)

        self.assertIn('access_token', tokens)
        self.assertIn('refresh_token', tokens)
        self.assertIn('access_token_expires', tokens)
        self.assertIn('refresh_token_expires', tokens)

        # Kiểm tra session được tạo
        session = RefreshTokenSession.objects.filter(user=self.user).first()
        self.assertIsNotNone(session)
        self.assertEqual(session.refresh_token, tokens['refresh_token'])

    def test_get_client_ip(self):
        """Test lấy client IP"""
        # Mock request
        request = type('MockRequest', (), {
            'META': {
                'REMOTE_ADDR': '127.0.0.1'
            }
        })()

        ip = AuthService.get_client_ip(request)
        self.assertEqual(ip, '127.0.0.1')

    def test_generate_device_info(self):
        """Test tạo device info"""
        request = type('MockRequest', (), {
            'META': {
                'HTTP_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'REMOTE_ADDR': '127.0.0.1'
            }
        })()

        device_info = AuthService.generate_device_info(request)

        self.assertIn('name', device_info)
        self.assertIn('browser', device_info)
        self.assertIn('os', device_info)
        self.assertIn('ip_address', device_info)


class VerificationServiceTests(TestCase):
    """Test cho VerificationService"""

    @patch('apps.auth.services.send_mail')
    def test_send_email_verification(self, mock_send_mail):
        """Test gửi email verification"""
        email = "test@example.com"
        service = VerificationService()
        success, message = service.send_email_verification(email)

        self.assertTrue(success)
        self.assertIn("được gửi", message)
        mock_send_mail.assert_called_once()

    def test_create_verification_cancels_old_codes(self):
        """Test tạo mã mới hủy mã cũ"""
        email = "test@example.com"

        # Tạo mã cũ
        old_verification = VerificationCode.create_verification(email=email)

        # Tạo mã mới
        new_verification = VerificationCode.create_verification(email=email)

        # Mã cũ phải bị đánh dấu là used
        old_verification.refresh_from_db()
        self.assertTrue(old_verification.is_used)

        # Mã mới phải active
        self.assertFalse(new_verification.is_used)

    def test_verify_code_with_service(self):
        """Test xác thực mã qua service"""
        email = "test@example.com"
        verification = VerificationCode.create_verification(email=email)

        service = VerificationService()
        result = service.verify_code(
            email=email,
            code=verification.code,
            verification_type='email'
        )

        self.assertTrue(result['success'])
        self.assertIn("thành công", result['message'])


class AuthenticationAPITests(APITestCase):
    """Test cho authentication API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'TestPass123!',
            'password_confirm': 'TestPass123!',
            'first_name': 'Test',
            'last_name': 'User'
        }

    @patch('apps.auth.services.send_mail')
    def test_register_success(self, mock_send_mail):
        """Test đăng ký thành công"""
        response = self.client.post('/api/auth/register/', self.user_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('verification_sent', response.data['data'])

        # Kiểm tra user được tạo
        user = User.objects.get(email='test@example.com')
        self.assertEqual(user.username, 'testuser')
        self.assertFalse(user.is_verified)  # Chưa xác thực

    def test_register_password_mismatch(self):
        """Test đăng ký mật khẩu không khớp"""
        data = self.user_data.copy()
        data['password_confirm'] = 'different'

        response = self.client.post('/api/auth/register/', data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_email(self):
        """Test đăng ký email đã tồn tại"""
        # Tạo user trước
        User.objects.create_user(
            username='existing',
            email='test@example.com',
            password='TestPass123!'
        )

        response = self.client.post('/api/auth/register/', self.user_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Email đã được sử dụng', str(response.data))

    def test_login_success(self):
        """Test đăng nhập thành công"""
        # Tạo user đã xác thực
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            is_verified=True
        )

        login_data = {
            'identifier': 'test@example.com',
            'password': 'TestPass123!'
        }

        response = self.client.post('/api/auth/login/', login_data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data['data'])
        self.assertIn('refresh_token', response.data['data'])

    def test_login_unverified_user(self):
        """Test đăng nhập user chưa xác thực"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            is_verified=False  # Chưa xác thực
        )

        login_data = {
            'identifier': 'test@example.com',
            'password': 'TestPass123!'
        }

        response = self.client.post('/api/auth/login/', login_data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('chưa được xác thực', response.data['message'])

    def test_login_wrong_password(self):
        """Test đăng nhập sai mật khẩu"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            is_verified=True
        )

        login_data = {
            'identifier': 'test@example.com',
            'password': 'wrongpassword'
        }

        response = self.client.post('/api/auth/login/', login_data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('Mật khẩu không đúng', response.data['message'])

    @patch('apps.auth.services.send_mail')
    def test_send_email_verification_endpoint(self, mock_send_mail):
        """Test endpoint gửi email verification"""
        data = {'email': 'test@example.com'}

        response = self.client.post('/api/auth/verify/email/send/', data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('được gửi', response.data['message'])

    @patch('apps.auth.services.send_mail')
    def test_verify_code_endpoint(self, mock_send_mail):
        """Test endpoint xác thực mã"""
        # Tạo verification code
        verification = VerificationCode.create_verification(email='test@example.com')

        data = {
            'email': 'test@example.com',
            'code': verification.code,
            'verification_type': 'email'
        }

        response = self.client.post('/api/auth/verify/', data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('thành công', response.data['message'])

    def test_protected_endpoint_requires_auth(self):
        """Test protected endpoint yêu cầu authentication"""
        response = self.client.get('/api/auth/profile/')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_protected_endpoint_with_token(self):
        """Test protected endpoint với valid token"""
        # Tạo và login user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            is_verified=True
        )

        login_data = {
            'identifier': 'test@example.com',
            'password': 'TestPass123!'
        }

        login_response = self.client.post('/api/auth/login/', login_data)
        token = login_response.data['data']['access_token']

        # Sử dụng token để gọi protected endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/auth/profile/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['email'], 'test@example.com')


class PasswordServiceTests(TestCase):
    """Test cho PasswordService"""

    def test_validate_password_strength_valid(self):
        """Test validate password strength với password hợp lệ"""
        is_valid, message = PasswordService.validate_password_strength("TestPass123")
        self.assertTrue(is_valid)
        self.assertEqual(message, 'Mật khẩu hợp lệ')

    def test_validate_password_strength_too_short(self):
        """Test validate password quá ngắn"""
        is_valid, message = PasswordService.validate_password_strength("Test1")
        self.assertFalse(is_valid)
        self.assertIn('8 ký tự', message)

    def test_validate_password_strength_no_uppercase(self):
        """Test validate password thiếu chữ hoa"""
        is_valid, message = PasswordService.validate_password_strength("testpass123")
        self.assertFalse(is_valid)
        self.assertIn('chữ hoa', message)

    def test_validate_password_strength_no_lowercase(self):
        """Test validate password thiếu chữ thường"""
        is_valid, message = PasswordService.validate_password_strength("TESTPASS123")
        self.assertFalse(is_valid)
        self.assertIn('chữ thường', message)

    def test_validate_password_strength_no_digit(self):
        """Test validate password thiếu số"""
        is_valid, message = PasswordService.validate_password_strength("TestPass")
        self.assertFalse(is_valid)
        self.assertIn('số', message)

    def test_generate_secure_password(self):
        """Test generate secure password"""
        password = PasswordService.generate_secure_password()
        self.assertGreaterEqual(len(password), 12)
        
        # Validate generated password
        is_valid, _ = PasswordService.validate_password_strength(password)
        self.assertTrue(is_valid)


class UserSelectorCacheTests(TestCase):
    """Test cho UserSelector caching"""

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            username='cachetest',
            email='cache@example.com',
            phone_number='+84123456789',
            password='TestPass123!'
        )

    def tearDown(self):
        cache.clear()

    def test_get_user_by_email_caching(self):
        """Test caching cho get_user_by_email"""
        # First call - should hit database
        user1 = UserSelector.get_user_by_email('cache@example.com')
        self.assertEqual(user1.id, self.user.id)

        # Second call - should hit cache
        with patch('apps.auth.selectors.User.objects') as mock_objects:
            user2 = UserSelector.get_user_by_email('cache@example.com')
            self.assertEqual(user2.id, self.user.id)
            # Should not call get() again
            mock_objects.get.assert_not_called()

    def test_get_user_by_phone_caching(self):
        """Test caching cho get_user_by_phone"""
        # First call
        user1 = UserSelector.get_user_by_phone('+84123456789')
        self.assertEqual(user1.id, self.user.id)

        # Second call - should hit cache
        with patch('apps.auth.selectors.User.objects') as mock_objects:
            user2 = UserSelector.get_user_by_phone('+84123456789')
            self.assertEqual(user2.id, self.user.id)
            mock_objects.get.assert_not_called()

    def test_check_email_exists_caching(self):
        """Test caching cho check_email_exists"""
        # First call
        exists1 = UserSelector.check_email_exists('cache@example.com')
        self.assertTrue(exists1)

        # Second call - should hit cache
        with patch('apps.auth.selectors.User.objects') as mock_objects:
            exists2 = UserSelector.check_email_exists('cache@example.com')
            self.assertTrue(exists2)
            mock_objects.filter.assert_not_called()

    def test_invalidate_user_cache(self):
        """Test invalidate cache"""
        # Cache user
        UserSelector.get_user_by_email('cache@example.com')
        
        # Verify cached
        cache_key = "user_email_cache@example.com"
        self.assertIsNotNone(cache.get(cache_key))
        
        # Invalidate
        UserSelector.invalidate_user_cache(self.user)
        
        # Should be cleared
        self.assertIsNone(cache.get(cache_key))


class SMSServiceTests(TestCase):
    """Test cho SMSService"""

    @override_settings(SMS_PROVIDER='local_sms', LOCAL_SMS_LOG_TO_CONSOLE=True)
    def test_send_local_sms(self):
        """Test gửi local SMS"""
        success, message = SMSService.send_sms(
            phone_number='+84123456789',
            message='Test message',
            message_type='verification'
        )
        self.assertTrue(success)
        self.assertIn('local mode', message.lower())

    @override_settings(SMS_PROVIDER='local_sms')
    def test_sms_rate_limiting(self):
        """Test SMS rate limiting"""
        phone_number = '+84123456789'
        
        # Send multiple SMS quickly
        for i in range(6):  # More than per_minute limit (5)
            success, msg = SMSService.send_sms(
                phone_number=phone_number,
                message=f'Test {i}',
                message_type='verification'
            )
            if i < 5:
                self.assertTrue(success)
            else:
                # Should be rate limited
                self.assertFalse(success)
                self.assertIn('phút', msg)

    def tearDown(self):
        cache.clear()


class VerificationRateLimitTests(TestCase):
    """Test cho verification rate limiting"""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    @patch('apps.auth.services.send_mail')
    def test_email_verification_rate_limit(self, mock_send_mail):
        """Test rate limiting cho email verification"""
        service = VerificationService()
        email = 'ratelimit@example.com'

        # Send multiple verification requests
        results = []
        for i in range(4):  # More than per_10min limit (3)
            result = service.send_email_verification(email)
            results.append(result)

        # First 3 should succeed
        self.assertTrue(results[0][0])
        self.assertTrue(results[1][0])
        self.assertTrue(results[2][0])
        
        # 4th should be rate limited
        self.assertFalse(results[3][0])
        self.assertIn('10 phút', results[3][1])

    @override_settings(SMS_PROVIDER='local_sms')
    def test_phone_verification_rate_limit(self):
        """Test rate limiting cho phone verification"""
        service = VerificationService()
        phone = '+84123456789'

        # Send multiple verification requests
        results = []
        for i in range(4):  # More than per_10min limit (3)
            result = service.send_phone_verification(phone)
            results.append(result)

        # First 3 should succeed
        self.assertTrue(results[0][0])
        self.assertTrue(results[1][0])
        self.assertTrue(results[2][0])
        
        # 4th should be rate limited
        self.assertFalse(results[3][0])
        self.assertIn('10 phút', results[3][1])

    def tearDown(self):
        cache.clear()
