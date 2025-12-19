from django.urls import path, include
from .views import (
    CartView,
    CartItemsView,
    CartItemDetailView,
    CartBatchOperationsView,
    CartCalculateView,
    CartUpdateView,
    CartCheckoutView,
)

app_name = 'cart'

# === API View URLs ===
# Sử dụng path với as_view() cho từng endpoint
urlpatterns = [
    # Main cart endpoints
    path('', CartView.as_view(), name='cart-main'),

    # Cart items endpoints
    path('items/', CartItemsView.as_view(), name='cart-items'),
    path('items/<int:item_id>/', CartItemDetailView.as_view(), name='cart-item-detail'),

    # Batch operations
    path('batch/', CartBatchOperationsView.as_view(), name='cart-batch'),

    # Cart operations
    path('calculate/', CartCalculateView.as_view(), name='cart-calculate'),
    path('update/', CartUpdateView.as_view(), name='cart-update'),
    path('checkout/', CartCheckoutView.as_view(), name='cart-checkout'),

]