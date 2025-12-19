"""
Views for Chain Dishes APIs
"""
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.openapi import OpenApiParameter
from apps.api.mixins import StandardResponseMixin
from apps.api.response import ApiResponse
from apps.api.pagination import StandardPageNumberPagination
from apps.restaurants.selectors import RestaurantChainSelector
from .selectors import CategorySelector, MenuItemSelector
from .serializers import (
    CategoryListSerializer,
    CategoryWithItemsSerializer,
    MenuItemListSerializer,
    MenuItemDetailSerializer
)


class ChainCategoriesView(StandardResponseMixin, APIView):
    """
    GET /api/chains/{chain_id}/categories/ - Get categories of chain
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        tags=['Chain Menu'],
        summary="Get chain categories",
        description="Get list of all categories in chain's menu",
        parameters=[
            {'name': 'search', 'type': 'string', 'required': False, 'in': 'query'},
            {'name': 'with_items', 'type': 'boolean', 'required': False, 'in': 'query', 
             'description': 'Include menu items in each category'}
        ],
        responses={200: CategoryListSerializer(many=True)}
    )
    def get(self, request, chain_id):
        """Get categories of chain"""
        try:
            # Validate chain exists
            chain_selector = RestaurantChainSelector()
            chain = chain_selector.get_chain_by_id(chain_id)
            if not chain:
                return ApiResponse.not_found(message="Chain not found")
            
            # Get categories
            category_selector = CategorySelector()
            filters = {
                'search': request.query_params.get('search')
            }
            filters = {k: v for k, v in filters.items() if v is not None}
            
            categories = category_selector.get_categories_by_chain(chain_id, filters)
            
            # Choose serializer based on with_items parameter
            with_items = request.query_params.get('with_items', '').lower() == 'true'
            if with_items:
                serializer = CategoryWithItemsSerializer(
                    categories, many=True, context={'request': request}
                )
            else:
                serializer = CategoryListSerializer(
                    categories, many=True, context={'request': request}
                )
            
            return ApiResponse.success(
                data=serializer.data,
                message="Categories retrieved successfully"
            )
        
        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChainCategoryDetailView(StandardResponseMixin, APIView):
    """
    GET /api/chains/{chain_id}/categories/{category_id}/ - Get category details
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        tags=['Chain Menu'],
        summary="Get chain category details",
        description="Get detailed information about a category including its items",
        responses={200: CategoryWithItemsSerializer}
    )
    def get(self, request, chain_id, category_id):
        """Get category details with items"""
        try:
            # Validate chain exists
            chain_selector = RestaurantChainSelector()
            chain = chain_selector.get_chain_by_id(chain_id)
            if not chain:
                return ApiResponse.not_found(message="Chain not found")
            
            # Get category
            category_selector = CategorySelector()
            category = category_selector.get_category_by_id(category_id)
            
            if not category:
                return ApiResponse.not_found(message="Category not found")
            
            # Validate category belongs to chain
            if category.chain_id != chain_id:
                return ApiResponse.bad_request(
                    message="Category does not belong to this chain"
                )
            
            serializer = CategoryWithItemsSerializer(category, context={'request': request})
            
            return ApiResponse.success(
                data=serializer.data,
                message="Category retrieved successfully"
            )
        
        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChainMenuItemsView(StandardResponseMixin, APIView):
    """
    GET /api/chains/{chain_id}/menu-items/ - Get menu items of chain
    """
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardPageNumberPagination

    @extend_schema(
        tags=['Chain Menu'],
        summary="Get chain menu items",
        description="Get list of menu items in chain's menu with optional category filtering and pagination",
        parameters=[
            OpenApiParameter(
                name='category_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by category ID (optional - if not specified, returns all dishes)'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search menu items by name or description'
            ),
            OpenApiParameter(
                name='is_featured',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter featured items'
            ),
            OpenApiParameter(
                name='is_vegetarian',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter vegetarian items'
            ),
            OpenApiParameter(
                name='is_spicy',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter spicy items'
            ),
            OpenApiParameter(
                name='min_price',
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
                description='Minimum price filter'
            ),
            OpenApiParameter(
                name='max_price',
                type=OpenApiTypes.NUMBER,
                location=OpenApiParameter.QUERY,
                description='Maximum price filter'
            ),
            OpenApiParameter(
                name='price_range',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Price range: budget|mid|premium|luxury'
            ),
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Page number for pagination'
            ),
            OpenApiParameter(
                name='page_size',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Number of items per page (default: 20, max: 100)'
            ),
        ],
        responses={200: MenuItemListSerializer(many=True)}
    )
    def get(self, request, chain_id):
        """Get menu items of chain with optional category filtering and pagination"""
        try:
            # Validate chain exists
            chain_selector = RestaurantChainSelector()
            chain = chain_selector.get_chain_by_id(chain_id)
            if not chain:
                return ApiResponse.not_found(message="Chain not found")

            # Get menu items
            menu_item_selector = MenuItemSelector()
            filters = {
                'search': request.query_params.get('search'),
                'is_featured': request.query_params.get('is_featured'),
                'is_vegetarian': request.query_params.get('is_vegetarian'),
                'is_spicy': request.query_params.get('is_spicy'),
                'min_price': request.query_params.get('min_price'),
                'max_price': request.query_params.get('max_price'),
                'price_range': request.query_params.get('price_range')
            }

            # Handle category_id as optional parameter
            category_id = request.query_params.get('category_id')
            if category_id:
                try:
                    filters['category_id'] = int(category_id)
                except (ValueError, TypeError):
                    pass  # Invalid category_id will be ignored

            # Convert boolean strings
            for bool_field in ['is_featured', 'is_vegetarian', 'is_spicy']:
                if filters.get(bool_field):
                    filters[bool_field] = filters[bool_field].lower() == 'true'

            # Convert numeric strings
            for num_field in ['min_price', 'max_price']:
                if filters.get(num_field):
                    try:
                        filters[num_field] = float(filters[num_field])
                    except (ValueError, TypeError):
                        filters[num_field] = None

            # Remove None values
            filters = {k: v for k, v in filters.items() if v is not None}

            # Get menu items queryset
            menu_items = menu_item_selector.get_menu_items_by_chain(chain_id, filters)

            # Apply pagination
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(menu_items, request)

            if page is not None:
                serializer = MenuItemListSerializer(page, many=True, context={'request': request})
                return paginator.get_paginated_response(serializer.data)

            # Fallback for non-paginated response
            serializer = MenuItemListSerializer(menu_items, many=True, context={'request': request})
            return ApiResponse.success(
                data=serializer.data,
                message="Menu items retrieved successfully"
            )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChainMenuItemDetailView(StandardResponseMixin, APIView):
    """
    GET /api/chains/{chain_id}/menu-items/{item_id}/ - Get menu item details
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        tags=['Chain Menu'],
        summary="Get chain menu item details",
        description="Get detailed information about a menu item",
        responses={200: MenuItemDetailSerializer}
    )
    def get(self, request, chain_id, item_id):
        """Get menu item details"""
        try:
            # Validate chain exists
            chain_selector = RestaurantChainSelector()
            chain = chain_selector.get_chain_by_id(chain_id)
            if not chain:
                return ApiResponse.not_found(message="Chain not found")
            
            # Get menu item
            menu_item_selector = MenuItemSelector()
            menu_item = menu_item_selector.get_menu_item_by_id(item_id)
            
            if not menu_item:
                return ApiResponse.not_found(message="Menu item not found")
            
            # Validate item belongs to chain
            if menu_item.chain_id != chain_id:
                return ApiResponse.bad_request(
                    message="Menu item does not belong to this chain"
                )
            
            serializer = MenuItemDetailSerializer(menu_item, context={'request': request})
            
            return ApiResponse.success(
                data=serializer.data,
                message="Menu item retrieved successfully"
            )
        
        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChainCategoryMenuItemsView(StandardResponseMixin, APIView):
    """
    GET /api/chains/{chain_id}/categories/{category_id}/items/ - Get items in category
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        tags=['Chain Menu'],
        summary="Get menu items in category",
        description="Get all menu items in a specific category",
        parameters=[
            {'name': 'is_featured', 'type': 'boolean', 'required': False, 'in': 'query'},
            {'name': 'is_vegetarian', 'type': 'boolean', 'required': False, 'in': 'query'},
            {'name': 'is_spicy', 'type': 'boolean', 'required': False, 'in': 'query'},
            {'name': 'min_price', 'type': 'number', 'required': False, 'in': 'query'},
            {'name': 'max_price', 'type': 'number', 'required': False, 'in': 'query'}
        ],
        responses={200: MenuItemListSerializer(many=True)}
    )
    def get(self, request, chain_id, category_id):
        """Get items in category"""
        try:
            # Validate chain exists
            chain_selector = RestaurantChainSelector()
            chain = chain_selector.get_chain_by_id(chain_id)
            if not chain:
                return ApiResponse.not_found(message="Chain not found")
            
            # Validate category exists and belongs to chain
            category_selector = CategorySelector()
            category = category_selector.get_category_by_id(category_id)
            
            if not category:
                return ApiResponse.not_found(message="Category not found")
            
            if category.chain_id != chain_id:
                return ApiResponse.bad_request(
                    message="Category does not belong to this chain"
                )
            
            # Get menu items
            menu_item_selector = MenuItemSelector()
            filters = {
                'is_featured': request.query_params.get('is_featured'),
                'is_vegetarian': request.query_params.get('is_vegetarian'),
                'is_spicy': request.query_params.get('is_spicy'),
                'min_price': request.query_params.get('min_price'),
                'max_price': request.query_params.get('max_price')
            }
            
            # Convert boolean strings
            for bool_field in ['is_featured', 'is_vegetarian', 'is_spicy']:
                if filters.get(bool_field):
                    filters[bool_field] = filters[bool_field].lower() == 'true'
            
            # Convert numeric strings
            for num_field in ['min_price', 'max_price']:
                if filters.get(num_field):
                    try:
                        filters[num_field] = float(filters[num_field])
                    except (ValueError, TypeError):
                        filters[num_field] = None
            
            # Remove None values
            filters = {k: v for k, v in filters.items() if v is not None}
            
            menu_items = menu_item_selector.get_menu_items_by_category_and_chain(
                chain_id, category_id, filters
            )
            serializer = MenuItemListSerializer(menu_items, many=True, context={'request': request})
            
            return ApiResponse.success(
                data=serializer.data,
                message="Menu items retrieved successfully"
            )
        
        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

