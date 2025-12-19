from django.db import transaction
from decimal import Decimal, InvalidOperation
from .selectors import CartSelector, CartItemSelector
from .models import Cart, CartItem


class CartService:
    """
    Service layer - Xử lý business logic và CUD operations cho Cart
    """

    def __init__(self):
        self.cart_selector = CartSelector()
        self.item_selector = CartItemSelector()

    def get_or_create_user_cart(self, user):
        """
        Lấy hoặc tạo giỏ hàng cho user
        """
        try:
            # Gọi selector để lấy giỏ hàng (SELECT)
            cart = self.cart_selector.get_cart_by_user(user)
            if cart:
                return {
                    'success': True,
                    'data': cart,
                    'message': 'Lấy giỏ hàng thành công'
                }

            # Tạo giỏ hàng mới nếu chưa có (CREATE)
            with transaction.atomic():
                cart = Cart.objects.create(user=user)
                return {
                    'success': True,
                    'data': cart,
                    'message': 'Tạo giỏ hàng mới thành công'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi lấy/tạo giỏ hàng: {str(e)}'
            }

    def get_user_cart_with_items(self, user):
        """
        Lấy giỏ hàng của user kèm các món
        """
        try:
            # Gọi selector để lấy giỏ hàng và items (SELECT)
            cart = self.cart_selector.get_cart_with_items(user)
            if cart:
                return {
                    'success': True,
                    'data': cart,
                    'message': 'Lấy giỏ hàng thành công'
                }
            else:
                # Tạo giỏ hàng mới nếu chưa có (CREATE)
                cart = self.get_or_create_user_cart(user)
                if cart['success']:
                    return {
                        'success': True,
                        'data': cart['data'],
                        'message': 'Tạo giỏ hàng mới thành công'
                    }
                return cart

        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi lấy giỏ hàng: {str(e)}'
            }

    def clear_cart(self, user):
        """
        Xóa toàn bộ giỏ hàng của user
        """
        try:
            with transaction.atomic():
                # Gọi selector để lấy giỏ hàng (SELECT)
                cart = self.cart_selector.get_cart_by_user(user)
                if not cart:
                    return {
                        'success': False,
                        'message': 'Giỏ hàng không tồn tại'
                    }

                # Xóa tất cả các món trong giỏ (DELETE)
                deleted_count, _ = cart.items.all().delete()

                # Cập nhật lại tổng giá trị
                cart.calculate_totals()

                return {
                    'success': True,
                    'message': f'Đã xóa {deleted_count} món khỏi giỏ hàng'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi xóa giỏ hàng: {str(e)}'
            }

    def update_cart_notes(self, user, notes):
        """
        Cập nhật ghi chú giỏ hàng
        """
        try:
            with transaction.atomic():
                # Gọi selector để lấy giỏ hàng (SELECT)
                cart = self.cart_selector.get_cart_by_user(user)
                if not cart:
                    return {
                        'success': False,
                        'message': 'Giỏ hàng không tồn tại'
                    }

                # Cập nhật ghi chú (UPDATE)
                cart.notes = notes
                cart.save(update_fields=['notes'])

                return {
                    'success': True,
                    'data': cart,
                    'message': 'Cập nhật ghi chú giỏ hàng thành công'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi cập nhật ghi chú: {str(e)}'
            }

    def calculate_cart_totals(self, user):
        """
        Tính toán lại tổng giá trị giỏ hàng
        """
        try:
            # Gọi selector để lấy giỏ hàng (SELECT)
            cart = self.cart_selector.get_cart_by_user(user)
            if not cart:
                return {
                    'success': False,
                    'message': 'Giỏ hàng không tồn tại'
                }

            # Tính toán lại tổng
            cart.calculate_totals()

            return {
                'success': True,
                'data': cart,
                'message': 'Tính toán lại giỏ hàng thành công'
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi tính toán giỏ hàng: {str(e)}'
            }


