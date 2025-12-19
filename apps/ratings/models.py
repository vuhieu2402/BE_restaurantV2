from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from apps.dishes.models import MenuItem
from apps.orders.models import OrderItem

User = get_user_model()


class RatingCategory(models.Model):
    """Categories for detailed rating aspects"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rating_categories'
        verbose_name_plural = "Rating Categories"
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class MenuItemRating(models.Model):
    """Individual user ratings for menu items"""
    id = models.BigAutoField(primary_key=True)
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='user_ratings'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='menu_item_ratings'
    )
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rating'
    )

    # Rating fields
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )

    # Review content
    review_text = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed review of the menu item"
    )
    review_images = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of image URLs"
    )

    # Helpful/Not helpful voting
    helpful_count = models.IntegerField(default=0)
    not_helpful_count = models.IntegerField(default=0)

    # Moderation
    is_verified_purchase = models.BooleanField(
        default=False,
        help_text="User actually ordered this item"
    )
    is_approved = models.BooleanField(
        default=True,
        help_text="Review passed moderation"
    )
    moderation_notes = models.TextField(
        blank=True,
        null=True
    )

    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'menu_item_ratings'
        unique_together = ['menu_item', 'user']  # One rating per user per item
        indexes = [
            models.Index(fields=['menu_item', 'rating']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_approved']),
            models.Index(fields=['is_verified_purchase']),
            models.Index(fields=['rating', 'is_approved']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.menu_item.name} - {self.rating}★"

    @property
    def helpful_percentage(self):
        """Calculate helpful percentage"""
        total = self.helpful_count + self.not_helpful_count
        if total == 0:
            return 0
        return round((self.helpful_count / total) * 100, 1)

    @property
    def can_edit(self):
        """Check if rating can be edited (within 30 days of creation)"""
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        return self.created_at > thirty_days_ago

    def mark_helpful(self, user):
        """Mark rating as helpful by user"""
        # TODO: Implement user helpful tracking to prevent duplicate votes
        self.helpful_count += 1
        self.save(update_fields=['helpful_count'])

    def mark_not_helpful(self, user):
        """Mark rating as not helpful by user"""
        # TODO: Implement user helpful tracking to prevent duplicate votes
        self.not_helpful_count += 1
        self.save(update_fields=['not_helpful_count'])


class RatingResponse(models.Model):
    """Responses from restaurant owners to reviews"""
    rating = models.ForeignKey(
        MenuItemRating,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    responder = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='rating_responses'
    )
    response_text = models.TextField()
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rating_responses'
        indexes = [
            models.Index(fields=['rating', 'is_public']),
            models.Index(fields=['responder', 'created_at']),
        ]
        ordering = ['created_at']

    def __str__(self):
        return f"Response to {self.rating}"


class RatingHelpful(models.Model):
    """Track which users marked a rating as helpful/not helpful"""
    rating = models.ForeignKey(MenuItemRating, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_helpful = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'rating_helpful'
        unique_together = ['rating', 'user']
        indexes = [
            models.Index(fields=['rating', 'is_helpful']),
            models.Index(fields=['user', 'created_at']),
        ]