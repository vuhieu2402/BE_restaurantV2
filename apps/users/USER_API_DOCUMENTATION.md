# User Management API Documentation

## 🔐 Authentication & Permissions

All endpoints require authentication (JWT token) and implement role-based access control:

- **Admin**: Full access to all endpoints
- **Manager**: Can manage staff and view customers of their restaurants
- **Staff**: Limited access, can view customers they're assigned to
- **Customer**: Can only view and update their own profile

## 📋 API Endpoints

### 1. User List
```
GET /api/users/
```

**Description**: Lấy danh sách người dùng với phân trang và lọc

**Permissions**: Admin, Manager

**Query Parameters**:
- `user_type` (string, optional): Filter by user type (`customer`, `staff`, `manager`, `admin`)
- `is_active` (boolean, optional): Filter by active status
- `is_verified` (boolean, optional): Filter by verification status
- `search` (string, optional): Search in username, email, name
- `restaurant_id` (integer, optional): Filter by restaurant (for staff)
- `ordering` (string, optional): Sort by field (`username`, `-username`, `created_at`, `-created_at`)
- `page` (integer, optional): Page number (default: 1)
- `page_size` (integer, optional): Items per page (10, 20, 50, 100, default: 20)

**Response**:
```json
{
    "success": true,
    "message": "Lấy danh sách người dùng thành công",
    "data": {
        "items": [...], // List of UserListSerializer objects
        "pagination": {
            "current_page": 1,
            "page_size": 20,
            "total_count": 150,
            "page_count": 8,
            "has_next": true,
            "has_previous": false
        }
    }
}
```

### 2. User Details
```
GET /api/users/{id}/
```

**Description**: Lấy thông tin chi tiết của một người dùng

**Permissions**: Based on role hierarchy

**Response**:
```json
{
    "success": true,
    "message": "Lấy thông tin người dùng thành công",
    "data": {
        "user": { ... }, // User object with profile
        "profile": { ... } // CustomerProfile or StaffProfile object
    }
}
```

### 3. Create User
```
POST /api/users/create/
```

**Description**: Tạo người dùng mới với profile tương ứng

**Permissions**: Admin, Manager (staff only for their restaurants)

**Request Body**:
```json
{
    "user": {
        "username": "john_doe",
        "email": "john@example.com",
        "phone_number": "+84912345678",
        "first_name": "John",
        "last_name": "Doe",
        "password": "SecurePass123!",
        "password_confirm": "SecurePass123!",
        "user_type": "customer", // or "staff" or "manager"
        "date_of_birth": "1990-01-01",
        "address": "123 Main St",
        "city": "Ho Chi Minh",
        "district": "District 1",
        "ward": "Ward 1",
        "postal_code": "700000"
    },
    "profile": { // Profile data based on user_type
        // For customer:
        "preferred_language": "vi",
        "receive_promotions": true,
        "receive_notifications": true,

        // For staff/manager:
        "employee_id": "EMP001",
        "position": "Waiter",
        "hire_date": "2023-01-01",
        "salary": "5000000",
        "restaurant_id": 1
    }
}
```

### 4. Update User
```
PATCH /api/users/{id}/update/
```

**Description**: Cập nhật thông tin người dùng (partial update)

**Permissions**: Based on role hierarchy

**Response**:
```json
{
    "success": true,
    "message": "Cập nhật thông tin người dùng thành công",
    "data": { ... } // Updated user object
}
```

### 5. Delete User
```
DELETE /api/users/{id}/delete/
```

**Description**: Xóa người dùng (soft delete - deactivates account)

**Permissions**: Based on role hierarchy

**Response**:
```json
{
    "success": true,
    "message": "Xóa người dùng thành công",
    "data": {
        "deleted_user_id": 123
    }
}
```

### 6. Toggle User Status
```
PATCH /api/users/{id}/toggle-status/?is_active=true
```

**Description**: Activate hoặc deactivate người dùng

**Permissions**: Admin, Manager

**Query Parameters**:
- `is_active` (boolean, required): New status (`true`=active, `false`=inactive)

### 7. Bulk Operations
```
POST /api/users/bulk-operation/
```

**Description**: Thực hiện thao tác trên nhiều user cùng lúc

**Permissions**: Admin, Manager

