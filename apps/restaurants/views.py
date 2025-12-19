from rest_framework import permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from apps.api.mixins import StandardResponseMixin
from apps.api.response import ApiResponse
from django.shortcuts import get_object_or_404
from .selectors import RestaurantSelector, TableSelector
from .services import RestaurantService, TableService
from .serializers import (
    RestaurantListSerializer, RestaurantDetailSerializer, RestaurantCreateSerializer,
    RestaurantUpdateSerializer, NearbyRestaurantSerializer, RestaurantSearchSerializer,
    TableListSerializer, TableLayoutSerializer, TableCreateSerializer,
    TableUpdateSerializer, AvailableTableSerializer, TableSearchSerializer,
    BulkTableOperationSerializer
)


class RestaurantListView(StandardResponseMixin, APIView):
    """
    GET /api/restaurants/ - List restaurants with filtering
    POST /api/restaurants/ - Create new restaurant (admin/manager only)
    """
    permission_classes = [permissions.AllowAny]  # Public access for GET

    @extend_schema(
        tags=['Restaurants'],
        summary="List restaurants",
        description="Get list of restaurants with filtering and pagination",
        parameters=[RestaurantSearchSerializer],
        responses={200: RestaurantListSerializer(many=True)}
    )
    def get(self, request):
        """
        GET method - View chỉ làm 2 việc:
        1. Nhận request và validate cơ bản
        2. Gọi service/selector và return response
        """
        try:
            # ✅ Chỉ gọi service hoặc selector
            service = RestaurantService()
            filters = {
                'search': request.query_params.get('search'),
                'city': request.query_params.get('city'),
                'district': request.query_params.get('district'),
                'is_open': request.query_params.get('is_open'),
                'min_rating': request.query_params.get('min_rating')
            }

            # Remove None values
            filters = {k: v for k, v in filters.items() if v is not None}
            result = service.get_restaurants_with_business_logic(filters)

            if result['success']:
                return ApiResponse.success(
                    data=result['data'],
                    message=result['message']
                )
            else:
                return ApiResponse.error(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Restaurants'],
        summary="Create restaurant",
        description="Create new restaurant (admin/manager only)",
        request=RestaurantCreateSerializer,
        responses={201: RestaurantDetailSerializer}
    )
    def post(self, request):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Validate request level (chỉ required fields)
            required_fields = ['name', 'slug', 'phone_number', 'address', 'city', 'opening_time', 'closing_time']
            for field in required_fields:
                if field not in request.data:
                    return ApiResponse.bad_request(
                        message=f"Missing required field: {field}"
                    )

            # ✅ Chỉ gọi service
            service = RestaurantService()
            result = service.create_restaurant(request.data, request.user)

            if result['success']:
                # Serialize restaurant data before returning
                serializer = RestaurantDetailSerializer(result['data'], context={'request': request})
                return ApiResponse.created(
                    data=serializer.data,
                    message=result['message']
                )
            else:
                return ApiResponse.validation_error(
                    message=result['message'],
                    errors=result.get('errors')
                )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RestaurantDetailView(StandardResponseMixin, APIView):
    """
    GET /api/restaurants/{id}/ - Get restaurant details
    PUT /api/restaurants/{id}/ - Update restaurant (admin/manager only)
    PATCH /api/restaurants/{id}/ - Partial update restaurant (admin/manager only)
    DELETE /api/restaurants/{id}/ - Delete restaurant (admin only)
    """
    permission_classes = [permissions.AllowAny]  # Public access for GET

    @extend_schema(
        tags=['Restaurants'],
        summary="Get restaurant details",
        description="Get detailed information about a specific restaurant",
        responses={200: RestaurantDetailSerializer}
    )
    def get(self, request, restaurant_id):
        """
        GET method - View chỉ làm 2 việc:
        1. Nhận request và validate cơ bản
        2. Gọi service/selector và return response
        """
        try:
            # ✅ Chỉ gọi selector
            selector = RestaurantSelector()
            restaurant = selector.get_restaurant_by_id(restaurant_id)

            if not restaurant:
                return ApiResponse.not_found(message="Restaurant not found")

            # Serialize restaurant data
            serializer = RestaurantDetailSerializer(restaurant, context={'request': request})

            return ApiResponse.success(
                data=serializer.data,
                message="Restaurant retrieved successfully"
            )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Restaurants'],
        summary="Update restaurant",
        description="Update restaurant information (admin/manager only)",
        request=RestaurantUpdateSerializer,
        responses={200: RestaurantDetailSerializer}
    )
    def put(self, request, restaurant_id):
        """
        PUT method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Chỉ gọi service
            service = RestaurantService()
            result = service.update_restaurant(restaurant_id, request.data, request.user)

            if result['success']:
                # Serialize restaurant data before returning
                serializer = RestaurantDetailSerializer(result['data'], context={'request': request})
                return ApiResponse.success(
                    data=serializer.data,
                    message=result['message']
                )
            elif result['message'] == 'Restaurant not found':
                return ApiResponse.not_found(message=result['message'])
            else:
                return ApiResponse.validation_error(
                    message=result['message'],
                    errors=result.get('errors')
                )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Restaurants'],
        summary="Delete restaurant",
        description="Soft delete restaurant (admin only)",
        responses={204}
    )
    def delete(self, request, restaurant_id):
        """
        DELETE method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Chỉ gọi service
            service = RestaurantService()
            result = service.delete_restaurant(restaurant_id, request.user)

            if result['success']:
                return ApiResponse.no_content(message=result['message'])
            elif result['message'] == 'Restaurant not found':
                return ApiResponse.not_found(message=result['message'])
            else:
                return ApiResponse.error(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RestaurantBySlugView(StandardResponseMixin, APIView):
    """
    GET /api/restaurants/slug/{slug}/ - Get restaurant by slug
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Restaurants'],
        summary="Get restaurant by slug",
        description="Get restaurant information using slug",
        responses={200: RestaurantDetailSerializer}
    )
    def get(self, request, slug):
        """
        GET method - View chỉ làm 2 việc:
        1. Nhận request và validate cơ bản
        2. Gọi selector và return response
        """
        try:
            # ✅ Chỉ gọi selector
            selector = RestaurantSelector()
            restaurant = selector.get_restaurant_by_slug(slug)

            if not restaurant:
                return ApiResponse.not_found(message="Restaurant not found")

            # Serialize restaurant data
            serializer = RestaurantDetailSerializer(restaurant, context={'request': request})

            return ApiResponse.success(
                data=serializer.data,
                message="Restaurant retrieved successfully"
            )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NearbyRestaurantsView(StandardResponseMixin, APIView):
    """
    GET /api/restaurants/nearby/ - Find restaurants by location
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Restaurants'],
        summary="Find nearby restaurants",
        description="Find restaurants within specified radius from coordinates",
        parameters=[
            {'name': 'latitude', 'type': 'float', 'required': True, 'in': 'query'},
            {'name': 'longitude', 'type': 'float', 'required': True, 'in': 'query'},
            {'name': 'radius', 'type': 'float', 'required': False, 'in': 'query', 'description': 'Radius in km (default: 5)'}
        ],
        responses={200: NearbyRestaurantSerializer(many=True)}
    )
    def get(self, request):
        """
        GET method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Validate request level
            latitude = request.query_params.get('latitude')
            longitude = request.query_params.get('longitude')
            radius_km = float(request.query_params.get('radius', 5))

            if not latitude or not longitude:
                return ApiResponse.bad_request(
                    message="latitude and longitude are required"
                )

            # ✅ Chỉ gọi service
            service = RestaurantService()
            result = service.get_nearby_restaurants(float(latitude), float(longitude), radius_km)

            if result['success']:
                # Add request context for distance calculation
                for restaurant in result['data']:
                    restaurant['distance_km'] = self._calculate_distance(
                        float(latitude), float(longitude),
                        restaurant['latitude'], restaurant['longitude']
                    )

                return ApiResponse.success(
                    data=result['data'],
                    message=result['message']
                )
            else:
                return ApiResponse.error(message=result['message'])

        except ValueError:
            return ApiResponse.bad_request(
                message="Invalid latitude, longitude, or radius format"
            )
        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate distance between two coordinates (simplified)
        """
        from math import sqrt, radians

        # Rough approximation for small distances
        lat_diff = (lat2 - lat1) * 111  # ~111km per degree latitude
        lon_diff = (lon2 - lon1) * 111 * abs(lat1)  # longitude varies by latitude

        return round(sqrt(lat_diff**2 + lon_diff**2), 2)


