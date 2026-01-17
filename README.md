# 🍽️ Restaurant Management System

Hệ thống quản lý nhà hàng toàn diện với Django REST Framework, hỗ trợ WebSocket real-time, Celery background tasks, và AWS deployment.
Được xây dựng cho 3 role: 
-customer https://v0-restaurant-management-interface.vercel.app/
-manager https://v0-restaurant-management-interface.vercel.app/manage 
-staff https://v0-restaurant-management-interface.vercel.app/staff 

## 📋 Mục lục

- [Tổng quan](#tổng-quan)
- [Tính năng](#tính-năng)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Tech Stack](#tech-stack)
- [Cài đặt Local](#cài-đặt-local)
- [Cấu hình Production](#cấu-hình-production)
- [API Documentation](#api-documentation)
- [WebSocket](#websocket)
- [Deployment AWS](#deployment-aws)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Tổng quan

Hệ thống quản lý nhà hàng cho phép:
- **Khách hàng:** Đặt món, thanh toán, theo dõi đơn hàng
- **Nhân viên:** Quản lý đơn hàng, menu, bàn ăn
- **Quản lý:** Dashboard analytics, quản lý danh mục món ăn, chi tiết các món
- **Real-time:** WebSocket cho notifications và chat
- **Background Tasks:** Email, báo cáo tự động

---

## ✨ Tính năng

### 🔐 Authentication & Authorization
- JWT token authentication
- Email verification
- Role-based permissions (Customer, Staff, Manager, Admin)
- OAuth social login

### 🍕 Menu Management
- Categories & dishes management
- Price variations
- Availability status
- Image uploads (S3)

### 🛒 Order Management
- Create, update, cancel orders
- Real-time order status
- Order history
- Rating & reviews

### 🪑 Table Management
- Table booking
- Table status tracking
- Seat capacity management

### 💳 Payment Processing
- Multiple payment methods
- Payment history
- Invoice generation

### 🔔 Notifications
- Real-time WebSocket notifications
- Email notifications (Celery)
- Push notifications

### 📊 Analytics & Reports
- Sales reports
- Revenue analytics
- Popular dishes tracking
- Customer insights

### 💬 Real-time Chat
- WebSocket-based chat
- Customer support
- Order discussions

---

## 🏗️ Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────┐
│                      CLIENTS                            │
│  Web App     │  Admin Dashboard    │
└───────────────────┬─────────────────────────────────────┘
                    │
         ┌──────────┴──────────┐
         │    Load Balancer    │ 
         │    Nginx (Port 80)  │
         └──────────┬──────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
    ┌────▼────┐          ┌─────▼─────┐
    │Gunicorn │          │  Daphne   │
    │ :8000   │          │  :8001    │
    │ (HTTP)  │          │(WebSocket)│
    └────┬────┘          └─────┬─────┘
         │                     │
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │  Django Application │
         │  - REST API         │
         │  - WebSocket        │
         │  - Business Logic   │
         └──┬────────┬────────┬┘
            │        │        │
    ┌───────▼──┐  ┌──▼───┐  ┌▼───────┐
    │PostgreSQL│  │Redis │  │  S3    │
    │   (RDS)  │  │Cache │  │CloudFr.│
    └──────────┘  └──┬───┘  └────────┘
                     │
              ┌──────▼──────┐
              │   Celery    │
              │  Worker +   │
              │    Beat     │
              └─────────────┘
```

### Giải thích:

1. **Nginx:** Reverse proxy, load balancer, static file serving
2. **Gunicorn:** WSGI server cho HTTP/REST API (3 workers)
3. **Daphne:** ASGI server cho WebSocket connections
4. **Django:** Core application logic
5. **PostgreSQL (RDS):** Primary database
6. **Redis:** Cache, session storage, Celery broker, Channels layer
7. **Celery:** Async tasks (email, reports)
8. **S3 + CloudFront:** Static & media file storage + CDN
9. **Supervisor:** Process management & monitoring

---

## 🛠️ Tech Stack

### Backend
- **Framework:** Django 5.0 + Django REST Framework 3.14
- **ASGI/WSGI:** Daphne + Gunicorn
- **Real-time:** Django Channels 4.0 + WebSocket
- **Task Queue:** Celery 5.3 + Celery Beat
- **Authentication:** JWT (djangorestframework-simplejwt)
- **API Docs:** drf-spectacular (OpenAPI/Swagger)

### Database & Cache
- **Database:** PostgreSQL 16 (AWS RDS)
- **Cache:** Redis 7.x (Local + AWS ElastiCache)
- **ORM:** Django ORM

### Storage & CDN
- **Media Storage:** AWS S3
- **CDN:** AWS CloudFront
- **Static Files:** S3 + WhiteNoise (fallback)

### Infrastructure (AWS)
- **Compute:** EC2 (Ubuntu 22.04)
- **Database:** RDS PostgreSQL
- **Cache:** ElastiCache (Valkey)
- **Storage:** S3
- **CDN:** CloudFront
- **Network:** VPC, Security Groups, Elastic IP

### DevOps
- **Web Server:** Nginx
- **Process Manager:** Supervisor
- **CI/CD:** GitHub Actions (planned)
- **Monitoring:** CloudWatch (planned)

