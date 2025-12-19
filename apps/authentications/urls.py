from django.urls import path
from . import views

app_name = 'authentications'

urlpatterns = [
    # Registration & Authentication
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),

    # Email & Phone Verification
    path('verify/email/send/', views.SendEmailVerificationView.as_view(), name='send_email_verification'),
    path('verify/phone/send/', views.SendPhoneVerificationView.as_view(), name='send_phone_verification'),
    path('verify/', views.VerifyCodeView.as_view(), name='verify_code'),

    # Password Reset
    path('password/reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('password/reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password/change/', views.ChangePasswordView.as_view(), name='change_password'),

    # Token Management
    path('token/refresh/', views.RefreshTokenView.as_view(), name='refresh_token'),
    path('token/revoke/', views.RevokeTokenView.as_view(), name='revoke_token'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('logout/all/', views.LogoutAllView.as_view(), name='logout_all'),

    # User Profile & Sessions
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),
    path('sessions/', views.UserSessionsView.as_view(), name='user_sessions'),
]