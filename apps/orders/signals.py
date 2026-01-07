"""
Signals for Order notifications
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Order
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def notify_restaurant_on_new_order(sender, instance, created, **kwargs):
    """
    Thông báo cho nhà hàng khi có đơn hàng mới
    """
    # Chỉ thông báo cho đơn hàng mới và đã có restaurant
    if not created or not instance.restaurant:
        return
    
    # Chỉ thông báo cho đơn pending
    if instance.status != 'pending':
        return
    
    try:
        restaurant = instance.restaurant
        
        # Thông tin đơn hàng
        order_info = {
            'order_number': instance.order_number,
            'order_type': instance.get_order_type_display(),
            'total': float(instance.total),
            'customer_phone': instance.delivery_phone or (instance.customer.phone_number if instance.customer else 'N/A'),
            'delivery_address': instance.delivery_address or 'N/A',
            'restaurant_name': restaurant.name,
            'restaurant_id': restaurant.id,
            'assignment_method': instance.get_assignment_method_display(),
            'distance': f"{instance.assignment_distance} km" if instance.assignment_distance else 'N/A',
            'created_at': instance.created_at.isoformat(),
        }
        
        # Log thông báo
        logger.info(
            f"Đơn hàng mới: {order_info['order_number']} - "
            f"Chi nhánh: {order_info['restaurant_name']} - "
            f"Phương thức: {order_info['assignment_method']}"
        )
        
        # TODO: Gửi thông báo qua các kênh khác nhau
        # 1. Email cho manager
        if restaurant.manager and restaurant.manager.email:
            send_email_notification(restaurant.manager.email, order_info)
        
        # 2. SMS (tích hợp sau)
        # send_sms_notification(restaurant.phone_number, order_info)
        
        # 3. Push notification (tích hợp sau)
        # send_push_notification(restaurant.manager, order_info)
        
        # 4. WebSocket/Real-time notification
        send_realtime_notification(restaurant.id, order_info)
        
    except Exception as e:
        logger.error(f"Lỗi khi gửi thông báo đơn hàng {instance.order_number}: {str(e)}")


def send_email_notification(email, order_info):
    """
    Gửi email thông báo đơn hàng mới
    """
    try:
        subject = f"Đơn hàng mới #{order_info['order_number']}"
        
        message = f"""
        Đơn hàng mới đã được phân cho chi nhánh {order_info['restaurant_name']}
        
        Mã đơn hàng: {order_info['order_number']}
        Loại đơn: {order_info['order_type']}
        Tổng tiền: {order_info['total']:,.0f} VND
        
        Thông tin giao hàng:
        - Địa chỉ: {order_info['delivery_address']}
        - SĐT: {order_info['customer_phone']}
        - Khoảng cách: {order_info['distance']}
        
        Phương thức phân: {order_info['assignment_method']}
        
        Vui lòng xác nhận và xử lý đơn hàng.
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )
        
        logger.info(f"Đã gửi email thông báo đến {email}")
        
    except Exception as e:
        logger.error(f"Lỗi khi gửi email: {str(e)}")


def send_realtime_notification(restaurant_id, order_info):
    """
    Gửi thông báo qua WebSocket cho nhân viên
    
    Args:
        restaurant_id: ID của restaurant
        order_info: Dict chứa thông tin đơn hàng
    """
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        
        # Gửi thông báo đến group của restaurant cụ thể
        async_to_sync(channel_layer.group_send)(
            f'orders_restaurant_{restaurant_id}',
            {
                'type': 'new_order',
                'order': order_info
            }
        )
        
        # Gửi thông báo đến group tất cả orders (cho admin)
        async_to_sync(channel_layer.group_send)(
            'orders_all',
            {
                'type': 'new_order',
                'order': order_info
            }
        )
        
        logger.info(f"Đã gửi WebSocket thông báo cho restaurant {restaurant_id}")
        
    except Exception as e:
        logger.error(f"Lỗi khi gửi WebSocket thông báo: {str(e)}")


@receiver(post_save, sender=Order)
def update_order_statistics(sender, instance, created, **kwargs):
    """
    Cập nhật thống kê đơn hàng cho restaurant và chain
    """
    if not created:
        return
    
    try:
        # TODO: Cập nhật cache/redis cho thống kê real-time
        # - Tổng đơn hàng trong ngày
        # - Doanh thu trong ngày
        # - Số đơn đang xử lý
        pass
    except Exception as e:
        logger.error(f"Lỗi khi cập nhật thống kê: {str(e)}")