**Request Body**:
```json
{
    "user_ids": [1, 2, 3, 4],
    "operation": "activate", // "activate", "deactivate", "delete"
    "reason": "System maintenance" // optional
}
```

**Response**:
```json
{
    "success": true,
    "message": "Bulk activate: 3 thành công, 1 thất bại",
    "data": {
        "results": [...],
        "summary": {
            "total": 4,
            "success_count": 3,
            "failed_count": 1
        }
    }
}
```

### 8. Customer Profile
```
GET /api/users/profile/
```

**Description**: Lấy thông tin profile của customer hiện tại

**Permissions**: Customer (own profile only), Manager (customers of their restaurants)

**Response**:
```json
{
    "success": true,
    "message": "Lấy thông tin profile thành công",
    "data": {
        "loyalty_points": 150,
        "total_orders": 25,
        "total_spent": "2500000.00",
        "current_tier": "Silver",
        "current_discount": 0.10,
        "next_tier": "Gold",
        "points_to_next_tier": 350
    }
}
```

### 9. Update Customer Preferences
```
PATCH /api/users/profile/preferences/
```

**Description**: Cập nhật preferences của customer

**Permissions**: Customer (own profile only)

**Request Body**:
```json
{
    "preferred_language": "vi",
    "receive_promotions": true,
    "receive_notifications": false
}
```

### 10. User Statistics
```
GET /api/users/statistics/
```

**Description**: Lấy thống kê về người dùng

**Permissions**: Admin only

**Response**:
```json
{
    "success": true,
    "message": "Lấy thống kê người dùng thành công",
    "data": {
        "total_users": 1250,
        "active_users": 1200,
        "verified_users": 1150,
        "by_user_type": {
            "customer": 1000,
            "staff": 150,
            "manager": 80,
            "admin": 20
        },
        "created_this_month": 45,
        "created_this_week": 12
    }
}
```

### 11. Customer Analytics
```
GET /api/users/analytics/customers/
```

**Description**: Lấy thống kê chi tiết về customers

**Permissions**: Admin, Manager

**Response**:
```json
{
    "success": true,
    "message": "Lấy analytics khách hàng thành công",
    "data": {
        "total_customers": 1000,
        "active_customers": 950,
        "loyalty_stats": {
            "total_points": 150000,
            "average_points": 150,
            "customers_with_points": 800
        },
        "orders_stats": {
            "total_orders": 25000,
            "average_orders": 25,
            "customers_with_orders": 900
        },
        "spending_stats": {
            "total_spent": "2500000000",
            "average_spent": "2500000",
            "customers_with_spending": 850
        },
        "new_customers_this_month": 45
    }
}
```

### 12. Staff Analytics
```
GET /api/users/analytics/staff/
```

**Description**: Lấy thống kê chi tiết về staff

**Permissions**: Admin, Manager

**Response**:
```json
{
    "success": true,
    "message": "Lấy analytics nhân viên thành công",
    "data": {
        "total_staff": 230,
        "active_staff": 220,
        "by_user_type": {
            "staff": 200,
            "manager": 30
        },
        "salary_stats": {
            "total_salary_budget": "4500000000",
            "average_salary": "19565217"
        },
        "by_restaurant": {
            "Restaurant A": 50,
            "Restaurant B": 35,
            "Restaurant C": 45
        },
        "staff_by_position": {
            "Waiter": 80,
            "Chef": 40,
            "Manager": 30,
            "Cashier": 50
        },
        "new_staff_this_month": 8
    }
}
```

## 🔐 Role-Based Access Control

### Permission Matrix

| Endpoint | Customer | Staff | Manager | Admin |
|----------|----------|-------|---------|-------|
| User List | ❌ | ❌ | ✅ | ✅ |
| User Details | ✅ (own) | ✅ (assigned) | ✅ | ✅ |
| Create User | ❌ | ❌ | ✅ (staff) | ✅ |
| Update User | ❌ | ❌ | ✅ (assigned) | ✅ |
| Delete User | ❌ | ❌ | ✅ (assigned) | ✅ |
| Toggle Status | ❌ | ❌ | ✅ (assigned) | ✅ |
| Bulk Operations | ❌ | ❌ | ✅ (assigned) | ✅ |
| Customer Profile | ✅ (own) | ✅ (customers) | ✅ | ✅ |
| Update Preferences | ✅ (own) | ❌ | ❌ | ✅ |
| Statistics | ❌ | ❌ | ❌ | ✅ |
| Customer Analytics | ❌ | ❌ | ✅ | ✅ |
| Staff Analytics | ❌ | ❌ | ✅ | ✅ |

