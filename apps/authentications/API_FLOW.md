# 🔐 Luồng Đăng Ký và Đăng Nhập - API Flow

## 📋 Tổng quan

Hệ thống authentication sử dụng **JWT tokens** với **email/SMS verification** và **stateful session management**.

---

## 🆕 LUỒNG ĐĂNG KÝ (Registration Flow)

### Bước 1: Đăng ký tài khoản mới

**API:** `POST /api/auth/register/`

**Request Body:**
```json
{
  "email": "user@example.com",           // Hoặc phone_number
  "phone_number": "+84123456789",        // Hoặc email
  "password": "TestPass123!",
  "password_confirm": "TestPass123!",
  "first_name": "John",
  "last_name": "Doe",
  "user_type": "customer",              // Optional, default: "customer"
  "date_of_birth": "1990-01-01",        // Optional
  "address": "123 Main St",             // Optional
  "city": "Ho Chi Minh",                // Optional
  "district": "District 1",             // Optional
  "ward": "Ward 1",                     // Optional
  "postal_code": "70000",               // Optional
  "latitude": 10.762622,                // Optional
  "longitude": 106.660172               // Optional
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": "Đăng ký thành công. Vui lòng kiểm tra email/SMS để xác thực tài khoản.",
  "data": {
    "user": {
      "id": 1,
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      ...
    },
    "verification_sent": true,
    "verification_target": "user@example.com"
  }
}
```

**Lưu ý:**
- ✅ Username được tự động generate từ email/phone (không cần gửi)
- ✅ User được tạo với `is_verified=False`
- ✅ Verification code tự động được gửi qua email/SMS
- ✅ Mã có hiệu lực trong 10 phút

---

### Bước 2: Xác thực mã OTP

**API:** `POST /api/auth/verify/`

**Request Body:**
```json
{
  "email": "user@example.com",          // Hoặc phone_number
  "phone_number": "+84123456789",       // Hoặc email
  "code": "123456",                     // Mã 6 số nhận được
  "verification_type": "email"          // "email" | "phone" | "password_reset"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Xác thực thành công",
  "data": null
}
```

**Sau khi verify thành công:**
- ✅ `user.is_verified = True`
- ✅ User có thể đăng nhập

**Rate Limiting:**
- ⚠️ Tối đa 3 mã trong 10 phút
- ⚠️ Tối đa 10 mã trong 1 giờ
- ⚠️ Tối đa 20 mã trong 1 ngày

---

## 🔑 LUỒNG ĐĂNG NHẬP (Login Flow)

### Bước 1: Đăng nhập

**API:** `POST /api/auth/login/`

**Request Body:**
```json
{
  "identifier": "user@example.com",     // Email hoặc số điện thoại
  "password": "TestPass123!",
  "device_info": {                     // Optional
    "name": "Chrome Desktop",
    "browser": "Chrome",
    "os": "Windows"
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Đăng nhập thành công",
  "data": {
    "user": {
      "id": 1,
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "is_verified": true,
      ...
    },
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "access_token_expires": 1701234567,
    "refresh_token_expires": 1701839367,
    "sessions": [
      {
        "id": "uuid-here",
        "device_name": "Chrome Desktop",
        "ip_address": "127.0.0.1",
        "created_at": "2025-11-30T10:00:00Z",
        "last_used_at": "2025-11-30T10:00:00Z",
        "expires_at": "2025-12-07T10:00:00Z",
        "is_current": true,
        "is_expired": false
      }
    ]
  }
}
```

**Token Lifetime:**
- ⏱️ Access Token: 15 phút
- ⏱️ Refresh Token: 7 ngày

**Validation Rules:**
- ✅ User phải tồn tại
- ✅ User phải active (`is_active=True`)
- ✅ User phải verified (`is_verified=True`)
- ✅ Password phải đúng

---

### Bước 2: Sử dụng Access Token

**API:** `GET /api/auth/profile/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Lấy thông tin người dùng thành công",
  "data": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "phone_number": "+84123456789",
    "user_type": "customer",
    "user_type_display": "Khách hàng",
    "is_verified": true,
    "is_active": true,
    ...
  }
}
```

---

### Bước 3: Refresh Access Token (khi hết hạn)

