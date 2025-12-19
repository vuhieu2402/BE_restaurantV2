from rest_framework.response import Response
from rest_framework import status


class ApiResponse:
    """
    Standardized API response format for consistent API responses
    
    All responses follow this structure:
    {
        "success": bool,
        "message": str,
        "data": any,
        "error": any (only present when success=False)
    }
    """

    @staticmethod
    def success(data=None, message="Success", status_code=status.HTTP_200_OK):
        """
        Return standardized success response
        
        Args:
            data: Response data (dict, list, or any serializable object)
            message: Success message
            status_code: HTTP status code (default: 200)
        
        Returns:
            Response object with standardized format
        """
        return Response({
            "success": True,
            "message": message,
            "data": data,
            "error": None
        }, status=status_code)

    @staticmethod
    def error(message="Error", errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        """
        Return standardized error response
        
        Args:
            message: Error message
            errors: Error details (dict, list, or any serializable object)
            status_code: HTTP status code (default: 400)
        
        Returns:
            Response object with standardized format
        """
        return Response({
            "success": False,
            "message": message,
            "data": None,
            "error": errors
        }, status=status_code)
    
    @staticmethod
    def paginated(data, pagination_info):
        """
        Return paginated response in standardized format
        
        Args:
            data: List of items for current page
            pagination_info: Dict containing pagination metadata:
                - count: Total number of items
                - next: URL to next page (or None)
                - previous: URL to previous page (or None)
                - current_page: Current page number
                - total_pages: Total number of pages
                - page_size: Number of items per page
        
        Returns:
            Response object with paginated data
        """
        return Response({
            "success": True,
            "message": "Success",
            "data": data,
            "pagination": pagination_info,
            "error": None
        }, status=status.HTTP_200_OK)
    
    @staticmethod
    def created(data=None, message="Resource created successfully"):
        """Shortcut for 201 Created response"""
        return ApiResponse.success(data, message, status.HTTP_201_CREATED)
    
    @staticmethod
    def updated(data=None, message="Resource updated successfully"):
        """Shortcut for 200 OK response after update"""
        return ApiResponse.success(data, message, status.HTTP_200_OK)
    
    @staticmethod
    def deleted(message="Resource deleted successfully"):
        """Shortcut for 204 No Content response"""
        return ApiResponse.success(None, message, status.HTTP_204_NO_CONTENT)
    
    @staticmethod
    def not_found(message="Resource not found", errors=None):
        """Shortcut for 404 Not Found response"""
        return ApiResponse.error(message, errors, status.HTTP_404_NOT_FOUND)
    
    @staticmethod
    def unauthorized(message="Authentication required", errors=None):
        """Shortcut for 401 Unauthorized response"""
        return ApiResponse.error(message, errors, status.HTTP_401_UNAUTHORIZED)
    
    @staticmethod
    def forbidden(message="Permission denied", errors=None):
        """Shortcut for 403 Forbidden response"""
        return ApiResponse.error(message, errors, status.HTTP_403_FORBIDDEN)
    
    @staticmethod
    def bad_request(message="Bad request", errors=None):
        """Shortcut for 400 Bad Request response"""
        return ApiResponse.error(message, errors, status.HTTP_400_BAD_REQUEST)
    
    @staticmethod
    def validation_error(message="Validation error", errors=None):
        """Shortcut for 422 Unprocessable Entity response"""
        return ApiResponse.error(message, errors, status.HTTP_422_UNPROCESSABLE_ENTITY)