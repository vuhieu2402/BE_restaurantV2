from django.db import models
from .models import Cart, CartItem


class CartSelector:
    """
    Selector layer - Chịu trách nhiệm truy vấn dữ liệu từ database (SELECT ONLY)
    """

    def get_cart_by_user(self, user):
        """
        Lấy giỏ hàng theo user (SELECT ONLY)
        """
        try:
            return Cart.objects.get(user=user)
        except Cart.DoesNotExist:
            return None

    def get_cart_by_id(self, cart_id):
        """
        Lấy giỏ hàng theo ID (SELECT ONLY)
        """
        try:
            return Cart.objects.get(id=cart_id)
        except Cart.DoesNotExist:
            return None

    def get_cart_with_items(self, user):
        """
        Lấy giỏ hàng kèm theo các món (SELECT ONLY)
        """
        return Cart.objects.filter(user=user).prefetch_related(
            models.Prefetch(
                'items',
                queryset=CartItem.objects.select_related(
                    'menu_item',
                    'restaurant',
                    'chain'
                ).order_by('created_at')
            )
        ).first()

    def check_cart_exists_for_user(self, user):
        """
        Kiểm tra user có giỏ hàng chưa (SELECT ONLY)
        """
        return Cart.objects.filter(user=user).exists()

    def count_carts_by_user(self, user):
        """
        Đếm số giỏ hàng của user (SELECT ONLY)
        """
        return Cart.objects.filter(user=user).count()


class CartItemSelector:
    """
    Selector layer cho CartItem (SELECT ONLY)
    """

    def get_items_by_cart(self, cart):
        """
        Lấy tất cả món trong giỏ hàng (SELECT ONLY)
        """
        return CartItem.objects.filter(cart=cart).select_related(
            'menu_item',
            'restaurant',
            'chain'
        ).order_by('created_at')

    def get_items_grouped_by_restaurant(self, cart):
        """
        Lấy món trong giỏ hàng nhóm theo nhà hàng (SELECT ONLY)
        """
        items = self.get_items_by_cart(cart)
        grouped = {}

        for item in items:
            restaurant_id = item.restaurant.id
            if restaurant_id not in grouped:
                grouped[restaurant_id] = {
                    'restaurant': item.restaurant,
                    'items': []
                }
            grouped[restaurant_id]['items'].append(item)

        return grouped

    def get_item_by_id(self, item_id):
        """
        Lấy món trong giỏ hàng theo ID (SELECT ONLY)
        """
        try:
            return CartItem.objects.select_related(
                'cart',
                'menu_item',
                'restaurant',
                'chain'
            ).get(id=item_id)
        except CartItem.DoesNotExist:
            return None

    def get_item_by_cart_and_menu_item(self, cart, menu_item):
        """
        Lấy món trong giỏ hàng theo giỏ hàng và món ăn (SELECT ONLY)
        """
        try:
            return CartItem.objects.get(cart=cart, menu_item=menu_item)
        except CartItem.DoesNotExist:
            return None

    def check_item_exists_in_cart(self, cart, menu_item):
        """
        Kiểm tra món đã có trong giỏ hàng chưa (SELECT ONLY)
        """
        return CartItem.objects.filter(cart=cart, menu_item=menu_item).exists()

    def get_items_by_restaurant(self, cart, restaurant_id):
        """
        Lấy món trong giỏ hàng theo nhà hàng (SELECT ONLY)
        """
        return CartItem.objects.filter(
            cart=cart,
            restaurant_id=restaurant_id
        ).select_related('menu_item').order_by('created_at')

    def get_restaurants_in_cart(self, cart):
        """
        Lấy danh sách nhà hàng có món trong giỏ (SELECT ONLY)
        """
        return CartItem.objects.filter(
            cart=cart
        ).select_related('restaurant').values_list(
            'restaurant',
            flat=True
        ).distinct()

    def count_items_in_cart(self, cart):
        """
        Đếm số món trong giỏ hàng (SELECT ONLY)
        """
        return CartItem.objects.filter(cart=cart).count()

    def get_total_quantity_in_cart(self, cart):
        """
        Lấy tổng số lượng món trong giỏ (SELECT ONLY)
        """
        result = CartItem.objects.filter(cart=cart).aggregate(
            total_quantity=models.Sum('quantity')
        )
        return result['total_quantity'] or 0

    def get_cart_subtotal(self, cart):
        """
        Lấy tổng tạm tính của giỏ hàng (SELECT ONLY)
        """
        result = CartItem.objects.filter(cart=cart).aggregate(
            subtotal=models.Sum('subtotal')
        )
        return result['subtotal'] or 0

    def get_menu_items_in_cart(self, user):
        """
        Lấy danh sách menu_item ID có trong giỏ hàng của user (SELECT ONLY)
        """
        return CartItem.objects.filter(
            cart__user=user
        ).values_list('menu_item_id', flat=True)

    def get_items_for_checkout(self, cart):
        """
        Lấy các món cần thiết cho checkout (SELECT ONLY)
        """
        return CartItem.objects.filter(cart=cart).select_related(
            'menu_item',
            'restaurant',
            'chain'
        ).order_by('restaurant_id', 'created_at')