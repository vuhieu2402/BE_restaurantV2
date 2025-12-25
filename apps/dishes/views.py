from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from drf_spectacular.utils import extend_schema
from apps.api.mixins import StandardResponseMixin
from apps.api.response import ApiResponse
from apps.api.pagination import StandardPageNumberPagination, LargeResultsSetPagination, SmallResultsSetPagination, DynamicPagination
from .selectors import CategorySelector, MenuItemSelector
from .services import CategoryService, MenuItemService
from .serializers import (
    CategorySerializer, CategoryCreateSerializer, CategoryUpdateSerializer,
    CategoryListSerializer, CategoryWithItemsSerializer,
    MenuItemSerializer, MenuItemCreateSerializer, MenuItemUpdateSerializer,
    MenuItemListSerializer, MenuItemDetailSerializer, FeaturedMenuItemSerializer,
    MenuItemImageSerializer, MenuItemImageCreateSerializer, MenuItemImageUpdateSerializer,
    CategorySearchSerializer, MenuItemSearchSerializer, CategoryReorderSerializer,
    MenuItemToggleSerializer, MenuItemPriceUpdateSerializer, BulkPriceUpdateSerializer,
    BulkPriceUpdateSerializer, CategoryReorderBulkSerializer, MenuAnalyticsSerializer,
    MenuSummarySerializer, DietaryPreferenceSerializer, MenuItemBulkCreateSerializer,
    CategoryBulkCreateSerializer
)
from apps.dishes.models import MenuItem


