from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from rest_framework import status
from .models import MenuItemReview, ReviewResponse
from .selectors import RatingSelector, RatingCategorySelector, ReviewResponseSelector
from apps.api.response import ApiResponse
from apps.orders.models import OrderItem

User = get_user_model()


class RatingService:
    """Service class for rating operations"""

    def __init__(self):
        self.rating_selector = RatingSelector()
        self.response_selector = ReviewResponseSelector()

    def create_or_update_rating(self, user, menu_item_id, rating_data):
        """Create or update a menu item rating"""
        try:
            with transaction.atomic():
                # Validate menu item exists and is available
                from apps.dishes.models import MenuItem
                try:
                    menu_item = MenuItem.objects.get(id=menu_item_id, is_available=True)
                except MenuItem.DoesNotExist:
                    return ApiResponse.bad_request(
                        message="Menu item not found or not available"
                    )

                # Check if user already rated this item
                existing_rating = self.rating_selector.get_user_rating_for_item(
                    user.id, menu_item_id
                )

                # Validate user can rate this item
                validation_result = self._validate_rating_eligibility(user, menu_item)
                if not validation_result['can_rate']:
                    return ApiResponse.bad_request(
                        message=validation_result['reason']
                    )

                if existing_rating:
                    # Update existing rating
                    rating = self._update_rating(existing_rating, rating_data)
                    message = "Rating updated successfully"
                else:
                    # Create new rating
                    rating = self._create_rating(user, menu_item, rating_data)
                    message = "Rating created successfully"

                # Auto-approval logic
                self._handle_auto_approval(rating)

                # Update menu item stats
                self._update_menu_item_stats(menu_item_id)

                # Refresh rating object with updated data
                rating = self.rating_selector.get_rating_by_id(rating.id)

                return ApiResponse.success(
                    data={
                        'rating_id': rating.id,
                        'rating': rating.rating,
                        'message': message
                    },
                    message=message
                )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error creating/updating rating: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete_rating(self, user, rating_id):
        """Delete a user's rating"""
        try:
            rating = self.rating_selector.get_rating_by_id(rating_id)

            if not rating:
                return ApiResponse.not_found(message="Rating not found")

            if rating.user != user:
                return ApiResponse.forbidden(
                    message="You can only delete your own ratings"
                )

            # Check if rating can be deleted (within 30 days)
            if not rating.can_edit:
                return ApiResponse.bad_request(
                    message="Rating can only be deleted within 30 days of creation"
                )

            menu_item_id = rating.menu_item_id

            with transaction.atomic():
                rating.delete()
                # Update menu item stats
                self._update_menu_item_stats(menu_item_id)

            return ApiResponse.success(
                message="Rating deleted successfully"
            )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error deleting rating: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def report_rating(self, user, rating_id, report_data):
        """Report an inappropriate rating"""
        try:
            rating = self.rating_selector.get_rating_by_id(rating_id)

            if not rating:
                return ApiResponse.not_found(message="Rating not found")

            # Create report (for now, just mark for moderation)
            reason = report_data.get('reason', 'other')
            description = report_data.get('description', '')

            with transaction.atomic():
                rating.is_approved = False
                rating.moderation_notes = (
                    f"Reported by {user.username}: {reason}. "
                    f"Description: {description}"
                )
                rating.save(update_fields=['is_approved', 'moderation_notes'])

                # TODO: Create RatingReport model for detailed tracking

            return ApiResponse.success(
                message="Rating reported successfully. Thank you for helping keep our community safe."
            )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error reporting rating: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _validate_rating_eligibility(self, user, menu_item):
        """Validate if user is eligible to rate the menu item"""
        # Check if user has ordered this item
        has_ordered = OrderItem.objects.filter(
            menu_item=menu_item,
            order__customer=user,
            order__status='completed'
        ).exists()

        # For now, allow all users to rate, but mark verified purchases
        # In production, you might want to require verified purchases
        return {
            'can_rate': True,
            'reason': 'User is eligible to rate' if has_ordered else 'User has not purchased this item',
            'is_verified_purchase': has_ordered
        }

    def _create_rating(self, user, menu_item, rating_data):
        """Create a new rating"""
        rating = MenuItemReview.objects.create(
            user=user,
            menu_item=menu_item,
            rating=rating_data['rating'],
            content=rating_data.get('content', ''),
            ip_address=self._get_client_ip(),
            is_verified_purchase=self._check_verified_purchase(user, menu_item)
        )
        return rating

    def _update_rating(self, rating, rating_data):
        """Update an existing rating"""
        rating.rating = rating_data['rating']
        rating.content = rating_data.get('content', rating.content)
        rating.save()
        return rating

    def _check_verified_purchase(self, user, menu_item):
        """Check if user has actually ordered this item"""
        return OrderItem.objects.filter(
            menu_item=menu_item,
            order__customer=user,
            order__status='completed'
        ).exists()

    def _get_client_ip(self, request=None):
        """Get client IP address"""
        # This would need request context, for now return None
        return None

    def _handle_auto_approval(self, rating):
        """Handle automatic approval logic"""
        # Auto-approve for verified purchases with 3+ stars
        if rating.is_verified_purchase and rating.rating >= 3:
            rating.is_approved = True
            rating.save(update_fields=['is_approved'])
        # Auto-approve for new users with no history of spam
        elif (hasattr(rating.user, 'customer_profile') and 
              rating.user.customer_profile.total_orders > 0 and 
              rating.rating >= 3):
            rating.is_approved = True
            rating.save(update_fields=['is_approved'])

    def _update_menu_item_stats(self, menu_item_id):
        """Update menu item rating statistics"""
        self.rating_selector.update_menu_item_rating_stats(menu_item_id)


