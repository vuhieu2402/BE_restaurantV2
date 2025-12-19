"""
Serializers for Salary and Bonus Management
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import Employee, Shift, SalaryRate, BonusRule, Payroll, PayrollItem

User = get_user_model()


class EmployeeSerializer(serializers.ModelSerializer):
    """Serializer cho Employee"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'user', 'user_name', 'user_email', 'restaurant', 'restaurant_name',
            'employee_id', 'position', 'department', 'hire_date', 'status',
            'termination_date', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class ShiftSerializer(serializers.ModelSerializer):
    """Serializer cho Shift"""
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    total_hours = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    scheduled_hours = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    overtime_hours = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    regular_hours = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    
    class Meta:
        model = Shift
        fields = [
            'id', 'employee', 'employee_name', 'employee_id', 'restaurant', 'restaurant_name',
            'date', 'scheduled_start_time', 'scheduled_end_time',
            'actual_start_time', 'actual_end_time', 'break_duration_minutes',
            'status', 'notes', 'location',
            'total_hours', 'scheduled_hours', 'regular_hours', 'overtime_hours',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'total_hours', 'scheduled_hours', 
                           'regular_hours', 'overtime_hours']
    
    def validate(self, attrs):
        """Validate shift data"""
        # Nếu có actual_end_time, phải có actual_start_time
        if attrs.get('actual_end_time') and not attrs.get('actual_start_time'):
            if not self.instance or not self.instance.actual_start_time:
                raise serializers.ValidationError({
                    'actual_end_time': 'Phải có thời gian check-in trước khi check-out'
                })
        
        # actual_end_time phải sau actual_start_time
        if attrs.get('actual_start_time') and attrs.get('actual_end_time'):
            if attrs['actual_end_time'] <= attrs['actual_start_time']:
                raise serializers.ValidationError({
                    'actual_end_time': 'Thời gian check-out phải sau thời gian check-in'
                })
        
        return attrs


class ShiftCheckInSerializer(serializers.Serializer):
    """Serializer cho check-in"""
    location = serializers.CharField(max_length=200, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class ShiftCheckOutSerializer(serializers.Serializer):
    """Serializer cho check-out"""
    notes = serializers.CharField(required=False, allow_blank=True)


class SalaryRateSerializer(serializers.ModelSerializer):
    """Serializer cho SalaryRate"""
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    overtime_rate = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = SalaryRate
        fields = [
            'id', 'restaurant', 'restaurant_name', 'position',
            'hourly_rate', 'overtime_rate_multiplier', 'overtime_rate',
            'effective_date', 'expiry_date', 'is_active', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'overtime_rate']
    
    def validate(self, attrs):
        """Validate salary rate"""
        # expiry_date phải sau effective_date
        if attrs.get('expiry_date') and attrs.get('effective_date'):
            if attrs['expiry_date'] <= attrs['effective_date']:
                raise serializers.ValidationError({
                    'expiry_date': 'Ngày hết hạn phải sau ngày bắt đầu áp dụng'
                })
        
        return attrs


class BonusRuleSerializer(serializers.ModelSerializer):
    """Serializer cho BonusRule"""
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    
    class Meta:
        model = BonusRule
        fields = [
            'id', 'restaurant', 'restaurant_name', 'name', 'description',
            'bonus_type', 'condition_value', 'calculation_type', 'bonus_amount',
            'effective_date', 'expiry_date', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate(self, attrs):
        """Validate bonus rule"""
        # expiry_date phải sau effective_date
        if attrs.get('expiry_date') and attrs.get('effective_date'):
            if attrs['expiry_date'] <= attrs['effective_date']:
                raise serializers.ValidationError({
                    'expiry_date': 'Ngày hết hạn phải sau ngày bắt đầu áp dụng'
                })
        
        return attrs


class PayrollItemSerializer(serializers.ModelSerializer):
    """Serializer cho PayrollItem"""
    item_type_display = serializers.CharField(source='get_item_type_display', read_only=True)
    
    class Meta:
        model = PayrollItem
        fields = [
            'id', 'payroll', 'item_type', 'item_type_display',
            'description', 'quantity', 'unit_rate', 'amount',
            'shift', 'bonus_rule', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class PayrollSerializer(serializers.ModelSerializer):
    """Serializer cho Payroll"""
    employee_name = serializers.CharField(source='employee.user.get_full_name', read_only=True)
    employee_id = serializers.CharField(source='employee.employee_id', read_only=True)
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    items = PayrollItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Payroll
        fields = [
            'id', 'employee', 'employee_name', 'employee_id',
            'restaurant', 'restaurant_name',
            'month', 'year', 'period_start', 'period_end',
            'total_hours', 'regular_hours', 'overtime_hours',
            'base_salary', 'overtime_salary', 'total_bonus', 'total_deductions', 'net_salary',
            'status', 'status_display',
            'calculated_at', 'approved_at', 'approved_by', 'approved_by_name', 'paid_at',
            'notes', 'items',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'calculated_at', 'approved_at', 'paid_at',
            'total_hours', 'regular_hours', 'overtime_hours',
            'base_salary', 'overtime_salary', 'total_bonus', 'total_deductions', 'net_salary'
        ]


class PayrollCalculateSerializer(serializers.Serializer):
    """Serializer cho tính bảng lương"""
    employee_id = serializers.IntegerField(required=False)
    restaurant_id = serializers.IntegerField(required=False)
    month = serializers.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(12)])
    year = serializers.IntegerField(validators=[MinValueValidator(2000), MaxValueValidator(2100)])
    force_recalculate = serializers.BooleanField(default=False, help_text="Tính lại nếu đã tồn tại")


class PayrollApproveSerializer(serializers.Serializer):
    """Serializer cho duyệt bảng lương"""
    notes = serializers.CharField(required=False, allow_blank=True)


class PayrollMarkPaidSerializer(serializers.Serializer):
    """Serializer cho đánh dấu đã trả lương"""
    notes = serializers.CharField(required=False, allow_blank=True)

