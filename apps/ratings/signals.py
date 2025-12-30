"""
Django signals for ratings app
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Count, Avg, Q
from .models import MenuItemReview, ReviewResponse
from .tasks import update_menu_item_rating_stats


@receiver(post_save, sender=MenuItemReview)
def rating_created_or_updated(sender, instance, created, **kwargs):
    """
    Handle rating creation and updates
    """
    # Update menu item statistics asynchronously
    update_menu_item_rating_stats(instance.menu_item_id)

    # If this is a new rating, send notification
    if created and instance.is_approved:
        # TODO: Send notification to restaurant owner
        pass


@receiver(post_delete, sender=MenuItemReview)
def rating_deleted(sender, instance, **kwargs):
    """
    Handle rating deletion
    """
    # Update menu item statistics asynchronously
    update_menu_item_rating_stats(instance.menu_item_id)


@receiver(post_save, sender=ReviewResponse)
def response_created(sender, instance, created, **kwargs):
    """
    Handle rating response creation
    """
    if created and instance.is_public:
        # TODO: Send notification to rating user about response
        pass