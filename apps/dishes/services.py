from django.db import transaction
from django.core.exceptions import ValidationError
from .selectors import CategorySelector, MenuItemSelector
from .models import Category, MenuItem
import logging

logger = logging.getLogger(__name__)


class CategoryService:
    """
    Service layer - Xử lý business logic và CUD operations cho Category
    """

    def __init__(self):
        self.selector = CategorySelector()

    def create_category(self, restaurant_id, category_data, user=None):
        """
        Create category với validation và business rules
        """
        try:
            with transaction.atomic():
                # Validate business rules
                validation_errors = self._validate_category_data(restaurant_id, category_data)
                if validation_errors:
                    return {
                        'success': False,
                        'message': 'Validation failed',
                        'errors': validation_errors
                    }

                # Add restaurant_id to category_data
                category_data['restaurant_id'] = restaurant_id

                # Create category
                category = Category.objects.create(**category_data)

                # Get created data via selector
                created_category = self.selector.get_category_by_id(category.id)

                return {
                    'success': True,
                    'data': created_category,
                    'message': 'Category created successfully'
                }

        except Exception as e:
            logger.error(f"Error creating category: {str(e)}")
            return {
                'success': False,
                'message': f'Error creating category: {str(e)}'
            }

    def update_category(self, category_id, update_data, user=None):
        """
        Update category với validation và business rules
        """
        try:
            with transaction.atomic():
                # Get category via selector
                category = self.selector.get_category_by_id(category_id)
                if not category:
                    return {
                        'success': False,
                        'message': 'Category not found'
                    }

                # Validate business rules
                validation_errors = self._validate_update_data(category, update_data)
                if validation_errors:
                    return {
                        'success': False,
                        'message': 'Validation failed',
                        'errors': validation_errors
                    }

                # Update category
                for field, value in update_data.items():
                    if hasattr(category, field):
                        setattr(category, field, value)
                category.save()

                # Get updated data via selector
                updated_category = self.selector.get_category_by_id(category.id)

                return {
                    'success': True,
                    'data': updated_category,
                    'message': 'Category updated successfully'
                }

        except Exception as e:
            logger.error(f"Error updating category: {str(e)}")
            return {
                'success': False,
                'message': f'Error updating category: {str(e)}'
            }

    def delete_category(self, category_id, user=None):
        """
        Delete category với business rules validation
        """
        try:
            with transaction.atomic():
                # Get category via selector
                category = self.selector.get_category_by_id(category_id)
                if not category:
                    return {
                        'success': False,
                        'message': 'Category not found'
                    }

                # Validate business rules for delete
                if not self._can_delete_category(category):
                    return {
                        'success': False,
                        'message': 'Cannot delete category with existing menu items'
                    }

                # Soft delete
                category.is_active = False
                category.save()

                return {
                    'success': True,
                    'message': 'Category deleted successfully'
                }

        except Exception as e:
            logger.error(f"Error deleting category: {str(e)}")
            return {
                'success': False,
                'message': f'Error deleting category: {str(e)}'
            }

    def get_categories_with_business_logic(self, restaurant_id, filters):
        """
        Get categories với filtering và business logic (READ)
        """
        try:
            # Get data via selector
            categories = self.selector.get_categories_with_item_count(restaurant_id, filters)

            # Apply business logic processing
            processed_data = self._process_category_data(categories)

            return {
                'success': True,
                'data': processed_data,
                'message': 'Categories retrieved successfully'
            }

        except Exception as e:
            logger.error(f"Error retrieving categories: {str(e)}")
            return {
                'success': False,
                'message': f'Error retrieving categories: {str(e)}'
            }

    def reorder_categories(self, restaurant_id, category_orders, user=None):
        """
        Reorder categories display order
        """
        try:
            with transaction.atomic():
                results = []

                for category_order in category_orders:
                    category_id = category_order.get('id')
                    display_order = category_order.get('display_order')

                    if not category_id or display_order is None:
                        results.append({
                            'category_id': category_id,
                            'success': False,
                            'message': 'Category ID and display_order are required'
                        })
                        continue

                    # Get category via selector
                    category = self.selector.get_category_by_id(category_id)
                    if not category:
                        results.append({
                            'category_id': category_id,
                            'success': False,
                            'message': 'Category not found'
                        })
                        continue

                    # Validate category belongs to restaurant
                    if category.restaurant_id != int(restaurant_id):
                        results.append({
                            'category_id': category_id,
                            'success': False,
                            'message': 'Category does not belong to this restaurant'
                        })
                        continue

                    # Update display order
                    category.display_order = display_order
                    category.save()

                    results.append({
                        'category_id': category_id,
                        'success': True,
                        'message': 'Category reordered successfully'
                    })

                return {
                    'success': True,
                    'data': results,
                    'message': 'Categories reordered successfully'
                }

        except Exception as e:
            logger.error(f"Error reordering categories: {str(e)}")
            return {
                'success': False,
                'message': f'Error reordering categories: {str(e)}'
            }

    def _validate_category_data(self, restaurant_id, data):
        """
        Private method cho category business validation
        """
        errors = {}

        # Check if category name already exists for this restaurant
        if data.get('name') and self.selector.check_category_name_exists(restaurant_id, data['name']):
            errors['name'] = 'Category with this name already exists for this restaurant'

        # Check if slug already exists for this restaurant
        if data.get('slug') and self.selector.check_category_slug_exists(restaurant_id, data['slug']):
            errors['slug'] = 'Slug already exists for this restaurant'

        # Validate display order
        if data.get('display_order') and data['display_order'] < 0:
            errors['display_order'] = 'Display order must be non-negative'

        return errors

    def _validate_update_data(self, category, update_data):
        """
        Validate business rules cho category update
        """
        errors = {}

        # Check unique constraints except current record
        if 'name' in update_data:
            if self.selector.check_category_name_exists(
                category.restaurant_id, update_data['name'], category.id
            ):
                errors['name'] = 'Category with this name already exists for this restaurant'

        if 'slug' in update_data:
            if self.selector.check_category_slug_exists(
                category.restaurant_id, update_data['slug'], category.id
            ):
                errors['slug'] = 'Slug already exists for this restaurant'

        # Validate display order
        if 'display_order' in update_data and update_data['display_order'] < 0:
            errors['display_order'] = 'Display order must be non-negative'

        return errors

    def _can_delete_category(self, category):
        """
        Business rules check cho category delete
        """
        # Check if category has active menu items
        item_count = MenuItem.objects.filter(
            category_id=category.id,
            is_active=True,
            is_available=True
        ).count()

        return item_count == 0

    def _process_category_data(self, categories):
        """
        Apply business logic vào category data
        """
        processed_categories = []

        for category in categories:
            category_data = {
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
                'image': category.image.url if category.image else None,
                'display_order': category.display_order,
                'is_active': category.is_active,
                'item_count': getattr(category, 'item_count', 0),
                'created_at': category.created_at,
                'updated_at': category.updated_at
            }
            processed_categories.append(category_data)

        return processed_categories


