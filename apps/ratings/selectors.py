from django.db import models
from django.db.models import Count, Avg, Sum, Q, F, Window
from django.db.models.functions import RowNumber
from django.utils import timezone
from datetime import timedelta
from .models import MenuItemRating, RatingCategory, RatingResponse, RatingHelpful
from apps.dishes.models import MenuItem


class RatingSelector:
    """Selectors for MenuItemRating queries"""

    def __init__(self):
        pass

    def get_rating_by_id(self, rating_id):
        """Get rating by ID with related data"""
        try:
            return MenuItemRating.objects.select_related(
                'menu_item', 'user', 'order_item'
            ).prefetch_related(
                'responses',
                'responses__responder'
            ).get(id=rating_id)
        except MenuItemRating.DoesNotExist:
            return None

    def get_user_rating_for_item(self, user_id, menu_item_id):
        """Get user's rating for specific menu item"""
        try:
            return MenuItemRating.objects.get(
                user_id=user_id,
                menu_item_id=menu_item_id
            )
        except MenuItemRating.DoesNotExist:
            return None

    def get_ratings_for_menu_item(self, menu_item_id, filters=None):
        """Get ratings for a specific menu item"""
        queryset = MenuItemRating.objects.filter(
            menu_item_id=menu_item_id,
            is_approved=True
        ).select_related('user').prefetch_related('responses')

        if filters:
            if filters.get('rating'):
                queryset = queryset.filter(rating=filters['rating'])
            if filters.get('verified_only'):
                queryset = queryset.filter(is_verified_purchase=True)
            if filters.get('has_review'):
                queryset = queryset.exclude(review_text='')
            if filters.get('min_helpful'):
                queryset = queryset.filter(
                    helpful_count__gte=filters['min_helpful']
                )

        return queryset.order_by('-created_at')

    def get_ratings_by_chain(self, chain_id, filters=None, limit=None):
        """Get ratings for all items in a chain"""
        queryset = MenuItemRating.objects.filter(
            menu_item__chain_id=chain_id,
            is_approved=True
        ).select_related(
            'menu_item', 'user'
        ).prefetch_related('responses')

        if filters:
            if filters.get('rating'):
                queryset = queryset.filter(rating=filters['rating'])
            if filters.get('verified_only'):
                queryset = queryset.filter(is_verified_purchase=True)
            if filters.get('menu_item_id'):
                queryset = queryset.filter(menu_item_id=filters['menu_item_id'])
            if filters.get('user_id'):
                queryset = queryset.filter(user_id=filters['user_id'])
            if filters.get('date_from'):
                queryset = queryset.filter(created_at__gte=filters['date_from'])
            if filters.get('date_to'):
                queryset = queryset.filter(created_at__lte=filters['date_to'])

        queryset = queryset.order_by('-created_at')

        if limit:
            return queryset[:limit]
        return queryset

    def get_user_ratings(self, user_id, filters=None):
        """Get all ratings by a user"""
        queryset = MenuItemRating.objects.filter(
            user_id=user_id,
            is_approved=True
        ).select_related('menu_item', 'menu_item__chain')

        if filters:
            if filters.get('rating'):
                queryset = queryset.filter(rating=filters['rating'])
            if filters.get('chain_id'):
                queryset = queryset.filter(menu_item__chain_id=filters['chain_id'])
            if filters.get('has_review'):
                if filters['has_review']:
                    queryset = queryset.exclude(review_text='')
                else:
                    queryset = queryset.filter(review_text='')
            if filters.get('date_from'):
                queryset = queryset.filter(created_at__gte=filters['date_from'])
            if filters.get('date_to'):
                queryset = queryset.filter(created_at__lte=filters['date_to'])

        return queryset.order_by('-created_at')

    def get_recent_ratings(self, days=7, chain_id=None):
        """Get recent ratings within specified days"""
        date_from = timezone.now() - timedelta(days=days)
        queryset = MenuItemRating.objects.filter(
            created_at__gte=date_from,
            is_approved=True
        ).select_related('menu_item', 'user')

        if chain_id:
            queryset = queryset.filter(menu_item__chain_id=chain_id)

        return queryset.order_by('-created_at')

    def get_top_rated_items(self, chain_id, limit=10, min_reviews=5):
        """Get top rated items in a chain"""
        return MenuItem.objects.filter(
            chain_id=chain_id,
            total_reviews__gte=min_reviews,
            is_available=True
        ).annotate(
            avg_rating=models.Avg(
                'user_ratings__rating',
                filter=Q(user_ratings__is_approved=True)
            )
        ).order_by('-avg_rating', '-total_reviews')[:limit]

    def get_rating_summary_for_item(self, menu_item_id):
        """Get comprehensive rating summary for a menu item"""
        ratings = MenuItemRating.objects.filter(
            menu_item_id=menu_item_id,
            is_approved=True
        ).aggregate(
            average_rating=Avg('rating'),
            total_reviews=Count('id'),
            verified_reviews=Count(
                'id',
                filter=Q(is_verified_purchase=True)
            ),
            total_helpful=Sum('helpful_count'),
            total_not_helpful=Sum('not_helpful_count'),
            five_star=Count('id', filter=Q(rating=5)),
            four_star=Count('id', filter=Q(rating=4)),
            three_star=Count('id', filter=Q(rating=3)),
            two_star=Count('id', filter=Q(rating=2)),
            one_star=Count('id', filter=Q(rating=1))
        )

        total_reviews = ratings['total_reviews'] or 0
        if total_reviews > 0:
            verified_percentage = (ratings['verified_reviews'] / total_reviews) * 100
            helpful_percentage = (ratings['total_helpful'] /
                                (ratings['total_helpful'] + ratings['total_not_helpful']) * 100) \
                               if (ratings['total_helpful'] + ratings['total_not_helpful']) > 0 else 0
        else:
            verified_percentage = 0
            helpful_percentage = 0

        return {
            'average_rating': float(ratings['average_rating'] or 0),
            'total_reviews': total_reviews,
            'verified_reviews': ratings['verified_reviews'] or 0,
            'verified_purchase_percentage': round(verified_percentage, 2),
            'helpful_percentage': round(helpful_percentage, 2),
            'rating_distribution': {
                '5_star': ratings['five_star'] or 0,
                '4_star': ratings['four_star'] or 0,
                '3_star': ratings['three_star'] or 0,
                '2_star': ratings['two_star'] or 0,
                '1_star': ratings['one_star'] or 0
            }
        }

    def get_rating_trends(self, chain_id, days=30):
        """Get rating trends over time"""
        date_from = timezone.now() - timedelta(days=days)

        ratings = MenuItemRating.objects.filter(
            menu_item__chain_id=chain_id,
            created_at__gte=date_from,
            is_approved=True
        ).extra(
            select={'day': 'date(created_at)'}
        ).values('day').annotate(
            avg_rating=Avg('rating'),
            count=Count('id')
        ).order_by('day')

        return list(ratings)

    def get_top_reviewers(self, chain_id, limit=10, min_reviews=3):
        """Get users with most reviews in a chain"""
        return MenuItemRating.objects.filter(
            menu_item__chain_id=chain_id,
            is_approved=True
        ).values('user__username', 'user__first_name', 'user__last_name', 'user__avatar').annotate(
            review_count=Count('id'),
            avg_rating=Avg('rating'),
            helpful_count=Sum('helpful_count')
        ).filter(
            review_count__gte=min_reviews
        ).order_by('-review_count', '-helpful_count')[:limit]

    def search_ratings(self, chain_id, query, filters=None):
        """Search ratings by review text"""
        queryset = MenuItemRating.objects.filter(
            menu_item__chain_id=chain_id,
            is_approved=True,
            review_text__icontains=query
        ).select_related('menu_item', 'user')

        if filters:
            if filters.get('rating'):
                queryset = queryset.filter(rating=filters['rating'])
            if filters.get('verified_only'):
                queryset = queryset.filter(is_verified_purchase=True)

        return queryset.order_by('-created_at')

    def get_ratings_needing_moderation(self, chain_id=None):
        """Get ratings that need moderation"""
        queryset = MenuItemRating.objects.filter(
            is_approved=False
        ).select_related('menu_item', 'user')

        if chain_id:
            queryset = queryset.filter(menu_item__chain_id=chain_id)

        return queryset.order_by('-created_at')

    def update_menu_item_rating_stats(self, menu_item_id):
        """Update menu item rating statistics (called from signals/tasks)"""
        try:
            menu_item = MenuItem.objects.get(id=menu_item_id)

            ratings = MenuItemRating.objects.filter(
                menu_item_id=menu_item_id,
                is_approved=True
            )

            # Calculate new stats
            stats = ratings.aggregate(
                avg_rating=Avg('rating'),
                total_reviews=Count('id'),
                verified_count=Count('id', filter=Q(is_verified_purchase=True)),
                five_star=Count('id', filter=Q(rating=5)),
                four_star=Count('id', filter=Q(rating=4)),
                three_star=Count('id', filter=Q(rating=3)),
                two_star=Count('id', filter=Q(rating=2)),
                one_star=Count('id', filter=Q(rating=1))
            )

            # Update menu item
            menu_item.rating = float(stats['avg_rating'] or 0)
            menu_item.total_reviews = stats['total_reviews'] or 0
            menu_item.rating_distribution = {
                '5_star': stats['five_star'] or 0,
                '4_star': stats['four_star'] or 0,
                '3_star': stats['three_star'] or 0,
                '2_star': stats['two_star'] or 0,
                '1_star': stats['one_star'] or 0
            }

            if stats['total_reviews'] > 0:
                menu_item.verified_purchase_percentage = round(
                    (stats['verified_count'] / stats['total_reviews']) * 100, 2
                )
            else:
                menu_item.verified_purchase_percentage = 0

            # Update last rated timestamp
            latest_rating = ratings.order_by('-created_at').first()
            if latest_rating:
                menu_item.last_rated_at = latest_rating.created_at

            menu_item.save(update_fields=[
                'rating', 'total_reviews', 'rating_distribution',
                'verified_purchase_percentage', 'last_rated_at'
            ])

        except MenuItem.DoesNotExist:
            pass

    def get_similar_items_by_rating(self, menu_item_id, limit=5):
        """Get similar items based on rating patterns"""
        try:
            menu_item = MenuItem.objects.get(id=menu_item_id)

            # Find items with similar rating ranges and category
            min_rating = max(0, float(menu_item.rating) - 0.5)
            max_rating = min(5, float(menu_item.rating) + 0.5)

            similar_items = MenuItem.objects.filter(
                chain_id=menu_item.chain_id,
                rating__gte=min_rating,
                rating__lte=max_rating,
                total_reviews__gte=3,
                is_available=True
            ).exclude(id=menu_item_id).order_by('-rating', '-total_reviews')[:limit]

            return similar_items

        except MenuItem.DoesNotExist:
            return MenuItem.objects.none()


class RatingCategorySelector:
    """Selectors for RatingCategory queries"""

    def get_active_categories(self):
        """Get all active rating categories"""
        return RatingCategory.objects.filter(
            is_active=True
        ).order_by('display_order', 'name')

    def get_category_by_code(self, code):
        """Get category by code"""
        try:
            return RatingCategory.objects.get(code=code)
        except RatingCategory.DoesNotExist:
            return None


class RatingResponseSelector:
    """Selectors for RatingResponse queries"""

    def get_responses_for_rating(self, rating_id):
        """Get all responses for a rating"""
        return RatingResponse.objects.filter(
            rating_id=rating_id,
            is_public=True
        ).select_related('responder').order_by('created_at')

    def get_responses_by_user(self, user_id, filters=None):
        """Get responses by a user"""
        queryset = RatingResponse.objects.filter(
            responder_id=user_id
        ).select_related('rating', 'rating__menu_item')

        if filters:
            if filters.get('is_public') is not None:
                queryset = queryset.filter(is_public=filters['is_public'])
            if filters.get('rating_id'):
                queryset = queryset.filter(rating_id=filters['rating_id'])

        return queryset.order_by('-created_at')