**API:** `POST /api/auth/token/refresh/`

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "device_info": {                     // Optional
    "name": "Chrome Desktop"
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Refresh token thành công",
  "data": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",  // New token (rotation)
    "access_token_expires": 1701234567,
    "refresh_token_expires": 1701839367
  }
}
```

**Lưu ý:**
- 🔄 Refresh token được rotate (tạo mới) mỗi lần refresh
- 🔄 Token cũ bị revoke tự động

---

## 🔄 LUỒNG ĐĂNG XUẤT (Logout Flow)

### Logout từ thiết bị hiện tại

**API:** `POST /api/auth/token/revoke/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Đăng xuất thành công",
  "data": null
}
```

---

### Logout từ tất cả thiết bị

**API:** `POST /api/auth/logout/all/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Đã đăng xuất khỏi 3 thiết bị khác",
  "data": {
    "revoked_sessions": 3
  }
}
```

---

## 📱 LUỒNG QUÊN MẬT KHẨU (Password Reset Flow)

### Bước 1: Yêu cầu reset password

**API:** `POST /api/auth/password/reset/`

**Request Body:**
```json
{
  "email": "user@example.com"          // Hoặc phone_number
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Mã đặt lại mật khẩu đã được gửi",
  "data": null
}
```

---

### Bước 2: Xác thực mã và đặt lại mật khẩu

**API:** `POST /api/auth/password/reset/confirm/`

**Request Body:**
```json
{
  "email": "user@example.com",
  "code": "123456",
  "new_password": "NewPass123!",
  "new_password_confirm": "NewPass123!"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Đặt lại mật khẩu thành công. Vui lòng đăng nhập lại.",
  "data": null
}
```

**Lưu ý:**
- ✅ Tất cả sessions của user bị revoke
- ✅ User phải đăng nhập lại

---

## 🔐 LUỒNG ĐỔI MẬT KHẨU (Change Password Flow)

**API:** `POST /api/auth/password/change/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "old_password": "OldPass123!",
  "new_password": "NewPass123!",
  "new_password_confirm": "NewPass123!"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Đổi mật khẩu thành công. Vui lòng đăng nhập lại.",
  "data": null
}
```

**Lưu ý:**
- ✅ Tất cả sessions bị revoke (trừ session hiện tại)
- ✅ User phải đăng nhập lại

---

## 📊 LUỒNG XEM SESSIONS

**API:** `GET /api/auth/sessions/`

**Headers:**
```
Authorization: Bearer {access_token}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Lấy danh sách session thành công",
  "data": [
    {
      "id": "uuid-1",
      "device_name": "Chrome Desktop",
      "ip_address": "127.0.0.1",
      "created_at": "2025-11-30T10:00:00Z",
      "last_used_at": "2025-11-30T10:05:00Z",
      "expires_at": "2025-12-07T10:00:00Z",
      "is_current": true,
      "is_expired": false
    },
    {
      "id": "uuid-2",
      "device_name": "Firefox Mobile",
      "ip_address": "192.168.1.1",
      "created_at": "2025-11-29T08:00:00Z",
      "last_used_at": "2025-11-29T08:30:00Z",
      "expires_at": "2025-12-06T08:00:00Z",
      "is_current": false,
      "is_expired": false
    }
  ]
}
```

---

## 🔄 LUỒNG GỬI LẠI MÃ XÁC THỰC

### Gửi lại mã email

**API:** `POST /api/auth/verify/email/send/`

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Mã xác thực đã được gửi đến email của bạn",
  "data": null
}
```

---

### Gửi lại mã SMS

**API:** `POST /api/auth/verify/phone/send/`

**Request Body:**
```json
{
  "phone_number": "+84123456789"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Mã xác thực đã được gửi đến số điện thoại của bạn",
  "data": null
}
```

---

## 📝 TÓM TẮT LUỒNG HOÀN CHỈNH

### 🆕 Đăng ký mới:
```
1. POST /api/auth/register/
   ↓
2. Nhận mã OTP qua email/SMS
   ↓
3. POST /api/auth/verify/
   ↓
4. Tài khoản được kích hoạt (is_verified=True)
   ↓
5. POST /api/auth/login/
   ↓
6. Nhận access_token và refresh_token
   ↓
7. Sử dụng access_token để gọi các API protected
```

### 🔑 Đăng nhập lại:
```
1. POST /api/auth/login/
   ↓
2. Nhận access_token và refresh_token
   ↓
3. Sử dụng access_token (15 phút)
   ↓
4. Khi hết hạn: POST /api/auth/token/refresh/
   ↓
5. Nhận access_token mới
```

### 🔐 Quên mật khẩu:
```
1. POST /api/auth/password/reset/
   ↓
2. Nhận mã OTP qua email/SMS
   ↓
3. POST /api/auth/password/reset/confirm/
   ↓
4. Mật khẩu được đặt lại
   ↓
5. POST /api/auth/login/ (với mật khẩu mới)
```

---

## ⚠️ LƯU Ý QUAN TRỌNG

1. **Username**: Không cần gửi trong API, tự động generate từ email/phone
2. **Verification**: Bắt buộc phải verify trước khi login
3. **Token Rotation**: Refresh token được rotate mỗi lần refresh
4. **Session Management**: Mỗi login tạo một session mới
5. **Rate Limiting**: Có giới hạn số lần gửi mã xác thực
6. **Password Strength**: Tối thiểu 8 ký tự, có chữ hoa, chữ thường, số

---

## 🧪 VÍ DỤ TEST VỚI CURL

### 1. Đăng ký:
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!",
    "password_confirm": "TestPass123!",
    "first_name": "Test",
    "last_name": "User"
  }'
```

### 2. Xác thực mã:
```bash
curl -X POST http://localhost:8000/api/auth/verify/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "code": "123456",
    "verification_type": "email"
  }'
```

### 3. Đăng nhập:
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "test@example.com",
    "password": "TestPass123!"
  }'
```

### 4. Lấy profile:
```bash
curl -X GET http://localhost:8000/api/auth/profile/ \
  -H "Authorization: Bearer {access_token}"
```

### 5. Refresh token:
```bash
curl -X POST http://localhost:8000/api/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "{refresh_token}"
  }'
```

---

## 📚 TÀI LIỆU THAM KHẢO

- Base URL: `http://localhost:8000/api/auth/`
- Token Type: `Bearer`
- Content-Type: `application/json`
- Response Format: Standard `ApiResponse` format

