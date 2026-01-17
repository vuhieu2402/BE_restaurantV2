"""
Cache utilities for dishes app - Cache key management and operations

Implements Cache-Aside pattern (Lazy Loading) for categories and menu items:
1. Read from cache first
2. On cache miss, query database and save to cache
3. Invalidate cache on create/update/delete operations
"""
from django.core.cache import cache
from django.db.models import QuerySet
from typing import Any, Optional, List
import logging
import json
import hashlib

logger = logging.getLogger(__name__)


# ==================== CACHE KEY CONSTANTS ====================

class CacheKeyPattern:
    """Cache key patterns for dishes app"""

    # Category keys
    CATEGORY_LIST = "category:list:{scope_type}:{scope_id}"  # scope_type: restaurant|chain
    CATEGORY_DETAIL = "category:detail:{id}"
    CATEGORY_BY_SLUG = "category:slug:{scope_type}:{scope_id}:{slug}"

    # MenuItem keys
    MENU_ITEM_LIST = "menuitem:list:{scope_type}:{scope_id}"
    MENU_ITEM_DETAIL = "menuitem:detail:{id}"
    MENU_ITEM_BY_SLUG = "menuitem:slug:{scope_type}:{scope_id}:{slug}"
    MENU_ITEM_FEATURED = "menuitem:featured:{scope_type}:{scope_id}"
    MENU_ITEM_BY_CATEGORY = "menuitem:category:{category_id}"

    # Aggregate keys
    MENU_BY_CATEGORIES = "menu:grouped:{scope_type}:{scope_id}"


class CacheTTL:
    """Cache TTL values in seconds"""
    DEFAULT = 3600  # 1 hour
    SHORT = 300     # 5 minutes
    LONG = 86400    # 24 hours


# ==================== CACHE KEY GENERATION ====================

def make_category_list_key(scope_type: str, scope_id: int) -> str:
    """Generate cache key for category list"""
    return CacheKeyPattern.CATEGORY_LIST.format(
        scope_type=scope_type,
        scope_id=scope_id
    )


def make_category_detail_key(category_id: int) -> str:
    """Generate cache key for single category"""
    return CacheKeyPattern.CATEGORY_DETAIL.format(id=category_id)


def make_category_slug_key(scope_type: str, scope_id: int, slug: str) -> str:
    """Generate cache key for category by slug"""
    return CacheKeyPattern.CATEGORY_BY_SLUG.format(
        scope_type=scope_type,
        scope_id=scope_id,
        slug=slug
    )


def make_menu_item_list_key(scope_type: str, scope_id: int, filters: dict = None) -> str:
    """
    Generate cache key for menu item list

    For filtered queries, include hash of filters in key
    """
    base_key = CacheKeyPattern.MENU_ITEM_LIST.format(
        scope_type=scope_type,
        scope_id=scope_id
    )

    if filters and any(filters.values()):
        # Create deterministic hash from filters for variant results
        filter_hash = hashlib.md5(
            json.dumps(filters, sort_keys=True).encode()
        ).hexdigest()[:8]
        return f"{base_key}:filters:{filter_hash}"

    return base_key


def make_menu_item_detail_key(item_id: int) -> str:
    """Generate cache key for single menu item"""
    return CacheKeyPattern.MENU_ITEM_DETAIL.format(id=item_id)


def make_menu_item_slug_key(scope_type: str, scope_id: int, slug: str) -> str:
    """Generate cache key for menu item by slug"""
    return CacheKeyPattern.MENU_ITEM_BY_SLUG.format(
        scope_type=scope_type,
        scope_id=scope_id,
        slug=slug
    )


def make_menu_item_featured_key(scope_type: str, scope_id: int, limit: int = None) -> str:
    """Generate cache key for featured menu items"""
    base_key = CacheKeyPattern.MENU_ITEM_FEATURED.format(
        scope_type=scope_type,
        scope_id=scope_id
    )
    if limit:
        return f"{base_key}:limit:{limit}"
    return base_key


def make_menu_item_by_category_key(category_id: int) -> str:
    """Generate cache key for menu items by category"""
    return CacheKeyPattern.MENU_ITEM_BY_CATEGORY.format(category_id=category_id)


def make_menu_by_categories_key(scope_type: str, scope_id: int) -> str:
    """Generate cache key for menu grouped by categories"""
    return CacheKeyPattern.MENU_BY_CATEGORIES.format(
        scope_type=scope_type,
        scope_id=scope_id
    )


# ==================== CACHE OPERATIONS ====================

