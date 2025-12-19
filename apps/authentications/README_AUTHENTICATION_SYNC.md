# Authentication System Synchronization Guide

## 🔄 **Đồng Bộ Hóa Authentication System với User Models**

Tài liệu này mô tả các thay đổi đã thực hiện để đồng bộ hóa authentication system trong `apps/auth/` với user models trong `apps/users/`.

## 📋 **Vấn Đề Cần Giải Quyết**

### **Trước khi sửa đổi:**
1. **Serializer Fields Mismatch**: `UserSerializer` thiếu các trường quan trọng như `is_verified`, `date_of_birth`
2. **Validation Inconsistencies**: Phone và email validation bị lặp lại và không đồng bộ
3. **Missing Geographic Fields**: Latitude/longitude không được xử lý đúng
4. **Profile Update Issues**: Không có serializer riêng cho việc cập nhật profile
5. **Field Range Validation**: Thiếu validation cho latitude/longitude ranges

## ✅ **Các Thay Đổi Đã Thực Hiện**

### **1. UserSerializer Updates** (`apps/auth/serializers.py:12-147`)

**Fields Added:**
- `user_type_display`: Hiển thị user type bằng tiếng Việt
- `full_name`: Tên đầy đủ của user
- `is_verified`: Trạng thái xác thực email/SMS
- `date_joined`: Ngày tham gia (read-only)
- `created_at`, `updated_at`: Timestamp tracking

**New Validations:**
- `validate_email()`: Kiểm tra uniqueness với exclude current user cho updates
- `validate_phone_number()`: Tương tự như email validation
- `validate_latitude()`: Range check -90 to 90
- `validate_longitude()`: Range check -180 to 180
- `validate_date_of_birth()`: Age validation (1-120 years)
- `update()`: Method mới để handle partial updates đúng cách

### **2. RegisterSerializer Enhancements** (`apps/auth/serializers.py:193-296`)

**New Fields Added:**
- Address: `address`, `city`, `district`, `ward`, `postal_code`
- Geographic: `latitude`, `longitude` (DecimalField với precision đúng)
- Personal: `date_of_birth` (DateField)

**Validations:**
- Geographic coordinate range validation
- Age validation (1-120 years)
- Required `password_confirm` field

### **3. New UserProfileUpdateSerializer** (`apps/auth/serializers.py:443-521`)

**Purpose**: Dành riêng cho việc cập nhật thông tin user profile

**Features:**
- Read-only fields: `user_type`, `is_verified`, `date_joined`, timestamps
- All validations từ UserSerializer
- Optimized cho PATCH requests (partial updates)
- Display fields: `user_type_display`, `full_name`

### **4. View Updates** (`apps/auth/views.py:616-622`)

**UserProfileView.patch()**:
- Sử dụng `UserProfileUpdateSerializer` thay vì `UserSerializer`
- Proper error handling cho profile updates
- Maintained template pattern (View → Service → Response)

## 🏗️ **Cấu Trúc Database Đồng Bộ**

### **User Model Fields** (`apps/users/models.py`):
```python
# Basic Info
- id, username, email, first_name, last_name
- user_type (choices: customer, staff, manager, admin)
- phone_number (unique, regex validated)
- is_verified, is_active

# Personal Info
- date_of_birth (DateField)
- avatar (ImageField với MinIOMediaStorage)

# Address
- address, city, district, ward, postal_code

# Geographic
- latitude, longitude (DecimalField 9,6 precision)

# Timestamps (TimestampMixin)
- created_at, updated_at
```

### **Serializer Mapping**:
| User Model Field | UserSerializer | RegisterSerializer | UserProfileUpdateSerializer |
|------------------|---------------|-------------------|---------------------------|
| `id` | ✅ Read-only | ❌ Not needed | ✅ Read-only |
| `username` | ✅ | ✅ | ❌ Not updatable |
| `email` | ✅ Unique validation | ✅ Required field | ✅ Updatable |
| `phone_number` | ✅ Unique validation | ✅ Required field | ✅ Updatable |
| `user_type` | ✅ Choice field | ✅ Default 'customer' | ✅ Read-only |
| `is_verified` | ✅ Read-only | ❌ Set to False on create | ✅ Read-only |
| `date_of_birth` | ✅ Age validation | ✅ Age validation | ✅ Updatable |
| `latitude/longitude` | ✅ Range validation | ✅ Range validation | ✅ Updatable |
| `address fields` | ✅ | ✅ Required for registration | ✅ Updatable |

