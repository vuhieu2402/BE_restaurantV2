"""
Signals for Payment app
Tự động xử lý logic khi payment status thay đổi
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Payment
from decimal import Decimal


@receiver(post_save, sender=Payment)
def update_order_on_payment_status_change(sender, instance, created, **kwargs):
    """
    Tự động cập nhật Order status khi Payment status thay đổi

    Business rules:
    - Payment completed -> Order confirmed (nếu đang pending)
    - Payment failed -> Order giữ nguyên (user có thể thử lại)
    - Payment refunded -> Order status = refunded
    """
    if not instance.order:
        return

    order = instance.order

    # Payment completed -> Confirm order
    if instance.status == 'completed' and not created:
        if order.status == 'pending':
            order.status = 'confirmed'
            order.notes = f"Thanh toán thành công. {order.notes or ''}"
            order.save()

            # Log payment completion time
            if not instance.paid_at:
                instance.paid_at = timezone.now()
                instance.save(update_fields=['paid_at'])

    # Payment refunded -> Refund order
    elif instance.status == 'refunded':
        if order.status not in ['refunded', 'cancelled']:
            order.status = 'refunded'
            order.notes = f"Đã hoàn tiền. {order.notes or ''}"
            order.save()

            # Release table if dine_in
            if order.order_type == 'dine_in' and order.table:
                order.table.status = 'available'
                order.table.save()

    # Payment failed -> Log to order notes (không thay đổi status)
    elif instance.status == 'failed':
        order.notes = f"Thanh toán thất bại: {instance.failure_reason or 'Không rõ lý do'}. {order.notes or ''}"
        order.save(update_fields=['notes'])


@receiver(post_save, sender=Payment)
def update_reservation_on_payment_status_change(sender, instance, created, **kwargs):
    """
    Tự động cập nhật Reservation status khi Payment status thay đổi

    Business rules:
    - Payment completed -> Reservation confirmed (nếu đang pending) + Update deposit_paid
    - Payment failed -> Reservation giữ nguyên pending (user có thể thử lại)
    - Payment refunded -> Reservation cancelled
    """
    if not instance.reservation:
        return

    reservation = instance.reservation

    # Payment completed -> Confirm reservation
    if instance.status == 'completed' and not created:
        # Update deposit_paid
        if reservation.deposit_paid != instance.amount:
            reservation.deposit_paid = instance.amount

        # Confirm reservation if pending
        if reservation.status == 'pending':
            reservation.status = 'confirmed'
            reservation.notes = f"Thanh toán cọc thành công. {reservation.notes or ''}".strip()
            reservation.save(update_fields=['status', 'deposit_paid', 'notes'])

        # Log payment completion time
        if not instance.paid_at:
            instance.paid_at = timezone.now()
            instance.save(update_fields=['paid_at'])

    # Payment refunded -> Cancel reservation
    elif instance.status == 'refunded':
        if reservation.status not in ['cancelled', 'completed']:
            reservation.status = 'cancelled'
            reservation.notes = f"Đã hoàn tiền cọc. {reservation.notes or ''}".strip()
            reservation.deposit_paid = Decimal('0.00')
            reservation.save(update_fields=['status', 'deposit_paid', 'notes'])

        # Release table if assigned
        if reservation.table:
            reservation.table.status = 'available'
            reservation.table.save()

    # Payment failed -> Log to reservation notes (không thay đổi status)
    elif instance.status == 'failed':
        reservation.notes = f"Thanh toán cọc thất bại: {instance.failure_reason or 'Không rõ lý do'}. {reservation.notes or ''}".strip()
        reservation.save(update_fields=['notes'])
