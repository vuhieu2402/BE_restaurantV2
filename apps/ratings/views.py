from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.openapi import OpenApiParameter
from apps.api.mixins import StandardResponseMixin
from apps.api.pagination import StandardPageNumberPagination
from apps.api.response import ApiResponse
from .serializers import (
    MenuItemReviewSerializer,
    MenuItemReviewCreateSerializer,
    MenuItemReviewSummarySerializer,
    ReviewResponseSerializer,
    ReviewResponseCreateSerializer
)
from .services import RatingService, ReviewResponseService, RatingAnalyticsService
from .selectors import RatingSelector
from .models import MenuItemReview


class MenuItemRatingView(StandardResponseMixin, APIView):
    """
    GET /api/chains/{chain_id}/menu-items/{item_id}/ratings/ - Get item ratings
    POST /api/chains/{chain_id}/menu-items/{item_id}/ratings/ - Create/update rating
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = StandardPageNumberPagination

    @extend_schema(
        tags=['Menu Ratings'],
        summary="Get menu item ratings",
        description="Get paginated list of ratings for a specific menu item",
        parameters=[
            OpenApiParameter(
                name='rating',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by specific rating (1-5)'
            ),
            OpenApiParameter(
                name='verified_only',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Show only verified purchase reviews'
            ),
            OpenApiParameter(
                name='has_review',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Show only reviews with text content'
            ),
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Page number'
            ),
            OpenApiParameter(
                name='page_size',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Items per page'
            ),
        ],
        responses={200: MenuItemReviewSerializer(many=True)}
    )
    def get(self, request, chain_id, item_id):
        """Get ratings for a specific menu item"""
        try:
            # Validate menu item exists and belongs to chain
            from apps.dishes.models import MenuItem
            try:
                menu_item = MenuItem.objects.get(
                    id=item_id, chain_id=chain_id, is_available=True
                )
            except MenuItem.DoesNotExist:
                return ApiResponse.not_found(message="Menu item not found")

            # Get filters from query parameters
            filters = {
                'rating': request.query_params.get('rating'),
                'verified_only': request.query_params.get('verified_only', '').lower() == 'true',
                'has_review': request.query_params.get('has_review', '').lower() == 'true'
            }

            # Remove None values
            filters = {k: v for k, v in filters.items() if v is not None}

            # Get ratings
            rating_selector = RatingSelector()
            ratings = rating_selector.get_ratings_for_menu_item(item_id, filters)

            # Apply pagination
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(ratings, request)

            if page is not None:
                serializer = MenuItemReviewSerializer(
                    page, many=True, context={'request': request}
                )
                return paginator.get_paginated_response(serializer.data)

            # Fallback for non-paginated response
            serializer = MenuItemReviewSerializer(
                ratings, many=True, context={'request': request}
            )
            return ApiResponse.success(
                data=serializer.data,
                message="Ratings retrieved successfully"
            )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error retrieving ratings: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Menu Ratings'],
        summary="Create/update menu item rating",
        description="Create a new rating or update existing rating for a menu item",
        request=MenuItemReviewCreateSerializer,
        responses={201: MenuItemReviewSerializer}
    )
    def post(self, request, chain_id, item_id):
        """Create or update a rating for a menu item"""
        try:
            # Validate menu item exists and belongs to chain
            from apps.dishes.models import MenuItem
            try:
                menu_item = MenuItem.objects.get(
                    id=item_id, chain_id=chain_id, is_available=True
                )
            except MenuItem.DoesNotExist:
                return ApiResponse.not_found(message="Menu item not found")

            # Validate user is authenticated for rating
            if not request.user.is_authenticated:
                return ApiResponse.unauthorized(
                    message="Authentication required to create ratings"
                )

            # Prepare rating data
            rating_data = {
                'menu_item': menu_item.id,
                'rating': request.data.get('rating'),
                'content': request.data.get('content') or request.data.get('review_text', '')
            }

            # Validate rating data using serializer
            serializer = MenuItemReviewCreateSerializer(
                data=rating_data,
                context={'request': request}
            )
            if not serializer.is_valid():
                return ApiResponse.bad_request(
                    message="Validation failed",
                    errors=serializer.errors
                )

            # Create/update rating using service
            rating_service = RatingService()
            result = rating_service.create_or_update_rating(
                request.user, menu_item.id, rating_data
            )

            return result

        except Exception as e:
            return ApiResponse.error(
                message=f"Error creating rating: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MenuItemRatingDetailView(StandardResponseMixin, APIView):
    """
    GET /api/chains/{chain_id}/menu-items/{item_id}/ratings/{rating_id}/ - Get specific rating
    PUT /api/chains/{chain_id}/menu-items/{item_id}/ratings/{rating_id}/ - Update rating
    DELETE /api/chains/{chain_id}/menu-items/{item_id}/ratings/{rating_id}/ - Delete rating
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @extend_schema(
        tags=['Menu Ratings'],
        summary="Get specific rating",
        description="Get detailed information about a specific rating",
        responses={200: MenuItemReviewSerializer}
    )
    def get(self, request, chain_id, item_id, rating_id):
        """Get specific rating details"""
        try:
            rating_selector = RatingSelector()
            rating = rating_selector.get_rating_by_id(rating_id)

            if not rating:
                return ApiResponse.not_found(message="Rating not found")

            # Validate rating belongs to the specified item and chain
            if rating.menu_item_id != item_id or rating.menu_item.chain_id != chain_id:
                return ApiResponse.bad_request(
                    message="Rating does not belong to this menu item"
                )

            # Only show approved ratings to public
            if not rating.is_approved and rating.user != request.user:
                return ApiResponse.forbidden(
                    message="This rating is not yet approved"
                )

            serializer = MenuItemReviewSerializer(
                rating, context={'request': request}
            )
            return ApiResponse.success(
                data=serializer.data,
                message="Rating retrieved successfully"
            )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error retrieving rating: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Menu Ratings'],
        summary="Update rating",
        description="Update an existing rating (owner only)",
        request=MenuItemReviewCreateSerializer,
        responses={200: MenuItemReviewSerializer}
    )
    def put(self, request, chain_id, item_id, rating_id):
        """Update an existing rating"""
        try:
            rating_selector = RatingSelector()
            rating = rating_selector.get_rating_by_id(rating_id)

            if not rating:
                return ApiResponse.not_found(message="Rating not found")

            # Validate ownership and edit permissions
            if rating.user != request.user:
                return ApiResponse.forbidden(
                    message="You can only edit your own ratings"
                )

            if not rating.can_edit:
                return ApiResponse.bad_request(
                    message="Rating can only be edited within 30 days of creation"
                )

            # Validate rating belongs to the specified item and chain
            if rating.menu_item_id != item_id or rating.menu_item.chain_id != chain_id:
                return ApiResponse.bad_request(
                    message="Rating does not belong to this menu item"
                )

            # Prepare update data
            rating_data = {
                'rating': request.data.get('rating', rating.rating),
                'content': request.data.get('content') or request.data.get('review_text', rating.content)
            }

            # Validate rating data
            serializer = MenuItemReviewCreateSerializer(
                data=rating_data,
                context={'request': request}
            )
            if not serializer.is_valid():
                return ApiResponse.bad_request(
                    message="Validation failed",
                    errors=serializer.errors
                )

            # Update rating using service
            rating_service = RatingService()
            result = rating_service.create_or_update_rating(
                request.user, item_id, rating_data
            )

            return result

        except Exception as e:
            return ApiResponse.error(
                message=f"Error updating rating: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        tags=['Menu Ratings'],
        summary="Delete rating",
        description="Delete a rating (owner only, within 30 days)",
        responses={204: None}
    )
    def delete(self, request, chain_id, item_id, rating_id):
        """Delete a rating"""
        if not request.user.is_authenticated:
            return ApiResponse.unauthorized(
                message="Authentication required to delete ratings"
            )

        # Validate rating belongs to the specified item and chain
        rating_selector = RatingSelector()
        rating = rating_selector.get_rating_by_id(rating_id)

        if not rating:
            return ApiResponse.not_found(message="Rating not found")

        if rating.menu_item_id != item_id or rating.menu_item.chain_id != chain_id:
            return ApiResponse.bad_request(
                message="Rating does not belong to this menu item"
            )

        # Delete rating using service
        rating_service = RatingService()
        return rating_service.delete_rating(request.user, rating_id)