class CartItemService:
    """
    Service layer - Xử lý business logic và CUD operations cho CartItem
    """

    def __init__(self):
        self.cart_service = CartService()
        self.cart_selector = CartSelector()
        self.item_selector = CartItemSelector()

    def add_item_to_cart(self, user, menu_item_id, quantity=1, special_instructions=''):
        """
        Thêm món vào giỏ hàng
        """
        try:
            with transaction.atomic():
                # Import here to avoid circular imports
                from apps.dishes.models import MenuItem

                # Validate menu_item exists and is available
                # Select both restaurant and chain to handle both cases
                try:
                    menu_item = MenuItem.objects.select_related(
                        'restaurant', 
                        'chain'
                    ).get(
                        id=menu_item_id,
                        is_available=True
                    )
                except MenuItem.DoesNotExist:
                    return {
                        'success': False,
                        'message': 'Món ăn không tồn tại hoặc không còn bán'
                    }

                # Validate quantity
                if quantity < 1:
                    return {
                        'success': False,
                        'message': 'Số lượng phải lớn hơn 0'
                    }

                # Xác định restaurant và chain dựa trên loại menu_item
                if menu_item.restaurant:
                    # MenuItem thuộc restaurant độc lập
                    restaurant = menu_item.restaurant
                    chain = menu_item.restaurant.chain  # Có thể là None nếu không thuộc chain
                    restaurant_name = restaurant.name
                elif menu_item.chain:
                    # MenuItem thuộc chain - cần chọn chi nhánh
                    # TODO: Implement logic chọn chi nhánh dựa trên địa chỉ giao hàng
                    # Hiện tại chọn chi nhánh đầu tiên đang hoạt động
                    chain = menu_item.chain
                    restaurant = chain.restaurants.filter(
                        is_active=True,
                        is_open=True
                    ).first()
                    
                    if not restaurant:
                        return {
                            'success': False,
                            'message': f'Chuỗi {chain.name} hiện không có chi nhánh nào đang hoạt động'
                        }
                    restaurant_name = f"{chain.name} - {restaurant.name}"
                else:
                    # Không nên xảy ra vì MenuItem.clean() đã validate
                    return {
                        'success': False,
                        'message': 'Món ăn không thuộc nhà hàng hoặc chuỗi nào'
                    }

                # Lấy hoặc tạo giỏ hàng
                cart_result = self.cart_service.get_or_create_user_cart(user)
                if not cart_result['success']:
                    return cart_result
                cart = cart_result['data']

                # Validate restaurant: cart chỉ có thể chứa món từ 1 restaurant
                try:
                    cart.validate_single_restaurant(restaurant.id)
                except ValidationError as e:
                    return {
                        'success': False,
                        'message': e.message_dict.get('restaurant', ['Lỗi validation restaurant'])[0]
                    }

                # Kiểm tra món đã có trong giỏ chưa
                existing_item = self.item_selector.get_item_by_cart_and_menu_item(
                    cart, menu_item
                )

                if existing_item:
                    # Cập nhật số lượng nếu món đã có (UPDATE)
                    existing_item.quantity += quantity
                    existing_item.special_instructions = special_instructions
                    existing_item.save(update_fields=['quantity', 'special_instructions', 'updated_at'])
                    existing_item.calculate_subtotal()
                    item = existing_item
                    action = "Cập nhật số lượng"
                else:
                    # Tạo món mới trong giỏ (CREATE)
                    item = CartItem.objects.create(
                        cart=cart,
                        menu_item=menu_item,
                        restaurant=restaurant,
                        chain=chain,
                        item_name=menu_item.name,
                        item_price=menu_item.price,
                        item_image=menu_item.image.url if menu_item.image else '',
                        restaurant_name=restaurant_name,
                        quantity=quantity,
                        special_instructions=special_instructions
                    )
                    item.calculate_subtotal()
                    action = "Thêm mới"

                # Lấy lại giỏ hàng với đầy đủ thông tin
                updated_cart = self.cart_selector.get_cart_with_items(user)

                return {
                    'success': True,
                    'data': {
                        'cart': updated_cart,
                        'item': item,
                        'action': action
                    },
                    'message': f'{action} món vào giỏ hàng thành công'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi thêm món vào giỏ hàng: {str(e)}'
            }

    def update_item_quantity(self, user, item_id, quantity):
        """
        Cập nhật số lượng món trong giỏ hàng
        """
        try:
            with transaction.atomic():
                if quantity < 1:
                    return {
                        'success': False,
                        'message': 'Số lượng phải lớn hơn 0'
                    }

                # Gọi selector để lấy món (SELECT)
                item = self.item_selector.get_item_by_id(item_id)
                if not item:
                    return {
                        'success': False,
                        'message': 'Món không tồn tại'
                    }

                # Validate ownership
                if item.cart.user != user:
                    return {
                        'success': False,
                        'message': 'Bạn không có quyền cập nhật món này'
                    }

                # Cập nhật số lượng (UPDATE)
                item.quantity = quantity
                item.save(update_fields=['quantity', 'updated_at'])
                item.calculate_subtotal()

                # Lấy lại giỏ hàng với đầy đủ thông tin
                cart = self.cart_selector.get_cart_with_items(user)

                return {
                    'success': True,
                    'data': {
                        'cart': cart,
                        'item': item
                    },
                    'message': 'Cập nhật số lượng món thành công'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi cập nhật số lượng: {str(e)}'
            }

    def update_item_instructions(self, user, item_id, special_instructions):
        """
        Cập nhật yêu cầu đặc biệt cho món
        """
        try:
            with transaction.atomic():
                # Gọi selector để lấy món (SELECT)
                item = self.item_selector.get_item_by_id(item_id)
                if not item:
                    return {
                        'success': False,
                        'message': 'Món không tồn tại'
                    }

                # Validate ownership
                if item.cart.user != user:
                    return {
                        'success': False,
                        'message': 'Bạn không có quyền cập nhật món này'
                    }

                # Cập nhật ghi chú (UPDATE)
                item.special_instructions = special_instructions
                item.save(update_fields=['special_instructions', 'updated_at'])

                return {
                    'success': True,
                    'data': item,
                    'message': 'Cập nhật yêu cầu đặc biệt thành công'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi cập nhật yêu cầu đặc biệt: {str(e)}'
            }

    def remove_item_from_cart(self, user, item_id):
        """
        Xóa món khỏi giỏ hàng
        """
        try:
            with transaction.atomic():
                # Gọi selector để lấy món (SELECT)
                item = self.item_selector.get_item_by_id(item_id)
                if not item:
                    return {
                        'success': False,
                        'message': 'Món không tồn tại'
                    }

                # Validate ownership
                if item.cart.user != user:
                    return {
                        'success': False,
                        'message': 'Bạn không có quyền xóa món này'
                    }

                # Lưu thông tin trước khi xóa
                cart = item.cart
                item_name = item.item_name

                # Xóa món (DELETE)
                item.delete()

                # Cập nhật lại tổng giỏ hàng
                cart.calculate_totals()

                # Lấy lại giỏ hàng với đầy đủ thông tin
                updated_cart = self.cart_selector.get_cart_with_items(user)

                return {
                    'success': True,
                    'data': updated_cart,
                    'message': f'Đã xóa "{item_name}" khỏi giỏ hàng'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi xóa món khỏi giỏ hàng: {str(e)}'
            }

    def add_multiple_items_to_cart(self, user, items_data):
        """
        Thêm nhiều món vào giỏ hàng cùng lúc
        """
        try:
            with transaction.atomic():
                # Import here to avoid circular imports
                from apps.dishes.models import MenuItem

                # Lấy hoặc tạo giỏ hàng
                cart_result = self.cart_service.get_or_create_user_cart(user)
                if not cart_result['success']:
                    return cart_result
                cart = cart_result['data']

                added_items = []
                updated_items = []
                errors = []

                for item_data in items_data:
                    menu_item_id = item_data.get('menu_item_id')
                    quantity = item_data.get('quantity', 1)
                    special_instructions = item_data.get('special_instructions', '')

                    try:
                        # Validate menu_item exists and is available
                        # Select both restaurant and chain to handle both cases
                        menu_item = MenuItem.objects.select_related(
                            'restaurant',
                            'chain'
                        ).get(
                            id=menu_item_id,
                            is_available=True
                        )

                        # Validate quantity
                        if quantity < 1:
                            errors.append(f'Món {menu_item_id}: số lượng phải lớn hơn 0')
                            continue

                        # Xác định restaurant và chain dựa trên loại menu_item
                        if menu_item.restaurant:
                            # MenuItem thuộc restaurant độc lập
                            restaurant = menu_item.restaurant
                            chain = menu_item.restaurant.chain
                            restaurant_name = restaurant.name
                        elif menu_item.chain:
                            # MenuItem thuộc chain - chọn chi nhánh
                            chain = menu_item.chain
                            restaurant = chain.restaurants.filter(
                                is_active=True,
                                is_open=True
                            ).first()
                            
                            if not restaurant:
                                errors.append(f'Món {menu_item_id}: Chuỗi {chain.name} không có chi nhánh nào đang hoạt động')
                                continue
                            restaurant_name = f"{chain.name} - {restaurant.name}"
                        else:
                            errors.append(f'Món {menu_item_id}: Không thuộc nhà hàng hoặc chuỗi nào')
                            continue

                        # Kiểm tra món đã có trong giỏ chưa
                        existing_item = self.item_selector.get_item_by_cart_and_menu_item(
                            cart, menu_item
                        )

                        if existing_item:
                            # Cập nhật số lượng nếu món đã có
                            existing_item.quantity += quantity
                            existing_item.save(update_fields=['quantity', 'updated_at'])
                            existing_item.calculate_subtotal()
                            updated_items.append(existing_item)
                        else:
                            # Tạo món mới trong giỏ
                            item = CartItem.objects.create(
                                cart=cart,
                                menu_item=menu_item,
                                restaurant=restaurant,
                                chain=chain,
                                item_name=menu_item.name,
                                item_price=menu_item.price,
                                item_image=menu_item.image.url if menu_item.image else '',
                                restaurant_name=restaurant_name,
                                quantity=quantity,
                                special_instructions=special_instructions
                            )
                            item.calculate_subtotal()
                            added_items.append(item)

                    except MenuItem.DoesNotExist:
                        errors.append(f'Món {menu_item_id}: không tồn tại hoặc không còn bán')
                    except Exception as e:
                        errors.append(f'Món {menu_item_id}: {str(e)}')

                # Lấy lại giỏ hàng với đầy đủ thông tin
                updated_cart = self.cart_selector.get_cart_with_items(user)

                return {
                    'success': len(errors) == 0,
                    'data': {
                        'cart': updated_cart,
                        'added_items': added_items,
                        'updated_items': updated_items
                    },
                    'message': f'Đã xử lý {len(added_items) + len(updated_items)} món' +
                             (f'. Lỗi: {"; ".join(errors)}' if errors else ''),
                    'errors': errors if errors else None
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi thêm nhiều món vào giỏ hàng: {str(e)}'
            }

    def remove_multiple_items_from_cart(self, user, item_ids):
        """
        Xóa nhiều món khỏi giỏ hàng cùng lúc
        """
        try:
            with transaction.atomic():
                # Gọi selector để lấy các món cần xóa (SELECT)
                items = self.item_selector.get_items_by_cart(
                    self.cart_selector.get_cart_by_user(user)
                ).filter(id__in=item_ids)

                if not items:
                    return {
                        'success': False,
                        'message': 'Không có món nào cần xóa'
                    }

                # Validate ownership
                for item in items:
                    if item.cart.user != user:
                        return {
                            'success': False,
                            'message': 'Bạn không có quyền xóa một số món này'
                        }

                # Lưu thông tin trước khi xóa
                cart = items[0].cart
                deleted_count = items.count()

                # Xóa các món (DELETE)
                items.delete()

                # Cập nhật lại tổng giỏ hàng
                cart.calculate_totals()

                # Lấy lại giỏ hàng với đầy đủ thông tin
                updated_cart = self.cart_selector.get_cart_with_items(user)

                return {
                    'success': True,
                    'data': updated_cart,
                    'message': f'Đã xóa {deleted_count} món khỏi giỏ hàng'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Lỗi khi xóa nhiều món: {str(e)}'
            }