class ReviewResponseService:
    """Service class for rating response operations"""

    def __init__(self):
        self.response_selector = ReviewResponseSelector()

    def create_response(self, user, rating_id, content):
        """Create a response to a rating"""
        try:
            rating = RatingSelector().get_rating_by_id(rating_id)

            if not rating:
                return ApiResponse.not_found(message="Rating not found")

            # Check if user is authorized to respond (staff/manager of the restaurant)
            if not self._can_respond_to_rating(user, rating):
                return ApiResponse.forbidden(
                    message="You are not authorized to respond to this rating"
                )

            with transaction.atomic():
                response = ReviewResponse.objects.create(
                    review=rating,
                    responder=user,
                    content=content,
                    is_public=True
                )

            return ApiResponse.success(
                data={
                    'response_id': response.id,
                    'message': 'Response created successfully'
                },
                message='Response created successfully'
            )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error creating response: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update_response(self, user, response_id, content):
        """Update a rating response"""
        try:
            response = ReviewResponse.objects.filter(
                id=response_id,
                responder=user
            ).first()

            if not response:
                return ApiResponse.not_found(message="Response not found")

            response.content = content
            response.save(update_fields=['content', 'updated_at'])

            return ApiResponse.success(
                message="Response updated successfully"
            )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error updating response: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _can_respond_to_rating(self, user, rating):
        """Check if user can respond to the rating"""
        # Check if user is staff or manager of the restaurant
        if user.is_superuser:
            return True

        # Check if user is manager or staff of the restaurant chain
        from apps.restaurants.models import RestaurantChain
        from apps.users.models import StaffProfile

        # Check staff profile
        staff_profile = StaffProfile.objects.filter(
            user=user,
            restaurant__chain_id=rating.menu_item.chain_id,
            is_active=True
        ).first()

        if staff_profile:
            return True

        # Check if user is manager of the chain
        chain = RestaurantChain.objects.filter(
            id=rating.menu_item.chain_id,
            manager=user
        ).first()

        if chain:
            return True

        return False


class RatingAnalyticsService:
    """Service class for rating analytics"""

    def __init__(self):
        self.rating_selector = RatingSelector()

    def get_chain_rating_analytics(self, chain_id, days=30):
        """Get comprehensive rating analytics for a chain"""
        try:
            # Overall statistics
            overall_stats = self._get_overall_stats(chain_id, days)

            # Rating trends
            rating_trends = self.rating_selector.get_rating_trends(chain_id, days)

            # Top rated items
            top_items = self.rating_selector.get_top_rated_items(chain_id, limit=10)

            # Top reviewers
            top_reviewers = self.rating_selector.get_top_reviewers(chain_id, limit=10)

            # Recent ratings
            recent_ratings = self.rating_selector.get_recent_ratings(days, chain_id)[:5]

            return ApiResponse.success(
                data={
                    'overall_stats': overall_stats,
                    'rating_trends': rating_trends,
                    'top_rated_items': [
                        {
                            'id': item.id,
                            'name': item.name,
                            'rating': float(item.rating),
                            'total_reviews': item.total_reviews
                        }
                        for item in top_items
                    ],
                    'top_reviewers': list(top_reviewers),
                    'recent_ratings': [
                        {
                            'id': rating.id,
                            'menu_item': rating.menu_item.name,
                            'rating': rating.rating,
                            'user': rating.user.get_full_name(),
                            'created_at': rating.created_at
                        }
                        for rating in recent_ratings
                    ]
                },
                message="Analytics retrieved successfully"
            )

        except Exception as e:
            return ApiResponse.error(
                message=f"Error retrieving analytics: {str(e)}",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _get_overall_stats(self, chain_id, days):
        """Get overall rating statistics"""
        from django.db.models import Count, Avg, Q

        ratings = MenuItemReview.objects.filter(
            menu_item__chain_id=chain_id,
            is_approved=True,
            created_at__gte=timezone.now() - timezone.timedelta(days=days)
        )

        return ratings.aggregate(
            total_ratings=Count('id'),
            average_rating=Avg('rating'),
            five_star=Count('id', filter=Q(rating=5)),
            four_star=Count('id', filter=Q(rating=4)),
            three_star=Count('id', filter=Q(rating=3)),
            two_star=Count('id', filter=Q(rating=2)),
            one_star=Count('id', filter=Q(rating=1)),
            verified_ratings=Count('id', filter=Q(is_verified_purchase=True))
        )