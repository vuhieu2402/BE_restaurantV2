"""
Analytics URLs - URL Routing
- Define URL patterns for analytics API endpoints
- Follow REST conventions
"""
from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Orders Analytics - Get orders grouped by date
    path('orders/', views.OrdersAnalyticsView.as_view(), name='orders_analytics'),

    # Revenue Analytics - Get revenue grouped by date
    path('revenue/', views.RevenueAnalyticsView.as_view(), name='revenue_analytics'),

    # New Customers Analytics - Get new customers grouped by date
    path('new-customers/', views.NewCustomersAnalyticsView.as_view(), name='new_customers_analytics'),

    # Reservations Analytics - Get reservations grouped by date
    path('reservations/', views.ReservationsAnalyticsView.as_view(), name='reservations_analytics'),
]
