"""
Authentication Views - API Layer
- Chỉ nhận HTTP request và validate cơ bản
- Gọi Service layer
- Format response theo chuẩn
- KHÔNG chứa business logic
- KHÔNG query database trực tiếp
- KHÔNG validate business rules
"""
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from drf_spectacular.utils import extend_schema
from apps.api.mixins import StandardResponseMixin
from apps.api.response import ApiResponse
from django.contrib.auth import get_user_model
from .services import AuthService, RegistrationService, VerificationService, PasswordService
from .serializers import (
    LoginSerializer, RegisterSerializer, EmailVerificationSerializer,
    PhoneVerificationSerializer, VerifyCodeSerializer, PasswordResetSerializer,
    PasswordResetConfirmSerializer, ChangePasswordSerializer,
    RefreshTokenSerializer, RevokeTokenSerializer, UserSerializer,
    UserProfileUpdateSerializer, SessionSerializer
)

User = get_user_model()


class RegisterView(StandardResponseMixin, GenericAPIView):
    """
    View cho user registration
    Template chuẩn cho API View
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    @extend_schema(
        summary="Register new user",
        description="Đăng ký tài khoản mới với email hoặc số điện thoại"
    )
    def post(self, request, *args, **kwargs):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # Validate request data using serializer
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # ❌ KHÔNG validate business rules ở đây
            # ❌ KHÔNG check unique constraints ở đây

            # ✅ Chỉ gọi service
            registration_service = RegistrationService()
            result = registration_service.register_user(serializer.validated_data)

            if result['success']:
                # Serialize user object trước khi trả về
                response_data = result['data'].copy()
                if 'user' in response_data:
                    user = response_data.pop('user')
                    response_data['user'] = UserSerializer(user).data
                
                return ApiResponse.created(
                    data=response_data,
                    message=result['message']
                )
            else:
                return ApiResponse.validation_error(
                    message=result['message'],
                    errors=result.get('errors')
                )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LoginView(StandardResponseMixin, GenericAPIView):
    """
    View cho user login
    Template chuẩn cho API View
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    @extend_schema(
        summary="Login user",
        description="Đăng nhập với email/số điện thoại và mật khẩu"
    )
    def post(self, request, *args, **kwargs):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # Validate request data using serializer
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # ❌ KHÔNG validate business rules ở đây
            # ❌ KHÔNG check unique constraints ở đây

            # ✅ Chỉ gọi service
            auth_service = AuthService()
            device_info = auth_service.generate_device_info(request)

            # Authenticate user
            auth_result = auth_service.authenticate_user(
                identifier=serializer.validated_data['identifier'],
                password=serializer.validated_data['password']
            )

            if not auth_result['success']:
                return ApiResponse.unauthorized(message=auth_result['message'])

            # Generate tokens
            token_result = auth_service.generate_tokens(
                user=auth_result['data']['user'],
                device_info=device_info
            )

            # Get user sessions
            sessions_result = auth_service.get_user_sessions(auth_result['data']['user'])

            if token_result['success'] and sessions_result['success']:
                # Serialize sessions before returning
                serialized_sessions = [
                    SessionSerializer(session).data 
                    for session in sessions_result['data']
                ]
                
                return ApiResponse.success(
                    data={
                        'user': UserSerializer(auth_result['data']['user']).data,
                        'access_token': token_result['data']['access_token'],
                        'refresh_token': token_result['data']['refresh_token'],
                        'access_token_expires': token_result['data']['access_token_expires'],
                        'refresh_token_expires': token_result['data']['refresh_token_expires']
                    },
                    message="Đăng nhập thành công"
                )
            else:
                return ApiResponse.error(
                    message="Đăng nhập thất bại, vui lòng thử lại"
                )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SendEmailVerificationView(StandardResponseMixin, GenericAPIView):
    """
    View cho sending email verification
    Template chuẩn cho API View
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailVerificationSerializer

    @extend_schema(
        summary="Send email verification",
        description="Gửi mã xác thực qua email"
    )
    def post(self, request, *args, **kwargs):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # Validate request data using serializer
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # ✅ Chỉ gọi service
            verification_service = VerificationService()
            success, message = verification_service.send_email_verification(
                email=serializer.validated_data['email']
            )

            if success:
                return ApiResponse.success(message=message)
            else:
                return ApiResponse.bad_request(message=message)

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SendPhoneVerificationView(StandardResponseMixin, GenericAPIView):
    """
    View cho sending phone verification
    Template chuẩn cho API View
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PhoneVerificationSerializer

    @extend_schema(
        summary="Send SMS verification",
        description="Gửi mã xác thực qua SMS"
    )
    def post(self, request, *args, **kwargs):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # Validate request data using serializer
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # ✅ Chỉ gọi service
            verification_service = VerificationService()
            success, message = verification_service.send_phone_verification(
                phone_number=serializer.validated_data['phone_number']
            )

            if success:
                return ApiResponse.success(message=message)
            else:
                return ApiResponse.bad_request(message=message)

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerifyCodeView(StandardResponseMixin, GenericAPIView):
    """
    View cho code verification
    Template chuẩn cho API View
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = VerifyCodeSerializer

    @extend_schema(
        summary="Verify code",
        description="Xác thực mã email/SMS"
    )
    def post(self, request, *args, **kwargs):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # Validate request data using serializer
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # ✅ Chỉ gọi service
            verification_service = VerificationService()
            result = verification_service.verify_code(
                email=serializer.validated_data.get('email'),
                phone_number=serializer.validated_data.get('phone_number'),
                code=serializer.validated_data['code'],
                verification_type=serializer.validated_data['verification_type']
            )

            if result['success']:
                return ApiResponse.success(message=result['message'])
            else:
                return ApiResponse.bad_request(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PasswordResetView(StandardResponseMixin, GenericAPIView):
    """
    View cho password reset request
    Template chuẩn cho API View
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetSerializer

    @extend_schema(
        summary="Request password reset",
        description="Gửi mã đặt lại mật khẩu qua email/SMS"
    )
    def post(self, request, *args, **kwargs):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # Validate request data using serializer
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # ✅ Chỉ gọi service
            verification_service = VerificationService()
            result = verification_service.send_password_reset(
                email=serializer.validated_data.get('email'),
                phone_number=serializer.validated_data.get('phone_number')
            )

            if result['success']:
                return ApiResponse.success(message=result['message'])
            else:
                return ApiResponse.bad_request(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PasswordResetConfirmView(StandardResponseMixin, GenericAPIView):
    """
    View cho password reset confirmation
    Template chuẩn cho API View
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    @extend_schema(
        summary="Confirm password reset",
        description="Đặt lại mật khẩu với mã xác thực"
    )
    def post(self, request, *args, **kwargs):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # Validate request data using serializer
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # ✅ Chỉ gọi service
            password_service = PasswordService()
            result = password_service.reset_password(
                email=serializer.validated_data.get('email'),
                phone_number=serializer.validated_data.get('phone_number'),
                code=serializer.validated_data['code'],
                new_password=serializer.validated_data['new_password']
            )

            if result['success']:
                return ApiResponse.success(message=result['message'])
            else:
                return ApiResponse.bad_request(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChangePasswordView(StandardResponseMixin, GenericAPIView):
    """
    View cho password change (authenticated)
    Template chuẩn cho API View
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    @extend_schema(
        summary="Change password",
        description="Đổi mật khẩu cho người dùng đã đăng nhập"
    )
    def post(self, request, *args, **kwargs):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # Validate request data using serializer
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # ✅ Chỉ gọi service
            password_service = PasswordService()
            result = password_service.change_password(
                user=request.user,
                old_password=serializer.validated_data['old_password'],
                new_password=serializer.validated_data['new_password']
            )

            if result['success']:
                return ApiResponse.success(message=result['message'])
            else:
                return ApiResponse.bad_request(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RefreshTokenView(StandardResponseMixin, GenericAPIView):
    """
    View cho refresh access token
    Template chuẩn cho API View
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = RefreshTokenSerializer

    @extend_schema(
        summary="Refresh access token",
        description="Làm mới access token với refresh token"
    )
    def post(self, request, *args, **kwargs):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # Validate request data using serializer
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # ✅ Chỉ gọi service
            auth_service = AuthService()
            device_info = auth_service.generate_device_info(request)

            result = auth_service.refresh_token(
                refresh_token=serializer.validated_data['refresh_token'],
                device_info=device_info
            )

            if result['success']:
                return ApiResponse.success(
                    data=result['data'],
                    message=result['message']
                )
            else:
                return ApiResponse.unauthorized(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RevokeTokenView(StandardResponseMixin, GenericAPIView):
    """
    View cho revoke refresh token (logout)
    Template chuẩn cho API View
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RevokeTokenSerializer

    @extend_schema(
        summary="Revoke refresh token",
        description="Thu hồi refresh token (đăng xuất)"
    )
    def post(self, request, *args, **kwargs):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # Validate request data using serializer
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # ✅ Chỉ gọi service
            auth_service = AuthService()
            result = auth_service.revoke_refresh_token(
                refresh_token=serializer.validated_data['refresh_token']
            )

            if result['success']:
                return ApiResponse.success(message=result['message'])
            else:
                return ApiResponse.bad_request(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogoutView(StandardResponseMixin, APIView):
    """
    View cho logout từ thiết bị hiện tại
    Template chuẩn cho API View
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Logout from current device",
        description="Đăng xuất khỏi thiết bị hiện tại",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": True},
                    "message": {"type": "string", "example": "Đăng xuất thành công"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "device_name": {"type": "string", "example": "Chrome on Windows"},
                            "logged_out_at": {"type": "string", "format": "date-time"}
                        }
                    }
                }
            }
        }
    )
    def post(self, request, *args, **kwargs):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Chỉ gọi service
            auth_service = AuthService()
            result = auth_service.revoke_current_session(request)

            if result['success']:
                # Clear refresh token cookie if it exists
                response = self.success_response(
                    data=result.get('data'),
                    message=result['message']
                )

                # Clear refresh token cookie
                response.delete_cookie('refresh_token', path='/', samesite='Lax')

                return response
            else:
                return self.error_response(message=result['message'])

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        summary="Logout from current device (GET method)",
        description="Đăng xuất khỏi thiết bị hiện tại (phương thức GET cho dễ sử dụng)"
    )
    def get(self, request, *args, **kwargs):
        """
        GET method - Cho phép logout bằng GET request (thường cho web)
        """
        return self.post(request, *args, **kwargs)


class LogoutAllView(StandardResponseMixin, APIView):
    """
    View cho logout from all devices
    Template chuẩn cho API View
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Logout from all devices",
        description="Đăng xuất khỏi tất cả thiết bị"
    )
    def post(self, request, *args, **kwargs):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Chỉ gọi service
            auth_service = AuthService()
            result = auth_service.revoke_all_user_sessions(user=request.user)

            if result['success']:
                return ApiResponse.success(message=result['message'])
            else:
                return ApiResponse.bad_request(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserSessionsView(StandardResponseMixin, APIView):
    """
    View cho listing user sessions
    Template chuẩn cho API View
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get user sessions",
        description="Xem danh sách các session đang hoạt động"
    )
    def get(self, request, *args, **kwargs):
        """
        GET method - View chỉ làm 2 việc:
        1. Nhận request và validate cơ bản
        2. Gọi service/selector và return response
        """
        try:
            # ❌ KHÔNG viết business logic ở đây
            # ❌ KHÔNG query database trực tiếp
            # ❌ KHÔNG validate business rules

            # ✅ Chỉ gọi service
            auth_service = AuthService()
            result = auth_service.get_user_sessions(user=request.user)

            # Serialize sessions before returning
            if result['success']:
                serialized_sessions = [
                    SessionSerializer(session).data 
                    for session in result['data']
                ]
                return ApiResponse.success(
                    data=serialized_sessions,
                    message=result['message']
                )
            else:
                return ApiResponse.error(
                    message=result['message'],
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserProfileView(StandardResponseMixin, APIView):
    """
    View cho user profile
    Template chuẩn cho API View
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get user profile",
        description="Xem thông tin người dùng hiện tại"
    )
    def get(self, request, *args, **kwargs):
        """
        GET method - View chỉ làm 2 việc:
        1. Nhận request và validate cơ bản
        2. Gọi service/selector và return response
        """
        try:
            # ❌ KHÔNG viết business logic ở đây
            # ❌ KHÔNG query database trực tiếp
            # ❌ KHÔNG validate business rules

            # ✅ Direct response for simple GET
            return ApiResponse.success(
                data=UserSerializer(request.user).data,
                message="Lấy thông tin người dùng thành công"
            )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        summary="Update user profile",
        description="Cập nhật thông tin người dùng"
    )
    def patch(self, request, *args, **kwargs):
        """
        PATCH method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Validate request level (chỉ required fields)
            # For PATCH, we allow partial updates, so no required fields check needed

            # ❌ KHÔNG validate business rules ở đây
            # ❌ KHÔNG check unique constraints ở đây

            # ✅ Sử dụng UserProfileUpdateSerializer cho việc cập nhật profile
            serializer = UserProfileUpdateSerializer(
                request.user,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return ApiResponse.success(
                data=serializer.data,
                message="Cập nhật thông tin thành công"
            )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )