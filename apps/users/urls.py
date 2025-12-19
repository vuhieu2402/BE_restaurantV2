"""
User Management URLs
- Định tuyến API endpoints cho user management
- Tương thích với REST conventions
- Tránh naming conflicts
"""
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # User CRUD Operations
    path('', views.UserListView.as_view(), name='user_list'),
    path('<int:user_id>/', views.UserDetailView.as_view(), name='user_detail'),
    path('create/', views.UserCreateView.as_view(), name='user_create'),
    path('<int:user_id>/update/', views.UserUpdateView.as_view(), name='user_update'),
    path('<int:user_id>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('<int:user_id>/toggle-status/', views.UserToggleStatusView.as_view(), name='user_toggle_status'),

    # Bulk Operations
    path('bulk-operation/', views.BulkUserOperationView.as_view(), name='user_bulk_operation'),

    # Profile Management
    path('profile/', views.CustomerProfileView.as_view(), name='customer_profile'),
    path('profile/preferences/', views.CustomerProfileView.as_view(), name='customer_preferences_update'),

    # Analytics & Statistics
    path('statistics/', views.UserStatsView.as_view(), name='user_statistics'),
    path('analytics/customers/', views.CustomerAnalyticsView.as_view(), name='customer_analytics'),
    path('analytics/staff/', views.StaffAnalyticsView.as_view(), name='staff_analytics'),
]