class TableView(StandardResponseMixin, APIView):
    """
    GET /api/restaurants/{restaurant_id}/tables/ - Get restaurant tables
    POST /api/restaurants/{restaurant_id}/tables/ - Add new table
    """
    permission_classes = [permissions.AllowAny]  # Public access for GET

    @extend_schema(
        tags=['Restaurants'],
        summary="Get restaurant tables",
        description="Get list of tables for a specific restaurant",
        parameters=[TableSearchSerializer],
        responses={200: TableListSerializer(many=True)}
    )
    def get(self, request, restaurant_id):
        """
        GET method - View chỉ làm 2 việc:
        1. Nhận request và validate cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Validate restaurant exists
            selector = RestaurantSelector()
            restaurant = selector.get_restaurant_by_id(restaurant_id)
            if not restaurant:
                return ApiResponse.not_found(message="Restaurant not found")

            # ✅ Chỉ gọi service
            service = TableService()
            filters = {
                'status': request.query_params.get('status'),
                'floor': request.query_params.get('floor'),
                'section': request.query_params.get('section'),
                'min_capacity': request.query_params.get('min_capacity')
            }

            # Remove None values and convert numeric fields
            filters = {k: (float(v) if k in ['min_capacity', 'floor'] else v)
                      for k, v in filters.items() if v is not None}

            result = service.get_tables_with_layout(restaurant_id, filters)

            if result['success']:
                return ApiResponse.success(
                    data=result['data'],
                    message=result['message']
                )
            else:
                return ApiResponse.error(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Restaurants'],
        summary="Create table",
        description="Add new table to restaurant",
        request=TableCreateSerializer,
        responses={201: TableListSerializer}
    )
    def post(self, request, restaurant_id):
        """
        POST method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Validate request level
            required_fields = ['table_number', 'capacity']
            for field in required_fields:
                if field not in request.data:
                    return ApiResponse.bad_request(
                        message=f"Missing required field: {field}"
                    )

            # ✅ Validate restaurant exists
            selector = RestaurantSelector()
            restaurant = selector.get_restaurant_by_id(restaurant_id)
            if not restaurant:
                return ApiResponse.not_found(message="Restaurant not found")

            # ✅ Chỉ gọi service
            service = TableService()
            result = service.create_table(restaurant_id, request.data, request.user)

            if result['success']:
                return ApiResponse.created(
                    data=result['data'],
                    message=result['message']
                )
            else:
                return ApiResponse.validation_error(
                    message=result['message'],
                    errors=result.get('errors')
                )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TableDetailView(StandardResponseMixin, APIView):
    """
    GET /api/restaurants/{restaurant_id}/tables/{table_id}/ - Get table details
    PUT /api/restaurants/{restaurant_id}/tables/{table_id}/ - Update table
    DELETE /api/restaurants/{restaurant_id}/tables/{table_id}/ - Delete table
    """
    permission_classes = [permissions.AllowAny]  # Public access for GET

    @extend_schema(
        tags=['Restaurants'],
        summary="Get table details",
        description="Get detailed information about a specific table",
        responses={200: TableListSerializer}
    )
    def get(self, request, restaurant_id, table_id):
        """
        GET method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi selector và return response
        """
        try:
            # ✅ Validate restaurant exists
            restaurant_selector = RestaurantSelector()
            restaurant = restaurant_selector.get_restaurant_by_id(restaurant_id)
            if not restaurant:
                return ApiResponse.not_found(message="Restaurant not found")

            # ✅ Chỉ gọi selector
            table_selector = TableSelector()
            table = table_selector.get_table_by_id(table_id)

            if not table:
                return ApiResponse.not_found(message="Table not found")

            # Validate table belongs to restaurant
            if table.restaurant_id != int(restaurant_id):
                return ApiResponse.bad_request(
                    message="Table does not belong to this restaurant"
                )

            # Serialize table data
            serializer = TableListSerializer(table)

            return ApiResponse.success(
                data=serializer.data,
                message="Table retrieved successfully"
            )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Restaurants'],
        summary="Update table",
        description="Update table information",
        request=TableUpdateSerializer,
        responses={200: TableListSerializer}
    )
    def put(self, request, restaurant_id, table_id):
        """
        PUT method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Chỉ gọi service
            service = TableService()
            result = service.update_table(table_id, request.data, request.user)

            if result['success']:
                # Validate table belongs to restaurant
                if result['data'].restaurant_id != int(restaurant_id):
                    return ApiResponse.bad_request(
                        message="Table does not belong to this restaurant"
                    )

                return ApiResponse.success(
                    data=result['data'],
                    message=result['message']
                )
            elif result['message'] == 'Table not found':
                return ApiResponse.not_found(message=result['message'])
            else:
                return ApiResponse.validation_error(
                    message=result['message'],
                    errors=result.get('errors')
                )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Restaurants'],
        summary="Delete table",
        description="Soft delete table",
        responses={204}
    )
    def delete(self, request, restaurant_id, table_id):
        """
        DELETE method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Validate table belongs to restaurant before deletion
            table_selector = TableSelector()
            table = table_selector.get_table_by_id(table_id)

            if not table:
                return ApiResponse.not_found(message="Table not found")

            if table.restaurant_id != int(restaurant_id):
                return ApiResponse.bad_request(
                    message="Table does not belong to this restaurant"
                )

            # ✅ Chỉ gọi service
            service = TableService()
            result = service.delete_table(table_id, request.user)

            if result['success']:
                return ApiResponse.no_content(message=result['message'])
            else:
                return ApiResponse.error(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AvailableTablesView(StandardResponseMixin, APIView):
    """
    GET /api/restaurants/{restaurant_id}/tables/available/ - Get available tables
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Restaurants'],
        summary="Get available tables",
        description="Get list of available tables for restaurant",
        parameters=[
            {'name': 'capacity', 'type': 'int', 'required': False, 'in': 'query', 'description': 'Minimum capacity'}
        ],
        responses={200: AvailableTableSerializer(many=True)}
    )
    def get(self, request, restaurant_id):
        """
        GET method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi selector và return response
        """
        try:
            # ✅ Validate restaurant exists
            restaurant_selector = RestaurantSelector()
            restaurant = restaurant_selector.get_restaurant_by_id(restaurant_id)
            if not restaurant:
                return ApiResponse.not_found(message="Restaurant not found")

            # ✅ Chỉ gọi selector
            table_selector = TableSelector()
            capacity = request.query_params.get('capacity')
            capacity = int(capacity) if capacity else None

            tables = table_selector.get_available_tables(restaurant_id, capacity)

            # Serialize tables data
            serializer = AvailableTableSerializer(tables, many=True)

            return ApiResponse.success(
                data=serializer.data,
                message="Available tables retrieved successfully"
            )

        except ValueError:
            return ApiResponse.bad_request(
                message="Invalid capacity format"
            )
        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TableLayoutView(StandardResponseMixin, APIView):
    """
    GET /api/restaurants/{restaurant_id}/tables/layout/ - Get restaurant table layout
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Restaurants'],
        summary="Get table layout",
        description="Get restaurant floor plan with table positions",
        responses={200: TableLayoutSerializer(many=True)}
    )
    def get(self, request, restaurant_id):
        """
        GET method - View chỉ làm 2 việc:
        1. Validate request level cơ bản
        2. Gọi service và return response
        """
        try:
            # ✅ Validate restaurant exists
            restaurant_selector = RestaurantSelector()
            restaurant = restaurant_selector.get_restaurant_by_id(restaurant_id)
            if not restaurant:
                return ApiResponse.not_found(message="Restaurant not found")

            # ✅ Chỉ gọi service
            service = TableService()
            result = service.get_tables_with_layout(restaurant_id)

            if result['success']:
                return ApiResponse.success(
                    data=result['data'],
                    message="Table layout retrieved successfully"
                )
            else:
                return ApiResponse.error(message=result['message'])

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BulkTableOperationView(StandardResponseMixin, APIView):
    """
    POST /api/restaurants/{restaurant_id}/tables/bulk/ - Bulk table operations
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['Restaurants'],
        summary="Bulk table operations",
        description="Perform bulk operations on multiple tables",
        request=BulkTableOperationSerializer,
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
            required_fields = ['action', 'table_ids']
            for field in required_fields:
                if field not in request.data:
                    return ApiResponse.bad_request(
                        message=f"Missing required field: {field}"
                    )

            # ✅ Validate restaurant exists
            restaurant_selector = RestaurantSelector()
            restaurant = restaurant_selector.get_restaurant_by_id(restaurant_id)
            if not restaurant:
                return ApiResponse.not_found(message="Restaurant not found")

            # ✅ Process bulk operations via service
            service = TableService()
            results = []

            for table_id in request.data['table_ids']:
                # Validate table belongs to restaurant
                table_selector = TableSelector()
                table = table_selector.get_table_by_id(table_id)

                if not table:
                    results.append({'table_id': table_id, 'success': False, 'message': 'Table not found'})
                    continue

                if table.restaurant_id != int(restaurant_id):
                    results.append({'table_id': table_id, 'success': False, 'message': 'Table does not belong to this restaurant'})
                    continue

                # Perform operation based on action
                action = request.data['action']
                operation_data = request.data.get('data', {})

                if action == 'update_status':
                    if 'status' not in operation_data:
                        results.append({'table_id': table_id, 'success': False, 'message': 'Status is required for update_status action'})
                        continue

                    result = service.update_table(table_id, {'status': operation_data['status']}, request.user)

                elif action == 'delete':
                    result = service.delete_table(table_id, request.user)

                elif action == 'update_floor':
                    if 'floor' not in operation_data:
                        results.append({'table_id': table_id, 'success': False, 'message': 'Floor is required for update_floor action'})
                        continue

                    result = service.update_table(table_id, {'floor': operation_data['floor']}, request.user)

                else:
                    results.append({'table_id': table_id, 'success': False, 'message': f'Unknown action: {action}'})
                    continue

                results.append({
                    'table_id': table_id,
                    'success': result['success'],
                    'message': result['message']
                })

            return ApiResponse.success(
                data={'results': results},
                message="Bulk operation completed"
            )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

