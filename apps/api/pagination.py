from rest_framework.pagination import PageNumberPagination, CursorPagination
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from decouple import config


class BasePaginationMixin:
    """
    Base pagination mixin with shared functionality for all pagination classes
    """

    def get_paginated_response_data(self, data):
        """
        Return paginated response data in standardized format with enhanced metadata
        This returns the response data that can be used by StandardResponseMixin
        """
        # Basic pagination info
        pagination_info = {
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'current_page': self.page.number,
            'total_pages': self.page.paginator.num_pages,
            'page_size': self.get_page_size(self.request),
            'has_next': self.page.has_next(),
            'has_previous': self.page.has_previous(),
            'start_index': self.page.start_index(),
            'end_index': self.page.end_index(),
        }

        # Add performance hints for large datasets
        if hasattr(self, 'add_performance_hints'):
            pagination_info.update(self.get_performance_hints())

        return {
            'data': data,
            'pagination': pagination_info
        }

    def get_paginated_response_with_cache(self, data):
        """
        Return paginated response with caching headers
        """
        response_data = self.get_paginated_response_data(data)

        # Create response using ApiResponse
        from apps.api.response import ApiResponse
        response = ApiResponse.paginated(response_data['data'], response_data['pagination'])

        # Add caching headers for better performance
        if hasattr(self, 'add_cache_headers'):
            self.add_cache_headers(response)

        return response

    def get_page_size(self, request):
        """
        Get page size from query parameter or use default, with validation
        """
        if hasattr(self, 'page_size_query_param'):
            try:
                page_size = int(request.query_params.get(self.page_size_query_param, self.page_size))
                # Validate against min and max
                if hasattr(self, 'min_page_size') and page_size < self.min_page_size:
                    page_size = self.min_page_size
                if hasattr(self, 'max_page_size') and page_size > self.max_page_size:
                    page_size = self.max_page_size
                return page_size
            except (ValueError, TypeError):
                pass
        return self.page_size

    def get_performance_hints(self):
        """
        Return performance hints for large datasets
        """
        hints = {}
        if hasattr(self, 'performance_hints') and self.performance_hints:
            hints['performance'] = self.performance_hints
        return hints

    def add_cache_headers(self, response):
        """
        Add cache headers for better performance
        """
        if hasattr(self, 'cache_timeout') and self.cache_timeout:
            response['Cache-Control'] = f'public, max-age={self.cache_timeout}'
        return response


class BasePageNumberPagination(PageNumberPagination, BasePaginationMixin):
    """
    Base page number pagination class with shared functionality
    """
    page_size_query_param = 'page_size'
    min_page_size = 1

    def __init__(self):
        super().__init__()
        # Allow configuration via environment variables
        if hasattr(self, 'config_key'):
            env_page_size = config(f'{self.config_key}_PAGE_SIZE', default=self.page_size, cast=int)
            env_max_page_size = config(f'{self.config_key}_MAX_PAGE_SIZE', default=self.max_page_size, cast=int)
            self.page_size = env_page_size
            self.max_page_size = env_max_page_size

    def get_paginated_response(self, data):
        """
        Return paginated response using our custom format
        """
        return self.get_paginated_response_with_cache(data)


class StandardPageNumberPagination(BasePageNumberPagination):
    """
    Standard pagination class with customizable page size

    Usage:
        class YourView(ListAPIView):
            pagination_class = StandardPageNumberPagination
            # Optionally override in view:
            # page_size = 20
            # max_page_size = 100
    """
    config_key = 'STANDARD_PAGINATION'
    page_size = config('STANDARD_PAGINATION_PAGE_SIZE', default=20, cast=int)
    max_page_size = config('STANDARD_PAGINATION_MAX_PAGE_SIZE', default=100, cast=int)
    cache_timeout = 300  # 5 minutes
    performance_hints = {
        'optimal_page_size': '20-50 items for best performance',
        'total_items_threshold': 1000
    }


