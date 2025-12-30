from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Avg, Count
from apps.dishes.models import MenuItem
from apps.orders.models import OrderItem

User = get_user_model()


class MenuItemReview(models.Model):
    """
    Simplified review system for menu items.
    Rating (1-5 stars) + Content only. No images, no title.
    One review per user per menu item.
    """
    id = models.BigAutoField(primary_key=True)

    # Relationships
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name='reviews',
        help_text="Menu item being reviewed"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='menu_item_reviews',
        help_text="User who wrote the review"
    )
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='review',
        help_text="Linked order item for verified purchase"
    )

    # Core review fields (ONLY rating + content)
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    content = models.TextField(
        help_text="Review content/text"
    )

    # Moderation
    is_verified_purchase = models.BooleanField(
        default=False,
        help_text="User actually ordered this item"
    )
    is_approved = models.BooleanField(
        default=True,
        help_text="Review passed moderation"
    )

    # Metadata
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of reviewer"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Review created date"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Review last updated date"
    )

    class Meta:
        db_table = 'menu_item_reviews'
        verbose_name = 'Menu Item Review'
        verbose_name_plural = 'Menu Item Reviews'
        unique_together = ['menu_item', 'user']  # One review per user per item
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
    def can_edit(self):
        """Check if review can be edited (within 30 days of creation)"""
        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
        return self.created_at > thirty_days_ago

    def save(self, *args, **kwargs):
        """Save review and update menu item rating statistics"""
        super().save(*args, **kwargs)
        # Update the menu item's aggregated rating stats
        self.menu_item.update_rating_stats()

    def delete(self, *args, **kwargs):
        """Delete review and update menu item rating statistics"""
        menu_item = self.menu_item
        super().delete(*args, **kwargs)
        # Update the menu item's aggregated rating stats
        menu_item.update_rating_stats()


class ReviewResponse(models.Model):
    """
    Responses from restaurant owners/managers to menu item reviews.
    Simplified - only works with MenuItemReview.
    """
    review = models.ForeignKey(
        MenuItemReview,
        on_delete=models.CASCADE,
        related_name='responses',
        help_text="Review being responded to"
    )
    responder = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='review_responses',
        help_text="Restaurant staff/owner who responded"
    )
    content = models.TextField(
        help_text="Response content"
    )
    is_public = models.BooleanField(
        default=True,
        help_text="Show response publicly"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Response created date"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Response last updated date"
    )

    class Meta:
        db_table = 'review_responses'
        verbose_name = 'Review Response'
        verbose_name_plural = 'Review Responses'
        indexes = [
            models.Index(fields=['review', 'is_public']),
            models.Index(fields=['responder', 'created_at']),
        ]
        ordering = ['created_at']

    def __str__(self):
        return f"Response to review {self.review.id}"
