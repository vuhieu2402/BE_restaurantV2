"""
URLs for Orders app
"""
from django.urls import path
from .views import (
    CalculateDeliveryView,
    OrderCheckoutView,
    OrderListView,
    OrderDetailView,
    OrderUpdateStatusView,
    OrderCancelView,
)

app_name = 'orders'

urlpatterns = [
    # Calculate delivery fee
    path('calculate-delivery/', CalculateDeliveryView.as_view(), name='calculate-delivery'),
    
    # Checkout - tạo order từ cart
    path('checkout/', OrderCheckoutView.as_view(), name='checkout'),
    
    # List orders
    path('', OrderListView.as_view(), name='list'),
    
    # Order detail
    path('<int:order_id>/', OrderDetailView.as_view(), name='detail'),
    
    # Update order status (staff/admin)
    path('<int:order_id>/status/', OrderUpdateStatusView.as_view(), name='update-status'),
    
    # Cancel order (customer)
    path('<int:order_id>/cancel/', OrderCancelView.as_view(), name='cancel'),
]
