"""
User Management Services - Business Logic Layer
- Xử lý business logic cho user management
- Validation business rules
- Điều phối các operation
- Transaction management
- Gọi Selector layer để lấy data
- KHÔNG query database trực tiếp
"""
from django.conf import settings
from django.db import transaction
from django.core.files.base import ContentFile
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .selectors import UserSelector, CustomerProfileSelector, StaffProfileSelector
from .models import CustomerProfile, StaffProfile
from apps.authentications.selectors import RefreshTokenSessionSelector
from apps.restaurants.selectors import RestaurantSelector
from apps.restaurants.models import Restaurant
from apps.api.response import ApiResponse

import logging
from datetime import timedelta
from decouple import config

User = get_user_model()
logger = logging.getLogger(__name__)


class UserService:
    """Service cho user CRUD operations"""

    def __init__(self):
        self.user_selector = UserSelector()
        self.customer_selector = CustomerProfileSelector()
        self.staff_selector = StaffProfileSelector()
        self.session_selector = RefreshTokenSessionSelector()
        self.restaurant_selector = RestaurantSelector()

    def get_user_list(self, user, filters=None, ordering=None, page=1, page_size=20):
        """Lấy danh sách users với phân trang và filtering"""
        try:
            # Business rule: Chỉ admin/manager có thể xem danh sách users
            if not user.is_superuser and user.user_type not in ['manager', 'admin']:
                return {
                    'success': False,
                    'message': 'Bạn không có quyền xem danh sách người dùng',
                    'error_code': 'PERMISSION_DENIED'
                }

            # Lọc theo user_type và restaurant nếu là manager
            if user.user_type == 'manager':
                restaurant_id = filters.get('restaurant_id') if filters else None
                if restaurant_id:
                    # Business rule: Manager chỉ có thể xem users của nhà hàng mình
                    if not self.restaurant_selector.user_can_access_restaurant(user, restaurant_id):
                        return {
                            'success': False,
                            'message': 'Bạn không có quyền xem người dùng của nhà hàng này',
                            'error_code': 'PERMISSION_DENIED'
                        }
                    filters['restaurant_id'] = restaurant_id
                else:
                    # Lấy tất cả users của nhà hàng manager đang quản lý
                    managed_restaurants = self.restaurant_selector.get_restaurants_by_manager(user)
                    if managed_restaurants:
                        filters['restaurant_id__in'] = [r.id for r in managed_restaurants]
                    else:
                        filters['restaurant_id__in'] = [0]  # Empty result

            # Superuser có thể xem tất cả
            result = self.user_selector.get_users_paginated(
                filters=filters,
                ordering=ordering,
                page=page,
                page_size=page_size
            )

            return {
                'success': True,
                'message': 'Lấy danh sách người dùng thành công',
                'data': result
            }

        except Exception as e:
            logger.error(f"Get user list error: {str(e)}")
            return {
                'success': False,
                'message': f'Lấy danh sách người dùng thất bại: {str(e)}',
                'error_code': 'DATABASE_ERROR'
            }

    def get_user_detail(self, user, user_id):
        """Lấy chi tiết user với permission check"""
        try:
            target_user = self.user_selector.get_user_by_id(user_id)
            if not target_user:
                return {
                    'success': False,
                    'message': 'Người dùng không tồn tại',
                    'error_code': 'USER_NOT_FOUND'
                }

            # Permission check
            permission_result = self._check_user_access_permission(user, target_user)
            if not permission_result['allowed']:
                return {
                    'success': False,
                    'message': permission_result['message'],
                    'error_code': 'PERMISSION_DENIED'
                }

            # Lấy thông tin profile theo user_type
            profile_data = None
            if target_user.user_type == 'customer':
                profile = self.customer_selector.get_profile_by_user(target_user)
                if profile:
                    profile_data = {
                        'preferred_language': profile.preferred_language,
                        'loyalty_points': profile.loyalty_points,
                        'total_orders': profile.total_orders,
                        'total_spent': str(profile.total_spent),
                        'receive_promotions': profile.receive_promotions,
                        'receive_notifications': profile.receive_notifications,
                        'created_at': profile.created_at,
                        'updated_at': profile.updated_at,
                    }
            elif target_user.user_type in ['staff', 'manager']:
                profile = self.staff_selector.get_profile_by_user(target_user)
                if profile:
                    profile_data = {
                        'employee_id': profile.employee_id,
                        'position': profile.position,
                        'hire_date': profile.hire_date,
                        'salary': str(profile.salary) if profile.salary else None,
                        'restaurant': profile.restaurant_id,
                        'is_active': profile.is_active,
                        'created_at': profile.created_at,
                        'updated_at': profile.updated_at,
                    }

            return {
                'success': True,
                'message': 'Lấy thông tin người dùng thành công',
                'data': {
                    'user': target_user,
                    'profile': profile_data
                }
            }

        except Exception as e:
            logger.error(f"Get user detail error: {str(e)}")
            return {
                'success': False,
                'message': f'Lấy thông tin người dùng thất bại: {str(e)}',
                'error_code': 'DATABASE_ERROR'
            }

    def create_user(self, admin_user, user_data):
        """Tạo user mới với business logic và validation"""
        try:
            with transaction.atomic():
                # Business rule: Chỉ admin/manager có thể tạo user
                if not admin_user.is_superuser and admin_user.user_type not in ['manager', 'admin']:
                    return {
                        'success': False,
                        'message': 'Bạn không có quyền tạo người dùng',
                        'error_code': 'PERMISSION_DENIED'
                    }

                user_type = user_data.get('user_type')

                # Business rule: Manager chỉ có thể tạo staff cho nhà hàng mình
                if admin_user.user_type == 'manager':
                    if user_type not in ['staff']:
                        return {
                            'success': False,
                            'message': 'Manager chỉ có thể tạo tài khoản nhân viên',
                            'error_code': 'PERMISSION_DENIED'
                        }

                    restaurant_id = user_data.get('restaurant_id')
                    if not restaurant_id:
                        return {
                            'success': False,
                            'message': 'Vui lòng chọn nhà hàng cho nhân viên',
                            'error_code': 'VALIDATION_ERROR'
                        }

                    if not self.restaurant_selector.user_can_access_restaurant(admin_user, restaurant_id):
                        return {
                            'success': False,
                            'message': 'Bạn không có quyền tạo nhân viên cho nhà hàng này',
                            'error_code': 'PERMISSION_DENIED'
                        }

                # Business rule: Email/phone uniqueness check
                email = user_data.get('email')
                phone_number = user_data.get('phone_number')

                if email and self.user_selector.check_email_exists(email):
                    return {
                        'success': False,
                        'message': 'Email đã được sử dụng',
                        'error_code': 'EMAIL_EXISTS'
                    }

                if phone_number and self.user_selector.check_phone_exists(phone_number):
                    return {
                        'success': False,
                        'message': 'Số điện thoại đã được sử dụng',
                        'error_code': 'PHONE_EXISTS'
                    }

                # Remove profile data từ user_data
                profile_data = self._extract_profile_data(user_data, user_type)
                user_data = {k: v for k, v in user_data.items()
                            if k not in ['preferred_language', 'loyalty_points',
                                         'employee_id', 'position', 'hire_date', 'salary', 'restaurant_id']}

                # Tạo user
                new_user = User.objects.create_user(**user_data)

                # Tạo profile tương ứng
                if user_type == 'customer':
                    CustomerProfile.objects.create(
                        user=new_user,
                        **profile_data
                    )
                elif user_type in ['staff', 'manager']:
                    StaffProfile.objects.create(
                        user=new_user,
                        **profile_data
                    )

                return {
                    'success': True,
                    'message': f'Tạo người dùng {user_type} thành công',
                    'data': {'user': new_user}
                }

        except ValidationError as e:
            logger.error(f"Create user validation error: {str(e)}")
            return {
                'success': False,
                'message': str(e),
                'error_code': 'VALIDATION_ERROR'
            }
        except Exception as e:
            logger.error(f"Create user error: {str(e)}")
            return {
                'success': False,
                'message': f'Tạo người dùng thất bại: {str(e)}',
                'error_code': 'DATABASE_ERROR'
            }

    def update_user(self, admin_user, user_id, user_data):
        """Cập nhật user với business logic và permission check"""
        try:
            with transaction.atomic():
                target_user = self.user_selector.get_user_by_id(user_id)
                if not target_user:
                    return {
                        'success': False,
                        'message': 'Người dùng không tồn tại',
                        'error_code': 'USER_NOT_FOUND'
                    }

                # Permission check
                permission_result = self._check_user_modify_permission(admin_user, target_user)
                if not permission_result['allowed']:
                    return {
                        'success': False,
                        'message': permission_result['message'],
                        'error_code': 'PERMISSION_DENIED'
                    }

                # Extract profile data
                profile_data = self._extract_profile_data(user_data, target_user.user_type)
                user_update_data = {k: v for k, v in user_data.items()
                                  if k not in ['preferred_language', 'loyalty_points',
                                               'employee_id', 'position', 'hire_date', 'salary', 'restaurant_id']}

                # Cập nhật user
                for field, value in user_update_data.items():
                    setattr(target_user, field, value)
                target_user.save()

                # Cập nhật profile
                if target_user.user_type == 'customer':
                    profile = self.customer_selector.get_profile_by_user(target_user)
                    if profile:
                        for field, value in profile_data.items():
                            setattr(profile, field, value)
                        profile.save()
                elif target_user.user_type in ['staff', 'manager']:
                    profile = self.staff_selector.get_profile_by_user(target_user)
                    if profile:
                        for field, value in profile_data.items():
                            setattr(profile, field, value)
                        profile.save()

                return {
                    'success': True,
                    'message': 'Cập nhật thông tin người dùng thành công',
                    'data': {'user': target_user}
                }

        except ValidationError as e:
            logger.error(f"Update user validation error: {str(e)}")
            return {
                'success': False,
                'message': str(e),
                'error_code': 'VALIDATION_ERROR'
            }
        except Exception as e:
            logger.error(f"Update user error: {str(e)}")
            return {
                'success': False,
                'message': f'Cập nhật người dùng thất bại: {str(e)}',
                'error_code': 'DATABASE_ERROR'
            }

    def delete_user(self, admin_user, user_id):
        """Xóa user với business logic và permission check"""
        try:
            with transaction.atomic():
                target_user = self.user_selector.get_user_by_id(user_id)
                if not target_user:
                    return {
                        'success': False,
                        'message': 'Người dùng không tồn tại',
                        'error_code': 'USER_NOT_FOUND'
                    }

                # Permission check
                permission_result = self._check_user_modify_permission(admin_user, target_user)
                if not permission_result['allowed']:
                    return {
                        'success': False,
                        'message': permission_result['message'],
                        'error_code': 'PERMISSION_DENIED'
                    }

                # Business rule: Không thể xóa chính mình
                if admin_user.id == target_user.id:
                    return {
                        'success': False,
                        'message': 'Không thể xóa tài khoản của chính mình',
                        'error_code': 'SELF_DELETE'
                    }

                # Revoke tất cả sessions của user bị xóa
                self.session_selector.revoke_user_sessions(target_user)

                # Soft delete bằng cách deactivate và xóa các thông tin nhạy cảm
                target_user.is_active = False
                target_user.email = f"deleted_{target_user.id}@deleted.com"
                target_user.phone_number = None
                target_user.save()

                return {
                    'success': True,
                    'message': 'Xóa người dùng thành công',
                    'data': {'deleted_user_id': target_user.id}
                }

        except Exception as e:
            logger.error(f"Delete user error: {str(e)}")
            return {
                'success': False,
                'message': f'Xóa người dùng thất bại: {str(e)}',
                'error_code': 'DATABASE_ERROR'
            }

    def toggle_user_status(self, admin_user, user_id, is_active):
        """Activate/Deactivate user với permission check"""
        try:
            with transaction.atomic():
                target_user = self.user_selector.get_user_by_id(user_id)
                if not target_user:
                    return {
                        'success': False,
                        'message': 'Người dùng không tồn tại',
                        'error_code': 'USER_NOT_FOUND'
                    }

                # Permission check
                permission_result = self._check_user_modify_permission(admin_user, target_user)
                if not permission_result['allowed']:
                    return {
                        'success': False,
                        'message': permission_result['message'],
                        'error_code': 'PERMISSION_DENIED'
                    }

                # Business rule: Không thể deactivate chính mình
                if admin_user.id == target_user.id:
                    return {
                        'success': False,
                        'message': 'Không thể thay đổi trạng thái tài khoản của chính mình',
                        'error_code': 'SELF_MODIFY'
                    }

                # Cập nhật trạng thái
                target_user.is_active = is_active
                target_user.save()

                # Revoke sessions nếu deactivate
                if not is_active:
                    self.session_selector.revoke_user_sessions(target_user)

                action = 'kích hoạt' if is_active else 'vô hiệu hóa'
                return {
                    'success': True,
                    'message': f'{action} người dùng thành công',
                    'data': {'user_id': target_user.id, 'is_active': is_active}
                }

        except Exception as e:
            logger.error(f"Toggle user status error: {str(e)}")
            return {
                'success': False,
                'message': f'Không thể thay đổi trạng thái người dùng: {str(e)}',
                'error_code': 'DATABASE_ERROR'
            }

    def bulk_operations(self, admin_user, user_ids, operation, operation_data=None):
        """Thực hiện bulk operations với business logic"""
        try:
            with transaction.atomic():
                # Permission check
                if not admin_user.is_superuser and admin_user.user_type not in ['manager', 'admin']:
                    return {
                        'success': False,
                        'message': 'Bạn không có quyền thực hiện thao tác này',
                        'error_code': 'PERMISSION_DENIED'
                    }

                # Validate operation
                if operation not in ['activate', 'deactivate', 'delete']:
                    return {
                        'success': False,
                        'message': 'Thao tác không hợp lệ',
                        'error_code': 'INVALID_OPERATION'
                    }

                results = []
                failed_count = 0
                success_count = 0

                for user_id in user_ids:
                    try:
                        if operation == 'activate':
                            result = self.toggle_user_status(admin_user, user_id, True)
                        elif operation == 'deactivate':
                            result = self.toggle_user_status(admin_user, user_id, False)
                        elif operation == 'delete':
                            result = self.delete_user(admin_user, user_id)

                        if result['success']:
                            success_count += 1
                        else:
                            failed_count += 1

                        results.append({
                            'user_id': user_id,
                            'success': result['success'],
                            'message': result['message'],
                            'error_code': result.get('error_code', 'UNKNOWN_ERROR')
                        })

                    except Exception as e:
                        failed_count += 1
                        results.append({
                            'user_id': user_id,
                            'success': False,
                            'message': str(e),
                            'error_code': 'UNKNOWN_ERROR'
                        })

                operation_name = {
                    'activate': 'kích hoạt',
                    'deactivate': 'vô hiệu hóa',
                    'delete': 'xóa'
                }[operation]

                return {
                    'success': True if failed_count == 0 else False,
                    'message': f'Bulk {operation_name}: {success_count} thành công, {failed_count} thất bại',
                    'data': {
                        'results': results,
                        'summary': {
                            'total': len(user_ids),
                            'success_count': success_count,
                            'failed_count': failed_count
                        }
                    }
                }

        except Exception as e:
            logger.error(f"Bulk operation error: {str(e)}")
            return {
                'success': False,
                'message': f'Thao tác hàng loạt thất bại: {str(e)}',
                'error_code': 'DATABASE_ERROR'
            }

    def _check_user_access_permission(self, current_user, target_user):
        """Check permission để xem thông tin user"""
        # Superuser có thể xem tất cả
        if current_user.is_superuser:
            return {'allowed': True, 'message': ''}

        # Admin có thể xem tất cả
        if current_user.user_type == 'admin':
            return {'allowed': True, 'message': ''}

        # Manager có thể xem:
        # - Staff của nhà hàng mình quản lý
        # - Customer (để quản lý orders)
        if current_user.user_type == 'manager':
            if target_user.user_type == 'staff':
                # Kiểm tra staff có thuộc nhà hàng của manager không
                profile = self.staff_selector.get_profile_by_user(target_user)
                if profile and profile.restaurant_id:
                    if self.restaurant_selector.user_can_access_restaurant(current_user, profile.restaurant_id):
                        return {'allowed': True, 'message': ''}

                return {'allowed': False, 'message': 'Bạn không có quyền xem nhân viên này'}
            elif target_user.user_type == 'customer':
                return {'allowed': True, 'message': ''}  # Manager có thể xem customers

        # Staff chỉ có thể xem customers (để phục vụ)
        if current_user.user_type == 'staff':
            if target_user.user_type == 'customer':
                return {'allowed': True, 'message': ''}
            elif target_user.id == current_user.id:
                return {'allowed': True, 'message': ''}

        # Customer chỉ có thể xem thông tin của chính mình
        if current_user.user_type == 'customer':
            if target_user.id == current_user.id:
                return {'allowed': True, 'message': ''}

        return {'allowed': False, 'message': 'Bạn không có quyền xem thông tin người dùng này'}

    def _check_user_modify_permission(self, current_user, target_user):
        """Check permission để sửa/xóa user"""
        # Superuser có thể sửa/xóa tất cả
        if current_user.is_superuser:
            return {'allowed': True, 'message': ''}

        # Admin có thể sửa/xóa tất cả
        if current_user.user_type == 'admin':
            return {'allowed': True, 'message': ''}

        # Manager chỉ có thể sửa/xóa:
        # - Staff của nhà hàng mình quản lý
        # - Customer
        if current_user.user_type == 'manager':
            if target_user.user_type == 'staff':
                # Kiểm tra staff có thuộc nhà hàng của manager không
                profile = self.staff_selector.get_profile_by_user(target_user)
                if profile and profile.restaurant_id:
                    if self.restaurant_selector.user_can_access_restaurant(current_user, profile.restaurant_id):
                        return {'allowed': True, 'message': ''}

                return {'allowed': False, 'message': 'Bạn không có quyền sửa/xóa nhân viên này'}
            elif target_user.user_type in ['customer']:
                return {'allowed': True, 'message': ''}

        return {'allowed': False, 'message': 'Bạn không có quyền sửa/xóa người dùng này'}

    def _extract_profile_data(self, user_data, user_type):
        """Extract profile data từ user_data theo user_type"""
        if user_type == 'customer':
            return {
                'preferred_language': user_data.get('preferred_language', 'vi'),
                'loyalty_points': user_data.get('loyalty_points', 0),
                'total_orders': user_data.get('total_orders', 0),
                'total_spent': user_data.get('total_spent', 0),
                'receive_promotions': user_data.get('receive_promotions', True),
                'receive_notifications': user_data.get('receive_notifications', True),
            }
        elif user_type in ['staff', 'manager']:
            return {
                'employee_id': user_data.get('employee_id'),
                'position': user_data.get('position'),
                'hire_date': user_data.get('hire_date'),
                'salary': user_data.get('salary'),
                'restaurant_id': user_data.get('restaurant_id'),
                'is_active': user_data.get('is_active', True),
            }

        return {}