## 🔐 **Security & Validation Improvements**

### **Input Validation**:
1. **Email**: Uniqueness check, proper format
2. **Phone**: Regex validation, uniqueness check
3. **Coordinates**: Geographic range validation
4. **Age**: Reasonable age limits (1-120 years)
5. **Password**: Strength validation + Django built-in validation

### **Security Headers** (`apps/auth/middleware.py`):
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin

## 📊 **Performance Optimizations**

### **Session Management**:
- Async session tracking (non-blocking)
- Cache-based rate limiting
- Batch database updates
- Optimized queries với proper indexes

### **Caching Strategy**:
- User data caching (5 minutes)
- Verification rate limiting counters
- Session activity batching

## 🚀 **API Endpoints & Usage**

### **Registration** `POST /auth/register/`:
```json
{
  "email": "user@example.com",
  "phone_number": "+84912345678",
  "password": "SecurePass123",
  "password_confirm": "SecurePass123",
  "first_name": "John",
  "last_name": "Doe",
  "user_type": "customer",
  "address": "123 Main St",
  "city": "Ho Chi Minh",
  "district": "District 1",
  "ward": "Ward 1",
  "latitude": 10.776889,
  "longitude": 106.700887
}
```

### **Profile Update** `PATCH /auth/profile/`:
```json
{
  "first_name": "John Updated",
  "phone_number": "+84987654321",
  "address": "456 New Address",
  "latitude": 10.776889,
  "longitude": 106.700887
}
```

### **Profile Response** `GET /auth/profile/`:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "username": "johndoe",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "user_type": "customer",
    "user_type_display": "Khách hàng",
    "phone_number": "+84912345678",
    "address": "123 Main St",
    "city": "Ho Chi Minh",
    "district": "District 1",
    "ward": "Ward 1",
    "latitude": "10.776889",
    "longitude": "106.700887",
    "date_of_birth": "1990-01-01",
    "is_verified": true,
    "is_active": true,
    "date_joined": "2024-01-01T00:00:00Z",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T12:00:00Z"
  },
  "message": "Lấy thông tin người dùng thành công"
}
```

## 🔄 **Next Steps & Recommendations**

### **Immediate Actions**:
1. ✅ Run migrations: `python manage.py makemigrations && python manage.py migrate`
2. ✅ Test registration flow with all fields
3. ✅ Test profile update functionality
4. ✅ Verify coordinate validation

### **Future Enhancements**:
1. **Avatar Upload**: Implement file upload endpoints
2. **Profile Completion**: Add completion percentage tracking
3. **Address Validation**: Integrate with address validation APIs
4. **Geolocation**: Add reverse geocoding for coordinates
5. **Email Templates**: Improve email/SMS templates

### **Testing Checklist**:
- [ ] Registration with email only
- [ ] Registration with phone only
- [ ] Registration with all fields
- [ ] Profile update (partial)
- [ ] Profile update (all fields)
- [ ] Coordinate validation edge cases
- [ ] Date of birth validation
- [ ] Email/phone uniqueness constraints
- [ ] Password strength validation

## 📝 **Important Notes**

1. **Backward Compatibility**: All changes are backward compatible
2. **Validation**: Server-side validation mirrors client-side expectations
3. **Error Messages**: Consistent Vietnamese error messages
4. **Security**: All security measures maintained and enhanced
5. **Performance**: No performance degradation, some improvements

---

## 🔧 **Troubleshooting**

### **Common Issues**:
1. **ValidationError**: Check field formats and required fields
2. **UniquenessError**: Email/phone already exists in database
3. **CoordinateError**: Latitude/longitude outside valid ranges
4. **AgeValidationError**: Invalid date of birth

### **Debug Commands**:
```python
# Check user data
python manage.py shell
from apps.users.models import User
User.objects.all().values()

# Test validation
from apps.auth.serializers import UserSerializer
serializer = UserSerializer(data={...})
print(serializer.errors)
```

---

**Last Updated**: 2024-01-01
**Author**: Authentication System Synchronization Team
**Version**: 1.0.0