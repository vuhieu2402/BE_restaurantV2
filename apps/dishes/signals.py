"""
Django signals for automatic cache invalidation

Ensures cache consistency even when models are modified directly
(bypassing the service layer). This acts as a safety net.
"""
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import Category, MenuItem
from .cache_utils import CategoryCacheInvalidator, MenuItemCacheInvalidator
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Category)
def invalidate_category_on_save(sender, instance, created, **kwargs):
    """
    Invalidate category caches when a category is saved
    Covers both create and update operations
    """
    try:
        scope_type = 'chain' if instance.chain_id else 'restaurant'
        scope_id = instance.chain_id or instance.restaurant_id

        CategoryCacheInvalidator.invalidate_category(
            category_id=instance.id,
            scope_type=scope_type,
            scope_id=scope_id
        )

        logger.info(f"Category cache invalidated via signal: {instance.id}")
    except Exception as e:
        logger.error(f"Error invalidating category cache on save: {e}")


@receiver(pre_delete, sender=Category)
def invalidate_category_on_delete(sender, instance, **kwargs):
    """
    Invalidate category caches before deletion
    """
    try:
        scope_type = 'chain' if instance.chain_id else 'restaurant'
        scope_id = instance.chain_id or instance.restaurant_id

        CategoryCacheInvalidator.invalidate_category(
            category_id=instance.id,
            scope_type=scope_type,
            scope_id=scope_id
        )

        logger.info(f"Category cache invalidated via delete signal: {instance.id}")
    except Exception as e:
        logger.error(f"Error invalidating category cache on delete: {e}")


@receiver(post_save, sender=MenuItem)
def invalidate_menu_item_on_save(sender, instance, created, **kwargs):
    """
    Invalidate menu item caches when a menu item is saved
    """
    try:
        scope_type = 'chain' if instance.chain_id else 'restaurant'
        scope_id = instance.chain_id or instance.restaurant_id

        MenuItemCacheInvalidator.invalidate_menu_item(
            item_id=instance.id,
            scope_type=scope_type,
            scope_id=scope_id,
            category_id=instance.category_id
        )

        # Also invalidate category items cache
        if instance.category_id:
            MenuItemCacheInvalidator.invalidate_category_items(instance.category_id)

        logger.info(f"Menu item cache invalidated via signal: {instance.id}")
    except Exception as e:
        logger.error(f"Error invalidating menu item cache on save: {e}")


@receiver(pre_delete, sender=MenuItem)
def invalidate_menu_item_on_delete(sender, instance, **kwargs):
    """
    Invalidate menu item caches before deletion
    """
    try:
        scope_type = 'chain' if instance.chain_id else 'restaurant'
        scope_id = instance.chain_id or instance.restaurant_id

        MenuItemCacheInvalidator.invalidate_menu_item(
            item_id=instance.id,
            scope_type=scope_type,
            scope_id=scope_id,
            category_id=instance.category_id
        )

        logger.info(f"Menu item cache invalidated via delete signal: {instance.id}")
    except Exception as e:
        logger.error(f"Error invalidating menu item cache on delete: {e}")
