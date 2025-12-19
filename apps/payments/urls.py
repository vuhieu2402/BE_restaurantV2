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
    
    # Webhook callback
    path('callback/<str:gateway>/', PaymentCallbackView.as_view(), name='callback'),
]