class MenuItemRatingSummaryView(StandardResponseMixin, APIView):
    """
    GET /api/chains/{chain_id}/menu-items/{item_id}/ratings/summary/ - Get rating summary
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        tags=['Menu Ratings'],
        summary="Get menu item rating summary",
        description="Get comprehensive rating summary for a menu item",
        responses={200: MenuItemReviewSummarySerializer}
    )
    def get(self, request, chain_id, item_id):
        """Get rating summary for a menu item"""
        try:
            # Validate menu item exists and belongs to chain
            from apps.dishes.models import MenuItem
            try:
                menu_item = MenuItem.objects.get(
                    id=item_id, chain_id=chain_id, is_available=True
                )
            except MenuItem.DoesNotExist:
                return ApiResponse.not_found(message="Menu item not found")

            rating_selector = RatingSelector()
            summary = rating_selector.get_rating_summary_for_item(item_id)

            # Get recent reviews
            recent_filters = {'verified_only': request.query_params.get('verified_only', '').lower() == 'true'}
            # recent_ratings = rating_selector.get_ratings_for_menu_item(item_id, recent_filters)[:5]

            # Get top positive and critical reviews
            # positive_ratings = rating_selector.get_ratings_for_menu_item(
            #     item_id, {'rating': 5}
            # )[:3]

            # critical_ratings = rating_selector.get_ratings_for_menu_item(
            #     item_id, {'rating': 1}
            # )[:3]

            response_data = {
                'average_rating': summary['average_rating'],
                'total_reviews': summary['total_reviews'],
                'verified_reviews': summary['verified_reviews'],
                'verified_purchase_percentage': summary['verified_purchase_percentage'],
                'rating_distribution': summary['rating_distribution'],
                # 'recent_reviews': MenuItemReviewSerializer(
                #     recent_ratings, many=True, context={'request': request}
                # ).data,
                # 'top_positive_reviews': MenuItemReviewSerializer(
                #     positive_ratings, many=True, context={'request': request}
                # ).data,
                # 'top_critical_reviews': MenuItemReviewSerializer(
                #     critical_ratings, many=True, context={'request': request}
                # ).data
            }

            return ApiResponse.success(
                data=response_data,
                message="Rating summary retrieved successfully"
            )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error retrieving rating summary: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# TODO: Remove this view - helpful voting and reporting features have been removed
# class RatingInteractionView(StandardResponseMixin, APIView):
#     """
#     POST /api/chains/{chain_id}/menu-items/{item_id}/ratings/{rating_id}/helpful/ - Mark as helpful
#     POST /api/chains/{chain_id}/menu-items/{item_id}/ratings/{rating_id}/report/ - Report rating
#     """
#     permission_classes = [permissions.IsAuthenticated]
#
#     @extend_schema(
#         tags=['Menu Ratings'],
#         summary="Mark rating as helpful/not helpful",
#         description="Mark a rating as helpful or not helpful",
#         request=RatingHelpfulSerializer,
#         responses={200: dict}
#     )
#     def post(self, request, chain_id, item_id, rating_id, action):
#         """Handle rating interactions (helpful/report)"""
#         pass


