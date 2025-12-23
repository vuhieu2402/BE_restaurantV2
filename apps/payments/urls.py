"""
URLs for Payments app
"""
from django.urls import path
from .views import (
    PaymentMethodListView,
    PaymentProcessView,
    PaymentDetailView,
    PaymentConfirmCODView,
    PaymentCallbackView,
    VNPayCallbackView,
    VNPayReturnView,
)

app_name = 'payments'

urlpatterns = [
    # Payment methods
    path('methods/', PaymentMethodListView.as_view(), name='methods'),

    # Process payment
    path('process/', PaymentProcessView.as_view(), name='process'),

    # Payment detail
    path('<int:payment_id>/', PaymentDetailView.as_view(), name='detail'),

    # Confirm COD (staff only)
    path('<int:payment_id>/confirm-cod/', PaymentConfirmCODView.as_view(), name='confirm-cod'),

    # VNPay endpoints
    path('vnpay/callback/', VNPayCallbackView.as_view(), name='vnpay-callback'),
    path('vnpay/return/', VNPayReturnView.as_view(), name='vnpay-return'),

    # Webhook callback (generic)
    path('callback/<str:gateway>/', PaymentCallbackView.as_view(), name='callback'),
]