class CacheOperations:
    """High-level cache operations with error handling"""

    @staticmethod
    def get(key: str) -> Optional[Any]:
        """Get value from cache with error handling"""
        try:
            value = cache.get(key)
            if value is not None:
                logger.debug(f"Cache HIT: {key}")
            return value
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None

    @staticmethod
    def set(key: str, value: Any, ttl: int = CacheTTL.DEFAULT) -> bool:
        """Set value in cache with error handling"""
        try:
            cache.set(key, value, ttl)
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    @staticmethod
    def delete(key: str) -> bool:
        """Delete key from cache with error handling"""
        try:
            cache.delete(key)
            logger.debug(f"Cache DELETE: {key}")
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    @staticmethod
    def delete_many(keys: List[str]) -> bool:
        """Delete multiple keys from cache"""
        try:
            cache.delete_many(keys)
            logger.debug(f"Cache DELETE_MANY: {len(keys)} keys")
            return True
        except Exception as e:
            logger.error(f"Cache delete_many error: {e}")
            return False

    @staticmethod
    def get_or_set(
        key: str,
        callable_func,
        ttl: int = CacheTTL.DEFAULT
    ) -> Any:
        """
        Cache-Aside pattern: Get from cache or execute callable and cache result

        Args:
            key: Cache key
            callable_func: Function to execute on cache miss
            ttl: Time to live in seconds

        Returns:
            Cached or fresh data
        """
        # Try to get from cache
        cached_value = CacheOperations.get(key)
        if cached_value is not None:
            return cached_value

        logger.debug(f"Cache MISS: {key}")

        # Execute callable to get fresh data
        try:
            fresh_data = callable_func()

            if fresh_data is None:
                return None

            # Store in cache
            CacheOperations.set(key, fresh_data, ttl)

            return fresh_data
        except Exception as e:
            logger.error(f"Error in get_or_set for {key}: {e}")
            # Return None on error to prevent cascading failures
            return None


# ==================== CACHE INVALIDATION ====================

class CategoryCacheInvalidator:
    """Handles cache invalidation for Category operations"""

    @staticmethod
    def invalidate_category(category_id: int, scope_type: str, scope_id: int):
        """
        Invalidate all caches related to a specific category

        Args:
            category_id: The category ID that changed
            scope_type: 'restaurant' or 'chain'
            scope_id: Restaurant or chain ID
        """
        keys_to_delete = [
            make_category_list_key(scope_type, scope_id),
            make_category_detail_key(category_id),
            make_menu_by_categories_key(scope_type, scope_id),
        ]

        CacheOperations.delete_many(keys_to_delete)
        logger.info(f"Invalidated category caches for ID {category_id}")

    @staticmethod
    def invalidate_all_categories(scope_type: str, scope_id: int):
        """Invalidate all category-related caches for a scope"""
        keys_to_delete = [
            make_category_list_key(scope_type, scope_id),
            make_menu_by_categories_key(scope_type, scope_id),
        ]

        CacheOperations.delete_many(keys_to_delete)
        logger.info(f"Invalidated all category caches for {scope_type}={scope_id}")


class MenuItemCacheInvalidator:
    """Handles cache invalidation for MenuItem operations"""

    @staticmethod
    def invalidate_menu_item(
        item_id: int,
        scope_type: str,
        scope_id: int,
        category_id: Optional[int] = None
    ):
        """
        Invalidate all caches related to a specific menu item

        Args:
            item_id: The menu item ID that changed
            scope_type: 'restaurant' or 'chain'
            scope_id: Restaurant or chain ID
            category_id: Optional category ID for related invalidation
        """
        keys_to_delete = [
            make_menu_item_list_key(scope_type, scope_id),
            make_menu_item_detail_key(item_id),
            make_menu_item_featured_key(scope_type, scope_id),
            make_menu_item_featured_key(scope_type, scope_id, limit=10),
            make_menu_by_categories_key(scope_type, scope_id),
        ]

        # Invalidate category-specific cache if category_id provided
        if category_id:
            keys_to_delete.append(make_menu_item_by_category_key(category_id))

        CacheOperations.delete_many(keys_to_delete)
        logger.info(f"Invalidated menu item caches for ID {item_id}")

    @staticmethod
    def invalidate_category_items(category_id: int):
        """Invalidate caches when items in a category change"""
        keys_to_delete = [
            make_menu_item_by_category_key(category_id),
        ]
        CacheOperations.delete_many(keys_to_delete)
        logger.info(f"Invalidated menu item caches for category {category_id}")

    @staticmethod
    def invalidate_all_menu_items(scope_type: str, scope_id: int):
        """Invalidate all menu item caches for a scope"""
        # Delete list cache (including filtered variants would require pattern matching)
        base_key = make_menu_item_list_key(scope_type, scope_id)
        CacheOperations.delete(base_key)

        # Also delete featured and grouped menu caches
        CacheOperations.delete(make_menu_item_featured_key(scope_type, scope_id))
        CacheOperations.delete(make_menu_item_featured_key(scope_type, scope_id, limit=10))
        CacheOperations.delete(make_menu_by_categories_key(scope_type, scope_id))

        logger.info(f"Invalidated all menu item caches for {scope_type}={scope_id}")