class LargeResultsSetPagination(BasePageNumberPagination):
    """
    Pagination for large result sets (e.g., search results, analytics)

    Optimized for performance with larger page sizes and caching
    """
    config_key = 'LARGE_PAGINATION'
    page_size = config('LARGE_PAGINATION_PAGE_SIZE', default=50, cast=int)
    max_page_size = config('LARGE_PAGINATION_MAX_PAGE_SIZE', default=200, cast=int)
    cache_timeout = 600  # 10 minutes
    performance_hints = {
        'optimal_page_size': '50-100 items for large datasets',
        'total_items_threshold': 10000,
        'recommendation': 'Consider using cursor pagination for very large datasets'
    }


class SmallResultsSetPagination(BasePageNumberPagination):
    """
    Pagination for small result sets (e.g., dropdown lists, autocomplete)

    Optimized for quick responses with smaller page sizes
    """
    config_key = 'SMALL_PAGINATION'
    page_size = config('SMALL_PAGINATION_PAGE_SIZE', default=10, cast=int)
    max_page_size = config('SMALL_PAGINATION_MAX_PAGE_SIZE', default=50, cast=int)
    cache_timeout = 1800  # 30 minutes
    performance_hints = {
        'optimal_page_size': '5-20 items for UI components',
        'total_items_threshold': 100
    }


class CursorBasedPagination(CursorPagination, BasePaginationMixin):
    """
    Cursor-based pagination for large datasets with optimal performance

    Benefits:
    - Consistent performance regardless of dataset size
    - No duplicate items when data changes during pagination
    - Ideal for real-time feeds, logs, and large datasets

    Usage:
        class YourView(ListAPIView):
            pagination_class = CursorBasedPagination
            ordering = '-created_at'  # Required for cursor pagination
    """
    page_size = config('CURSOR_PAGINATION_PAGE_SIZE', default=20, cast=int)
    page_size_query_param = 'page_size'
    max_page_size = config('CURSOR_PAGINATION_MAX_PAGE_SIZE', default=100, cast=int)
    ordering = '-created_at'  # Default ordering, can be overridden in views
    cache_timeout = 300  # 5 minutes

    def get_paginated_response(self, data):
        """
        Return cursor-based paginated response using our custom format
        """
        from apps.api.response import ApiResponse

        pagination_info = {
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'page_size': self.get_page_size(self.request),
            'has_next': self.has_next,
            'has_previous': self.has_previous,
        }

        # Add cursor-specific hints
        pagination_info.update({
            'pagination_type': 'cursor',
            'performance': {
                'benefits': [
                    'Consistent performance regardless of offset',
                    'No duplicate items during pagination',
                    'Ideal for real-time data'
                ],
                'optimal_for': 'Large datasets (>10,000 items)'
            }
        })

        response = ApiResponse.paginated(data, pagination_info)

        # Add caching headers
        if self.cache_timeout:
            response['Cache-Control'] = f'public, max-age={self.cache_timeout}'

        return response


class DynamicPagination:
    """
    Dynamic pagination selector that chooses optimal pagination based on dataset size

    Automatically switches between pagination methods for optimal performance
    """

    @staticmethod
    def get_pagination_class(estimated_count=None, default_class=StandardPageNumberPagination):
        """
        Return appropriate pagination class based on estimated count

        Args:
            estimated_count: Estimated number of items (optional)
            default_class: Default pagination class if count unknown

        Returns:
            Pagination class instance
        """
        if estimated_count is None:
            return default_class

        if estimated_count >= 10000:
            # Very large datasets - use cursor pagination
            return CursorBasedPagination
        elif estimated_count >= 1000:
            # Large datasets - use large results pagination
            return LargeResultsSetPagination
        elif estimated_count <= 100:
            # Small datasets - use small results pagination
            return SmallResultsSetPagination
        else:
            # Medium datasets - use standard pagination
            return StandardPageNumberPagination

    @staticmethod
    def get_optimal_page_size(estimated_count, min_size=10, max_size=100):
        """
        Calculate optimal page size based on dataset size
        """
        if estimated_count <= 50:
            return min(estimated_count, max_size)
        elif estimated_count <= 1000:
            return 20
        elif estimated_count <= 10000:
            return 50
        else:
            return 100

