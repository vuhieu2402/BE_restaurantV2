"""
Salary and Bonus Services - Business Logic Layer
Xử lý tính lương, thưởng và các business rules
"""
from django.db import transaction, models
from django.utils import timezone
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import datetime, timedelta
import logging
from .models import Employee, Shift, SalaryRate, BonusRule, Payroll, PayrollItem

logger = logging.getLogger(__name__)


class ShiftService:
    """Service cho quản lý ca làm việc"""
    
    @staticmethod
    def check_in(shift_id, location=None, notes=None):
        """
        Check-in cho ca làm việc
        Returns: (success: bool, message: str, shift: Shift or None)
        """
        try:
            with transaction.atomic():
                shift = Shift.objects.select_for_update().get(id=shift_id)
                
                # Validate status
                if shift.status != 'scheduled':
                    return False, f"Không thể check-in. Trạng thái hiện tại: {shift.get_status_display()}", None
                
                # Check-in
                shift.actual_start_time = timezone.now()
                shift.status = 'checked_in'
                if location:
                    shift.location = location
                if notes:
                    shift.notes = (shift.notes or '') + f"\n[Check-in] {notes}"
                shift.save()
                
                logger.info(f"Employee {shift.employee.employee_id} checked in for shift {shift_id}")
                return True, "Check-in thành công", shift
                
        except Shift.DoesNotExist:
            return False, "Không tìm thấy ca làm việc", None
        except Exception as e:
            logger.error(f"Check-in error: {str(e)}")
            return False, f"Lỗi check-in: {str(e)}", None
    
    @staticmethod
    def check_out(shift_id, notes=None):
        """
        Check-out cho ca làm việc
        Returns: (success: bool, message: str, shift: Shift or None)
        """
        try:
            with transaction.atomic():
                shift = Shift.objects.select_for_update().get(id=shift_id)
                
                # Validate status
                if shift.status != 'checked_in':
                    return False, f"Không thể check-out. Trạng thái hiện tại: {shift.get_status_display()}", None
                
                # Check-out
                shift.actual_end_time = timezone.now()
                shift.status = 'checked_out'
                if notes:
                    shift.notes = (shift.notes or '') + f"\n[Check-out] {notes}"
                shift.save()
                
                logger.info(f"Employee {shift.employee.employee_id} checked out for shift {shift_id}. Total hours: {shift.total_hours}")
                return True, f"Check-out thành công. Tổng giờ làm: {shift.total_hours}", shift
                
        except Shift.DoesNotExist:
            return False, "Không tìm thấy ca làm việc", None
        except Exception as e:
            logger.error(f"Check-out error: {str(e)}")
            return False, f"Lỗi check-out: {str(e)}", None
    
    @staticmethod
    def get_employee_shifts(employee_id, start_date=None, end_date=None):
        """Lấy danh sách ca làm của nhân viên"""
        shifts = Shift.objects.filter(employee_id=employee_id)
        
        if start_date:
            shifts = shifts.filter(date__gte=start_date)
        if end_date:
            shifts = shifts.filter(date__lte=end_date)
        
        return shifts.order_by('-date', '-scheduled_start_time')


