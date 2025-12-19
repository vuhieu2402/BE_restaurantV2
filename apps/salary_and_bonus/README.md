# Hệ thống Quản lý Lương Thưởng

## 📋 Tổng quan

Hệ thống quản lý lương thưởng cho nhân viên nhà hàng với các tính năng:
- ✅ Ghi nhận ca làm việc (check-in/check-out)
- ✅ Tính lương theo giờ với mức lương tùy chỉnh
- ✅ Tính thưởng theo quy tắc linh hoạt
- ✅ Tạo bảng lương tháng tự động
- ✅ Theo dõi lịch sử lương và thưởng

## 🏗️ Cấu trúc

### Models

1. **Employee** - Nhân viên
   - Liên kết User với Restaurant
   - Thông tin: position, department, hire_date, status

2. **Shift** - Ca làm việc
   - Ghi nhận check-in/check-out
   - Tính toán giờ làm, giờ làm thêm tự động

3. **SalaryRate** - Mức lương
   - Cấu hình lương theo giờ theo position
   - Hệ số làm thêm (overtime multiplier)

4. **BonusRule** - Quy tắc thưởng
   - Thưởng theo số ca làm, tỷ lệ đi làm, doanh số, đánh giá
   - Có thể là số tiền cố định hoặc % lương

5. **Payroll** - Bảng lương
   - Tổng hợp lương tháng
   - Trạng thái: draft → calculated → approved → paid

6. **PayrollItem** - Chi tiết lương
   - Các khoản: lương cơ bản, làm thêm, thưởng, khấu trừ

### Services

- **ShiftService**: Quản lý check-in/check-out
- **PayrollService**: Tính lương, duyệt bảng lương
- **BonusService**: Tính thưởng theo quy tắc

## 🚀 Cài đặt

1. **Tạo migrations**:
```bash
python manage.py makemigrations salary_and_bonus
```

2. **Apply migrations**:
```bash
python manage.py migrate salary_and_bonus
```

3. **Tạo superuser** (nếu chưa có):
```bash
python manage.py createsuperuser
```

4. **Truy cập admin**:
- URL: `http://localhost:8000/admin/`
- Đăng nhập và quản lý các models

## 📝 Sử dụng

### 1. Tạo nhân viên (Employee)
- Vào Admin → Employees → Add Employee
- Chọn User và Restaurant
- Nhập thông tin: employee_id, position, department, hire_date

### 2. Cấu hình mức lương (SalaryRate)
- Vào Admin → Salary Rates → Add Salary Rate
- Chọn Restaurant, Position
- Nhập hourly_rate và overtime_rate_multiplier

### 3. Tạo ca làm việc (Shift)
- Vào Admin → Shifts → Add Shift
- Chọn Employee, Restaurant, Date
- Nhập scheduled_start_time và scheduled_end_time

### 4. Check-in/Check-out
- Nhân viên check-in khi bắt đầu ca làm
- Check-out khi kết thúc ca làm
- Hệ thống tự động tính giờ làm

### 5. Tính bảng lương
- Vào Admin → Payrolls → Add Payroll
- Hoặc sử dụng API để tính tự động
- Hệ thống sẽ:
  - Tính lương cơ bản dựa trên giờ làm
  - Tính lương làm thêm (nếu > 8 giờ/ngày)
  - Tính thưởng dựa trên BonusRule
  - Tính lương thực nhận

## 🔄 Luồng hoạt động

```
1. Tạo Employee → Link User với Restaurant
2. Cấu hình SalaryRate → Mức lương theo position
3. Tạo Shift → Lên lịch ca làm
4. Check-in → Bắt đầu ca làm
5. Check-out → Kết thúc ca làm, tính giờ
6. Tính Payroll → Tự động tính lương + thưởng
7. Duyệt Payroll → Manager approve
8. Trả lương → Mark as paid
```

## 📊 API Endpoints (Cần implement)

Xem file `DESIGN.md` để biết chi tiết các API endpoints cần thiết.

## 🔐 Permissions

- **Employee**: Xem ca làm của mình, check-in/check-out
- **Manager**: Xem tất cả ca làm, tạo/sửa bảng lương, approve payroll
- **Admin**: Tất cả quyền

## 📌 Lưu ý

1. **Tích hợp với Orders**: 
   - BonusRule loại `sales_target` cần tích hợp với orders app để tính doanh số

2. **Tích hợp với Reviews**:
   - BonusRule loại `customer_rating` cần tích hợp với reviews/ratings

3. **Tính lương**:
   - Mức lương được lấy dựa trên SalaryRate tại thời điểm ca làm
   - Nếu có nhiều SalaryRate, lấy mức lương mới nhất (effective_date)

4. **Giờ làm thêm**:
   - Tự động tính nếu > 8 giờ/ngày
   - Áp dụng overtime_rate_multiplier

## 🎯 Next Steps

1. ✅ Models đã được tạo
2. ✅ Admin đã được cấu hình
3. ✅ Serializers đã được tạo
4. ✅ Services đã được tạo
5. ⏳ Views và URLs cần được tạo
6. ⏳ Tests cần được viết
7. ⏳ Tích hợp với Orders và Reviews apps