class MenuItemService:
    """
    Service layer - Xử lý business logic và CUD operations cho MenuItem
    """

    def __init__(self):
        self.selector = MenuItemSelector()

    def create_menu_item(self, restaurant_id, menu_item_data, user=None):
        """
        Create menu item với validation và business rules
        """
        try:
            with transaction.atomic():
                # Normalize data: handle empty string/list values from multipart/form-data
                normalized_data = {}
                for key, value in menu_item_data.items():
                    # Handle list values from multipart/form-data
                    if isinstance(value, list):
                        if len(value) > 0 and value[0] and str(value[0]).strip():
                            normalized_data[key] = value[0]
                        else:
                            # Empty list or list with empty string -> set to None for optional fields
                            normalized_data[key] = None
                    else:
                        # Handle empty strings
                        if value == '' or (isinstance(value, str) and value.strip() == ''):
                            # For optional fields, set to None; for required fields with defaults, use default
                            if key in ['preparation_time', 'calories', 'display_order', 'original_price']:
                                normalized_data[key] = None if key in ['preparation_time', 'calories', 'original_price'] else 0
                            else:
                                normalized_data[key] = None
                        else:
                            normalized_data[key] = value
                
                # Normalize integer fields
                for field in ['preparation_time', 'calories', 'display_order']:
                    if field in normalized_data and normalized_data[field] is not None:
                        try:
                            normalized_data[field] = int(normalized_data[field])
                        except (ValueError, TypeError):
                            normalized_data[field] = None if field != 'display_order' else 0
                    elif field == 'display_order' and field not in normalized_data:
                        normalized_data[field] = 0  # Default value
                
                # Normalize category field (ForeignKey)
                if 'category' in normalized_data:
                    category_value = normalized_data.get('category')
                    
                    # Handle list values (e.g., ['1'] -> '1')
                    if isinstance(category_value, list):
                        category_value = category_value[0] if category_value else None
                    
                    # Convert empty/zero values to None
                    if category_value == 0 or category_value == '0' or category_value == '' or category_value is None:
                        normalized_data['category'] = None
                    else:
                        # Convert to integer if it's a string number
                        try:
                            category_id = int(category_value)
                            # Validate that category exists and belongs to restaurant
                            category_selector = CategorySelector()
                            category = category_selector.get_category_by_id(category_id)
                            if not category or category.restaurant_id != restaurant_id:
                                return {
                                    'success': False,
                                    'message': f'Category with ID {category_id} does not exist or does not belong to this restaurant',
                                    'errors': {'category': f'Category with ID {category_id} not found'}
                                }
                            normalized_data['category_id'] = category_id
                            # Remove 'category' key and use 'category_id' for ForeignKey assignment
                            normalized_data.pop('category', None)
                        except (ValueError, TypeError):
                            return {
                                'success': False,
                                'message': 'Invalid category ID format',
                                'errors': {'category': 'Category must be a valid category ID'}
                            }
                
                # Normalize BooleanField values (is_available, is_featured, is_vegetarian, is_spicy)
                boolean_fields = ['is_available', 'is_featured', 'is_vegetarian', 'is_spicy']
                for field in boolean_fields:
                    value = normalized_data.get(field)
                    
                    # Skip if field not provided (will use model default)
                    if field not in normalized_data or value is None:
                        continue
                    
                    # Handle string boolean values from multipart/form-data
                    if isinstance(value, str):
                        value_lower = value.lower().strip()
                        if value_lower in ['true', '1', 'yes', 'on']:
                            normalized_data[field] = True
                        elif value_lower in ['false', '0', 'no', 'off', '']:
                            normalized_data[field] = False
                        else:
                            return {
                                'success': False,
                                'message': f'Invalid {field} value. Must be true/false.',
                                'errors': {field: f'{field} must be true or false. Received: {value}'}
                            }
                    elif isinstance(value, bool):
                        # Already boolean, keep as is
                        normalized_data[field] = value
                    elif isinstance(value, (int, float)):
                        # Convert 1/0 to True/False
                        normalized_data[field] = bool(value)
                
                # Validate business rules
                validation_errors = self._validate_menu_item_data(restaurant_id, normalized_data)
                if validation_errors:
                    return {
                        'success': False,
                        'message': 'Validation failed',
                        'errors': validation_errors
                    }

                # Add restaurant_id to normalized_data
                normalized_data['restaurant_id'] = restaurant_id

                # Create menu item
                menu_item = MenuItem.objects.create(**normalized_data)

                # Get created data via selector
                created_item = self.selector.get_menu_item_by_id(menu_item.id)

                return {
                    'success': True,
                    'data': created_item,
                    'message': 'Menu item created successfully'
                }

        except Exception as e:
            logger.error(f"Error creating menu item: {str(e)}")
            return {
                'success': False,
                'message': f'Error creating menu item: {str(e)}'
            }

    def update_menu_item(self, menu_item_id, update_data, user=None):
        """
        Update menu item với validation và business rules
        """
        try:
            with transaction.atomic():
                # Get menu item via selector
                menu_item = self.selector.get_menu_item_by_id(menu_item_id)
                if not menu_item:
                    return {
                        'success': False,
                        'message': 'Menu item not found'
                    }

                # Normalize data: handle category field (ForeignKey)
                normalized_data = update_data.copy()
                if 'category' in normalized_data:
                    category_value = normalized_data.get('category')
                    
                    # Handle list values (e.g., ['1'] -> '1')
                    if isinstance(category_value, list):
                        category_value = category_value[0] if category_value else None
                    
                    # Convert empty/zero values to None
                    if category_value == 0 or category_value == '0' or category_value == '' or category_value is None:
                        normalized_data['category'] = None
                    else:
                        # Convert to integer if it's a string number
                        try:
                            category_id = int(category_value)
                            # Validate that category exists and belongs to restaurant
                            category_selector = CategorySelector()
                            category = category_selector.get_category_by_id(category_id)
                            if not category or category.restaurant_id != menu_item.restaurant_id:
                                return {
                                    'success': False,
                                    'message': f'Category with ID {category_id} does not exist or does not belong to this restaurant',
                                    'errors': {'category': f'Category with ID {category_id} not found'}
                                }
                            normalized_data['category_id'] = category_id
                            # Remove 'category' key and use 'category_id' for ForeignKey assignment
                            normalized_data.pop('category', None)
                        except (ValueError, TypeError):
                            return {
                                'success': False,
                                'message': 'Invalid category ID format',
                                'errors': {'category': 'Category must be a valid category ID'}
                            }

                # Normalize BooleanField values (is_available, is_featured, is_vegetarian, is_spicy)
                boolean_fields = ['is_available', 'is_featured', 'is_vegetarian', 'is_spicy']
                for field in boolean_fields:
                    if field in normalized_data:
                        value = normalized_data.get(field)
                        
                        # Handle string boolean values from multipart/form-data
                        if isinstance(value, str):
                            value_lower = value.lower().strip()
                            if value_lower in ['true', '1', 'yes', 'on']:
                                normalized_data[field] = True
                            elif value_lower in ['false', '0', 'no', 'off', '']:
                                normalized_data[field] = False
                            else:
                                return {
                                    'success': False,
                                    'message': f'Invalid {field} value. Must be true/false.',
                                    'errors': {field: f'{field} must be true or false. Received: {value}'}
                                }
                        elif isinstance(value, bool):
                            # Already boolean, keep as is
                            normalized_data[field] = value
                        elif isinstance(value, (int, float)):
                            # Convert 1/0 to True/False
                            normalized_data[field] = bool(value)

                # Validate business rules
                validation_errors = self._validate_update_data(menu_item, normalized_data)
                if validation_errors:
                    return {
                        'success': False,
                        'message': 'Validation failed',
                        'errors': validation_errors
                    }

                # Update menu item
                for field, value in update_data.items():
                    if hasattr(menu_item, field):
                        setattr(menu_item, field, value)
                menu_item.save()

                # Get updated data via selector
                updated_item = self.selector.get_menu_item_by_id(menu_item.id)

                return {
                    'success': True,
                    'data': updated_item,
                    'message': 'Menu item updated successfully'
                }

        except Exception as e:
            logger.error(f"Error updating menu item: {str(e)}")
            return {
                'success': False,
                'message': f'Error updating menu item: {str(e)}'
            }

    def delete_menu_item(self, menu_item_id, user=None):
        """
        Delete menu item với business rules validation
        """
        try:
            with transaction.atomic():
                # Get menu item via selector
                menu_item = self.selector.get_menu_item_by_id(menu_item_id)
                if not menu_item:
                    return {
                        'success': False,
                        'message': 'Menu item not found'
                    }

                # Validate business rules for delete
                if not self._can_delete_menu_item(menu_item):
                    return {
                        'success': False,
                        'message': 'Cannot delete menu item due to business constraints'
                    }

                # Soft delete - set is_available to False
                menu_item.is_available = False
                menu_item.save()

                return {
                    'success': True,
                    'message': 'Menu item deleted successfully'
                }

        except Exception as e:
            logger.error(f"Error deleting menu item: {str(e)}")
            return {
                'success': False,
                'message': f'Error deleting menu item: {str(e)}'
            }

    def get_menu_items_with_business_logic(self, restaurant_id, filters):
        """
        Get menu items với filtering và business logic (READ)
        """
        try:
            # Get data via selector
            queryset = self.selector.get_menu_items_by_restaurant(restaurant_id, filters)

            # Apply business logic processing
            processed_data = self._process_menu_item_data(queryset)

            return {
                'success': True,
                'data': processed_data,
                'message': 'Menu items retrieved successfully'
            }

        except Exception as e:
            logger.error(f"Error retrieving menu items: {str(e)}")
            return {
                'success': False,
                'message': f'Error retrieving menu items: {str(e)}'
            }

    def get_featured_menu_items(self, restaurant_id, limit=None):
        """
        Get featured menu items với business logic
        """
        try:
            # Get data via selector
            queryset = self.selector.get_featured_menu_items(restaurant_id, limit)

            # Apply business logic processing
            processed_data = self._process_menu_item_data(queryset)

            return {
                'success': True,
                'data': processed_data,
                'message': 'Featured menu items retrieved successfully'
            }

        except Exception as e:
            logger.error(f"Error retrieving featured menu items: {str(e)}")
            return {
                'success': False,
                'message': f'Error retrieving featured menu items: {str(e)}'
            }

    def search_menu_items(self, restaurant_id, search_term, filters=None):
        """
        Search menu items với business logic
        """
        try:
            if filters is None:
                filters = {}

            # Get data via selector
            queryset = self.selector.search_menu_items(restaurant_id, search_term, filters)

            # Apply business logic processing
            processed_data = self._process_menu_item_data(queryset)

            return {
                'success': True,
                'data': processed_data,
                'message': 'Menu items search completed successfully'
            }

        except Exception as e:
            logger.error(f"Error searching menu items: {str(e)}")
            return {
                'success': False,
                'message': f'Error searching menu items: {str(e)}'
            }

    def get_menu_by_categories(self, restaurant_id, filters=None):
        """
        Get menu items grouped by categories với business logic
        """
        try:
            # Get data via selector
            grouped_items = self.selector.get_menu_items_with_categories(restaurant_id, filters)

            # Apply business logic processing
            processed_data = {}
            for category_name, items in grouped_items.items():
                processed_data[category_name] = self._process_menu_item_data(items)

            return {
                'success': True,
                'data': processed_data,
                'message': 'Menu by categories retrieved successfully'
            }

        except Exception as e:
            logger.error(f"Error retrieving menu by categories: {str(e)}")
            return {
                'success': False,
                'message': f'Error retrieving menu by categories: {str(e)}'
            }

    def toggle_menu_item_availability(self, menu_item_id, user=None):
        """
        Toggle menu item availability
        """
        try:
            with transaction.atomic():
                # Get menu item via selector
                menu_item = self.selector.get_menu_item_by_id(menu_item_id)
                if not menu_item:
                    return {
                        'success': False,
                        'message': 'Menu item not found'
                    }

                # Toggle availability
                menu_item.is_available = not menu_item.is_available
                menu_item.save()

                # Get updated data via selector
                updated_item = self.selector.get_menu_item_by_id(menu_item.id)

                return {
                    'success': True,
                    'data': updated_item,
                    'message': f"Menu item marked as {'available' if menu_item.is_available else 'unavailable'}"
                }

        except Exception as e:
            logger.error(f"Error toggling menu item availability: {str(e)}")
            return {
                'success': False,
                'message': f'Error toggling menu item availability: {str(e)}'
            }

    def toggle_menu_item_featured(self, menu_item_id, user=None):
        """
        Toggle menu item featured status
        """
        try:
            with transaction.atomic():
                # Get menu item via selector
                menu_item = self.selector.get_menu_item_by_id(menu_item_id)
                if not menu_item:
                    return {
                        'success': False,
                        'message': 'Menu item not found'
                    }

                # Toggle featured status
                menu_item.is_featured = not menu_item.is_featured
                menu_item.save()

                # Get updated data via selector
                updated_item = self.selector.get_menu_item_by_id(menu_item.id)

                return {
                    'success': True,
                    'data': updated_item,
                    'message': f"Menu item marked as {'featured' if menu_item.is_featured else 'not featured'}"
                }

        except Exception as e:
            logger.error(f"Error toggling menu item featured status: {str(e)}")
            return {
                'success': False,
                'message': f'Error toggling menu item featured status: {str(e)}'
            }

    def update_menu_item_prices(self, restaurant_id, price_updates, user=None):
        """
        Bulk update menu item prices
        """
        try:
            with transaction.atomic():
                results = []

                for price_update in price_updates:
                    menu_item_id = price_update.get('id')
                    price = price_update.get('price')
                    original_price = price_update.get('original_price')

                    if not menu_item_id or price is None:
                        results.append({
                            'menu_item_id': menu_item_id,
                            'success': False,
                            'message': 'Menu item ID and price are required'
                        })
                        continue

                    # Get menu item via selector
                    menu_item = self.selector.get_menu_item_by_id(menu_item_id)
                    if not menu_item:
                        results.append({
                            'menu_item_id': menu_item_id,
                            'success': False,
                            'message': 'Menu item not found'
                        })
                        continue

                    # Validate menu item belongs to restaurant
                    if menu_item.restaurant_id != int(restaurant_id):
                        results.append({
                            'menu_item_id': menu_item_id,
                            'success': False,
                            'message': 'Menu item does not belong to this restaurant'
                        })
                        continue

                    # Validate price
                    if price < 0:
                        results.append({
                            'menu_item_id': menu_item_id,
                            'success': False,
                            'message': 'Price must be non-negative'
                        })
                        continue

                    # Validate original price
                    if original_price and original_price <= price:
                        results.append({
                            'menu_item_id': menu_item_id,
                            'success': False,
                            'message': 'Original price must be greater than current price'
                        })
                        continue

                    # Update prices
                    menu_item.price = price
                    menu_item.original_price = original_price
                    menu_item.save()

                    results.append({
                        'menu_item_id': menu_item_id,
                        'success': True,
                        'message': 'Menu item price updated successfully'
                    })

                return {
                    'success': True,
                    'data': results,
                    'message': 'Menu item prices updated successfully'
                }

        except Exception as e:
            logger.error(f"Error updating menu item prices: {str(e)}")
            return {
                'success': False,
                'message': f'Error updating menu item prices: {str(e)}'
            }

    def get_menu_analytics(self, restaurant_id):
        """
        Get menu analytics data
        """
        try:
            # Get data via selector
            stats = self.selector.get_menu_item_stats(restaurant_id)
            price_distribution = self.selector.get_price_distribution(restaurant_id)

            # Process analytics data
            analytics = {
                'overview': {
                    'total_items': stats['total_items'] or 0,
                    'available_items': stats['available_items'] or 0,
                    'featured_items': stats['featured_items'] or 0,
                    'vegetarian_items': stats['vegetarian_items'] or 0,
                    'spicy_items': stats['spicy_items'] or 0,
                    'avg_price': float(stats['avg_price'] or 0),
                    'min_price': float(stats['min_price'] or 0),
                    'max_price': float(stats['max_price'] or 0),
                    'avg_rating': float(stats['avg_rating'] or 0),
                    'total_reviews': int(stats['total_reviews'] or 0)
                },
                'price_distribution': price_distribution
            }

            return {
                'success': True,
                'data': analytics,
                'message': 'Menu analytics retrieved successfully'
            }

        except Exception as e:
            logger.error(f"Error retrieving menu analytics: {str(e)}")
            return {
                'success': False,
                'message': f'Error retrieving menu analytics: {str(e)}'
            }

    def _validate_menu_item_data(self, restaurant_id, data):
        """
        Private method cho menu item business validation
        """
        errors = {}

        # Check if menu item name already exists for this restaurant
        if data.get('name') and self.selector.check_menu_item_name_exists(restaurant_id, data['name']):
            errors['name'] = 'Menu item with this name already exists for this restaurant'

        # Check if slug already exists for this restaurant
        if data.get('slug') and self.selector.check_menu_item_slug_exists(restaurant_id, data['slug']):
            errors['slug'] = 'Slug already exists for this restaurant'

        # Validate price
        try:
            if data.get('price'):
                price = float(data['price'])
                if price < 0:
                    errors['price'] = 'Price must be non-negative'
        except (ValueError, TypeError):
            errors['price'] = 'Invalid price format'

        # Validate original price
        try:
            if data.get('original_price'):
                original_price = float(data['original_price'])
                price = float(data.get('price', 0))
                if original_price <= price:
                    errors['original_price'] = 'Original price must be greater than current price'
        except (ValueError, TypeError):
            errors['original_price'] = 'Invalid original price format'

        # Validate calories
        if data.get('calories') is not None:
            try:
                calories = int(data['calories'])
                if calories < 0:
                    errors['calories'] = 'Calories must be non-negative'
            except (ValueError, TypeError):
                errors['calories'] = 'Invalid calories format'

        # Validate preparation time (optional field)
        if data.get('preparation_time') is not None and data.get('preparation_time') != '':
            try:
                prep_time = int(data['preparation_time'])
                if prep_time < 0:
                    errors['preparation_time'] = 'Preparation time must be non-negative'
            except (ValueError, TypeError):
                # Skip validation if value is empty/invalid - it's optional
                pass

        # Validate rating
        if data.get('rating') is not None:
            try:
                rating = float(data['rating'])
                if not 0 <= rating <= 5:
                    errors['rating'] = 'Rating must be between 0 and 5'
            except (ValueError, TypeError):
                errors['rating'] = 'Invalid rating format'

        # Validate display order (optional field, defaults to 0)
        if data.get('display_order') is not None and data.get('display_order') != '':
            try:
                display_order = int(data['display_order'])
                if display_order < 0:
                    errors['display_order'] = 'Display order must be non-negative'
            except (ValueError, TypeError):
                # Skip validation if value is empty/invalid - it's optional
                pass

        return errors

    def _validate_update_data(self, menu_item, update_data):
        """
        Validate business rules cho menu item update
        """
        errors = {}

        # Check unique constraints except current record
        if 'name' in update_data:
            if self.selector.check_menu_item_name_exists(
                menu_item.restaurant_id, update_data['name'], menu_item.id
            ):
                errors['name'] = 'Menu item with this name already exists for this restaurant'

        if 'slug' in update_data:
            if self.selector.check_menu_item_slug_exists(
                menu_item.restaurant_id, update_data['slug'], menu_item.id
            ):
                errors['slug'] = 'Slug already exists for this restaurant'

        # Re-validate other fields if provided
        validation_errors = self._validate_menu_item_data(menu_item.restaurant_id, update_data)
        for key, value in validation_errors.items():
            if key in update_data:
                errors[key] = value

        return errors

    def _can_delete_menu_item(self, menu_item):
        """
        Business rules check cho menu item delete
        """
        # Check if menu item has active orders (this would need to be implemented)
        # For now, allow deletion
        return True

    def _process_menu_item_data(self, queryset):
        """
        Apply business logic vào menu item data
        """
        processed_items = []

        for item in queryset:
            item_data = {
                'id': item.id,
                'name': item.name,
                'slug': item.slug,
                'description': item.description,
                'price': float(item.price),
                'original_price': float(item.original_price) if item.original_price else None,
                'image': item.image.url if item.image else None,
                'calories': item.calories,
                'preparation_time': item.preparation_time,
                'rating': float(item.rating),
                'total_reviews': item.total_reviews,
                'is_available': item.is_available,
                'is_featured': item.is_featured,
                'is_vegetarian': item.is_vegetarian,
                'is_spicy': item.is_spicy,
                'display_order': item.display_order,
                'category_id': item.category_id if item.category else None,
                'category_name': item.category.name if item.category else None,
                'category_slug': item.category.slug if item.category else None,
                'is_on_sale': item.is_on_sale,
                'discount_percentage': item.discount_percentage,
                'created_at': item.created_at,
                'updated_at': item.updated_at
            }
            processed_items.append(item_data)

        return processed_items