class PayrollService:
    """Service cho tính lương và quản lý bảng lương"""
    
    @staticmethod
    def get_salary_rate(employee, date):
        """
        Lấy mức lương áp dụng cho nhân viên tại thời điểm cụ thể
        Returns: SalaryRate or None
        """
        # Tìm mức lương theo restaurant và position
        rates = SalaryRate.objects.filter(
            restaurant=employee.restaurant,
            position=employee.position,
            effective_date__lte=date,
            is_active=True
        )
        
        # Nếu có expiry_date, phải >= date
        rates = rates.filter(
            models.Q(expiry_date__isnull=True) | models.Q(expiry_date__gte=date)
        )
        
        # Lấy mức lương mới nhất
        return rates.order_by('-effective_date').first()
    
    @staticmethod
    def calculate_payroll(employee_id, month, year, force_recalculate=False):
        """
        Tính bảng lương cho nhân viên trong tháng
        Returns: (success: bool, message: str, payroll: Payroll or None)
        """
        try:
            with transaction.atomic():
                employee = Employee.objects.get(id=employee_id)
                
                # Kiểm tra đã tồn tại chưa
                payroll, created = Payroll.objects.get_or_create(
                    employee=employee,
                    month=month,
                    year=year,
                    defaults={
                        'restaurant': employee.restaurant,
                        'period_start': datetime(year, month, 1).date(),
                        'period_end': (datetime(year, month + 1, 1) - timedelta(days=1)).date() if month < 12 else datetime(year + 1, 1, 1).date() - timedelta(days=1),
                    }
                )
                
                if not created and not force_recalculate:
                    if payroll.status != 'draft':
                        return False, f"Bảng lương đã được tính. Trạng thái: {payroll.get_status_display()}", None
                
                # Xóa các items cũ nếu tính lại
                if not created:
                    PayrollItem.objects.filter(payroll=payroll).delete()
                    payroll.status = 'draft'
                
                # Lấy tất cả shifts trong tháng
                period_start = payroll.period_start
                period_end = payroll.period_end
                shifts = Shift.objects.filter(
                    employee=employee,
                    date__gte=period_start,
                    date__lte=period_end,
                    status='checked_out'
                )
                
                # Tính tổng giờ làm
                total_hours = Decimal('0.00')
                regular_hours = Decimal('0.00')
                overtime_hours = Decimal('0.00')
                base_salary = Decimal('0.00')
                overtime_salary = Decimal('0.00')
                
                # Tính lương cho từng ca
                for shift in shifts:
                    # Lấy mức lương tại thời điểm ca làm
                    salary_rate = PayrollService.get_salary_rate(employee, shift.date)
                    if not salary_rate:
                        logger.warning(f"No salary rate found for employee {employee_id} on {shift.date}")
                        continue
                    
                    shift_hours = shift.total_hours
                    shift_regular = shift.regular_hours
                    shift_overtime = shift.overtime_hours
                    
                    total_hours += shift_hours
                    regular_hours += shift_regular
                    overtime_hours += shift_overtime
                    
                    # Tính lương cơ bản
                    shift_base = shift_regular * salary_rate.hourly_rate
                    base_salary += shift_base
                    
                    # Tạo PayrollItem cho lương cơ bản
                    PayrollItem.objects.create(
                        payroll=payroll,
                        item_type='base_salary',
                        description=f"Lương ca làm {shift.date} ({shift_regular} giờ)",
                        quantity=shift_regular,
                        unit_rate=salary_rate.hourly_rate,
                        amount=shift_base,
                        shift=shift
                    )
                    
                    # Tính lương làm thêm
                    if shift_overtime > 0:
                        shift_overtime_pay = shift_overtime * salary_rate.overtime_rate
                        overtime_salary += shift_overtime_pay
                        
                        # Tạo PayrollItem cho lương làm thêm
                        PayrollItem.objects.create(
                            payroll=payroll,
                            item_type='overtime',
                            description=f"Lương làm thêm ca {shift.date} ({shift_overtime} giờ)",
                            quantity=shift_overtime,
                            unit_rate=salary_rate.overtime_rate,
                            amount=shift_overtime_pay,
                            shift=shift
                        )
                
                # Tính thưởng
                total_bonus = BonusService.calculate_bonuses(employee, period_start, period_end, payroll)
                
                # Tính khấu trừ (nếu có)
                total_deductions = Decimal('0.00')
                
                # Tính lương thực nhận
                net_salary = base_salary + overtime_salary + total_bonus - total_deductions
                
                # Cập nhật payroll
                payroll.total_hours = total_hours
                payroll.regular_hours = regular_hours
                payroll.overtime_hours = overtime_hours
                payroll.base_salary = base_salary
                payroll.overtime_salary = overtime_salary
                payroll.total_bonus = total_bonus
                payroll.total_deductions = total_deductions
                payroll.net_salary = net_salary
                payroll.status = 'calculated'
                payroll.calculated_at = timezone.now()
                payroll.save()
                
                logger.info(f"Calculated payroll for employee {employee_id}, month {month}/{year}. Net salary: {net_salary}")
                return True, "Tính lương thành công", payroll
                
        except Employee.DoesNotExist:
            return False, "Không tìm thấy nhân viên", None
        except Exception as e:
            logger.error(f"Calculate payroll error: {str(e)}")
            return False, f"Lỗi tính lương: {str(e)}", None
    
    @staticmethod
    def approve_payroll(payroll_id, approved_by, notes=None):
        """Duyệt bảng lương"""
        try:
            with transaction.atomic():
                payroll = Payroll.objects.select_for_update().get(id=payroll_id)
                
                if payroll.status != 'calculated':
                    return False, f"Chỉ có thể duyệt bảng lương ở trạng thái 'Đã tính'. Trạng thái hiện tại: {payroll.get_status_display()}", None
                
                payroll.status = 'approved'
                payroll.approved_at = timezone.now()
                payroll.approved_by = approved_by
                if notes:
                    payroll.notes = (payroll.notes or '') + f"\n[Duyệt] {notes}"
                payroll.save()
                
                logger.info(f"Payroll {payroll_id} approved by {approved_by.username}")
                return True, "Duyệt bảng lương thành công", payroll
                
        except Payroll.DoesNotExist:
            return False, "Không tìm thấy bảng lương", None
        except Exception as e:
            logger.error(f"Approve payroll error: {str(e)}")
            return False, f"Lỗi duyệt bảng lương: {str(e)}", None
    
    @staticmethod
    def mark_as_paid(payroll_id, notes=None):
        """Đánh dấu đã trả lương"""
        try:
            with transaction.atomic():
                payroll = Payroll.objects.select_for_update().get(id=payroll_id)
                
                if payroll.status != 'approved':
                    return False, f"Chỉ có thể đánh dấu đã trả khi bảng lương đã được duyệt. Trạng thái hiện tại: {payroll.get_status_display()}", None
                
                payroll.status = 'paid'
                payroll.paid_at = timezone.now()
                if notes:
                    payroll.notes = (payroll.notes or '') + f"\n[Trả lương] {notes}"
                payroll.save()
                
                logger.info(f"Payroll {payroll_id} marked as paid")
                return True, "Đánh dấu đã trả lương thành công", payroll
                
        except Payroll.DoesNotExist:
            return False, "Không tìm thấy bảng lương", None
        except Exception as e:
            logger.error(f"Mark paid error: {str(e)}")
            return False, f"Lỗi đánh dấu đã trả: {str(e)}", None


