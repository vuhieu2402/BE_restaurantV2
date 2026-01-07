"""
URLs for Reservations app
"""
from django.urls import path
from .views import (
    ReservationListView,
    ReservationDetailView,
    ReservationCreateView,
    ReservationDepositPaymentView,
    ReservationPaymentStatusView,
    ReservationCancelView,
    ReservationUpdateStatusView,
    ReservationSuccessView,
    ReservationPaymentReturnView,
    TableStatusView,
)

app_name = 'reservations'

urlpatterns = [
    # List reservations
    path('', ReservationListView.as_view(), name='list'),

    # Create reservation
    path('create/', ReservationCreateView.as_view(), name='create'),

    # Reservation detail
    path('<int:reservation_id>/', ReservationDetailView.as_view(), name='detail'),

    # Pay deposit
    path('<int:reservation_id>/pay-deposit/', ReservationDepositPaymentView.as_view(), name='pay-deposit'),

    # Get payment status
    path('<int:reservation_id>/payment-status/', ReservationPaymentStatusView.as_view(), name='payment-status'),

    # Update reservation status (staff/admin)
    path('<int:reservation_id>/status/', ReservationUpdateStatusView.as_view(), name='update-status'),

    # Cancel reservation (customer)
    path('<int:reservation_id>/cancel/', ReservationCancelView.as_view(), name='cancel'),

    # Check table status
    path('tables/status/', TableStatusView.as_view(), name='table-status'),

    # Success page
    path('success/', ReservationSuccessView.as_view(), name='success'),

    # Payment return page
    path('payment/return/', ReservationPaymentReturnView.as_view(), name='payment-return'),
]
