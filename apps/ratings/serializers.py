from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from .models import MenuItemRating, RatingCategory, RatingResponse, RatingHelpful
from apps.dishes.models import MenuItem
from apps.api.mixins import TimestampMixin

User = get_user_model()


class RatingCategorySerializer(serializers.ModelSerializer):
    """Serializer for RatingCategory model"""

    class Meta:
        model = RatingCategory
        fields = [
            'id', 'name', 'code', 'description', 'is_active',
            'display_order', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RatingResponseSerializer(serializers.ModelSerializer):
    """Serializer for RatingResponse model"""
    responder_name = serializers.CharField(source='responder.get_full_name', read_only=True)
    responder_avatar = serializers.ImageField(source='responder.avatar', read_only=True)

    class Meta:
        model = RatingResponse
        fields = [
            'id', 'responder', 'responder_name', 'responder_avatar',
            'response_text', 'is_public', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'responder', 'responder_name', 'responder_avatar',
            'created_at', 'updated_at'
        ]


class MenuItemRatingSerializer(serializers.ModelSerializer):
    """Serializer for MenuItemRating model"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_avatar = serializers.ImageField(source='user.avatar', read_only=True)
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_item_image = serializers.ImageField(source='menu_item.image', read_only=True)
    responses = RatingResponseSerializer(many=True, read_only=True)
    can_edit = serializers.ReadOnlyField()
    helpful_percentage = serializers.ReadOnlyField()
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = MenuItemRating
        fields = [
            'id', 'menu_item', 'user', 'user_name', 'user_avatar',
            'menu_item_name', 'menu_item_image', 'rating', 'review_text',
            'review_images', 'helpful_count', 'not_helpful_count',
            'helpful_percentage', 'is_verified_purchase', 'is_approved',
            'can_edit', 'time_ago', 'responses', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'user_name', 'user_avatar',
            'menu_item_name', 'menu_item_image', 'helpful_count',
            'not_helpful_count', 'is_verified_purchase', 'is_approved',
            'can_edit', 'helpful_percentage', 'responses',
            'created_at', 'updated_at'
        ]

    def get_time_ago(self, obj):
        """Get human readable time ago"""
        from django.utils.timesince import timesince
        return timesince(obj.created_at) + " ago"

    def validate_rating(self, value):
        """Validate rating is between 1 and 5"""
        from decimal import Decimal
        min_val = Decimal('1')
        max_val = Decimal('5')
        if not min_val <= value <= max_val:
            raise serializers.ValidationError("Rating must be between 1 and 5 stars")
        return value

    def validate_review_text(self, value):
        """Validate review text length"""
        if value:
            if len(value.strip()) < 10:
                raise serializers.ValidationError(
                    "Review text must be at least 10 characters long"
                )
            if len(value) > 2000:
                raise serializers.ValidationError(
                    "Review text cannot exceed 2000 characters"
                )
        return value

    def validate_review_images(self, value):
        """Validate review images array"""
        if value and len(value) > 5:
            raise serializers.ValidationError(
                "Cannot add more than 5 images to a review"
            )
        return value


class MenuItemRatingCreateSerializer(MenuItemRatingSerializer):
    """Serializer for creating/updating menu item ratings"""

    class Meta(MenuItemRatingSerializer.Meta):
        fields = [
            'menu_item', 'rating', 'review_text', 'review_images'
        ]

    def validate_menu_item(self, value):
        """Validate menu item exists and is available"""
        if not value.is_available:
            raise serializers.ValidationError(
                "Cannot rate an unavailable menu item"
            )
        return value

    def create(self, validated_data):
        """Create or update rating with validation"""
        user = self.context['request'].user
        menu_item = validated_data['menu_item']
        rating_value = validated_data['rating']

        # Check if user already rated this item
        existing_rating = MenuItemRating.objects.filter(
            menu_item=menu_item, user=user
        ).first()

        with transaction.atomic():
            if existing_rating:
                # Update existing rating
                for key, value in validated_data.items():
                    setattr(existing_rating, key, value)
                existing_rating.save()
                rating = existing_rating
            else:
                # Create new rating
                validated_data['user'] = user
                validated_data['ip_address'] = self._get_client_ip()
                rating = MenuItemRating.objects.create(**validated_data)

            # Check if user has actually ordered this item
            self._check_verified_purchase(rating)

            # Auto-approve for verified purchases with 3+ stars
            self._auto_approve_if_needed(rating)

            # Update menu item rating statistics
            self._update_menu_item_rating_stats(menu_item)

            return rating

    def _get_client_ip(self):
        """Get client IP address"""
        request = self.context.get('request')
        if request:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0]
            else:
                ip = request.META.get('REMOTE_ADDR')
            return ip
        return None

    def _check_verified_purchase(self, rating):
        """Check if user has actually ordered this item"""
        from apps.orders.models import OrderItem
        has_ordered = OrderItem.objects.filter(
            menu_item=rating.menu_item,
            order__customer=rating.user,
            order__status='completed'
        ).exists()

        rating.is_verified_purchase = has_ordered
        rating.save(update_fields=['is_verified_purchase'])

    def _auto_approve_if_needed(self, rating):
        """Auto-approve ratings from verified purchases with 3+ stars"""
        if rating.is_verified_purchase and rating.rating >= 3:
            rating.is_approved = True
            rating.save(update_fields=['is_approved'])

    def _update_menu_item_rating_stats(self, menu_item):
        """Update menu item rating statistics"""
        from .tasks import update_menu_item_rating_stats
        # Call task asynchronously if Celery is available
        try:
            update_menu_item_rating_stats.delay(menu_item.id)
        except:
            # Fallback to synchronous update
            self._sync_update_menu_item_stats(menu_item)

    def _sync_update_menu_item_stats(self, menu_item):
        """Synchronous fallback for updating menu item stats"""
        from apps.ratings.selectors import RatingSelector
        selector = RatingSelector()
        selector.update_menu_item_rating_stats(menu_item.id)


class MenuItemRatingSummarySerializer(serializers.Serializer):
    """Serializer for menu item rating summary"""
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    total_reviews = serializers.IntegerField()
    rating_distribution = serializers.DictField()
    verified_purchase_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )
    recent_reviews = MenuItemRatingSerializer(many=True)
    top_positive_reviews = MenuItemRatingSerializer(many=True)
    top_critical_reviews = MenuItemRatingSerializer(many=True)


class RatingHelpfulSerializer(serializers.Serializer):
    """Serializer for marking ratings as helpful/not helpful"""
    is_helpful = serializers.BooleanField(required=True)

    def validate(self, attrs):
        """Validate user hasn't already voted"""
        user = self.context['request'].user
        rating = self.context['rating']

        if RatingHelpful.objects.filter(rating=rating, user=user).exists():
            raise serializers.ValidationError(
                "You have already voted on this review"
            )
        return attrs


class RatingReportSerializer(serializers.Serializer):
    """Serializer for reporting inappropriate ratings"""
    reason = serializers.ChoiceField(choices=[
        ('spam', 'Spam or fake review'),
        ('offensive', 'Offensive content'),
        ('inappropriate', 'Inappropriate images'),
        ('irrelevant', 'Irrelevant to the item'),
        ('duplicate', 'Duplicate review'),
        ('other', 'Other')
    ])
    description = serializers.CharField(
        required=False,
        max_length=500,
        allow_blank=True
    )

    def create(self, validated_data):
        """Create a rating report"""
        rating = self.context['rating']
        user = self.context['request'].user

        # TODO: Implement RatingReport model
        # For now, just mark as needs moderation
        rating.is_approved = False
        rating.moderation_notes = f"Reported by {user.username}: {validated_data.get('reason', 'other')}"
        rating.save(update_fields=['is_approved', 'moderation_notes'])

        return validated_data