class BonusService:
    """Service cho tính thưởng"""
    
    @staticmethod
    def calculate_bonuses(employee, period_start, period_end, payroll):
        """
        Tính thưởng cho nhân viên trong kỳ
        Returns: total_bonus (Decimal)
        """
        total_bonus = Decimal('0.00')
        
        # Lấy tất cả bonus rules active của restaurant
        bonus_rules = BonusRule.objects.filter(
            restaurant=employee.restaurant,
            is_active=True,
            effective_date__lte=period_end
        ).filter(
            models.Q(expiry_date__isnull=True) | models.Q(expiry_date__gte=period_start)
        )
        
        for rule in bonus_rules:
            bonus_amount = BonusService._check_bonus_rule(employee, rule, period_start, period_end, payroll)
            if bonus_amount > 0:
                total_bonus += bonus_amount
        
        return total_bonus
    
    @staticmethod
    def _check_bonus_rule(employee, rule, period_start, period_end, payroll):
        """
        Kiểm tra và tính thưởng theo quy tắc
        Returns: bonus_amount (Decimal)
        """
        condition_met = False
        bonus_amount = Decimal('0.00')
        
        if rule.bonus_type == 'shift_count':
            # Thưởng theo số ca làm
            shift_count = Shift.objects.filter(
                employee=employee,
                date__gte=period_start,
                date__lte=period_end,
                status='checked_out'
            ).count()
            
            if shift_count >= rule.condition_value:
                condition_met = True
        
        elif rule.bonus_type == 'attendance':
            # Thưởng theo tỷ lệ đi làm
            # Tính số ngày làm việc / tổng số ngày trong kỳ
            total_days = (period_end - period_start).days + 1
            worked_days = Shift.objects.filter(
                employee=employee,
                date__gte=period_start,
                date__lte=period_end,
                status='checked_out'
            ).values('date').distinct().count()
            
            attendance_rate = (worked_days / total_days) * 100 if total_days > 0 else 0
            
            if attendance_rate >= rule.condition_value:
                condition_met = True
        
        elif rule.bonus_type == 'sales_target':
            # Thưởng theo doanh số
            # TODO: Cần tích hợp với orders app để tính doanh số
            # Tạm thời return 0
            pass
        
        elif rule.bonus_type == 'customer_rating':
            # Thưởng theo đánh giá khách hàng
            # TODO: Cần tích hợp với reviews/ratings
            # Tạm thời return 0
            pass
        
        elif rule.bonus_type == 'custom':
            # Thưởng tùy chỉnh - cần implement logic riêng
            pass
        
        if condition_met:
            if rule.calculation_type == 'fixed':
                bonus_amount = rule.bonus_amount
            elif rule.calculation_type == 'percentage':
                # Tính % của tổng lương cơ bản
                bonus_amount = (payroll.base_salary * rule.bonus_amount) / 100
            
            # Tạo PayrollItem cho thưởng
            PayrollItem.objects.create(
                payroll=payroll,
                item_type='bonus',
                description=f"Thưởng: {rule.name}",
                quantity=Decimal('1.00'),
                unit_rate=bonus_amount,
                amount=bonus_amount,
                bonus_rule=rule
            )
        
        return bonus_amount

