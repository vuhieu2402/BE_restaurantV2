"""
Views for RestaurantChain APIs
"""
from rest_framework import permissions, status
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from apps.api.mixins import StandardResponseMixin
from apps.api.response import ApiResponse
from .selectors import RestaurantChainSelector, RestaurantSelector
from .services import RestaurantChainService
from .serializers import (
    RestaurantChainListSerializer,
    RestaurantChainDetailSerializer,
    RestaurantChainCreateSerializer,
    RestaurantChainUpdateSerializer,
    NearestBranchSerializer,
    RestaurantListSerializer
)


class RestaurantChainListView(StandardResponseMixin, APIView):
    """
    GET /api/chains/ - List all chains
    POST /api/chains/ - Create new chain (admin only)
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        tags=['Restaurant Chains'],
        summary="List restaurant chains",
        description="Get list of all restaurant chains",
        responses={200: RestaurantChainListSerializer(many=True)}
    )
    def get(self, request):
        """Get list of chains"""
        try:
            service = RestaurantChainService()
            filters = {
                'search': request.query_params.get('search')
            }
            filters = {k: v for k, v in filters.items() if v is not None}
            
            result = service.get_chains(filters)
            
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
        tags=['Restaurant Chains'],
        summary="Create restaurant chain",
        description="Create new restaurant chain (admin only)",
        request=RestaurantChainCreateSerializer,
        responses={201: RestaurantChainDetailSerializer}
    )
    def post(self, request):
        """Create new chain"""
        try:
            # Validate required fields
            required_fields = ['name', 'slug']
            for field in required_fields:
                if field not in request.data:
                    return ApiResponse.bad_request(
                        message=f"Missing required field: {field}"
                    )
            
            service = RestaurantChainService()
            result = service.create_chain(request.data, request.user)
            
            if result['success']:
                serializer = RestaurantChainDetailSerializer(
                    result['data'],
                    context={'request': request}
                )
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


class RestaurantChainDetailView(StandardResponseMixin, APIView):
    """
    GET /api/chains/{id}/ - Get chain details
    PUT /api/chains/{id}/ - Update chain (admin only)
    DELETE /api/chains/{id}/ - Delete chain (admin only)
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        tags=['Restaurant Chains'],
        summary="Get chain details",
        description="Get detailed information about a restaurant chain",
        responses={200: RestaurantChainDetailSerializer}
    )
    def get(self, request, chain_id):
        """Get chain details"""
        try:
            selector = RestaurantChainSelector()
            chain = selector.get_chain_by_id(chain_id)
            
            if not chain:
                return ApiResponse.not_found(message="Chain not found")
            
            serializer = RestaurantChainDetailSerializer(
                chain,
                context={'request': request}
            )
            
            return ApiResponse.success(
                data=serializer.data,
                message="Chain retrieved successfully"
            )
        
        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        tags=['Restaurant Chains'],
        summary="Update chain",
        description="Update chain information (admin only)",
        request=RestaurantChainUpdateSerializer,
        responses={200: RestaurantChainDetailSerializer}
    )
    def put(self, request, chain_id):
        """Update chain"""
        try:
            service = RestaurantChainService()
            result = service.update_chain(chain_id, request.data, request.user)
            
            if result['success']:
                serializer = RestaurantChainDetailSerializer(
                    result['data'],
                    context={'request': request}
                )
                return ApiResponse.success(
                    data=serializer.data,
                    message=result['message']
                )
            elif result['message'] == 'Chain not found':
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
        tags=['Restaurant Chains'],
        summary="Delete chain",
        description="Soft delete chain (admin only)",
        responses={204}
    )
    def delete(self, request, chain_id):
        """Delete chain"""
        try:
            service = RestaurantChainService()
            result = service.delete_chain(chain_id, request.user)
            
            if result['success']:
                return ApiResponse.no_content(message=result['message'])
            elif result['message'] == 'Chain not found':
                return ApiResponse.not_found(message=result['message'])
            else:
                return ApiResponse.error(message=result['message'])
        
        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RestaurantChainBySlugView(StandardResponseMixin, APIView):
    """
    GET /api/chains/slug/{slug}/ - Get chain by slug
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        tags=['Restaurant Chains'],
        summary="Get chain by slug",
        description="Get chain information using slug",
        responses={200: RestaurantChainDetailSerializer}
    )
    def get(self, request, slug):
        """Get chain by slug"""
        try:
            selector = RestaurantChainSelector()
            chain = selector.get_chain_by_slug(slug)
            
            if not chain:
                return ApiResponse.not_found(message="Chain not found")
            
            serializer = RestaurantChainDetailSerializer(
                chain,
                context={'request': request}
            )
            
            return ApiResponse.success(
                data=serializer.data,
                message="Chain retrieved successfully"
            )
        
        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChainBranchesView(StandardResponseMixin, APIView):
    """
    GET /api/chains/{chain_id}/branches/ - Get all branches of a chain
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        tags=['Restaurant Chains'],
        summary="Get chain branches",
        description="Get list of all branches (restaurants) in a chain",
        responses={200: RestaurantListSerializer(many=True)}
    )
    def get(self, request, chain_id):
        """Get chain branches"""
        try:
            chain_selector = RestaurantChainSelector()
            chain = chain_selector.get_chain_by_id(chain_id)
            
            if not chain:
                return ApiResponse.not_found(message="Chain not found")
            
            filters = {
                'city': request.query_params.get('city'),
                'is_open': request.query_params.get('is_open')
            }
            filters = {k: v for k, v in filters.items() if v is not None}
            
            branches = chain_selector.get_chain_branches(chain_id, filters)
            serializer = RestaurantListSerializer(branches, many=True, context={'request': request})
            
            return ApiResponse.success(
                data=serializer.data,
                message="Branches retrieved successfully"
            )
        
        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NearestBranchView(StandardResponseMixin, APIView):
    """
    GET /api/chains/{chain_id}/nearest-branch/ - Find nearest branch for delivery
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        tags=['Restaurant Chains'],
        summary="Find nearest branch",
        description="Find the nearest branch that can deliver to specified location",
        parameters=[
            {'name': 'latitude', 'type': 'float', 'required': True, 'in': 'query'},
            {'name': 'longitude', 'type': 'float', 'required': True, 'in': 'query'}
        ],
        responses={200: NearestBranchSerializer}
    )
    def get(self, request, chain_id):
        """Find nearest branch"""
        try:
            latitude = request.query_params.get('latitude')
            longitude = request.query_params.get('longitude')
            
            if not latitude or not longitude:
                return ApiResponse.bad_request(
                    message="latitude and longitude are required"
                )
            
            try:
                latitude = float(latitude)
                longitude = float(longitude)
            except ValueError:
                return ApiResponse.bad_request(
                    message="Invalid latitude or longitude format"
                )
            
            service = RestaurantChainService()
            result = service.get_nearest_branch(chain_id, latitude, longitude)
            
            if result['success']:
                return ApiResponse.success(
                    data=result['data'],
                    message=result['message']
                )
            elif result['message'] == 'Chain not found':
                return ApiResponse.not_found(message=result['message'])
            else:
                return ApiResponse.error(message=result['message'])
        
        except Exception as e:
            return ApiResponse.error(
                message=f"Error: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

