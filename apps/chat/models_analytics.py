"""
Analytics Models for Chatbot

This module contains models for tracking chatbot performance,
user feedback, and recommendation analytics.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.users.models import User
from apps.restaurants.models import Restaurant
from apps.chat.models import ChatRoom
from apps.dishes.models import MenuItem


class ChatbotFeedback(models.Model):
    """
    User feedback on chatbot recommendations and responses.

    Tracks user satisfaction with recommendations to improve
    future suggestion quality.
    """

    FEEDBACK_TYPES = (
        ('recommendation', 'Recommendation Feedback'),
        ('response', 'Response Quality'),
        ('escalation', 'Escalation Feedback'),
    )

    RATING_CHOICES = (
        (1, 'Poor'),
        (2, 'Fair'),
        (3, 'Good'),
        (4, 'Very Good'),
        (5, 'Excellent'),
    )

    id = models.BigAutoField(primary_key=True)
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='feedbacks',
        help_text="Chat room where feedback was given"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='chatbot_feedbacks',
        help_text="User who provided feedback"
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.SET_NULL,
        null=True,
        related_name='chatbot_feedbacks',
        help_text="Restaurant context"
    )

    # Feedback details
    feedback_type = models.CharField(
        max_length=20,
        choices=FEEDBACK_TYPES,
        help_text="Type of feedback"
    )
    rating = models.IntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="User rating (1-5)"
    )

    # Recommendation-specific fields
    suggested_items = models.ManyToManyField(
        'dishes.MenuItem',
        blank=True,
        related_name='feedback_suggestions',
        help_text="Items that were suggested"
    )
    accepted_items = models.ManyToManyField(
        'dishes.MenuItem',
        blank=True,
        related_name='feedback_accepted',
        help_text="Items that user accepted/ordered"
    )

    # Context data
    intent = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Intent that triggered the response"
    )
    response_content = models.TextField(
        blank=True,
        null=True,
        help_text="Bot response that was rated"
    )
    user_comment = models.TextField(
        blank=True,
        help_text="Optional user comment"
    )

    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When feedback was given"
    )
    session_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Session identifier for tracking"
    )

    class Meta:
        db_table = 'chatbot_feedback'
        verbose_name = 'Chatbot Feedback'
        verbose_name_plural = 'Chatbot Feedbacks'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['restaurant', 'created_at']),
            models.Index(fields=['feedback_type', 'rating']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Feedback {self.id} - {self.feedback_type} - {self.rating}/5"


class ChatbotAnalytics(models.Model):
    """
    Daily analytics metrics for chatbot performance.

    Tracks aggregated metrics for monitoring and optimization.
    """

    METRIC_TYPES = (
        ('daily_interactions', 'Daily Interactions'),
        ('intent_accuracy', 'Intent Classification Accuracy'),
        ('recommendation_acceptance', 'Recommendation Acceptance Rate'),
        ('escalation_rate', 'Escalation Rate'),
        ('avg_response_time', 'Average Response Time'),
        ('user_satisfaction', 'User Satisfaction Score'),
        ('error_rate', 'Error Rate'),
    )

    id = models.BigAutoField(primary_key=True)
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.CASCADE,
        related_name='chatbot_analytics',
        help_text="Restaurant for these metrics"
    )
    metric_type = models.CharField(
        max_length=50,
        choices=METRIC_TYPES,
        help_text="Type of metric"
    )
    date = models.DateField(
        help_text="Date for these metrics"
    )

    # Metric values
    value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        help_text="Metric value"
    )
    count = models.IntegerField(
        default=0,
        help_text="Sample count (for averages)"
    )

    # Additional metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metric details"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When metric was recorded"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When metric was last updated"
    )

    class Meta:
        db_table = 'chatbot_analytics'
        verbose_name = 'Chatbot Analytics'
        verbose_name_plural = 'Chatbot Analytics'
        unique_together = ['restaurant', 'metric_type', 'date']
        indexes = [
            models.Index(fields=['restaurant', 'date']),
            models.Index(fields=['metric_type', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.restaurant.name} - {self.metric_type} - {self.date}"


class RecommendationInteraction(models.Model):
    """
    Track individual recommendation interactions for learning.

    Records which dishes were recommended, shown, clicked, and ordered
    to improve recommendation algorithm.
    """

    INTERACTION_TYPES = (
        ('shown', 'Shown to User'),
        ('clicked', 'User Clicked'),
        ('added_to_cart', 'Added to Cart'),
        ('ordered', 'Ordered'),
        ('ignored', 'Ignored'),
    )

    id = models.BigAutoField(primary_key=True)
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='recommendation_interactions',
        help_text="Chat room where recommendation occurred"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recommendation_interactions',
        help_text="User who received recommendation"
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.SET_NULL,
        null=True,
        related_name='recommendation_interactions',
        help_text="Restaurant context"
    )
    menu_item = models.ForeignKey(
        'dishes.MenuItem',
        on_delete=models.SET_NULL,
        null=True,
        related_name='recommendation_interactions',
        help_text="Recommended menu item"
    )

    # Interaction details
    interaction_type = models.CharField(
        max_length=20,
        choices=INTERACTION_TYPES,
        help_text="Type of interaction"
    )

    # Context when recommended
    recommendation_context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Context at time of recommendation (weather, time, etc.)"
    )

    # Scoring data (for learning)
    score = models.FloatField(
        null=True,
        blank=True,
        help_text="Recommendation score"
    )
    position = models.IntegerField(
        null=True,
        blank=True,
        help_text="Position in recommendation list"
    )

    # Feedback
    rating = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="User rating if provided"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When interaction occurred"
    )

    class Meta:
        db_table = 'recommendation_interactions'
        verbose_name = 'Recommendation Interaction'
        verbose_name_plural = 'Recommendation Interactions'
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['restaurant', 'created_at']),
            models.Index(fields=['menu_item', 'interaction_type']),
            models.Index(fields=['interaction_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.interaction_type} - {self.menu_item.name if self.menu_item else 'Unknown'}"


class ChatbotSession(models.Model):
    """
    Track chatbot conversation sessions for analytics.

    Records complete conversation sessions for analysis
    and performance monitoring.
    """

    id = models.BigAutoField(primary_key=True)
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='sessions',
        help_text="Associated chat room"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='chatbot_sessions',
        help_text="User in session"
    )
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.SET_NULL,
        null=True,
        related_name='chatbot_sessions',
        help_text="Restaurant context"
    )

    # Session metrics
    message_count = models.IntegerField(
        default=0,
        help_text="Number of messages in session"
    )
    escalated = models.BooleanField(
        default=False,
        help_text="Whether session was escalated to human"
    )
    resolved = models.BooleanField(
        default=False,
        help_text="Whether user's issue was resolved"
    )

    # Performance metrics
    avg_response_time = models.FloatField(
        null=True,
        blank=True,
        help_text="Average response time in seconds"
    )
    total_response_time = models.FloatField(
        default=0.0,
        help_text="Total response time for all messages"
    )

    # Context data
    session_start = models.DateTimeField(
        auto_now_add=True,
        help_text="Session start time"
    )
    session_end = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Session end time"
    )

    # Intents covered
    intents = models.JSONField(
        default=list,
        blank=True,
        help_text="List of intents covered in session"
    )

    # User satisfaction
    satisfaction_score = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Overall session satisfaction"
    )

    class Meta:
        db_table = 'chatbot_sessions'
        verbose_name = 'Chatbot Session'
        verbose_name_plural = 'Chatbot Sessions'
        indexes = [
            models.Index(fields=['user', 'session_start']),
            models.Index(fields=['restaurant', 'session_start']),
            models.Index(fields=['escalated', 'session_start']),
            models.Index(fields=['session_start']),
        ]

    def __str__(self):
        return f"Session {self.id} - Room {self.room_id}"

    @property
    def duration_minutes(self):
        """Calculate session duration in minutes"""
        if self.session_end:
            delta = self.session_end - self.session_start
            return delta.total_seconds() / 60
        return None
