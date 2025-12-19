from django.contrib import admin
from .models import MenuItemRating, RatingCategory, RatingResponse


@admin.register(MenuItemRating)
class MenuItemRatingAdmin(admin.ModelAdmin):
    """Admin configuration for MenuItemRating"""
    list_display = [
        'menu_item', 'user', 'rating', 'is_verified_purchase',
        'is_approved', 'helpful_count', 'created_at'
    ]
    list_filter = [
        'rating', 'is_verified_purchase', 'is_approved',
        'created_at', 'menu_item__restaurant'
    ]
    search_fields = [
        'menu_item__name', 'user__username', 'user__email',
        'review_text'
    ]
    readonly_fields = [
        'helpful_count', 'not_helpful_count', 'ip_address',
        'created_at', 'updated_at'
    ]

    fieldsets = (
        ('Rating Information', {
            'fields': ('menu_item', 'user', 'order_item', 'rating')
        }),
        ('Review Content', {
            'fields': ('review_text', 'review_images')
        }),
        ('Moderation', {
            'fields': ('is_verified_purchase', 'is_approved', 'moderation_notes')
        }),
        ('Engagement', {
            'fields': ('helpful_count', 'not_helpful_count')
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
        ).prefetch_related('menu_item__restaurant')


@admin.register(RatingCategory)
class RatingCategoryAdmin(admin.ModelAdmin):
    """Admin configuration for RatingCategory"""
    list_display = ['name', 'code', 'is_active', 'display_order']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'description']
    list_editable = ['is_active', 'display_order']

    prepopulated_fields = {'code': ('name',)}


@admin.register(RatingResponse)
class RatingResponseAdmin(admin.ModelAdmin):
    """Admin configuration for RatingResponse"""
    list_display = [
        'rating', 'responder', 'is_public', 'created_at'
    ]
    list_filter = [
        'is_public', 'created_at', 'rating__menu_item__restaurant'
    ]
    search_fields = [
        'rating__menu_item__name', 'responder__username',
        'response_text'
    ]
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Response Information', {
            'fields': ('rating', 'responder', 'is_public')
        }),
        ('Response Content', {
            'fields': ('response_text',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    raw_id_fields = ['rating', 'responder']
    date_hierarchy = 'created_at'