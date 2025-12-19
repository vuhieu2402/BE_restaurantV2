from rest_framework import permissions, status, serializers
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from apps.api.mixins import StandardResponseMixin
from apps.api.response import ApiResponse
from .serializers import (
    CartSerializer,
    CartUpdateSerializer,
    CartCalculateSerializer,
    CartItemSerializer,
    CartItemCreateUpdateSerializer,
    CartItemListSerializer,
    CartItemRemoveSerializer,
    CartCheckoutSerializer
)
from .services import CartService, CartItemService


class CartView(StandardResponseMixin, APIView):
    """
    View chính cho giỏ hàng - Tuân thủ kiến trúc View → Service → Selector
    """
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.cart_service = CartService()
        self.item_service = CartItemService()

    @extend_schema(
        tags=['Cart'],
        summary="Get user cart",
        description="Lấy giỏ hàng của người dùng hiện tại",
        responses={200: CartSerializer}
    )
    def get(self, request, *args, **kwargs):
        """
        GET method - View chỉ làm 2 việc:
        1. Nhận request và validate cơ bản
        2. Gọi service và return response
        """
        try:
            # ❌ KHÔNG viết business logic ở đây
            # ❌ KHÔNG query database trực tiếp
            # ❌ KHÔNG validate business rules

            # ✅ Chỉ gọi service
            result = self.cart_service.get_user_cart_with_items(request.user)

            if result['success']:
                serializer = CartSerializer(result['data'])
                return ApiResponse.success(
                    data=serializer.data,
                    message=result['message']
                )
            else:
                return ApiResponse.error(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Lỗi khi lấy giỏ hàng: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Cart'],
        summary="Clear cart",
        description="Xóa toàn bộ giỏ hàng của người dùng",
        responses={200: dict}
    )
    def delete(self, request, *args, **kwargs):
        """
        DELETE method - View chỉ làm 2 việc:
        1. Nhận request
        2. Gọi service và return response
        """
        try:
            # ✅ Chỉ gọi service
            result = self.cart_service.clear_cart(request.user)

            if result['success']:
                return ApiResponse.success(message=result['message'])
            else:
                return ApiResponse.error(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Lỗi khi xóa giỏ hàng: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CartItemsView(StandardResponseMixin, APIView):
    """
    View cho việc quản lý các món trong giỏ hàng
    """
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.item_service = CartItemService()
        self.cart_service = CartService()

    @extend_schema(
        tags=['Cart'],
        summary="Get cart items",
        description="Lấy danh sách các món trong giỏ hàng",
        responses={200: CartItemSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        """Get all cart items"""
        try:
            # ✅ Chỉ gọi service
            result = self.cart_service.get_user_cart_with_items(request.user)

            if result['success'] and result['data']:
                serializer = CartItemSerializer(
                    result['data'].items.all(),
                    many=True
                )
                return ApiResponse.success(
                    data=serializer.data,
                    message="Lấy danh sách món trong giỏ hàng thành công"
                )
            else:
                return ApiResponse.success(
                    data=[],
                    message="Giỏ hàng trống"
                )

        except Exception as e:
            return ApiResponse.error(
                message=f"Lỗi khi lấy danh sách món: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Cart'],
        summary="Add item to cart",
        description="Thêm món vào giỏ hàng",
        request=CartItemCreateUpdateSerializer,
        responses={201: CartItemSerializer}
    )
    def post(self, request, *args, **kwargs):
        """Add item to cart"""
        try:
            # ✅ Validate request level (chỉ required fields)
            required_fields = ['menu_item_id']
            for field in required_fields:
                if field not in request.data:
                    return ApiResponse.bad_request(
                        message=f"Missing required field: {field}"
                    )

            # ❌ KHÔNG validate business rules ở đây
            # ❌ KHÔNG check unique constraints ở đây

            # ✅ Chỉ gọi service
            menu_item_id = request.data.get('menu_item_id')
            quantity = request.data.get('quantity', 1)
            special_instructions = request.data.get('special_instructions', '')

            result = self.item_service.add_item_to_cart(
                user=request.user,
                menu_item_id=menu_item_id,
                quantity=quantity,
                special_instructions=special_instructions
            )

            if result['success']:
                # Return lightweight response with only the added item info
                item = result['data']['item']
                action = result['data']['action']

                # Create simple response with just the essential item info
                response_data = {
                    'item_id': item.id,
                    'menu_item_id': item.menu_item.id,
                    'item_name': item.item_name,
                    'item_price': float(item.item_price),
                    'quantity': item.quantity,
                    'subtotal': float(item.subtotal),
                    'subtotal_display': f"{item.subtotal:,.0f}đ",
                    'action': action,  # "Thêm mới" or "Cập nhật số lượng"
                    'restaurant_name': item.restaurant_name
                }

                return ApiResponse.created(
                    data=response_data,
                    message=result['message']
                )
            else:
                return ApiResponse.validation_error(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Lỗi khi thêm món vào giỏ hàng: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CartItemDetailView(StandardResponseMixin, APIView):
    """
    View cho việc quản lý một món cụ thể trong giỏ hàng
    """
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.item_service = CartItemService()

    @extend_schema(
        tags=['Cart'],
        summary="Update cart item",
        description="Cập nhật thông tin món trong giỏ hàng",
        request=CartItemCreateUpdateSerializer,
        responses={200: CartItemSerializer}
    )
    def put(self, request, item_id, *args, **kwargs):
        """Update cart item"""
        try:
            # ✅ Validate request level
            quantity = request.data.get('quantity')
            special_instructions = request.data.get('special_instructions', '')

            if quantity is None:
                return ApiResponse.bad_request(
                    message="Missing required field: quantity"
                )

            # ✅ Chỉ gọi service
            if special_instructions:
                # Cập nhật cả quantity và instructions
                result = self.item_service.update_item_quantity(
                    user=request.user,
                    item_id=item_id,
                    quantity=quantity
                )
                if result['success']:
                    instruction_result = self.item_service.update_item_instructions(
                        user=request.user,
                        item_id=item_id,
                        special_instructions=special_instructions
                    )
                    if not instruction_result['success']:
                        return ApiResponse.validation_error(
                            message=instruction_result['message']
                        )
            else:
                # Chỉ cập nhật quantity
                result = self.item_service.update_item_quantity(
                    user=request.user,
                    item_id=item_id,
                    quantity=quantity
                )

            if result['success']:
                serializer = CartItemSerializer(result['data']['item'])
                return ApiResponse.success(
                    data=serializer.data,
                    message=result['message']
                )
            else:
                return ApiResponse.validation_error(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Lỗi khi cập nhật món: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Cart'],
        summary="Remove item from cart",
        description="Xóa món khỏi giỏ hàng",
        responses={200: CartSerializer}
    )
    def delete(self, request, item_id, *args, **kwargs):
        """Remove item from cart"""
        try:
            # ✅ Chỉ gọi service
            result = self.item_service.remove_item_from_cart(
                user=request.user,
                item_id=item_id
            )

            if result['success']:
                serializer = CartSerializer(result['data'])
                return ApiResponse.success(
                    data=serializer.data,
                    message=result['message']
                )
            else:
                return ApiResponse.error(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Lỗi khi xóa món: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CartBatchOperationsView(StandardResponseMixin, APIView):
    """
    View cho các thao tác batch với giỏ hàng
    """
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.item_service = CartItemService()
        self.cart_service = CartService()

    @extend_schema(
        tags=['Cart'],
        summary="Add multiple items to cart",
        description="Thêm nhiều món vào giỏ hàng cùng lúc",
        request=CartItemListSerializer,
        responses={201: dict}
    )
    def post(self, request, *args, **kwargs):
        """Add multiple items to cart"""
        try:
            # ✅ Validate request level
            if 'items' not in request.data:
                return ApiResponse.bad_request(
                    message="Missing required field: items"
                )

            items_data = request.data.get('items', [])
            if not items_data:
                return ApiResponse.bad_request(
                    message="Items list cannot be empty"
                )

            # ✅ Chỉ gọi service
            result = self.item_service.add_multiple_items_to_cart(
                user=request.user,
                items_data=items_data
            )

            if result['success']:
                serializer = CartSerializer(result['data']['cart'])
                response_data = {
                    'cart': serializer.data,
                    'added_items': len(result['data']['added_items']),
                    'updated_items': len(result['data']['updated_items'])
                }
                if result.get('errors'):
                    response_data['errors'] = result['errors']

                return ApiResponse.created(
                    data=response_data,
                    message=result['message']
                )
            else:
                return ApiResponse.validation_error(
                    message=result['message'],
                    errors=result.get('errors')
                )

        except Exception as e:
            return ApiResponse.error(
                message=f"Lỗi khi thêm nhiều món: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Cart'],
        summary="Remove multiple items from cart",
        description="Xóa nhiều món khỏi giỏ hàng cùng lúc",
        request=CartItemRemoveSerializer,
        responses={200: dict}
    )
    def delete(self, request, *args, **kwargs):
        """Remove multiple items from cart"""
        try:
            # ✅ Validate request level
            if 'item_ids' not in request.data:
                return ApiResponse.bad_request(
                    message="Missing required field: item_ids"
                )

            item_ids = request.data.get('item_ids', [])
            if not item_ids:
                return ApiResponse.bad_request(
                    message="Item IDs list cannot be empty"
                )

            # ✅ Chỉ gọi service
            result = self.item_service.remove_multiple_items_from_cart(
                user=request.user,
                item_ids=item_ids
            )

            if result['success']:
                # Return lightweight response with just deletion confirmation
                cart = result['data']
                response_data = {
                    'deleted_count': len(item_ids),
                    'remaining_items_count': cart.get_total_items() if cart else 0,
                    'restaurant_count': cart.get_restaurant_count() if cart else 0,
                    'cart_subtotal': float(cart.subtotal) if cart else 0,
                    'cart_subtotal_display': f"{cart.subtotal:,.0f}đ" if cart else "0đ"
                }

                return ApiResponse.success(
                    data=response_data,
                    message=result['message']
                )
            else:
                return ApiResponse.error(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Lỗi khi xóa nhiều món: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CartCalculateView(StandardResponseMixin, APIView):
    """
    View cho việc tính toán lại giỏ hàng
    """
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.cart_service = CartService()

    @extend_schema(
        tags=['Cart'],
        summary="Calculate cart totals",
        description="Tính toán lại tổng giá trị giỏ hàng",
        request=CartCalculateSerializer,
        responses={200: CartSerializer}
    )
    def post(self, request, *args, **kwargs):
        """Calculate cart totals"""
        try:
            # ✅ Chỉ gọi service
            result = self.cart_service.calculate_cart_totals(request.user)

            if result['success']:
                serializer = CartSerializer(result['data'])
                return ApiResponse.success(
                    data=serializer.data,
                    message=result['message']
                )
            else:
                return ApiResponse.error(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Lỗi khi tính toán giỏ hàng: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CartUpdateView(StandardResponseMixin, APIView):
    """
    View cho việc cập nhật thông tin giỏ hàng
    """
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.cart_service = CartService()

    @extend_schema(
        tags=['Cart'],
        summary="Update cart notes",
        description="Cập nhật ghi chú giỏ hàng",
        request=CartUpdateSerializer,
        responses={200: CartSerializer}
    )
    def put(self, request, *args, **kwargs):
        """Update cart notes"""
        try:
            # ✅ Validate request level
            notes = request.data.get('notes', '')

            # ✅ Chỉ gọi service
            result = self.cart_service.update_cart_notes(
                user=request.user,
                notes=notes
            )

            if result['success']:
                serializer = CartSerializer(result['data'])
                return ApiResponse.success(
                    data=serializer.data,
                    message=result['message']
                )
            else:
                return ApiResponse.error(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Lỗi khi cập nhật giỏ hàng: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CartCheckoutView(StandardResponseMixin, APIView):
    """
    View cho việc checkout giỏ hàng - chuyển đổi thành các đơn hàng
    """
    permission_classes = [permissions.IsAuthenticated]

    def __init__(self):
        super().__init__()
        self.cart_service = CartService()
        self.item_service = CartItemService()

    @extend_schema(
        tags=['Cart'],
        summary="Checkout cart",
        description="Chuyển đổi giỏ hàng thành các đơn hàng (mỗi nhà hàng một đơn)",
        request=CartCheckoutSerializer,
        responses={201: dict}
    )
    def post(self, request, *args, **kwargs):
        """Checkout cart - convert to multiple orders"""
        try:
            # ✅ Validate request level cơ bản
            # Lấy giỏ hàng để kiểm tra
            cart_result = self.cart_service.get_user_cart_with_items(request.user)

            if not cart_result['success'] or not cart_result['data']:
                return ApiResponse.validation_error(
                    message="Giỏ hàng không tồn tại"
                )

            cart = cart_result['data']
            if not cart.items.exists():
                return ApiResponse.validation_error(
                    message="Giỏ hàng trống, không thể checkout"
                )

            # ❌ KHÔNG validate business rules phức tạp ở đây
            # ✅ Chỉ gọi service để xử lý business logic

            # Import OrderService để xử lý checkout
            # Chỉ tạo đơn hàng tạm thời, sẽ implement chi tiết sau
            from apps.orders.selectors import OrderSelector

            # Lấy các món theo nhóm nhà hàng
            from .selectors import CartItemSelector
            item_selector = CartItemSelector()
            grouped_items = item_selector.get_items_grouped_by_restaurant(cart)

            if not grouped_items:
                return ApiResponse.validation_error(
                    message="Không có món nào trong giỏ hàng để tạo đơn hàng"
                )

            # Tạo response tạm thời
            restaurant_groups = []
            for restaurant_id, group_data in grouped_items.items():
                restaurant_groups.append({
                    'restaurant_id': restaurant_id,
                    'restaurant_name': group_data['restaurant'].name,
                    'items_count': len(group_data['items']),
                    'items_summary': [
                        {
                            'id': item.id,
                            'name': item.item_name,
                            'quantity': item.quantity,
                            'subtotal': float(item.subtotal)
                        }
                        for item in group_data['items']
                    ]
                })

            response_data = {
                'cart_id': cart.id,
                'restaurant_groups': restaurant_groups,
                'total_amount': float(cart.total),
                'payment_info': {
                    'payment_method_id': request.data.get('payment_method_id'),
                    'delivery_address': request.data.get('delivery_address', cart.notes or ''),
                    'notes': request.data.get('notes', '')
                }
            }

            return ApiResponse.success(
                data=response_data,
                message="Giỏ hàng sẵn sàng để chuyển đổi thành đơn hàng. Vui lòng implement service hoàn chỉnh để tạo đơn hàng."
            )

        except Exception as e:
            return ApiResponse.error(
                message=f"Lỗi khi checkout giỏ hàng: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

