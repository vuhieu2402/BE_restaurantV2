# Hệ thống Quản lý Lương Thưởng - Thiết kế

## 📋 Tổng quan

Hệ thống quản lý lương thưởng cho nhân viên nhà hàng với các tính năng:
- Ghi nhận ca làm việc (check-in/check-out)
- Tính lương theo giờ với mức lương tùy chỉnh
- Tính thưởng theo quy tắc linh hoạt
- Tạo bảng lương tháng tự động
- Theo dõi lịch sử lương và thưởng

## 🏗️ Kiến trúc

### Models

#### 1. Employee (Nhân viên)
- Liên kết với User (qua StaffProfile)
- Liên kết với Restaurant
- Thông tin: position, department, hire_date, status
- **Note**: Có thể tái sử dụng StaffProfile hoặc tạo mới để có thêm tính năng

#### 2. Shift (Ca làm việc)
- Liên kết với Employee và Restaurant
- Thông tin: date, start_time, end_time, break_duration
- Trạng thái: scheduled, checked_in, checked_out, cancelled
- Tính toán: total_hours, overtime_hours
- Ghi chú: notes, location (nếu làm việc tại nhiều địa điểm)

#### 3. SalaryRate (Mức lương)
- Liên kết với Restaurant (hoặc global)
- Thông tin: position, hourly_rate, overtime_rate_multiplier
- Áp dụng: effective_date, expiry_date
- Có thể có nhiều mức lương cho cùng position (theo thời gian)

#### 4. BonusRule (Quy tắc thưởng)
- Liên kết với Restaurant
- Loại thưởng: sales_target, shift_count, customer_rating, attendance
- Điều kiện: condition_type, condition_value, bonus_amount/percentage
- Trạng thái: active, inactive

#### 5. Payroll (Bảng lương)
- Liên kết với Employee và Restaurant
- Thông tin: month, year, period_start, period_end
- Tổng hợp: total_hours, base_salary, overtime_salary, total_bonus, deductions, net_salary
- Trạng thái: draft, calculated, approved, paid
- Ngày: calculated_at, approved_at, paid_at

#### 6. PayrollItem (Chi tiết lương)
- Liên kết với Payroll
- Loại: base_salary, overtime, bonus, deduction, allowance
- Thông tin: description, amount, quantity (nếu áp dụng)
- Reference: shift_id, bonus_rule_id (nếu có)

## 🔄 Luồng hoạt động

### 1. Ghi nhận ca làm việc
```
Employee → Check-in → Shift (scheduled → checked_in)
         → Làm việc → Shift (checked_in)
         → Check-out → Shift (checked_out)
         → Tính giờ làm: total_hours = end_time - start_time - break_duration
```

### 2. Tính lương
```
Payroll Service:
1. Lấy tất cả shifts trong tháng của Employee
2. Tính base_salary = sum(shift.total_hours * hourly_rate)
3. Tính overtime_salary = sum(overtime_hours * hourly_rate * overtime_multiplier)
4. Tính bonus dựa trên BonusRule
5. Tính deductions (nếu có)
6. net_salary = base_salary + overtime_salary + total_bonus - deductions
```

### 3. Tính thưởng
```
Bonus Service:
1. Lấy các BonusRule active của Restaurant
2. Kiểm tra điều kiện:
   - sales_target: Tổng doanh số đạt target?
   - shift_count: Số ca làm đạt ngưỡng?
   - customer_rating: Đánh giá khách hàng >= threshold?
   - attendance: Tỷ lệ đi làm >= threshold?
3. Tính bonus amount
4. Tạo PayrollItem với type='bonus'
```

## 📊 Database Schema

### Relationships
```
Restaurant (1) ──< (N) Employee
Employee (1) ──< (N) Shift
Restaurant (1) ──< (N) SalaryRate
Restaurant (1) ──< (N) BonusRule
Employee (1) ──< (N) Payroll
Payroll (1) ──< (N) PayrollItem
Shift (1) ──< (N) PayrollItem (reference)
BonusRule (1) ──< (N) PayrollItem (reference)
```

## 🎯 Business Rules

1. **Ca làm việc**:
   - Một nhân viên không thể có 2 ca chồng chéo thời gian
   - Check-out phải sau check-in
   - Tự động tính overtime nếu > 8 giờ/ngày hoặc > 40 giờ/tuần

2. **Lương**:
   - Mức lương theo giờ có thể thay đổi theo thời gian
   - Overtime rate thường là 1.5x hoặc 2x hourly rate
   - Lương được tính dựa trên mức lương hiện tại tại thời điểm ca làm

3. **Thưởng**:
   - Có thể có nhiều loại thưởng cùng lúc
   - Thưởng có thể là số tiền cố định hoặc % lương
   - Thưởng chỉ áp dụng khi điều kiện được thỏa mãn

4. **Bảng lương**:
   - Mỗi nhân viên có 1 bảng lương/tháng
   - Bảng lương có thể được tính lại nếu có thay đổi
   - Chỉ có thể approve khi status = 'calculated'
   - Chỉ có thể mark paid khi status = 'approved'

## 🔐 Permissions

- **Employee**: Xem ca làm của mình, check-in/check-out
- **Manager**: Xem tất cả ca làm, tạo/sửa bảng lương, approve payroll
- **Admin**: Tất cả quyền, bao gồm cấu hình SalaryRate và BonusRule

## 📝 API Endpoints (Dự kiến)

### Shifts
- `POST /api/salary/shifts/` - Tạo ca làm (scheduled)
- `POST /api/salary/shifts/{id}/check-in/` - Check-in
- `POST /api/salary/shifts/{id}/check-out/` - Check-out
- `GET /api/salary/shifts/` - Danh sách ca làm
- `GET /api/salary/shifts/{id}/` - Chi tiết ca làm

### Payroll
- `POST /api/salary/payrolls/calculate/` - Tính bảng lương
- `GET /api/salary/payrolls/` - Danh sách bảng lương
- `GET /api/salary/payrolls/{id}/` - Chi tiết bảng lương
- `POST /api/salary/payrolls/{id}/approve/` - Duyệt bảng lương
- `POST /api/salary/payrolls/{id}/mark-paid/` - Đánh dấu đã trả

### Salary Rates
- `GET /api/salary/salary-rates/` - Danh sách mức lương
- `POST /api/salary/salary-rates/` - Tạo mức lương
- `PUT /api/salary/salary-rates/{id}/` - Cập nhật mức lương

### Bonus Rules
- `GET /api/salary/bonus-rules/` - Danh sách quy tắc thưởng
- `POST /api/salary/bonus-rules/` - Tạo quy tắc thưởng
- `PUT /api/salary/bonus-rules/{id}/` - Cập nhật quy tắc thưởng