class CategoryListView(StandardResponseMixin, ListAPIView):
    """
    GET /api/restaurants/{restaurant_id}/categories/ - List restaurant categories
    POST /api/restaurants/{restaurant_id}/categories/ - Create new category
    """
    permission_classes = [permissions.AllowAny]  # Public access for GET
    pagination_class = SmallResultsSetPagination  # Categories are typically limited in number

    def get_serializer_class(self):
        return CategoryListSerializer

    def get_queryset(self):
        """
        Get queryset for pagination - this will be used by ListAPIView
        """
        # Note: This is a simplified approach. In a real implementation,
        # you might want to create a proper Django queryset from your service results
        # or refactor your service to return Django QuerySets instead of dicts
        from apps.dishes.models import Category
        return Category.objects.filter(restaurant_id=self.kwargs['restaurant_id'], is_active=True)

    @extend_schema(
        tags=['Dishes'],
        summary="List restaurant categories",
        description="Get paginated list of categories for a specific restaurant",
        parameters=[
            CategorySearchSerializer,
            {'name': 'page', 'type': 'int', 'required': False, 'in': 'query', 'description': 'Page number'},
            {'name': 'page_size', 'type': 'int', 'required': False, 'in': 'query', 'description': 'Items per page'}
        ],
        responses={200: CategoryListSerializer(many=True)}
    )
    def get(self, request, restaurant_id):
        """
        GET method - Return paginated categories
        """
        try:
            # For now, we'll keep the existing service logic but add pagination at the response level
            # In a full refactor, you'd want to modify the service to work with Django QuerySets
            service = CategoryService()
            filters = {
                'search': request.query_params.get('search')
            }

            # Remove None values
            filters = {k: v for k, v in filters.items() if v is not None}
            result = service.get_categories_with_business_logic(restaurant_id, filters)

            if result['success']:
                try:
                    # Apply pagination to the results
                    paginator = self.pagination_class()
                    paginated_data = paginator.paginate_queryset(result['data'], request)

                    if paginated_data is not None:
                        # Use the custom pagination response format
                        return paginator.get_paginated_response(paginated_data)

                    # Fallback if pagination fails
                    return self.success_response(
                        data=result['data'],
                        message=result['message']
                    )
                except Exception as pagination_error:
                    # Fallback to non-paginated response if pagination fails
                    return self.success_response(
                        data=result['data'],
                        message=result['message'] + " (pagination disabled)"
                    )
            else:
                return self.error_response(message=result['message'])

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Dishes'],
        summary="Create category",
        description="Create new category for restaurant",
        request=CategoryCreateSerializer,
        responses={201: CategorySerializer}
    )
    def post(self, request, restaurant_id):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Validate request level (chỉ required fields)
            required_fields = ['name', 'slug']
            for field in required_fields:
                if field not in request.data:
                    return self.error_response(
                        message=f"Missing required field: {field}"
                    )

            # ✅ Chỉ gọi service
            service = CategoryService()
            result = service.create_category(restaurant_id, request.data, request.user)

            if result['success']:
                # Serialize category data before returning
                serializer = CategorySerializer(result['data'], context={'request': request})
                return self.created_response(
                    data=serializer.data,
                    message=result['message']
                )
            else:
                return self.error_response(
                    message=result['message'],
                    errors=result.get('errors')
                )

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CategoryDetailView(StandardResponseMixin, APIView):
    """
    GET /api/restaurants/{restaurant_id}/categories/{category_id}/ - Get category details
    PUT /api/restaurants/{restaurant_id}/categories/{category_id}/ - Update category
    DELETE /api/restaurants/{restaurant_id}/categories/{category_id}/ - Delete category
    """
    permission_classes = [permissions.AllowAny]  # Public access for GET

    @extend_schema(
        tags=['Dishes'],
        summary="Get category details",
        description="Get detailed information about a specific category",
        responses={200: CategoryWithItemsSerializer}
    )
    def get(self, request, restaurant_id, category_id):
        """
        GET method - View chỉ làm 2 việc:
        1. Nhận request và validate cơ bản
        2. Gọi service/selector và return response
        """
        try:
            # ✅ Validate category exists and belongs to restaurant
            selector = CategorySelector()
            category = selector.get_category_by_id(category_id)

            if not category:
                return self.not_found_response(message="Category not found")

            if category.restaurant_id != int(restaurant_id):
                return self.error_response(
                    message="Category does not belong to this restaurant"
                )

            # Get category with items via service
            service = CategoryService()
            categories_with_items = service.get_categories_with_business_logic(
                restaurant_id, {'search': category.name}
            )

            if categories_with_items['success']:
                # Find specific category in results
                category_data = None
                for cat_data in categories_with_items['data']:
                    if cat_data['id'] == category.id:
                        category_data = cat_data
                        break

                if category_data:
                    return self.success_response(
                        data=category_data,
                        message="Category retrieved successfully"
                    )

            return self.not_found_response(message="Category not found")

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Dishes'],
        summary="Update category",
        description="Update category information",
        request=CategoryUpdateSerializer,
        responses={200: CategorySerializer}
    )
    def put(self, request, restaurant_id, category_id):
        """
        PUT method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Validate category exists and belongs to restaurant
            selector = CategorySelector()
            category = selector.get_category_by_id(category_id)

            if not category:
                return self.not_found_response(message="Category not found")

            if category.restaurant_id != int(restaurant_id):
                return self.error_response(
                    message="Category does not belong to this restaurant"
                )

            # ✅ Chỉ gọi service
            service = CategoryService()
            result = service.update_category(category_id, request.data, request.user)

            if result['success']:
                # Serialize category data before returning
                serializer = CategorySerializer(result['data'], context={'request': request})
                return self.success_response(
                    data=serializer.data,
                    message=result['message']
                )
            else:
                return self.error_response(
                    message=result['message'],
                    errors=result.get('errors')
                )

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Dishes'],
        summary="Delete category",
        description="Soft delete category",
        responses={204}
    )
    def delete(self, request, restaurant_id, category_id):
        """
        DELETE method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Validate category exists and belongs to restaurant
            selector = CategorySelector()
            category = selector.get_category_by_id(category_id)

            if not category:
                return self.not_found_response(message="Category not found")

            if category.restaurant_id != int(restaurant_id):
                return self.error_response(
                    message="Category does not belong to this restaurant"
                )

            # ✅ Chỉ gọi service
            service = CategoryService()
            result = service.delete_category(category_id, request.user)

            if result['success']:
                return self.deleted_response(message=result['message'])
            else:
                return self.error_response(message=result['message'])

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CategoryReorderView(StandardResponseMixin, APIView):
    """
    POST /api/restaurants/{restaurant_id}/categories/reorder/ - Reorder categories
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Dishes'],
        summary="Reorder categories",
        description="Update display order for multiple categories",
        request=CategoryReorderBulkSerializer,
        responses={200}
    )
    def post(self, request, restaurant_id):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Validate request level
            required_fields = ['categories']
            for field in required_fields:
                if field not in request.data:
                    return self.error_response(
                        message=f"Missing required field: {field}"
                    )

            # ✅ Chỉ gọi service
            service = CategoryService()
            result = service.reorder_categories(restaurant_id, request.data['categories'], request.user)

            if result['success']:
                return self.success_response(
                    data=result['data'],
                    message=result['message']
                )
            else:
                return self.error_response(message=result['message'])

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MenuItemListView(StandardResponseMixin, ListAPIView):
    """
    GET /api/restaurants/{restaurant_id}/menu-items/ - List restaurant menu items
    POST /api/restaurants/{restaurant_id}/menu-items/ - Create new menu item
    """
    permission_classes = [permissions.AllowAny]  # Public access for GET
    pagination_class = StandardPageNumberPagination  # Standard pagination for menu items

    def get_serializer_class(self):
        return MenuItemListSerializer

    def get_queryset(self):
        """
        Get queryset for pagination - this will be used by ListAPIView
        """
        
        queryset = MenuItem.objects.filter(restaurant_id=self.kwargs['restaurant_id'], is_available=True)

        # Apply filters from query parameters
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        is_available = self.request.query_params.get('is_available')
        if is_available is not None:
            queryset = queryset.filter(is_available=is_available.lower() == 'true')

        is_featured = self.request.query_params.get('is_featured')
        if is_featured is not None:
            queryset = queryset.filter(is_featured=is_featured.lower() == 'true')

        is_vegetarian = self.request.query_params.get('is_vegetarian')
        if is_vegetarian is not None:
            queryset = queryset.filter(is_vegetarian=is_vegetarian.lower() == 'true')

        is_spicy = self.request.query_params.get('is_spicy')
        if is_spicy is not None:
            queryset = queryset.filter(is_spicy=is_spicy.lower() == 'true')

        min_price = self.request.query_params.get('min_price')
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except (ValueError, TypeError):
                pass

        max_price = self.request.query_params.get('max_price')
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except (ValueError, TypeError):
                pass

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset.order_by('category_id', 'display_order', 'name')

    @extend_schema(
        tags=['Dishes'],
        summary="List restaurant menu items",
        description="Get paginated list of menu items for a specific restaurant",
        parameters=[
            MenuItemSearchSerializer,
            {'name': 'page', 'type': 'int', 'required': False, 'in': 'query', 'description': 'Page number'},
            {'name': 'page_size', 'type': 'int', 'required': False, 'in': 'query', 'description': 'Items per page'}
        ],
        responses={200: MenuItemListSerializer(many=True)}
    )
    def get(self, request, restaurant_id):
        """
        GET method - Return paginated menu items
        """
        try:
            # Use Django's built-in pagination with our queryset
            queryset = self.get_queryset()

            # Apply pagination
            paginator = self.pagination_class()
            try:
                page = paginator.paginate_queryset(queryset, request)

                if page is not None:
                    serializer = self.get_serializer(page, many=True, context={'request': request})
                    # Use the custom pagination response format
                    return paginator.get_paginated_response(serializer.data)

                # Fallback if pagination fails
                serializer = self.get_serializer(queryset, many=True, context={'request': request})
                return self.success_response(
                    data=serializer.data,
                    message="Menu items retrieved successfully"
                )
            except Exception as pagination_error:
                # Fallback to non-paginated response if pagination fails
                serializer = self.get_serializer(queryset, many=True, context={'request': request})
                return self.success_response(
                    data=serializer.data,
                    message="Menu items retrieved successfully (pagination disabled)"
                )

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Dishes'],
        summary="Create menu item",
        description="Create new menu item for restaurant",
        request=MenuItemCreateSerializer,
        responses={201: MenuItemDetailSerializer}
    )
    def post(self, request, restaurant_id):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Validate request level (chỉ required fields)
            required_fields = ['name', 'slug', 'price']
            for field in required_fields:
                if field not in request.data:
                    return self.error_response(
                        message=f"Missing required field: {field}"
                    )

            # ✅ Chỉ gọi service
            service = MenuItemService()
            result = service.create_menu_item(restaurant_id, request.data, request.user)

            if result['success']:
                # Serialize menu item data before returning
                serializer = MenuItemDetailSerializer(result['data'], context={'request': request})
                return self.created_response(
                    data=serializer.data,
                    message=result['message']
                )
            else:
                return self.error_response(
                    message=result['message'],
                    errors=result.get('errors')
                )

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MenuItemDetailView(StandardResponseMixin, APIView):
    """
    GET /api/menu-items/{item_id}/ - Get menu item details (chỉ cần item_id)
    """
    permission_classes = [permissions.AllowAny]  # Public access for GET

    @extend_schema(
        tags=['Dishes'],
        summary="Get menu item details",
        description="Get detailed information about a specific menu item",
        responses={200: MenuItemDetailSerializer}
    )
    def get(self, request, item_id):
        """
        GET method - View chỉ làm 2 việc:
        1. Nhận request và validate cơ bản
        2. Gọi service/selector và return response
        """
        try:
            # ✅ Validate menu item exists
            selector = MenuItemSelector()
            menu_item = selector.get_menu_item_by_id(item_id)

            if not menu_item:
                return self.not_found_response(message="Menu item not found")

            # Serialize menu item data
            serializer = MenuItemDetailSerializer(menu_item, context={'request': request})

            return self.success_response(
                data=serializer.data,
                message="Menu item retrieved successfully"
            )

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MenuItemUpdateDeleteView(StandardResponseMixin, APIView):
    """
    PUT /api/restaurants/{restaurant_id}/menu-items/{item_id}/ - Update menu item
    DELETE /api/restaurants/{restaurant_id}/menu-items/{item_id}/ - Delete menu item
    """
    permission_classes = [permissions.AllowAny]  # Public access

    @extend_schema(
        tags=['Dishes'],
        summary="Update menu item",
        description="Update menu item information",
        request=MenuItemUpdateSerializer,
        responses={200: MenuItemDetailSerializer}
    )
    def put(self, request, restaurant_id, item_id):
        """
        PUT method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Validate menu item exists and belongs to restaurant
            selector = MenuItemSelector()
            menu_item = selector.get_menu_item_by_id(item_id)

            if not menu_item:
                return self.not_found_response(message="Menu item not found")

            if menu_item.restaurant_id != int(restaurant_id):
                return self.error_response(
                    message="Menu item does not belong to this restaurant"
                )

            # ✅ Chỉ gọi service
            service = MenuItemService()
            result = service.update_menu_item(item_id, request.data, request.user)

            if result['success']:
                # Serialize menu item data before returning
                serializer = MenuItemDetailSerializer(result['data'], context={'request': request})
                return self.success_response(
                    data=serializer.data,
                    message=result['message']
                )
            else:
                return self.error_response(
                    message=result['message'],
                    errors=result.get('errors')
                )

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Dishes'],
        summary="Delete menu item",
        description="Soft delete menu item",
        responses={204}
    )
    def delete(self, request, restaurant_id, item_id):
        """
        DELETE method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Validate menu item exists and belongs to restaurant
            selector = MenuItemSelector()
            menu_item = selector.get_menu_item_by_id(item_id)

            if not menu_item:
                return self.not_found_response(message="Menu item not found")

            if menu_item.restaurant_id != int(restaurant_id):
                return self.error_response(
                    message="Menu item does not belong to this restaurant"
                )

            # ✅ Chỉ gọi service
            service = MenuItemService()
            result = service.delete_menu_item(item_id, request.user)

            if result['success']:
                return self.deleted_response(message=result['message'])
            else:
                return self.error_response(message=result['message'])

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FeaturedMenuItemsView(StandardResponseMixin, ListAPIView):
    """
    GET /api/restaurants/{restaurant_id}/menu-items/featured/ - Get featured menu items
    """
    permission_classes = [permissions.AllowAny]
    pagination_class = SmallResultsSetPagination  # Featured items are typically limited

    def get_serializer_class(self):
        return FeaturedMenuItemSerializer

    def get_queryset(self):
        """
        Get queryset for featured items pagination
        """
        from apps.dishes.models import MenuItem
        queryset = MenuItem.objects.filter(
            restaurant_id=self.kwargs['restaurant_id'],
            is_available=True,
            is_featured=True
        ).order_by('display_order', 'name')

        # Apply limit if specified
        limit = self.request.query_params.get('limit')
        if limit:
            try:
                limit = int(limit)
                if limit > 0:
                    queryset = queryset[:limit]
            except (ValueError, TypeError):
                pass

        return queryset

    @extend_schema(
        tags=['Dishes'],
        summary="Get featured menu items",
        description="Get paginated list of featured menu items for restaurant",
        parameters=[
            {'name': 'limit', 'type': 'int', 'required': False, 'in': 'query', 'description': 'Maximum number of items to return'},
            {'name': 'page', 'type': 'int', 'required': False, 'in': 'query', 'description': 'Page number'},
            {'name': 'page_size', 'type': 'int', 'required': False, 'in': 'query', 'description': 'Items per page'}
        ],
        responses={200: FeaturedMenuItemSerializer(many=True)}
    )
    def get(self, request, restaurant_id):
        """
        GET method - Return paginated featured menu items
        """
        try:
            # Use Django's built-in pagination with our queryset
            queryset = self.get_queryset()

            # Apply pagination
            paginator = self.pagination_class()
            try:
                page = paginator.paginate_queryset(queryset, request)

                if page is not None:
                    serializer = self.get_serializer(page, many=True, context={'request': request})
                    # Use the custom pagination response format
                    return paginator.get_paginated_response(serializer.data)

                # Fallback if pagination fails
                serializer = self.get_serializer(queryset, many=True, context={'request': request})
                return self.success_response(
                    data=serializer.data,
                    message="Featured menu items retrieved successfully"
                )
            except Exception as pagination_error:
                # Fallback to non-paginated response if pagination fails
                serializer = self.get_serializer(queryset, many=True, context={'request': request})
                return self.success_response(
                    data=serializer.data,
                    message="Featured menu items retrieved successfully (pagination disabled)"
                )

        except ValueError:
            return self.error_response(
                message="Invalid limit parameter"
            )
        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MenuSearchView(StandardResponseMixin, ListAPIView):
    """
    GET /api/restaurants/{restaurant_id}/menu-items/search/ - Search menu items
    """
    permission_classes = [permissions.AllowAny]
    pagination_class = LargeResultsSetPagination  # Large results for search

    def get_serializer_class(self):
        return MenuItemListSerializer

    def get_queryset(self):
        """
        Get queryset for search pagination
        """
        from apps.dishes.models import MenuItem
        from django.db.models import Q
        search_query = self.request.query_params.get('q')

        if not search_query:
            return MenuItem.objects.none()

        queryset = MenuItem.objects.filter(
            restaurant_id=self.kwargs['restaurant_id'],
            is_available=True
        ).filter(
            # Search in name and description
            Q(name__icontains=search_query) | Q(description__icontains=search_query)
        )

        # Apply additional filters
        category_id = self.request.query_params.get('category')
        if category_id:
            try:
                queryset = queryset.filter(category_id=int(category_id))
            except (ValueError, TypeError):
                pass

        available_only = self.request.query_params.get('available_only', 'false').lower() == 'true'
        if available_only:
            queryset = queryset.filter(is_available=True)

        vegetarian = self.request.query_params.get('vegetarian', 'false').lower() == 'true'
        if vegetarian:
            queryset = queryset.filter(is_vegetarian=True)

        spicy = self.request.query_params.get('spicy', 'false').lower() == 'true'
        if spicy:
            queryset = queryset.filter(is_spicy=True)

        return queryset.order_by('-is_featured', 'display_order', 'name')

    @extend_schema(
        tags=['Dishes'],
        summary="Search menu items",
        description="Search menu items by name, description, or other criteria with pagination",
        parameters=[
            {'name': 'q', 'type': 'str', 'required': True, 'in': 'query', 'description': 'Search query'},
            {'name': 'category', 'type': 'int', 'required': False, 'in': 'query', 'description': 'Filter by category ID'},
            {'name': 'available_only', 'type': 'bool', 'required': False, 'in': 'query', 'description': 'Show only available items'},
            {'name': 'vegetarian', 'type': 'bool', 'required': False, 'in': 'query', 'description': 'Filter vegetarian items'},
            {'name': 'spicy', 'type': 'bool', 'required': False, 'in': 'query', 'description': 'Filter spicy items'},
            {'name': 'page', 'type': 'int', 'required': False, 'in': 'query', 'description': 'Page number'},
            {'name': 'page_size', 'type': 'int', 'required': False, 'in': 'query', 'description': 'Items per page'}
        ],
        responses={200: MenuItemListSerializer(many=True)}
    )
    def get(self, request, restaurant_id):
        """
        GET method - Return paginated search results
        """
        try:
            # Validate required search query
            search_query = request.query_params.get('q')
            if not search_query:
                return self.error_response(
                    message="Search query parameter 'q' is required"
                )

            # Use Django's built-in pagination with our queryset
            queryset = self.get_queryset()

            # Apply pagination
            paginator = self.pagination_class()
            try:
                page = paginator.paginate_queryset(queryset, request)

                if page is not None:
                    serializer = self.get_serializer(page, many=True, context={'request': request})
                    # Use the custom pagination response format
                    return paginator.get_paginated_response(serializer.data)

                # Fallback if pagination fails
                serializer = self.get_serializer(queryset, many=True, context={'request': request})
                return self.success_response(
                    data=serializer.data,
                    message=f"Search results for '{search_query}'"
                )
            except Exception as pagination_error:
                # Fallback to non-paginated response if pagination fails
                serializer = self.get_serializer(queryset, many=True, context={'request': request})
                return self.success_response(
                    data=serializer.data,
                    message=f"Search results for '{search_query}' (pagination disabled)"
                )

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MenuByCategoriesView(StandardResponseMixin, APIView):
    """
    GET /api/restaurants/{restaurant_id}/menu/ - Get menu organized by categories
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Dishes'],
        summary="Get menu by categories",
        description="Get restaurant menu organized by categories",
        parameters=[
            {'name': 'available_only', 'type': 'bool', 'required': False, 'in': 'query', 'description': 'Show only available items'},
            {'name': 'vegetarian', 'type': 'bool', 'required': False, 'in': 'query', 'description': 'Filter vegetarian items'},
            {'name': 'spicy', 'type': 'bool', 'required': False, 'in': 'query', 'description': 'Filter spicy items'}
        ],
        responses={200}
    )
    def get(self, request, restaurant_id):
        """
        GET method - View chỉ làm 2 việc:
        1. Nhận request và validate cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Build filters
            filters = {
                'is_available': request.query_params.get('available_only', 'false').lower() == 'true',
                'is_vegetarian': request.query_params.get('vegetarian', 'false').lower() == 'true',
                'is_spicy': request.query_params.get('spicy', 'false').lower() == 'true'
            }

            # ✅ Chỉ gọi service
            service = MenuItemService()
            result = service.get_menu_by_categories(restaurant_id, filters)

            if result['success']:
                return self.success_response(
                    data=result['data'],
                    message=result['message']
                )
            else:
                return self.error_response(message=result['message'])

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MenuToggleView(StandardResponseMixin, APIView):
    """
    POST /api/restaurants/{restaurant_id}/menu-items/toggle-availability/ - Toggle item availability
    POST /api/restaurants/{restaurant_id}/menu-items/toggle-featured/ - Toggle item featured status
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Dishes'],
        summary="Toggle menu item availability",
        description="Toggle availability status for multiple menu items",
        request=MenuItemToggleSerializer,
        responses={200}
    )
    def post(self, request, restaurant_id):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Determine toggle type based on URL
            toggle_type = 'availability' if 'toggle-availability' in request.path else 'featured'

            # ✅ Validate request level
            if 'item_ids' not in request.data:
                return self.error_response(
                    message="Missing required field: item_ids"
                )

            # ✅ Process toggle operations via service
            service = MenuItemService()
            results = []

            for item_id in request.data['item_ids']:
                # Validate menu item belongs to restaurant
                selector = MenuItemSelector()
                menu_item = selector.get_menu_item_by_id(item_id)

                if not menu_item:
                    results.append({
                        'item_id': item_id,
                        'success': False,
                        'message': 'Menu item not found'
                    })
                    continue

                if menu_item.restaurant_id != int(restaurant_id):
                    results.append({
                        'item_id': item_id,
                        'success': False,
                        'message': 'Menu item does not belong to this restaurant'
                    })
                    continue

                # Perform toggle operation
                if toggle_type == 'availability':
                    result = service.toggle_menu_item_availability(item_id, request.user)
                else:  # featured
                    result = service.toggle_menu_item_featured(item_id, request.user)

                results.append({
                    'item_id': item_id,
                    'success': result['success'],
                    'message': result['message']
                })

            return self.success_response(
                data={'results': results},
                message=f"Menu item {toggle_type} toggle completed"
            )

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BulkPriceUpdateView(StandardResponseMixin, APIView):
    """
    POST /api/restaurants/{restaurant_id}/menu-items/bulk-price-update/ - Bulk update prices
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Dishes'],
        summary="Bulk update menu item prices",
        description="Update prices for multiple menu items",
        request=BulkPriceUpdateSerializer,
        responses={200}
    )
    def post(self, request, restaurant_id):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Validate request level
            if 'price_updates' not in request.data:
                return self.error_response(
                    message="Missing required field: price_updates"
                )

            # ✅ Chỉ gọi service
            service = MenuItemService()
            result = service.update_menu_item_prices(restaurant_id, request.data['price_updates'], request.user)

            if result['success']:
                return self.success_response(
                    data=result['data'],
                    message=result['message']
                )
            else:
                return self.error_response(message=result['message'])

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MenuAnalyticsView(StandardResponseMixin, APIView):
    """
    GET /api/restaurants/{restaurant_id}/menu/analytics/ - Get menu analytics
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Dishes'],
        summary="Get menu analytics",
        description="Get comprehensive analytics for restaurant menu",
        responses={200: MenuAnalyticsSerializer}
    )
    def get(self, request, restaurant_id):
        """
        GET method - View chỉ làm 2 việc:
        1. Nhận request và validate cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Chỉ gọi service
            service = MenuItemService()
            result = service.get_menu_analytics(restaurant_id)

            if result['success']:
                return self.success_response(
                    data=result['data'],
                    message=result['message']
                )
            else:
                return self.error_response(message=result['message'])

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MenuItemImageView(StandardResponseMixin, APIView):
    """
    GET /api/restaurants/{restaurant_id}/menu-items/{item_id}/images/ - List all images for a menu item
    POST /api/restaurants/{restaurant_id}/menu-items/{item_id}/images/ - Add new image to menu item
    """
    permission_classes = [permissions.AllowAny]  # Public access for GET

    @extend_schema(
        tags=['Dishes'],
        summary="List menu item images",
        description="Get all images (primary + additional) for a specific menu item",
        responses={200: MenuItemImageSerializer(many=True)}
    )
    def get(self, request, restaurant_id, item_id):
        """
        GET method - List all images for a menu item
        """
        try:
            # Validate menu item exists and belongs to restaurant
            selector = MenuItemSelector()
            menu_item = selector.get_menu_item_by_id(item_id)

            if not menu_item:
                return self.not_found_response(message="Menu item not found")

            if menu_item.restaurant_id != int(restaurant_id):
                return self.error_response(
                    message="Menu item does not belong to this restaurant"
                )

            # Get all additional images
            from .models import MenuItemImage
            images = MenuItemImage.objects.filter(
                menu_item_id=item_id
            ).order_by('display_order', 'id')

            serializer = MenuItemImageSerializer(images, many=True, context={'request': request})

            # Include primary image info in response
            response_data = {
                'primary_image': menu_item.image if menu_item.image else None,
                'additional_images': serializer.data
            }

            return self.success_response(
                data=response_data,
                message="Menu item images retrieved successfully"
            )

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Dishes'],
        summary="Add image to menu item",
        description="Add a new additional image to a menu item",
        request=MenuItemImageCreateSerializer,
        responses={201: MenuItemImageSerializer}
    )
    def post(self, request, restaurant_id, item_id):
        """
        POST method - Add new image to menu item
        """
        try:
            # Validate menu item exists and belongs to restaurant
            selector = MenuItemSelector()
            menu_item = selector.get_menu_item_by_id(item_id)

            if not menu_item:
                return self.not_found_response(message="Menu item not found")

            if menu_item.restaurant_id != int(restaurant_id):
                return self.error_response(
                    message="Menu item does not belong to this restaurant"
                )

            # Validate required fields
            if 'image' not in request.data:
                return self.error_response(
                    message="Missing required field: image"
                )

            # Create new image
            from .models import MenuItemImage
            image_data = request.data.copy()
            image_data['menu_item'] = menu_item.id

            serializer = MenuItemImageCreateSerializer(data=image_data)
            if serializer.is_valid():
                image_obj = serializer.save(menu_item=menu_item)
                response_serializer = MenuItemImageSerializer(image_obj, context={'request': request})
                return self.created_response(
                    data=response_serializer.data,
                    message="Image added successfully"
                )
            else:
                return self.error_response(
                    message="Validation failed",
                    errors=serializer.errors
                )

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MenuItemImageDetailView(StandardResponseMixin, APIView):
    """
    PUT /api/restaurants/{restaurant_id}/menu-items/{item_id}/images/{image_id}/ - Update image
    DELETE /api/restaurants/{restaurant_id}/menu-items/{item_id}/images/{image_id}/ - Delete image
    """
    permission_classes = [permissions.AllowAny]  # Public access for GET

    @extend_schema(
        tags=['Dishes'],
        summary="Update menu item image",
        description="Update an additional image of a menu item",
        request=MenuItemImageUpdateSerializer,
        responses={200: MenuItemImageSerializer}
    )
    def put(self, request, restaurant_id, item_id, image_id):
        """
        PUT method - Update image
        """
        try:
            # Validate menu item exists and belongs to restaurant
            selector = MenuItemSelector()
            menu_item = selector.get_menu_item_by_id(item_id)

            if not menu_item:
                return self.not_found_response(message="Menu item not found")

            if menu_item.restaurant_id != int(restaurant_id):
                return self.error_response(
                    message="Menu item does not belong to this restaurant"
                )

            # Get image
            from .models import MenuItemImage
            try:
                image = MenuItemImage.objects.get(id=image_id, menu_item_id=item_id)
            except MenuItemImage.DoesNotExist:
                return self.not_found_response(message="Image not found")

            # Update image
            serializer = MenuItemImageUpdateSerializer(image, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                response_serializer = MenuItemImageSerializer(image, context={'request': request})
                return self.success_response(
                    data=response_serializer.data,
                    message="Image updated successfully"
                )
            else:
                return self.error_response(
                    message="Validation failed",
                    errors=serializer.errors
                )

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Dishes'],
        summary="Delete menu item image",
        description="Delete an additional image from a menu item",
        responses={204}
    )
    def delete(self, request, restaurant_id, item_id, image_id):
        """
        DELETE method - Delete image
        """
        try:
            # Validate menu item exists and belongs to restaurant
            selector = MenuItemSelector()
            menu_item = selector.get_menu_item_by_id(item_id)

            if not menu_item:
                return self.not_found_response(message="Menu item not found")

            if menu_item.restaurant_id != int(restaurant_id):
                return self.error_response(
                    message="Menu item does not belong to this restaurant"
                )

            # Get and delete image
            from .models import MenuItemImage
            try:
                image = MenuItemImage.objects.get(id=image_id, menu_item_id=item_id)
                image.delete()
                return self.deleted_response(message="Image deleted successfully")
            except MenuItemImage.DoesNotExist:
                return self.not_found_response(message="Image not found")

        except Exception as e:
            return self.error_response(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
