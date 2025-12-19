from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from decimal import Decimal, InvalidOperation
from .selectors import RestaurantSelector, RestaurantChainSelector, TableSelector
from .models import Restaurant, RestaurantChain, Table
from .utils import get_nearest_restaurant_for_delivery
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class RestaurantChainService:
    """
    Service layer for RestaurantChain - Business logic và CUD operations
    """
    
    def __init__(self):
        self.selector = RestaurantChainSelector()
    
    def get_chains(self, filters=None):
        """Get chains with business logic"""
        try:
            chains = self.selector.get_active_chains(filters)
            
            # Serialize chains
            from .serializers import RestaurantChainListSerializer
            serializer = RestaurantChainListSerializer(chains, many=True)
            
            return {
                'success': True,
                'data': serializer.data,
                'message': 'Chains retrieved successfully'
            }
        except Exception as e:
            logger.error(f"Error getting chains: {str(e)}")
            return {
                'success': False,
                'message': f'Error retrieving chains: {str(e)}'
            }
    
    def create_chain(self, chain_data, user=None):
        """Create chain với validation"""
        try:
            with transaction.atomic():
                # Validate slug uniqueness
                if self.selector.check_slug_exists(chain_data.get('slug')):
                    return {
                        'success': False,
                        'message': 'Slug already exists',
                        'errors': {'slug': 'This slug is already in use'}
                    }
                
                # Create chain
                chain = RestaurantChain.objects.create(**chain_data)
                
                return {
                    'success': True,
                    'data': chain,
                    'message': 'Chain created successfully'
                }
        except Exception as e:
            logger.error(f"Error creating chain: {str(e)}")
            return {
                'success': False,
                'message': f'Error creating chain: {str(e)}'
            }
    
    def update_chain(self, chain_id, update_data, user=None):
        """Update chain với validation"""
        try:
            with transaction.atomic():
                chain = self.selector.get_chain_by_id(chain_id)
                if not chain:
                    return {
                        'success': False,
                        'message': 'Chain not found'
                    }
                
                # Validate slug if being updated
                if 'slug' in update_data and update_data['slug'] != chain.slug:
                    if self.selector.check_slug_exists(update_data['slug'], exclude_id=chain_id):
                        return {
                            'success': False,
                            'message': 'Slug already exists',
                            'errors': {'slug': 'This slug is already in use'}
                        }
                
                # Update chain
                for field, value in update_data.items():
                    if hasattr(chain, field):
                        setattr(chain, field, value)
                chain.save()
                
                return {
                    'success': True,
                    'data': chain,
                    'message': 'Chain updated successfully'
                }
        except Exception as e:
            logger.error(f"Error updating chain: {str(e)}")
            return {
                'success': False,
                'message': f'Error updating chain: {str(e)}'
            }
    
    def delete_chain(self, chain_id, user=None):
        """Soft delete chain"""
        try:
            chain = self.selector.get_chain_by_id(chain_id)
            if not chain:
                return {
                    'success': False,
                    'message': 'Chain not found'
                }
            
            # Soft delete
            chain.is_active = False
            chain.save()
            
            return {
                'success': True,
                'message': 'Chain deleted successfully'
            }
        except Exception as e:
            logger.error(f"Error deleting chain: {str(e)}")
            return {
                'success': False,
                'message': f'Error deleting chain: {str(e)}'
            }
    
    def get_nearest_branch(self, chain_id, latitude, longitude):
        """Get nearest branch for delivery"""
        try:
            chain = self.selector.get_chain_by_id(chain_id)
            if not chain:
                return {
                    'success': False,
                    'message': 'Chain not found'
                }
            
            restaurant, distance = get_nearest_restaurant_for_delivery(
                chain, latitude, longitude
            )
            
            if not restaurant:
                return {
                    'success': False,
                    'message': 'No branch available for delivery to this location'
                }
            
            from .serializers import NearestBranchSerializer
            serializer = NearestBranchSerializer(restaurant)
            data = serializer.data
            data['distance_km'] = distance
            
            return {
                'success': True,
                'data': data,
                'message': 'Nearest branch found'
            }
        except Exception as e:
            logger.error(f"Error getting nearest branch: {str(e)}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }


class RestaurantService:
    """
    Service layer - Xử lý business logic và CUD operations
    """

    def __init__(self):
        self.selector = RestaurantSelector()

    def create_restaurant(self, restaurant_data, user=None):
        """
        Create restaurant với validation và business rules
        """
        try:
            with transaction.atomic():
                # Normalize data: First, handle all empty string/list values from multipart/form-data
                normalized_data = {}
                for key, value in restaurant_data.items():
                    # Handle list values from multipart/form-data (e.g., [''] -> None, ['value'] -> 'value')
                    if isinstance(value, list):
                        if len(value) > 0 and value[0] and str(value[0]).strip():
                            normalized_data[key] = value[0]
                        else:
                            # Empty list or list with empty string -> set to None for optional fields
                            normalized_data[key] = None
                    else:
                        # Handle empty strings
                        if value == '' or (isinstance(value, str) and value.strip() == ''):
                            normalized_data[key] = None
                        else:
                            normalized_data[key] = value
                
                # Now normalize specific field types
                if 'manager' in normalized_data and normalized_data['manager'] is not None:
                    manager_value = normalized_data.get('manager')
                    
                    # Handle list values (e.g., ['1'] -> 1)
                    if isinstance(manager_value, list):
                        manager_value = manager_value[0] if manager_value else None
                    
                    # Convert empty/zero values to None
                    if manager_value == 0 or manager_value == '0' or manager_value == '' or manager_value is None:
                        normalized_data['manager'] = None
                    else:
                        # Convert to integer if it's a string number
                        try:
                            manager_id = int(manager_value)
                            # Validate that user exists
                            if not User.objects.filter(id=manager_id).exists():
                                return {
                                    'success': False,
                                    'message': f'Manager with ID {manager_id} does not exist',
                                    'errors': {'manager': f'User with ID {manager_id} not found'}
                                }
                            normalized_data['manager_id'] = manager_id
                            # Remove 'manager' key and use 'manager_id' for ForeignKey assignment
                            normalized_data.pop('manager', None)
                        except (ValueError, TypeError):
                            return {
                                'success': False,
                                'message': 'Invalid manager ID format',
                                'errors': {'manager': 'Manager must be a valid user ID'}
                            }
                
                # Normalize DecimalField values (delivery_fee, delivery_radius, minimum_order, rating)
                # These fields should always have a value (default 0), so normalize None/empty to 0
                decimal_fields = ['delivery_fee', 'delivery_radius', 'minimum_order', 'rating']
                for field in decimal_fields:
                    value = normalized_data.get(field)
                    
                    # If field is None or empty string, set to default 0
                    if value is None or value == '' or (isinstance(value, str) and value.strip() == ''):
                        normalized_data[field] = Decimal('0')
                    else:
                        try:
                            # Convert to Decimal
                            normalized_data[field] = Decimal(str(value).strip())
                        except (ValueError, InvalidOperation, TypeError) as e:
                            return {
                                'success': False,
                                'message': f'Invalid {field} format. Must be a valid decimal number.',
                                'errors': {field: f'{field} must be a valid decimal number. Received: {value}'}
                            }
                
                # Normalize BooleanField values (is_open, is_active)
                boolean_fields = ['is_open', 'is_active']
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
                    else:
                        # Try to convert
                        try:
                            normalized_data[field] = bool(value)
                        except:
                            return {
                                'success': False,
                                'message': f'Invalid {field} value. Must be true/false.',
                                'errors': {field: f'{field} must be true or false. Received: {value}'}
                            }
                
                # Validate business rules
                validation_errors = self._validate_restaurant_data(normalized_data)
                if validation_errors:
                    return {
                        'success': False,
                        'message': 'Validation failed',
                        'errors': validation_errors
                    }

                # Create restaurant
                restaurant = Restaurant.objects.create(**normalized_data)

                # Get created data via selector
                created_restaurant = self.selector.get_restaurant_by_id(restaurant.id)

                return {
                    'success': True,
                    'data': created_restaurant,
                    'message': 'Restaurant created successfully'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error creating restaurant: {str(e)}'
            }

    def update_restaurant(self, restaurant_id, update_data, user=None):
        """
        Update restaurant với validation và business rules
        """
        try:
            with transaction.atomic():
                # Get restaurant via selector
                restaurant = self.selector.get_restaurant_by_id(restaurant_id)
                if not restaurant:
                    return {
                        'success': False,
                        'message': 'Restaurant not found'
                    }

                # Normalize data: convert manager=0 to None, handle list values
                normalized_data = update_data.copy()
                if 'manager' in normalized_data:
                    manager_value = normalized_data.get('manager')
                    
                    # Handle list values (e.g., ['1'] -> 1)
                    if isinstance(manager_value, list):
                        manager_value = manager_value[0] if manager_value else None
                    
                    # Convert empty/zero values to None
                    if manager_value == 0 or manager_value == '0' or manager_value == '' or manager_value is None:
                        normalized_data['manager'] = None
                    else:
                        # Convert to integer if it's a string number
                        try:
                            manager_id = int(manager_value)
                            # Validate that user exists
                            if not User.objects.filter(id=manager_id).exists():
                                return {
                                    'success': False,
                                    'message': f'Manager with ID {manager_id} does not exist',
                                    'errors': {'manager': f'User with ID {manager_id} not found'}
                                }
                            normalized_data['manager_id'] = manager_id
                            # Remove 'manager' key and use 'manager_id' for ForeignKey assignment
                            normalized_data.pop('manager', None)
                        except (ValueError, TypeError):
                            return {
                                'success': False,
                                'message': 'Invalid manager ID format',
                                'errors': {'manager': 'Manager must be a valid user ID'}
                            }

                # Normalize DecimalField values (delivery_fee, delivery_radius, minimum_order)
                decimal_fields = ['delivery_fee', 'delivery_radius', 'minimum_order']
                for field in decimal_fields:
                    if field in normalized_data:
                        value = normalized_data.get(field)
                        
                        # Handle list values (e.g., ['58.8'] -> '58.8')
                        if isinstance(value, list):
                            value = value[0] if value else None
                        
                        # Convert empty values to None or 0
                        if value == '' or value is None:
                            # Skip if None (don't update), or use 0 if field doesn't allow null
                            if value is None:
                                normalized_data.pop(field, None)
                            else:
                                normalized_data[field] = Decimal('0')
                        else:
                            try:
                                # Convert to Decimal
                                normalized_data[field] = Decimal(str(value))
                            except (ValueError, InvalidOperation, TypeError):
                                return {
                                    'success': False,
                                    'message': f'Invalid {field} format. Must be a valid decimal number.',
                                'errors': {field: f'{field} must be a valid decimal number'}
                            }

                # Normalize BooleanField values (is_open, is_active)
                boolean_fields = ['is_open', 'is_active']
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
                validation_errors = self._validate_update_data(restaurant, normalized_data)
                if validation_errors:
                    return {
                        'success': False,
                        'message': 'Validation failed',
                        'errors': validation_errors
                    }

                # Update restaurant
                for field, value in normalized_data.items():
                    if hasattr(restaurant, field):
                        setattr(restaurant, field, value)
                restaurant.save()

                # Get updated data via selector
                updated_restaurant = self.selector.get_restaurant_by_id(restaurant.id)

                return {
                    'success': True,
                    'data': updated_restaurant,
                    'message': 'Restaurant updated successfully'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error updating restaurant: {str(e)}'
            }

    def delete_restaurant(self, restaurant_id, user=None):
        """
        Delete restaurant với business rules validation
        """
        try:
            with transaction.atomic():
                # Get restaurant via selector
                restaurant = self.selector.get_restaurant_by_id(restaurant_id)
                if not restaurant:
                    return {
                        'success': False,
                        'message': 'Restaurant not found'
                    }

                # Validate business rules for delete
                if not self._can_delete_restaurant(restaurant):
                    return {
                        'success': False,
                        'message': 'Cannot delete restaurant due to business constraints'
                    }

                # Soft delete
                restaurant.is_active = False
                restaurant.save()

                return {
                    'success': True,
                    'message': 'Restaurant deleted successfully'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error deleting restaurant: {str(e)}'
            }

    def get_restaurants_with_business_logic(self, filters):
        """
        Get restaurants với filtering và business logic (READ)
        """
        try:
            # Get data via selector
            queryset = self.selector.get_active_restaurants(filters)

            # Apply business logic processing
            processed_data = self._process_restaurant_data(queryset)

            return {
                'success': True,
                'data': processed_data,
                'message': 'Restaurants retrieved successfully'
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving restaurants: {str(e)}'
            }

    def get_nearby_restaurants(self, latitude, longitude, radius_km=5):
        """
        Get nearby restaurants với business logic
        """
        try:
            # Get data via selector
            queryset = self.selector.get_nearby_restaurants(latitude, longitude, radius_km)

            # Apply distance calculation and sorting
            processed_data = self._process_nearby_restaurants(queryset, latitude, longitude)

            return {
                'success': True,
                'data': processed_data,
                'message': 'Nearby restaurants retrieved successfully'
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving nearby restaurants: {str(e)}'
            }

    def _validate_restaurant_data(self, data):
        """
        Private method cho business validation
        """
        errors = {}

        # Check if restaurant name already exists
        if data.get('name') and self.selector.check_restaurant_exists(data['name']):
            errors['name'] = 'Restaurant with this name already exists'

        # Check if slug already exists
        if data.get('slug') and self.selector.check_slug_exists(data['slug']):
            errors['slug'] = 'Slug already exists'

        # Validate coordinates
        try:
            if data.get('latitude'):
                lat = float(data['latitude'])
                if not -90 <= lat <= 90:
                    errors['latitude'] = 'Latitude must be between -90 and 90'
        except (ValueError, TypeError):
            errors['latitude'] = 'Invalid latitude format'

        try:
            if data.get('longitude'):
                lon = float(data['longitude'])
                if not -180 <= lon <= 180:
                    errors['longitude'] = 'Longitude must be between -180 and 180'
        except (ValueError, TypeError):
            errors['longitude'] = 'Invalid longitude format'

        # Validate opening hours
        opening_time = data.get('opening_time')
        closing_time = data.get('closing_time')
        if opening_time and closing_time and opening_time >= closing_time:
            errors['opening_hours'] = 'Opening time must be before closing time'

        return errors

    def _validate_update_data(self, restaurant, update_data):
        """
        Validate business rules cho update
        """
        errors = {}

        # Check unique constraints except current record
        if 'name' in update_data:
            if Restaurant.objects.filter(name=update_data['name']).exclude(id=restaurant.id).exists():
                errors['name'] = 'Restaurant with this name already exists'

        if 'slug' in update_data:
            if self.selector.check_slug_exists(update_data['slug'], restaurant.id):
                errors['slug'] = 'Slug already exists'

        # Re-validate coordinates if provided
        for field in ['latitude', 'longitude']:
            if field in update_data:
                try:
                    value = float(update_data[field])
                    if field == 'latitude' and not -90 <= value <= 90:
                        errors[field] = f'{field.capitalize()} must be between -90 and 90'
                    elif field == 'longitude' and not -180 <= value <= 180:
                        errors[field] = f'{field.capitalize()} must be between -180 and 180'
                except (ValueError, TypeError):
                    errors[field] = f'Invalid {field} format'

        return errors

    def _can_delete_restaurant(self, restaurant):
        """
        Business rules check cho delete
        """
        # Check if restaurant has active orders, reservations, etc.
        # This would need to be implemented based on related models
        return True

    def _process_restaurant_data(self, queryset):
        """
        Apply business logic vào restaurant data
        """
        restaurants = []
        for restaurant in queryset:
            restaurant_data = {
                'id': restaurant.id,
                'name': restaurant.name,
                'slug': restaurant.slug,
                'description': restaurant.description,
                'address': restaurant.address,
                'city': restaurant.city,
                'district': restaurant.district,
                'phone_number': restaurant.phone_number,
                'email': restaurant.email,
                'latitude': float(restaurant.latitude),
                'longitude': float(restaurant.longitude),
                'opening_time': restaurant.opening_time.strftime('%H:%M'),
                'closing_time': restaurant.closing_time.strftime('%H:%M'),
                'is_open': restaurant.is_open,
                'is_currently_open': restaurant.is_currently_open,
                'rating': float(restaurant.rating),
                'total_reviews': restaurant.total_reviews,
                'minimum_order': float(restaurant.minimum_order),
                'delivery_fee': float(restaurant.delivery_fee),
                'delivery_radius': float(restaurant.delivery_radius),
                'logo': restaurant.logo.url if restaurant.logo else None,
                'cover_image': restaurant.cover_image.url if restaurant.cover_image else None,
                'created_at': restaurant.created_at,
                'updated_at': restaurant.updated_at
            }
            restaurants.append(restaurant_data)

        return restaurants

    def _process_nearby_restaurants(self, queryset, user_lat, user_lon):
        """
        Apply distance calculation to nearby restaurants
        """
        restaurants = []
        for restaurant in queryset:
            # Calculate distance using haversine formula (simplified)
            distance = self._calculate_distance(
                float(restaurant.latitude), float(restaurant.longitude),
                float(user_lat), float(user_lon)
            )

            restaurant_data = {
                'id': restaurant.id,
                'name': restaurant.name,
                'slug': restaurant.slug,
                'address': restaurant.address,
                'distance_km': round(distance, 2),
                'rating': float(restaurant.rating),
                'phone_number': restaurant.phone_number,
                'is_open': restaurant.is_open,
                'is_currently_open': restaurant.is_currently_open,
                'delivery_fee': float(restaurant.delivery_fee),
                'logo': restaurant.logo.url if restaurant.logo else None
            }
            restaurants.append(restaurant_data)

        # Sort by distance
        restaurants.sort(key=lambda x: x['distance_km'])
        return restaurants

    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """
        Calculate distance between two coordinates (simplified)
        """
        from math import sqrt, radians

        # Rough approximation for small distances
        lat_diff = (lat2 - lat1) * 111  # ~111km per degree latitude
        lon_diff = (lon2 - lon1) * 111 * abs(lat1)  # longitude varies by latitude

        return sqrt(lat_diff**2 + lon_diff**2)


class TableService:
    """
    Service layer for Table model
    """

    def __init__(self):
        self.selector = TableSelector()

    def create_table(self, restaurant_id, table_data, user=None):
        """
        Create table với validation và business rules
        """
        try:
            with transaction.atomic():
                # Validate business rules
                validation_errors = self._validate_table_data(restaurant_id, table_data)
                if validation_errors:
                    return {
                        'success': False,
                        'message': 'Validation failed',
                        'errors': validation_errors
                    }

                # Add restaurant_id to table_data
                table_data['restaurant_id'] = restaurant_id

                # Create table
                table = Table.objects.create(**table_data)

                # Get created data via selector
                created_table = self.selector.get_table_by_id(table.id)

                return {
                    'success': True,
                    'data': created_table,
                    'message': 'Table created successfully'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error creating table: {str(e)}'
            }

    def update_table(self, table_id, update_data, user=None):
        """
        Update table với validation và business rules
        """
        try:
            with transaction.atomic():
                # Get table via selector
                table = self.selector.get_table_by_id(table_id)
                if not table:
                    return {
                        'success': False,
                        'message': 'Table not found'
                    }

                # Validate business rules
                validation_errors = self._validate_table_update_data(table, update_data)
                if validation_errors:
                    return {
                        'success': False,
                        'message': 'Validation failed',
                        'errors': validation_errors
                    }

                # Update table
                for field, value in update_data.items():
                    if hasattr(table, field):
                        setattr(table, field, value)
                table.save()

                # Get updated data via selector
                updated_table = self.selector.get_table_by_id(table.id)

                return {
                    'success': True,
                    'data': updated_table,
                    'message': 'Table updated successfully'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error updating table: {str(e)}'
            }

    def delete_table(self, table_id, user=None):
        """
        Delete table với business rules validation
        """
        try:
            with transaction.atomic():
                # Get table via selector
                table = self.selector.get_table_by_id(table_id)
                if not table:
                    return {
                        'success': False,
                        'message': 'Table not found'
                    }

                # Validate business rules for delete
                if not self._can_delete_table(table):
                    return {
                        'success': False,
                        'message': 'Cannot delete table due to business constraints'
                    }

                # Soft delete
                table.is_active = False
                table.save()

                return {
                    'success': True,
                    'message': 'Table deleted successfully'
                }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error deleting table: {str(e)}'
            }

    def get_tables_with_layout(self, restaurant_id, filters=None):
        """
        Get tables with floor plan layout information
        """
        try:
            # Get data via selector
            queryset = self.selector.get_tables_by_restaurant(restaurant_id, filters)

            # Process with layout information
            processed_data = self._process_table_layout_data(queryset)

            return {
                'success': True,
                'data': processed_data,
                'message': 'Tables retrieved successfully'
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving tables: {str(e)}'
            }

    def _validate_table_data(self, restaurant_id, data):
        """
        Private method cho table business validation
        """
        errors = {}

        # Check if table number already exists for this restaurant
        if data.get('table_number') and self.selector.check_table_number_exists(
            restaurant_id, data['table_number']
        ):
            errors['table_number'] = 'Table number already exists for this restaurant'

        # Validate capacity
        try:
            if data.get('capacity'):
                capacity = int(data['capacity'])
                if capacity < 1:
                    errors['capacity'] = 'Capacity must be at least 1'
                if capacity > 50:  # Business rule: max 50 people per table
                    errors['capacity'] = 'Capacity cannot exceed 50 people'
        except (ValueError, TypeError):
            errors['capacity'] = 'Invalid capacity format'

        # Validate floor
        try:
            if data.get('floor'):
                floor = int(data['floor'])
                if floor < 1 or floor > 99:  # Business rule: reasonable floor limits
                    errors['floor'] = 'Floor must be between 1 and 99'
        except (ValueError, TypeError):
            errors['floor'] = 'Invalid floor format'

        # Validate coordinates
        for field in ['x_position', 'y_position']:
            if field in data and data[field] is not None:
                try:
                    value = float(data[field])
                    if value < 0 or value > 10000:  # Business rule: reasonable coordinate limits
                        errors[field] = f'{field.replace("_", " ").title()} must be between 0 and 10000'
                except (ValueError, TypeError):
                    errors[field] = f'Invalid {field.replace("_", " ")} format'

        return errors

    def _validate_table_update_data(self, table, update_data):
        """
        Validate business rules cho table update
        """
        errors = {}

        # Check unique table number except current record
        if 'table_number' in update_data:
            if self.selector.check_table_number_exists(
                table.restaurant_id, update_data['table_number'], table.id
            ):
                errors['table_number'] = 'Table number already exists for this restaurant'

        # Re-validate other fields if provided
        validation_errors = self._validate_table_data(table.restaurant_id, update_data)
        for key, value in validation_errors.items():
            if key in update_data:
                errors[key] = value

        return errors

    def _can_delete_table(self, table):
        """
        Business rules check cho table delete
        """
        # Check if table has active reservations or orders
        # This would need to be implemented based on related models
        return table.status != 'occupied'

    def _process_table_layout_data(self, queryset):
        """
        Process tables with layout information
        """
        tables = []
        for table in queryset:
            table_data = {
                'id': table.id,
                'table_number': table.table_number,
                'capacity': table.capacity,
                'floor': table.floor,
                'section': table.section,
                'status': table.status,
                'x_position': float(table.x_position) if table.x_position else None,
                'y_position': float(table.y_position) if table.y_position else None,
                'is_active': table.is_active
            }
            tables.append(table_data)

        return tables