class UserRatingsView(StandardResponseMixin, APIView):
    """
    GET /api/users/me/ratings/ - Get current user's ratings
    """
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPageNumberPagination

    @extend_schema(
        tags=['User Ratings'],
        summary="Get current user's ratings",
        description="Get all ratings created by the current user",
        parameters=[
            OpenApiParameter(
                name='rating',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by specific rating (1-5)'
            ),
            OpenApiParameter(
                name='chain_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter by restaurant chain'
            ),
            OpenApiParameter(
                name='has_review',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Show only reviews with text content'
            ),
            OpenApiParameter(
                name='page',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Page number'
            ),
            OpenApiParameter(
                name='page_size',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Items per page'
            ),
        ],
        responses={200: MenuItemReviewSerializer(many=True)}
    )
    def get(self, request):
        """Get current user's ratings"""
        try:
            # Get filters from query parameters
            filters = {
                'rating': request.query_params.get('rating'),
                'chain_id': request.query_params.get('chain_id'),
                'has_review': request.query_params.get('has_review', '').lower() == 'true'
            }

            # Remove None values
            filters = {k: v for k, v in filters.items() if v is not None}

            # Get user's ratings
            rating_selector = RatingSelector()
            ratings = rating_selector.get_user_ratings(request.user.id, filters)

            # Apply pagination
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(ratings, request)

            if page is not None:
                serializer = MenuItemReviewSerializer(
                    page, many=True, context={'request': request}
                )
                return paginator.get_paginated_response(serializer.data)

            # Fallback for non-paginated response
            serializer = MenuItemReviewSerializer(
                ratings, many=True, context={'request': request}
            )
            return ApiResponse.success(
                data=serializer.data,
                message="User ratings retrieved successfully"
            )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error retrieving user ratings: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChainRatingAnalyticsView(StandardResponseMixin, APIView):
    """
    GET /api/chains/{chain_id}/ratings/analytics/ - Get chain rating analytics
    """
    permission_classes = [permissions.IsAuthenticated]  # Require authentication for analytics

    @extend_schema(
        tags=['Rating Analytics'],
        summary="Get chain rating analytics",
        description="Get comprehensive rating analytics for a restaurant chain",
        parameters=[
            OpenApiParameter(
                name='days',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Number of days to analyze (default: 30)'
            ),
        ],
        responses={200: dict}
    )
    def get(self, request, chain_id):
        """Get rating analytics for a chain"""
        try:
            # Validate chain exists
            from apps.restaurants.models import RestaurantChain
            try:
                chain = RestaurantChain.objects.get(id=chain_id)
            except RestaurantChain.DoesNotExist:
                return ApiResponse.not_found(message="Chain not found")

            # Check if user has permission to view analytics
            if not self._can_view_analytics(request.user, chain):
                return ApiResponse.forbidden(
                    message="You don't have permission to view analytics for this chain"
                )

            days = int(request.query_params.get('days', 30))
            analytics_service = RatingAnalyticsService()
            return analytics_service.get_chain_rating_analytics(chain_id, days)

        except Exception as e:
            return ApiResponse.error(
                message=f"Error retrieving analytics: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _can_view_analytics(self, user, chain):
        """Check if user can view analytics for the chain"""
        if user.is_superuser:
            return True

        if user.is_staff:
            return True

        # Check if user is manager or staff of the chain
        from apps.users.models import StaffProfile
        staff_profile = StaffProfile.objects.filter(
            user=user,
            restaurant__chain=chain,
            is_active=True
        ).first()

        return staff_profile is not None or chain.manager == user