### Business Rules

1. **Manager Limitations**:
   - Chỉ có thể tạo/manage staff cho nhà hàng mình quản lý
   - Có thể xem customers của tất cả nhà hàng
   - Không thể tạo tài khoản admin/manager khác

2. **Staff Limitations**:
   - Chỉ có thể xem thông tin customers được phân công
   - Không thể quản lý users khác
   - Có thể cập nhật thông tin cá nhân của mình

3. **Customer Limitations**:
   - Chỉ có thể xem và cập nhật thông tin của mình
   - Có thể xem thông tin orders và lịch sử dụng

## 📊 Response Format

All responses follow standard format:

```json
{
    "success": boolean,
    "message": "string",
    "data": object|null,
    "errors": object|null // Only for validation errors
}
```

### Error Codes

- `PERMISSION_DENIED`: Không có quyền truy cập
- `USER_NOT_FOUND`: Người dùng không tồn tại
- `VALIDATION_ERROR`: Lỗi validation dữ liệu
- `EMAIL_EXISTS`: Email đã được sử dụng
- `PHONE_EXISTS`: Số điện thoại đã được sử dụng
- `SELF_DELETE`: Không thể xóa tài khoản của mình
- `SELF_MODIFY`: Không thể sửa tài khoản của mình
- `DATABASE_ERROR`: Lỗi database
- `UNKNOWN_ERROR`: Lỗi không xác định

## 🔍 Usage Examples

### Create Customer
```bash
curl -X POST http://localhost:8000/api/users/create/ \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "user": {
      "username": "new_customer",
      "email": "customer@example.com",
      "password": "SecurePass123!",
      "password_confirm": "SecurePass123!",
      "user_type": "customer",
      "first_name": "John",
      "last_name": "Doe"
    },
    "profile": {
      "preferred_language": "vi",
      "receive_promotions": true
    }
  }'
```

### Create Staff (Manager only)
```bash
curl -X POST http://localhost:8000/api/users/create/ \
  -H "Authorization: Bearer manager-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "user": {
      "username": "new_staff",
      "email": "staff@example.com",
      "password": "SecurePass123!",
      "password_confirm": "SecurePass123!",
      "user_type": "staff",
      "first_name": "Jane",
      "last_name": "Smith"
    },
    "profile": {
      "employee_id": "STAFF001",
      "position": "Waiter",
      "salary": "5000000",
      "restaurant_id": 1
    }
  }'
```

### Bulk Activate Users
```bash
curl -X POST http://localhost:8000/api/users/bulk-operation/ \
  -H "Authorization: Bearer admin-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "user_ids": [1, 2, 3],
    "operation": "activate",
    "reason": "Reactivation after maintenance"
  }'
```

## 🚀 Rate Limiting

- **User Creation**: 5 requests per minute
- **Bulk Operations**: 3 requests per minute
- **Profile Updates**: 20 requests per minute
- **Analytics Requests**: 30 requests per minute

## 📝 Notes

1. **Soft Delete**: Users are deactivated rather than permanently deleted
2. **Caching**: Most operations use Redis caching for performance
3. **Audit Trail**: All important operations are logged
4. **File Upload**: Avatar images are automatically uploaded to MinIO
5. **Data Validation**: All input is validated according to model constraints

## 🧪 Testing

### Postman Collection
Import the provided Postman collection for easy API testing.

### Unit Tests
```python
# Test user creation
def test_create_customer():
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')

    data = {
        "user": {
            "username": "testuser",
            "email": "test@example.com",
            "password": "TestPass123!",
            "password_confirm": "TestPass123!",
            "user_type": "customer"
        }
    }

    response = client.post('/api/users/create/', data, format='json')

    assert response.status_code == 201
    assert User.objects.filter(username="testuser").exists()
```

## 🔄 Version History

- **v1.0.0**: Initial user management API
- **v1.1.0**: Added bulk operations and analytics
- **v1.2.0**: Enhanced permission system and caching
- **v1.3.0**: Added comprehensive validation and error handling