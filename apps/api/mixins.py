from django.db import models
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework.viewsets import ModelViewSet
from collections import OrderedDict


# ==================== MODEL MIXINS ====================
class TimestampMixin(models.Model):
    """
    Automatically adds created_at and updated_at fields to any model
    
    Usage:
        class YourModel(TimestampMixin, models.Model):
            # Your fields here
            pass
    """
    created_at = models.DateTimeField(auto_now_add=True, help_text="Thời gian tạo")
    updated_at = models.DateTimeField(auto_now=True, help_text="Thời gian cập nhật cuối")
    
    class Meta:
        abstract = True



# ==================== API VIEW MIXINS ====================
class StandardResponseMixin:
    """
    Standardized response methods for API views
    
    Usage:
        class YourView(StandardResponseMixin, APIView):
            def get(self, request):
                return self.success_response(data={...})
    """
    
    def success_response(self, data=None, message="Success", status_code=status.HTTP_200_OK):
        """Return standardized success response"""
        from apps.api.response import ApiResponse
        return ApiResponse.success(data, message, status_code)
    
    def error_response(self, message="Error", errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        """Return standardized error response"""
        from apps.api.response import ApiResponse
        return ApiResponse.error(message, errors, status_code)
    
    def created_response(self, data=None, message="Resource created successfully"):
        """Return 201 Created response"""
        return self.success_response(data, message, status.HTTP_201_CREATED)
    
    def updated_response(self, data=None, message="Resource updated successfully"):
        """Return 200 OK response after update"""
        return self.success_response(data, message, status.HTTP_200_OK)
    
    def deleted_response(self, message="Resource deleted successfully"):
        """Return 204 No Content response"""
        return self.success_response(None, message, status.HTTP_204_NO_CONTENT)
    
    def not_found_response(self, message="Resource not found", errors=None):
        """Return 404 Not Found response"""
        return self.error_response(message, errors, status.HTTP_404_NOT_FOUND)


class ValidationMixin:
    """
    Common validation utilities for views
    
    Usage:
        class YourView(ValidationMixin, APIView):
            def post(self, request):
                self.validate_required_fields(['name', 'email'])
                # Continue processing...
    """
    
    def validate_required_fields(self, required_fields, data=None):
        """Validate that required fields are present"""
        if data is None:
            data = self.request.data
        
        missing_fields = []
        for field in required_fields:
            if field not in data or not data[field]:
                missing_fields.append(field)
        
        if missing_fields:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                'missing_fields': f"Các trường bắt buộc: {', '.join(missing_fields)}"
            })
    
    def validate_ownership(self, obj, user, field_name='author'):
        """Validate that user owns the resource"""
        if getattr(obj, field_name) != user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Bạn không có quyền thay đổi resource này")
        
        return True
    
    def validate_unique_field(self, field_name, value, model_class, exclude_id=None):
        """Validate that a field value is unique"""
        query = model_class.objects.filter(**{field_name: value})
        if exclude_id:
            query = query.exclude(id=exclude_id)
        
        if query.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                field_name: f"{field_name} đã tồn tại"
            })
        
        return True


class FilterMixin:
    """
    Mixin for filtering querysets based on query parameters
    
    Usage:
        class YourView(FilterMixin, ListAPIView):
            filter_fields = ['status', 'category']
            filter_lookups = {
                'status': 'exact',
                'category': 'exact',
                'created_at': 'gte',  # greater than or equal
            }
    """
    filter_fields = []
    filter_lookups = {}
    
    def get_filtered_queryset(self, queryset):
        """Apply filters from query parameters"""
        filter_params = {}
        
        for field in self.filter_fields:
            value = self.request.query_params.get(field)
            if value is not None:
                lookup = self.filter_lookups.get(field, 'exact')
                if lookup == 'exact':
                    filter_params[field] = value
                else:
                    filter_params[f"{field}__{lookup}"] = value
        
        if filter_params:
            queryset = queryset.filter(**filter_params)
        
        return queryset
    
    def get_queryset(self):
        """Override to apply filters"""
        queryset = super().get_queryset()
        return self.get_filtered_queryset(queryset)


class OrderingMixin:
    """
    Mixin for ordering querysets
    
    Usage:
        class YourView(OrderingMixin, ListAPIView):
            ordering_fields = ['created_at', 'name', 'price']
            default_ordering = ['-created_at']
    """
    ordering_fields = []
    default_ordering = []
    
    def get_ordered_queryset(self, queryset):
        """Apply ordering from query parameters"""
        ordering_param = self.request.query_params.get('ordering')
        
        if ordering_param:
            # Validate ordering field
            ordering_fields = ordering_param.split(',')
            valid_ordering = []
            
            for field in ordering_fields:
                field = field.strip()
                # Remove leading - for descending
                base_field = field.lstrip('-')
                
                if base_field in self.ordering_fields:
                    valid_ordering.append(field)
            
            if valid_ordering:
                queryset = queryset.order_by(*valid_ordering)
        elif self.default_ordering:
            queryset = queryset.order_by(*self.default_ordering)
        
        return queryset
    
    def get_queryset(self):
        """Override to apply ordering"""
        queryset = super().get_queryset()
        return self.get_ordered_queryset(queryset)