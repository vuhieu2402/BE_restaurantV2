from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from .models import MenuItemReview, ReviewResponse
from apps.dishes.models import MenuItem
from apps.api.mixins import TimestampMixin

User = get_user_model()


class ReviewResponseSerializer(serializers.ModelSerializer):
    """Serializer for ReviewResponse model"""
    responder = serializers.SerializerMethodField()

    class Meta:
        model = ReviewResponse
        fields = [
            'id', 'review', 'responder',
            'content', 'is_public', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'responder', 'created_at', 'updated_at'
        ]

    def get_responder(self, obj):
        """Get responder object with name, id and avatar"""
        return {
            'id': obj.responder.id,
            'name': obj.responder.get_full_name(),
            'avatar': obj.responder.avatar.url if obj.responder.avatar else None
        }

class MenuItemReviewSerializer(serializers.ModelSerializer):
    """Serializer for MenuItemReview model - Simplified: rating + content only"""
    user = serializers.SerializerMethodField()
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_item_image = serializers.ImageField(source='menu_item.image', read_only=True)
    responses = ReviewResponseSerializer(many=True, read_only=True)
    can_edit = serializers.ReadOnlyField()
    time_ago = serializers.SerializerMethodField()

    class Meta:
        model = MenuItemReview
        fields = [
            'id', 'menu_item', 'user',
            'menu_item_name', 'menu_item_image', 'rating', 'content',
            'is_verified_purchase', 'is_approved', 'can_edit', 'time_ago',
            'responses', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'menu_item_name', 'menu_item_image',
            'is_verified_purchase', 'is_approved', 'can_edit', 'responses',
            'created_at', 'updated_at'
        ]

    def get_user(self, obj):
        """Get user object with name, id and avatar"""
        return {
            'id': obj.user.id,
            'name': obj.user.get_full_name(),
            'avatar': obj.user.avatar.url if obj.user.avatar else None
        }

    def get_time_ago(self, obj):
        """Get human readable time ago"""
        from django.utils.timesince import timesince
        return timesince(obj.created_at) + " ago"

    def validate_rating(self, value):
        """Validate rating is between 1 and 5"""
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5 stars")
        return value

    def validate_content(self, value):
        """Validate review content length"""
        if value:
            if len(value.strip()) < 10:
                raise serializers.ValidationError(
                    "Review content must be at least 10 characters long"
                )
            if len(value) > 2000:
                raise serializers.ValidationError(
                    "Review content cannot exceed 2000 characters"
                )
        return value


class MenuItemReviewCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating menu item reviews"""

    class Meta:
        model = MenuItemReview
        fields = ['menu_item', 'rating', 'content']

    def validate_menu_item(self, value):
        """Validate menu item exists and is available"""
        if not value.is_available:
            raise serializers.ValidationError(
                "Cannot review an unavailable menu item"
            )
        return value

    def create(self, validated_data):
        """Create or update review with validation"""
        user = self.context['request'].user
        menu_item = validated_data['menu_item']

        # Check if user already reviewed this item
        existing_review = MenuItemReview.objects.filter(
            menu_item=menu_item, user=user
        ).first()

        with transaction.atomic():
            if existing_review:
                # Update existing review
                for key, value in validated_data.items():
                    setattr(existing_review, key, value)
                existing_review.save()
                review = existing_review
            else:
                # Create new review
                validated_data['user'] = user
                validated_data['ip_address'] = self._get_client_ip()
                review = MenuItemReview.objects.create(**validated_data)

            # Check if user has actually ordered this item
            self._check_verified_purchase(review)

            # Auto-approve for verified purchases with 3+ stars
            self._auto_approve_if_needed(review)

            return review

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

    def _check_verified_purchase(self, review):
        """Check if user has actually ordered this item"""
        from apps.orders.models import OrderItem
        has_ordered = OrderItem.objects.filter(
            menu_item=review.menu_item,
            order__customer=review.user,
            order__status='completed'
        ).exists()

        review.is_verified_purchase = has_ordered
        review.save(update_fields=['is_verified_purchase'])

    def _auto_approve_if_needed(self, review):
        """Auto-approve reviews from verified purchases with 3+ stars"""
        if review.is_verified_purchase and review.rating >= 3:
            review.is_approved = True
            review.save(update_fields=['is_approved'])


class MenuItemReviewSummarySerializer(serializers.Serializer):
    """Serializer for menu item review summary"""
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    total_reviews = serializers.IntegerField()
    rating_distribution = serializers.DictField()
    verified_purchase_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2
    )
    recent_reviews = MenuItemReviewSerializer(many=True)


class ReviewResponseCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating responses to reviews"""

    class Meta:
        model = ReviewResponse
        fields = ['content', 'is_public']

    def create(self, validated_data):
        """Create response to review"""
        responder = self.context['request'].user
        review = self.context['review']

        validated_data['review'] = review
        validated_data['responder'] = responder

        return ReviewResponse.objects.create(**validated_data)