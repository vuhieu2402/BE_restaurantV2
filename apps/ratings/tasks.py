"""
Background tasks for rating system
Uses Celery for asynchronous processing
"""

try:
    from celery import shared_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False


def update_menu_item_rating_stats(menu_item_id):
    """
    Update menu item rating statistics
    This can be called both synchronously and asynchronously
    """
    from .selectors import RatingSelector

    try:
        selector = RatingSelector()
        selector.update_menu_item_rating_stats(menu_item_id)
        return True
    except Exception as e:
        # Log error if logger is available
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error updating menu item stats for {menu_item_id}: {str(e)}")
        except:
            pass
        return False


# Create Celery task if Celery is available
if CELERY_AVAILABLE:
    @shared_task
    def update_menu_item_rating_stats_task(menu_item_id):
        """
        Celery task for updating menu item rating statistics
        """
        return update_menu_item_rating_stats(menu_item_id)

    # Update the function to use the Celery task
    def update_menu_item_rating_stats(menu_item_id):
        """
        Update menu item rating statistics asynchronously if Celery is available
        """
        try:
            update_menu_item_rating_stats_task.delay(menu_item_id)
            return True
        except Exception:
            # Fallback to synchronous processing
            return update_menu_item_rating_stats(menu_item_id)


@shared_task
def cleanup_old_rating_helpful_votes():
    """
    Cleanup old helpful votes to prevent database bloat
    Remove votes older than 1 year
    """
    from datetime import timedelta
    from django.utils import timezone
    from .models import RatingHelpful

    try:
        one_year_ago = timezone.now() - timedelta(days=365)
        deleted_count, _ = RatingHelpful.objects.filter(
            created_at__lt=one_year_ago
        ).delete()
        return f"Deleted {deleted_count} old helpful votes"
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error cleaning up old helpful votes: {str(e)}")
        return f"Error: {str(e)}"


@shared_task
def calculate_rating_trends(chain_id, days=30):
    """
    Calculate rating trends for a restaurant chain
    """
    try:
        from .selectors import RatingSelector
        selector = RatingSelector()
        trends = selector.get_rating_trends(chain_id, days)
        return trends
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error calculating rating trends for chain {chain_id}: {str(e)}")
        return []


@shared_task
def send_rating_notifications():
    """
    Send notifications about new ratings to restaurant owners/managers
    """
    try:
        from datetime import timedelta
        from django.utils import timezone
        from django.contrib.auth import get_user_model
        from .models import MenuItemRating
        from django.core.mail import send_mail
        from django.conf import settings

        # Get ratings from the last 24 hours
        yesterday = timezone.now() - timedelta(days=1)
        recent_ratings = MenuItemRating.objects.filter(
            created_at__gte=yesterday,
            is_approved=True
        ).select_related('menu_item', 'menu_item__chain')

        # Group by restaurant chain
        chain_ratings = {}
        for rating in recent_ratings:
            chain_id = rating.menu_item.chain_id
            if chain_id not in chain_ratings:
                chain_ratings[chain_id] = []
            chain_ratings[chain_id].append(rating)

        # Send notifications to chain managers
        User = get_user_model()
        for chain_id, ratings in chain_ratings.items():
            try:
                # Get chain manager
                chain = ratings[0].menu_item.chain
                if chain.manager:
                    # Prepare email content
                    subject = f"New ratings for {chain.name}"
                    message = f"""
                    You have received {len(ratings)} new rating(s) for your restaurant chain:

                    """

                    for rating in ratings:
                        message += f"""
                        • {rating.menu_item.name}: {rating.rating}★
                          Review: {rating.review_text[:100]}{'...' if len(rating.review_text) > 100 else ''}
                          By: {rating.user.get_full_name() or rating.user.username}
                        """

                    message += f"""

                    View all ratings: {settings.FRONTEND_URL}/chains/{chain_id}/ratings
                    """

                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[chain.manager.email],
                        fail_silently=True,
                    )

            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error sending notification to chain {chain_id}: {str(e)}")

        return f"Processed notifications for {len(chain_ratings)} chains"

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in rating notifications task: {str(e)}")
        return f"Error: {str(e)}"