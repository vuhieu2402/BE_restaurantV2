"""
Service layer for Orders app
Xử lý business logic và operations cho Order
"""
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Order, OrderItem
from apps.restaurants.models import Restaurant, Table
from apps.restaurants.utils import calculate_distance
from apps.cart.models import Cart


class OrderService:
    """
    Service layer - Xử lý business logic cho Order
    """
    
    def calculate_delivery_fee_and_distance(self, restaurant_id, delivery_latitude, delivery_longitude):
        """
        Tính phí giao hàng và khoảng cách
        
        Args:
            restaurant_id: ID restaurant
            delivery_latitude: Vĩ độ giao hàng
            delivery_longitude: Kinh độ giao hàng
        
        Returns:
            dict: {
                'success': bool,
                'distance_km': Decimal,
                'delivery_fee': Decimal,
                'is_in_delivery_radius': bool,
                'estimated_time': int (minutes),
                'restaurant': Restaurant object,
                'message': str
            }
        """
        try:
            # Get restaurant
            restaurant = Restaurant.objects.get(
                id=restaurant_id,
                is_active=True,
                latitude__isnull=False,
                longitude__isnull=False
            )
        except Restaurant.DoesNotExist:
            return {
                'success': False,
                'message': 'Chi nhánh không tồn tại hoặc không có thông tin tọa độ.'
            }
        
        # Tính khoảng cách
        distance = calculate_distance(
            float(delivery_latitude),
            float(delivery_longitude),
            float(restaurant.latitude),
            float(restaurant.longitude)
        )
        distance_decimal = Decimal(str(distance))
        
        # Kiểm tra trong delivery_radius
        is_in_radius = distance_decimal <= restaurant.delivery_radius
        
        if not is_in_radius:
            return {
                'success': False,
                'distance_km': distance_decimal,
                'is_in_delivery_radius': False,
                'message': f'Địa chỉ nằm ngoài bán kính giao hàng ({restaurant.delivery_radius}km).'
            }
        
        # Tính phí giao hàng
        try:
            config = restaurant.delivery_pricing_config
            base_fee = config.base_fee
            per_km_fee = config.per_km_fee
            free_distance = config.free_distance_km
            
            # Check surge pricing
            if config.is_surge_time():
                per_km_fee = per_km_fee * config.surge_multiplier
        except:
            # Fallback
            base_fee = restaurant.delivery_fee
            per_km_fee = Decimal('5000.00')
            free_distance = Decimal('0.00')
        
        # Tính phí
        chargeable_distance = max(Decimal('0.00'), distance_decimal - free_distance)
        delivery_fee = base_fee + (chargeable_distance * per_km_fee)
        delivery_fee = delivery_fee.quantize(Decimal('0.01'))
        
        # Estimate time (giả sử 30km/h + 15 phút chuẩn bị)
        travel_time = int((float(distance_decimal) / 30) * 60)  # minutes
        preparation_time = 15  # minutes
        estimated_time = travel_time + preparation_time
        
        return {
            'success': True,
            'distance_km': distance_decimal,
            'delivery_fee': delivery_fee,
            'is_in_delivery_radius': True,
            'estimated_time': estimated_time,
            'restaurant': restaurant,
            'message': 'Tính toán thành công.'
        }
    
    def validate_order_creation(self, user, cart, order_data):
        """
        Validate business rules trước khi tạo order
        
        Args:
            user: User object
            cart: Cart object
            order_data: Dict chứa thông tin order
        
        Returns:
            dict: {'success': bool, 'errors': dict, 'message': str}
        """
        errors = {}
        
        # 1. Validate cart không empty
        if not cart.items.exists():
            errors['cart'] = 'Giỏ hàng trống.'
        
        # 2. Validate restaurant_id
        restaurant_id = order_data.get('restaurant_id')
        
        # 3. Validate restaurant exists và active
        try:
            restaurant = Restaurant.objects.select_related('chain').get(
                id=restaurant_id, 
                is_active=True
            )
            
            # 4. Validate restaurant match với cart items
            # Nếu menu items thuộc chain: cho phép chọn bất kỳ restaurant nào trong chain
            # Nếu menu items thuộc restaurant độc lập: phải match chính xác
            first_cart_item = cart.items.select_related('chain', 'restaurant').first()
            if first_cart_item:
                if first_cart_item.chain:
                    # Menu items thuộc chain - cho phép chọn bất kỳ restaurant nào trong chain
                    if restaurant.chain_id != first_cart_item.chain_id:
                        errors['restaurant'] = f'Vui lòng chọn chi nhánh thuộc chuỗi "{first_cart_item.chain.name}".'
                else:
                    # Menu items thuộc restaurant độc lập - phải match chính xác
                    if restaurant.id != first_cart_item.restaurant_id:
                        errors['restaurant'] = f'Vui lòng chọn chi nhánh "{first_cart_item.restaurant.name}".'
            
            # 5. Check minimum order
            if cart.subtotal < restaurant.minimum_order:
                errors['subtotal'] = f'Đơn hàng tối thiểu là {restaurant.minimum_order:,.0f}đ.'
        except Restaurant.DoesNotExist:
            errors['restaurant'] = 'Chi nhánh không tồn tại hoặc không hoạt động.'
            restaurant = None
        
        # 6. Validate tất cả items trong cart cùng 1 chain/restaurant
        chains = cart.items.values_list('chain_id', flat=True).distinct()
        restaurants_in_cart = cart.items.values_list('restaurant_id', flat=True).distinct()
        
        # Nếu có chain: tất cả phải cùng chain
        if any(chains):
            chains_filtered = [c for c in chains if c is not None]
            if len(chains_filtered) > 1:
                errors['cart'] = 'Giỏ hàng chứa món từ nhiều chuỗi nhà hàng khác nhau.'
        # Nếu không có chain (restaurant độc lập): tất cả phải cùng restaurant
        elif len(restaurants_in_cart) > 1:
            errors['cart'] = 'Giỏ hàng chứa món từ nhiều chi nhánh. Vui lòng chỉ giữ món từ 1 chi nhánh.'
        
        # 7. Validate menu items vẫn available
        unavailable_items = []
        for item in cart.items.all():
            if item.menu_item and not item.menu_item.is_available:
                unavailable_items.append(item.menu_item.name)
        
        if unavailable_items:
            errors['items'] = f"Các món sau không còn bán: {', '.join(unavailable_items)}"
        
        # 8. Validate theo order_type
        order_type = order_data.get('order_type')
        
        if order_type == 'delivery' and restaurant:
            # Validate địa chỉ trong delivery_radius
            delivery_lat = order_data.get('delivery_latitude')
            delivery_lng = order_data.get('delivery_longitude')
            
            if delivery_lat and delivery_lng:
                calc_result = self.calculate_delivery_fee_and_distance(
                    restaurant_id,
                    delivery_lat,
                    delivery_lng
                )
                
                if not calc_result['success']:
                    errors['delivery_address'] = calc_result['message']
        
        elif order_type == 'dine_in':
            # Validate table
            table_id = order_data.get('table_id')
            if table_id:
                try:
                    table = Table.objects.get(id=table_id, is_active=True)
                    if table.restaurant_id != restaurant_id:
                        errors['table'] = 'Bàn không thuộc chi nhánh đã chọn.'
                    if table.status not in ['available', 'reserved']:
                        errors['table'] = 'Bàn không khả dụng.'
                except Table.DoesNotExist:
                    errors['table'] = 'Bàn không tồn tại.'
        
        if errors:
            return {
                'success': False,
                'errors': errors,
                'message': 'Validation failed.'
            }
        
        return {
            'success': True,
            'errors': {},
            'message': 'Validation passed.'
        }
    
    @transaction.atomic
    def create_order_from_cart(self, user, cart, order_data):
        """
        Tạo order từ cart
        
        Args:
            user: User object
            cart: Cart object
            order_data: Dict chứa thông tin order từ serializer
        
        Returns:
            dict: {'success': bool, 'order': Order object, 'message': str}
        """
        # Validate trước
        validation = self.validate_order_creation(user, cart, order_data)
        if not validation['success']:
            return {
                'success': False,
                'errors': validation['errors'],
                'message': validation['message']
            }
        
        try:
            # Get restaurant
            restaurant = Restaurant.objects.get(id=order_data['restaurant_id'])
            
            # Create Order
            order = Order(
                customer=user,
                restaurant=restaurant,
                chain=restaurant.chain,
                order_type=order_data['order_type'],
                status='pending',
                assignment_method='customer',
            )
            
            # Set fields theo order_type
            if order_data['order_type'] == 'delivery':
                order.delivery_address = order_data.get('delivery_address')
                order.delivery_latitude = order_data.get('delivery_latitude')
                order.delivery_longitude = order_data.get('delivery_longitude')
                order.delivery_phone = order_data.get('delivery_phone')
            
            elif order_data['order_type'] == 'dine_in':
                table_id = order_data.get('table_id')
                if table_id:
                    order.table = Table.objects.get(id=table_id)
                    # Update table status to occupied
                    order.table.status = 'occupied'
                    order.table.save()
            
            # Set optional fields
            order.customer_notes = order_data.get('customer_notes', '')
            order.tax = order_data.get('tax', Decimal('0.00'))
            order.discount = order_data.get('discount', Decimal('0.00'))
            
            # Set subtotal from cart
            order.subtotal = cart.subtotal
            
            # Save order (sẽ tự động tính distance và delivery_fee)
            order.save()
            
            # Create OrderItems from CartItems
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    menu_item=cart_item.menu_item,
                    item_name=cart_item.item_name,
                    item_price=cart_item.item_price,
                    quantity=cart_item.quantity,
                    special_instructions=cart_item.special_instructions,
                    subtotal=cart_item.subtotal
                )
            
            # Calculate total
            order.calculate_total()
            order.save()
            
            # Clear cart
            cart.items.all().delete()
            cart.subtotal = Decimal('0.00')
            cart.save()
            
            return {
                'success': True,
                'order': order,
                'message': 'Đơn hàng đã được tạo thành công.'
            }
        
        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi tạo đơn hàng: {str(e)}'
            }
    
    def cancel_order(self, order, user, reason):
        """
        Hủy order
        
        Args:
            order: Order object
            user: User requesting cancellation
            reason: Lý do hủy
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        # Validate quyền hủy
        if order.customer != user:
            return {
                'success': False,
                'message': 'Bạn không có quyền hủy đơn hàng này.'
            }
        
        # Validate status
        if order.status not in ['pending', 'confirmed']:
            return {
                'success': False,
                'message': f'Không thể hủy đơn hàng ở trạng thái "{order.get_status_display()}".'
            }
        
        try:
            # Update status
            order.status = 'cancelled'
            order.notes = f"Đã hủy. Lý do: {reason}\n{order.notes or ''}"
            order.save()
            
            # Release table if dine_in
            if order.order_type == 'dine_in' and order.table:
                order.table.status = 'available'
                order.table.save()
            
            return {
                'success': True,
                'message': 'Đơn hàng đã được hủy thành công.'
            }
        
        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi hủy đơn hàng: {str(e)}'
            }
    
    def update_order_status(self, order, new_status, staff_user=None, notes=None):
        """
        Cập nhật trạng thái order
        
        Args:
            order: Order object
            new_status: Trạng thái mới
            staff_user: User thực hiện update (staff/admin)
            notes: Ghi chú thêm
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        try:
            old_status = order.status
            order.status = new_status
            
            # Set completed_at nếu status = completed
            if new_status == 'completed' and not order.completed_at:
                order.completed_at = timezone.now()
            
            # Update notes
            if notes:
                order.notes = f"{notes}\n{order.notes or ''}"
            
            # Assign staff nếu có
            if staff_user and not order.assigned_staff:
                order.assigned_staff = staff_user
            
            order.save()
            
            # Release table if order completed/cancelled and dine_in
            if new_status in ['completed', 'cancelled'] and order.order_type == 'dine_in' and order.table:
                if order.table.status == 'occupied':
                    order.table.status = 'available'
                    order.table.save()
            
            return {
                'success': True,
                'message': f'Đã cập nhật trạng thái từ "{dict(Order.ORDER_STATUS_CHOICES).get(old_status)}" sang "{dict(Order.ORDER_STATUS_CHOICES).get(new_status)}".'
            }
        
        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi cập nhật trạng thái: {str(e)}'
            }