class CustomerProfileService:
    """Service cho customer profile management"""

    def __init__(self):
        self.customer_selector = CustomerProfileSelector()

    def update_customer_preferences(self, user, preferences_data):
        """Cập nhật preferences của customer"""
        try:
            with transaction.atomic():
                profile = self.customer_selector.get_profile_by_user(user)
                if not profile:
                    return {
                        'success': False,
                        'message': 'Không tìm thấy hồ sơ khách hàng',
                        'error_code': 'PROFILE_NOT_FOUND'
                    }

                # Cập nhật preferences
                for field, value in preferences_data.items():
                    if hasattr(profile, field):
                        setattr(profile, field, value)

                profile.save()

                return {
                    'success': True,
                    'message': 'Cập nhật preferences thành công',
                    'data': {'profile': profile}
                }

        except Exception as e:
            logger.error(f"Update customer preferences error: {str(e)}")
            return {
                'success': False,
                'message': f'Cập nhật preferences thất bại: {str(e)}',
                'error_code': 'DATABASE_ERROR'
            }

    def get_loyalty_info(self, user):
        """Lấy thông tin loyalty của customer"""
        try:
            profile = self.customer_selector.get_profile_by_user(user)
            if not profile:
                return {
                    'success': False,
                    'message': 'Không tìm thấy hồ sơ khách hàng',
                    'error_code': 'PROFILE_NOT_FOUND'
                }

            # Calculate loyalty tier
                loyalty_tiers = getattr(settings, 'LOYALTY_TIERS', {
                    'bronze': {'min_points': 0, 'discount': 0.05},
                    'silver': {'min_points': 100, 'discount': 0.10},
                    'gold': {'min_points': 500, 'discount': 0.15},
                    'platinum': {'min_points': 1000, 'discount': 0.20},
                })

                current_tier = 'bronze'
                next_tier = None
                points_to_next = 0

                for tier_name, tier_info in sorted(loyalty_tiers.items(),
                                              key=lambda x: x[1]['min_points'], reverse=True):
                    if profile.loyalty_points >= tier_info['min_points']:
                        current_tier = tier_name
                        break

                # Find next tier
                tier_names = sorted(loyalty_tiers.keys(),
                                 key=lambda x: loyalty_tiers[x]['min_points'])
                current_index = tier_names.index(current_tier)
                if current_index < len(tier_names) - 1:
                    next_tier = tier_names[current_index + 1]
                    points_to_next = loyalty_tiers[next_tier]['min_points'] - profile.loyalty_points

                return {
                    'success': True,
                    'message': 'Lấy thông tin loyalty thành công',
                    'data': {
                        'loyalty_points': profile.loyalty_points,
                        'total_orders': profile.total_orders,
                        'total_spent': str(profile.total_spent),
                        'current_tier': current_tier,
                        'current_discount': loyalty_tiers[current_tier]['discount'],
                        'next_tier': next_tier,
                        'points_to_next_tier': points_to_next,
                        'preferred_language': profile.preferred_language,
                        'receive_promotions': profile.receive_promotions,
                        'receive_notifications': profile.receive_notifications,
                    }
                }

        except Exception as e:
            logger.error(f"Get loyalty info error: {str(e)}")
            return {
                'success': False,
                'message': f'Lấy thông tin loyalty thất bại: {str(e)}',
                'error_code': 'DATABASE_ERROR'
            }