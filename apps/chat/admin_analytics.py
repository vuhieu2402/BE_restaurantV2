"""
Admin Interface for Chatbot Analytics

This module provides Django admin interfaces for monitoring
chatbot performance, feedback, and analytics.
"""

from django.contrib import admin
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from django.urls import path
from django.shortcuts import render
from django.http import JsonResponse

from apps.chat.models_analytics import (
    ChatbotFeedback,
    ChatbotAnalytics,
    RecommendationInteraction,
    ChatbotSession,
)


@admin.register(ChatbotFeedback)
class ChatbotFeedbackAdmin(admin.ModelAdmin):
    """Admin interface for chatbot feedback"""

    list_display = [
        'id',
        'room',
        'user',
        'restaurant',
        'feedback_type',
        'rating',
        'created_at',
        'session_id',
    ]
    list_filter = [
        'feedback_type',
        'rating',
        'created_at',
        'restaurant',
    ]
    search_fields = [
        'user__username',
        'user__email',
        'room__room_number',
        'session_id',
        'user_comment',
    ]
    readonly_fields = [
        'created_at',
    ]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('room', 'user', 'restaurant', 'session_id')
        }),
        ('Feedback', {
            'fields': ('feedback_type', 'rating', 'user_comment')
        }),
        ('Context', {
            'fields': ('intent', 'response_content')
        }),
        ('Items', {
            'fields': ('suggested_items', 'accepted_items')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset with related objects"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'room', 'restaurant')


@admin.register(ChatbotAnalytics)
class ChatbotAnalyticsAdmin(admin.ModelAdmin):
    """Admin interface for chatbot analytics"""

    list_display = [
        'id',
        'restaurant',
        'metric_type',
        'date',
        'value',
        'count',
        'created_at',
    ]
    list_filter = [
        'metric_type',
        'date',
        'restaurant',
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    date_hierarchy = 'date'

    fieldsets = (
        ('Basic Information', {
            'fields': ('restaurant', 'metric_type', 'date')
        }),
        ('Metrics', {
            'fields': ('value', 'count', 'metadata')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_urls(self):
        """Add custom URLs for analytics dashboard"""
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_site.admin_view(self.dashboard_view),
                 name='chatbot_analytics_dashboard'),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        """
        Custom analytics dashboard view.

        Shows aggregated metrics and visualizations.
        """
        # Get date range (last 7 days by default)
        days = int(request.GET.get('days', 7))
        cutoff_date = timezone.now().date() - timedelta(days=days)

        # Get all analytics for the period
        analytics = ChatbotAnalytics.objects.filter(
            date__gte=cutoff_date
        ).select_related('restaurant')

        # Aggregate metrics by type
        metrics_by_type = {}
        for metric in analytics:
            if metric.metric_type not in metrics_by_type:
                metrics_by_type[metric.metric_type] = []
            metrics_by_type[metric.metric_type].append(metric)

        # Calculate averages and totals
        summary = {}
        for metric_type, values in metrics_by_type.items():
            total_count = sum(v.count for v in values)
            weighted_avg = sum(v.value * v.count for v in values) / total_count if total_count > 0 else 0
            summary[metric_type] = {
                'average': weighted_avg,
                'total_count': total_count,
                'latest': values[-1].value if values else 0,
            }

        # Get top restaurants by interaction count
        top_restaurants = ChatbotAnalytics.objects.filter(
            date__gte=cutoff_date,
            metric_type='daily_interactions',
        ).values('restaurant__name').annotate(
            total_count=Count('count')
        ).order_by('-total_count')[:10]

        # Calculate escalation rate
        escalated = ChatbotSession.objects.filter(
            session_start__gte=timezone.now() - timedelta(days=days),
            escalated=True,
        ).count()
        total_sessions = ChatbotSession.objects.filter(
            session_start__gte=timezone.now() - timedelta(days=days),
        ).count()
        escalation_rate = (escalated / total_sessions * 100) if total_sessions > 0 else 0

        context = {
            **self.admin_site.each_context(request),
            'title': 'Chatbot Analytics Dashboard',
            'days': days,
            'summary': summary,
            'top_restaurants': top_restaurants,
            'escalation_rate': escalation_rate,
            'total_sessions': total_sessions,
            'escalated_sessions': escalated,
        }

        return render(request, 'admin/chatbot_analytics/dashboard.html', context)


@admin.register(RecommendationInteraction)
class RecommendationInteractionAdmin(admin.ModelAdmin):
    """Admin interface for recommendation interactions"""

    list_display = [
        'id',
        'user',
        'restaurant',
        'menu_item',
        'interaction_type',
        'score',
        'position',
        'created_at',
    ]
    list_filter = [
        'interaction_type',
        'created_at',
        'restaurant',
        'menu_item',
    ]
    search_fields = [
        'user__username',
        'menu_item__name',
        'room__room_number',
    ]
    readonly_fields = [
        'created_at',
    ]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('room', 'user', 'restaurant', 'menu_item')
        }),
        ('Interaction', {
            'fields': ('interaction_type', 'score', 'position', 'rating')
        }),
        ('Context', {
            'fields': ('recommendation_context',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'restaurant', 'menu_item', 'room')


@admin.register(ChatbotSession)
class ChatbotSessionAdmin(admin.ModelAdmin):
    """Admin interface for chatbot sessions"""

    list_display = [
        'id',
        'room',
        'user',
        'restaurant',
        'message_count',
        'escalated',
        'resolved',
        'duration_minutes',
        'session_start',
    ]
    list_filter = [
        'escalated',
        'resolved',
        'session_start',
        'restaurant',
    ]
    search_fields = [
        'user__username',
        'room__room_number',
    ]
    readonly_fields = [
        'session_start',
        'session_end',
        'duration_minutes',
    ]
    date_hierarchy = 'session_start'

    fieldsets = (
        ('Basic Information', {
            'fields': ('room', 'user', 'restaurant')
        }),
        ('Session Metrics', {
            'fields': ('message_count', 'escalated', 'resolved', 'intents')
        }),
        ('Performance', {
            'fields': ('avg_response_time', 'total_response_time')
        }),
        ('Timing', {
            'fields': ('session_start', 'session_end', 'duration_minutes')
        }),
        ('Satisfaction', {
            'fields': ('satisfaction_score',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'restaurant', 'room')


# Custom admin site configuration
admin.site.enable_nav_sidebar = False
