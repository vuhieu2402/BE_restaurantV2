"""
Service layer for Reservations app
Xử lý business logic cho Reservation
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
import logging
from .models import Reservation, FIXED_DEPOSIT_AMOUNT
from apps.payments.models import Payment, PaymentMethod

logger = logging.getLogger(__name__)


class ReservationService:
    """
    Service layer - Xử lý business logic cho Reservation
    """

    @transaction.atomic
    def create_reservation(self, user, data):
        """
        Tạo Reservation mới

        Args:
            user: User object (customer)
            data: Dict chứa validated data từ serializer

        Returns:
            dict: {
                'success': bool,
                'reservation': Reservation object,
                'message': str
            }
        """
        try:
            from apps.restaurants.models import Restaurant

            # Lấy restaurant
            restaurant = Restaurant.objects.get(id=data['restaurant_id'])

            # Tạo reservation
            reservation = Reservation.objects.create(
                customer=user,
                restaurant=restaurant,
                table_id=data.get('table_id'),
                reservation_date=data['reservation_date'],
                reservation_time=data['reservation_time'],
                number_of_guests=data['number_of_guests'],
                contact_name=data['contact_name'],
                contact_phone=data['contact_phone'],
                contact_email=data.get('contact_email'),
                special_requests=data.get('special_requests'),
                special_occasion=data.get('special_occasion'),
                deposit_required=FIXED_DEPOSIT_AMOUNT,
                deposit_paid=Decimal('0.00'),
                status='pending'
            )

            logger.info(f"✅ Created reservation {reservation.reservation_number}")

            return {
                'success': True,
                'reservation': reservation,
                'message': f'Đặt bàn thành công. Mã đặt bàn: {reservation.reservation_number}. '
                          f'Vui lòng thanh toán cọc {FIXED_DEPOSIT_AMOUNT:,.0f}đ để xác nhận đặt bàn.'
            }

        except Exception as e:
            logger.error(f"❌ Error creating reservation: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Lỗi khi tạo đặt bàn: {str(e)}'
            }

    @transaction.atomic
    def update_reservation_status(self, reservation_id, new_status, notes=None, staff_user=None):
        """
        Cập nhật trạng thái reservation

        Args:
            reservation_id: ID của reservation
            new_status: Trạng thái mới
            notes: Ghi chú (optional)
            staff_user: User thực hiện (optional)

        Returns:
            dict: {
                'success': bool,
                'reservation': Reservation object,
                'message': str
            }
        """
        try:
            reservation = Reservation.objects.get(id=reservation_id)

            # Update status
            old_status = reservation.status
            reservation.status = new_status

            if notes:
                reservation.notes = f"{notes} {reservation.notes or ''}".strip()

            # Check-in action
            if new_status == 'confirmed' and old_status == 'pending':
                reservation.checked_in_at = timezone.now()

            # Complete action
            elif new_status == 'completed':
                reservation.completed_at = timezone.now()

                # Release table
                if reservation.table:
                    reservation.table.status = 'available'
                    reservation.table.save()

            # Cancel action
            elif new_status == 'cancelled':
                # Release table if assigned
                if reservation.table:
                    reservation.table.status = 'available'
                    reservation.table.save()

            reservation.save()

            logger.info(f"✅ Updated reservation {reservation.reservation_number} status: {old_status} -> {new_status}")

            return {
                'success': True,
                'reservation': reservation,
                'message': f'Cập nhật trạng thái đặt bàn thành công.'
            }

        except Reservation.DoesNotExist:
            return {
                'success': False,
                'message': 'Reservation không tồn tại.'
            }
        except Exception as e:
            logger.error(f"❌ Error updating reservation status: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Lỗi khi cập nhật trạng thái: {str(e)}'
            }

    @transaction.atomic
    def cancel_reservation(self, reservation_id, cancel_reason, user):
        """
        Hủy reservation

        Args:
            reservation_id: ID của reservation
            cancel_reason: Lý do hủy
            user: User thực hiện

        Returns:
            dict: {
                'success': bool,
                'reservation': Reservation object,
                'message': str
            }
        """
        try:
            reservation = Reservation.objects.get(id=reservation_id)

            # Validate status
            if reservation.status not in ['pending', 'confirmed']:
                return {
                    'success': False,
                    'message': f"Không thể hủy reservation ở trạng thái '{reservation.get_status_display()}'."
                }

            # Check deposit paid
            if reservation.is_paid:
                return {
                    'success': False,
                    'message': 'Reservation đã thanh toán cọc. Vui lòng hoàn tiền trước khi hủy.'
                }

            # Update status
            old_status = reservation.status
            reservation.status = 'cancelled'
            reservation.notes = f"Hủy bởi {user.username}. Lý do: {cancel_reason}. {reservation.notes or ''}".strip()
            reservation.save()

            # Release table if assigned
            if reservation.table:
                reservation.table.status = 'available'
                reservation.table.save()

            logger.info(f"✅ Cancelled reservation {reservation.reservation_number}")

            return {
                'success': True,
                'reservation': reservation,
                'message': 'Hủy đặt bàn thành công.'
            }

        except Reservation.DoesNotExist:
            return {
                'success': False,
                'message': 'Reservation không tồn tại.'
            }
        except Exception as e:
            logger.error(f"❌ Error cancelling reservation: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': f'Lỗi khi hủy đặt bàn: {str(e)}'
            }


class ReservationDepositService:
    """
    Service layer - Xử lý thanh toán cọc cho Reservation
    """

    @transaction.atomic
    def create_deposit_payment(self, reservation_id, payment_method_id, user):
        """
        Tạo Payment cho deposit của Reservation

        Args:
            reservation_id: ID của reservation
            payment_method_id: ID của payment method
            user: User thực hiện thanh toán

        Returns:
            dict: {
                'success': bool,
                'payment': Payment object,
                'payment_url': str (nếu là online payment),
                'message': str
            }
        """
        try:
            # Get reservation
            reservation = Reservation.objects.select_related('restaurant').get(id=reservation_id)

            # Validate quyền truy cập
            if user.user_type not in ['staff', 'manager', 'admin']:
                if reservation.customer != user:
                    return {
                        'success': False,
                        'message': 'Bạn không có quyền thanh toán cho reservation này.'
                    }

            # Validate reservation chưa có payment
            if hasattr(reservation, 'payment') and reservation.payment:
                return {
                    'success': False,
                    'message': 'Reservation này đã có thanh toán cọc.',
                    'payment': reservation.payment
                }

            # Validate reservation status
            if reservation.status not in ['pending']:
                return {
                    'success': False,
                    'message': f'Không thể thanh toán cọc cho reservation ở trạng thái "{reservation.get_status_display()}".'
                }

            # Get payment method
            try:
                payment_method = PaymentMethod.objects.get(
                    id=payment_method_id,
                    is_active=True
                )
            except PaymentMethod.DoesNotExist:
                return {
                    'success': False,
                    'message': 'Phương thức thanh toán không tồn tại hoặc không khả dụng.'
                }

            # Create Payment
            payment = Payment.objects.create(
                reservation=reservation,
                customer=user,
                payment_method=payment_method,
                amount=reservation.deposit_required,
                currency='VND',
                status='pending'
            )

            logger.info(f"✅ Created payment {payment.payment_number} for reservation {reservation.reservation_number}")

            result = {
                'success': True,
                'payment': payment,
                'message': 'Tạo thanh toán cọc thành công.'
            }

            # Xử lý theo loại payment
            if payment_method.requires_online:
                # Online payment - cần redirect đến gateway
                payment_url = self._generate_payment_url(payment, payment_method)
                result['payment_url'] = payment_url
                result['message'] = f'Vui lòng thanh toán cọc {reservation.deposit_required:,.0f}đ qua link sau.'
            else:
                # COD hoặc thanh toán tại quầy - không áp dụng cho reservation deposit
                return {
                    'success': False,
                    'message': 'Cọc đặt bàn bắt buộc thanh toán online. Vui lòng chọn phương thức thanh toán online.'
                }

            return result

        except Reservation.DoesNotExist:
            return {
                'success': False,
                'message': 'Reservation không tồn tại hoặc bạn không có quyền.'
            }

    def _generate_payment_url(self, payment, payment_method):
        """
        Generate payment URL cho online payment gateway

        Args:
            payment: Payment object
            payment_method: PaymentMethod object

        Returns:
            str: Payment URL
        """
        from apps.payments.vnpay_service import vnpay_service

        gateway_code = payment_method.code.lower()

        if gateway_code == 'vnpay':
            try:
                # Generate VNPay payment URL
                order_info = f"Thanh toan coc dat ban {payment.reservation.reservation_number}"
                client_ip = '127.0.0.1'  # TODO: Get real client IP

                payment_url, transaction_ref = vnpay_service.generate_payment_url(
                    order_id=payment.reservation.reservation_number,
                    amount=payment.amount,
                    order_info=order_info,
                    client_ip=client_ip
                )

                # Update payment with transaction reference
                payment.transaction_id = transaction_ref
                payment.payment_gateway = 'vnpay'
                payment.status = 'processing'
                payment.save(update_fields=['transaction_id', 'payment_gateway', 'status'])

                logger.info(f"✅ Generated VNPay URL for payment {payment.payment_number}")

                return payment_url

            except Exception as e:
                logger.error(f"❌ Error generating VNPay payment URL: {str(e)}", exc_info=True)
                raise

        elif gateway_code == 'momo':
            # TODO: Integrate MoMo
            raise NotImplementedError("MoMo payment gateway chưa được tích hợp.")

        elif gateway_code == 'zalopay':
            # TODO: Integrate ZaloPay
            raise NotImplementedError("ZaloPay payment gateway chưa được tích hợp.")

        else:
            raise NotImplementedError(f"Payment gateway {gateway_code} chưa được hỗ trợ.")

    def get_payment_by_reservation(self, reservation_id, user):
        """
        Lấy payment của reservation

        Args:
            reservation_id: ID của reservation
            user: User request

        Returns:
            dict: {
                'success': bool,
                'payment': Payment object hoặc None,
                'message': str
            }
        """
        try:
            reservation = Reservation.objects.get(id=reservation_id)

            # Validate quyền truy cập
            if user.user_type not in ['staff', 'manager', 'admin']:
                if reservation.customer != user:
                    return {
                        'success': False,
                        'message': 'Bạn không có quyền truy cập reservation này.'
                    }

            # Get payment
            if hasattr(reservation, 'payment') and reservation.payment:
                return {
                    'success': True,
                    'payment': reservation.payment,
                    'message': 'Lấy thông tin thanh toán thành công.'
                }
            else:
                return {
                    'success': True,
                    'payment': None,
                    'message': 'Reservation chưa có thanh toán cọc.'
                }

        except Reservation.DoesNotExist:
            return {
                'success': False,
                'message': 'Reservation không tồn tại.'
            }


class ReservationSelector:
    """
    Selector layer - Query reservations với filters
    """

    def get_reservation_by_id(self, reservation_id, user=None):
        """
        Lấy reservation theo ID

        Args:
            reservation_id: ID của reservation
            user: User request (optional - for permission check)

        Returns:
            Reservation object hoặc None
        """
        try:
            if user and user.user_type not in ['staff', 'manager', 'admin']:
                return Reservation.objects.get(id=reservation_id, customer=user)
            return Reservation.objects.get(id=reservation_id)
        except Reservation.DoesNotExist:
            return None

    def get_customer_reservations(self, user, status=None):
        """
        Lấy danh sách reservation của customer

        Args:
            user: User object
            status: Filter by status (optional)

        Returns:
            QuerySet of Reservation
        """
        queryset = Reservation.objects.filter(customer=user)

        if status:
            queryset = queryset.filter(status=status)

        return queryset.select_related('restaurant', 'table').order_by('-created_at')

    def get_restaurant_reservations(self, restaurant_id, date=None, status=None):
        """
        Lấy danh sách reservation của nhà hàng

        Args:
            restaurant_id: ID của restaurant
            date: Filter by date (optional)
            status: Filter by status (optional)

        Returns:
            QuerySet of Reservation
        """
        queryset = Reservation.objects.filter(restaurant_id=restaurant_id)

        if date:
            queryset = queryset.filter(reservation_date=date)

        if status:
            queryset = queryset.filter(status=status)

        return queryset.select_related('customer', 'table').order_by('reservation_date', 'reservation_time')
