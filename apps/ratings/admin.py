from django.contrib import admin
from .models import MenuItemReview, ReviewResponse


@admin.register(MenuItemReview)
class MenuItemReviewAdmin(admin.ModelAdmin):
    """Admin configuration for MenuItemReview"""
    list_display = [
        'menu_item', 'user', 'rating', 'is_verified_purchase',
        'is_approved', 'created_at'
    ]
    list_filter = [
        'rating', 'is_verified_purchase', 'is_approved',
        'created_at'
    ]
    search_fields = [
        'menu_item__name', 'user__username', 'user__email', 'content'
    ]
    readonly_fields = [
        'ip_address', 'created_at', 'updated_at'
    ]

    fieldsets = (
        ('Rating Information', {
            'fields': ('menu_item', 'user', 'order_item', 'rating')
        }),
        ('Review Content', {
            'fields': ('content',)
        }),
        ('Moderation', {
            'fields': ('is_verified_purchase', 'is_approved')
        }),
        ('Metadata', {
            'fields': ('ip_address', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    raw_id_fields = ['menu_item', 'user', 'order_item']
    date_hierarchy = 'created_at'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'menu_item', 'user', 'order_item'
        )


@admin.register(ReviewResponse)
class ReviewResponseAdmin(admin.ModelAdmin):
    """Admin configuration for ReviewResponse"""
    list_display = [
        'review', 'responder', 'is_public', 'created_at'
    ]
    list_filter = [
        'is_public', 'created_at'
    ]
    search_fields = [
        'review__menu_item__name', 'responder__username', 'content'
    ]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Response Information', {
            'fields': ('review', 'responder', 'is_public')
        }),
        ('Response Content', {
            'fields': ('content',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    raw_id_fields = ['review', 'responder']
    date_hierarchy = 'created_at'
