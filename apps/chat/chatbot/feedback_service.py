"""
Feedback Service for Chatbot

This module handles collecting, analyzing, and learning from
user feedback to improve recommendation quality.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate

from apps.chat.models_analytics import (
    ChatbotFeedback,
    ChatbotAnalytics,
    RecommendationInteraction,
    ChatbotSession,
)
from apps.chat.selectors import ChatbotSelector

logger = logging.getLogger(__name__)


class FeedbackService:
    """
    Service for collecting and analyzing user feedback.

    Features:
    - Track recommendation acceptance
    - Learn from user preferences
    - Update user profiles dynamically
    - Calculate analytics metrics
    """

    CACHE_KEY_PREFIX = 'chatbot:analytics'
    CACHE_TTL = 3600  # 1 hour

    def __init__(self):
        """Initialize the feedback service"""
        pass

    def record_feedback(
        self,
        room_id: int,
        user_id: int,
        restaurant_id: int,
        feedback_type: str,
        rating: int,
        suggested_items: Optional[List[int]] = None,
        accepted_items: Optional[List[int]] = None,
        intent: Optional[str] = None,
        response_content: Optional[str] = None,
        user_comment: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> ChatbotFeedback:
        """
        Record user feedback on chatbot interaction.

        Args:
            room_id: Chat room ID
            user_id: User ID
            restaurant_id: Restaurant ID
            feedback_type: Type of feedback (recommendation, response, escalation)
            rating: User rating (1-5)
            suggested_items: List of suggested item IDs
            accepted_items: List of accepted item IDs
            intent: Intent that triggered the response
            response_content: Bot response content
            user_comment: Optional user comment
            session_id: Session identifier

        Returns:
            Created ChatbotFeedback object
        """
        try:
            from apps.chat.models import ChatRoom
            from apps.users.models import User
            from apps.restaurants.models import Restaurant
            from apps.dishes.models import MenuItem

            # Get related objects
            room = ChatRoom.objects.filter(id=room_id).first()
            user = User.objects.filter(id=user_id).first()
            restaurant = Restaurant.objects.filter(id=restaurant_id).first()

            # Create feedback
            feedback = ChatbotFeedback.objects.create(
                room=room,
                user=user,
                restaurant=restaurant,
                feedback_type=feedback_type,
                rating=rating,
                intent=intent,
                response_content=response_content,
                user_comment=user_comment,
                session_id=session_id or f"{room_id}_{datetime.now().timestamp()}",
            )

            # Add suggested and accepted items
            if suggested_items:
                feedback.suggested_items.set(suggested_items)
            if accepted_items:
                feedback.accepted_items.set(accepted_items)

            logger.info(
                f"Recorded feedback: room={room_id}, type={feedback_type}, "
                f"rating={rating}, user={user_id}"
            )

            # Trigger learning from feedback
            if feedback_type == 'recommendation':
                self._learn_from_recommendation_feedback(feedback)

            # Update daily analytics
            self._update_daily_analytics(restaurant_id, feedback_type, rating)

            return feedback

        except Exception as e:
            logger.error(f"Error recording feedback: {str(e)}")
            raise

    def track_recommendation_interaction(
        self,
        room_id: int,
        user_id: int,
        restaurant_id: int,
        menu_item_id: int,
        interaction_type: str,
        context: Optional[Dict[str, Any]] = None,
        score: Optional[float] = None,
        position: Optional[int] = None,
    ) -> RecommendationInteraction:
        """
        Track recommendation interaction for learning.

        Args:
            room_id: Chat room ID
            user_id: User ID
            restaurant_id: Restaurant ID
            menu_item_id: Recommended item ID
            interaction_type: Type of interaction (shown, clicked, added_to_cart, ordered, ignored)
            context: Recommendation context (weather, time, etc.)
            score: Recommendation score
            position: Position in recommendation list

        Returns:
            Created RecommendationInteraction object
        """
        try:
            from apps.chat.models import ChatRoom
            from apps.users.models import User
            from apps.restaurants.models import Restaurant
            from apps.dishes.models import MenuItem

            # Get related objects
            room = ChatRoom.objects.filter(id=room_id).first()
            user = User.objects.filter(id=user_id).first()
            restaurant = Restaurant.objects.filter(id=restaurant_id).first()
            menu_item = MenuItem.objects.filter(id=menu_item_id).first()

            # Create interaction
            interaction = RecommendationInteraction.objects.create(
                room=room,
                user=user,
                restaurant=restaurant,
                menu_item=menu_item,
                interaction_type=interaction_type,
                recommendation_context=context or {},
                score=score,
                position=position,
            )

            logger.debug(
                f"Tracked interaction: {interaction_type} for item {menu_item_id} "
                f"by user {user_id}"
            )

            # Update learning cache
            self._update_interaction_cache(restaurant_id, menu_item_id, interaction_type)

            return interaction

        except Exception as e:
            logger.error(f"Error tracking interaction: {str(e)}")
            raise

    def start_session(
        self,
        room_id: int,
        user_id: int,
        restaurant_id: int,
    ) -> ChatbotSession:
        """
        Start a new chatbot session.

        Args:
            room_id: Chat room ID
            user_id: User ID
            restaurant_id: Restaurant ID

        Returns:
            Created ChatbotSession object
        """
        try:
            from apps.chat.models import ChatRoom
            from apps.users.models import User
            from apps.restaurants.models import Restaurant

            session = ChatbotSession.objects.create(
                room_id=room_id,
                user_id=user_id,
                restaurant_id=restaurant_id,
            )

            logger.debug(f"Started session {session.id} for room {room_id}")
            return session

        except Exception as e:
            logger.error(f"Error starting session: {str(e)}")
            raise

    def update_session(
        self,
        session_id: int,
        message_count: Optional[int] = None,
        response_time: Optional[float] = None,
        intent: Optional[str] = None,
        escalated: bool = False,
    ) -> None:
        """
        Update session metrics.

        Args:
            session_id: Session ID
            message_count: Increment message count
            response_time: Add to total response time
            intent: Add intent to list
            escalated: Mark as escalated
        """
        try:
            session = ChatbotSession.objects.filter(id=session_id).first()
            if not session:
                return

            if message_count:
                session.message_count += message_count

            if response_time:
                session.total_response_time += response_time
                # Recalculate average
                if session.message_count > 0:
                    session.avg_response_time = (
                        session.total_response_time / session.message_count
                    )

            if intent:
                if not session.intents:
                    session.intents = []
                if intent not in session.intents:
                    session.intents.append(intent)

            if escalated:
                session.escalated = escalated

            session.save()

        except Exception as e:
            logger.error(f"Error updating session: {str(e)}")

    def end_session(
        self,
        session_id: int,
        resolved: bool = False,
        satisfaction_score: Optional[int] = None,
    ) -> None:
        """
        End a chatbot session.

        Args:
            session_id: Session ID
            resolved: Whether issue was resolved
            satisfaction_score: User satisfaction (1-5)
        """
        try:
            session = ChatbotSession.objects.filter(id=session_id).first()
            if not session:
                return

            session.session_end = timezone.now()
            session.resolved = resolved
            if satisfaction_score:
                session.satisfaction_score = satisfaction_score

            session.save()
            logger.info(f"Ended session {session_id} (resolved={resolved})")

            # Update daily analytics
            if session.restaurant_id:
                self._update_session_analytics(session)

        except Exception as e:
            logger.error(f"Error ending session: {str(e)}")

    def get_recommendation_acceptance_rate(
        self,
        restaurant_id: int,
        days: int = 7,
    ) -> float:
        """
        Calculate recommendation acceptance rate.

        Args:
            restaurant_id: Restaurant ID
            days: Number of days to look back

        Returns:
            Acceptance rate (0-1)
        """
        try:
            cutoff_date = timezone.now() - timedelta(days=days)

            # Get shown and ordered counts
            interactions = RecommendationInteraction.objects.filter(
                restaurant_id=restaurant_id,
                created_at__gte=cutoff_date,
                interaction_type__in=['shown', 'ordered'],
            )

            shown_count = interactions.filter(interaction_type='shown').count()
            ordered_count = interactions.filter(interaction_type='ordered').count()

            if shown_count == 0:
                return 0.0

            return ordered_count / shown_count

        except Exception as e:
            logger.error(f"Error calculating acceptance rate: {str(e)}")
            return 0.0

    def get_popular_items(
        self,
        restaurant_id: int,
        days: int = 7,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get most recommended items by interaction count.

        Args:
            restaurant_id: Restaurant ID
            days: Number of days to look back
            limit: Maximum number of items to return

        Returns:
            List of popular items with stats
        """
        try:
            from apps.dishes.models import MenuItem

            cutoff_date = timezone.now() - timedelta(days=days)

            # Aggregate interactions by item
            items = MenuItem.objects.filter(
                recommendation_interactions__restaurant_id=restaurant_id,
                recommendation_interactions__created_at__gte=cutoff_date,
            ).annotate(
                interaction_count=Count('recommendation_interactions'),
                order_count=Count(
                    'recommendation_interactions',
                    filter=Q(recommendation_interactions__interaction_type='ordered'),
                ),
            ).order_by('-interaction_count')[:limit]

            results = []
            for item in items:
                results.append({
                    'id': item.id,
                    'name': item.name,
                    'interaction_count': item.interaction_count,
                    'order_count': item.order_count,
                    'acceptance_rate': (
                        item.order_count / item.interaction_count
                        if item.interaction_count > 0
                        else 0
                    ),
                })

            return results

        except Exception as e:
            logger.error(f"Error getting popular items: {str(e)}")
            return []

    def _learn_from_recommendation_feedback(self, feedback: ChatbotFeedback) -> None:
        """
        Learn from recommendation feedback to improve future suggestions.

        Args:
            feedback: Feedback object
        """
        try:
            if not feedback.user_id:
                return

            # Get accepted items
            accepted = list(feedback.accepted_items.all())
            if not accepted:
                return

            # Update user preferences based on accepted items
            from apps.chat.chatbot.context_manager import get_context_manager
            context_manager = get_context_manager()

            # Learn from categories
            categories = [item.category_id for item in accepted if item.category_id]
            if categories:
                # Add to favorite categories in context
                # (This would be persisted to user profile in a real system)
                pass

            # Learn from dietary attributes
            vegetarian_count = sum(1 for item in accepted if item.is_vegetarian)
            if vegetarian_count > len(accepted) / 2:
                # User prefers vegetarian
                context_manager.add_preference(
                    room_id=feedback.room_id,
                    user_id=feedback.user_id,
                    key='dietary_preference',
                    value='vegetarian',
                )

            # Learn from spice tolerance
            spicy_count = sum(1 for item in accepted if item.is_spicy)
            if spicy_count > len(accepted) / 2:
                context_manager.add_preference(
                    room_id=feedback.room_id,
                    user_id=feedback.user_id,
                    key='spice_tolerance',
                    value='high',
                )
            elif spicy_count == 0:
                context_manager.add_preference(
                    room_id=feedback.room_id,
                    user_id=feedback.user_id,
                    key='spice_tolerance',
                    value='low',
                )

            logger.info(f"Learned from feedback for user {feedback.user_id}")

        except Exception as e:
            logger.error(f"Error learning from feedback: {str(e)}")

    def _update_daily_analytics(
        self,
        restaurant_id: int,
        feedback_type: str,
        rating: int,
    ) -> None:
        """
        Update daily analytics metrics.

        Args:
            restaurant_id: Restaurant ID
            feedback_type: Type of feedback
            rating: Rating given
        """
        try:
            today = timezone.now().date()

            # Update satisfaction score
            metric, created = ChatbotAnalytics.objects.get_or_create(
                restaurant_id=restaurant_id,
                metric_type='user_satisfaction',
                date=today,
                defaults={'value': float(rating), 'count': 1},
            )

            if not created:
                # Update running average
                total_value = metric.value * metric.count + rating
                metric.count += 1
                metric.value = total_value / metric.count
                metric.save()

        except Exception as e:
            logger.error(f"Error updating analytics: {str(e)}")

    def _update_session_analytics(self, session: ChatbotSession) -> None:
        """
        Update analytics based on completed session.

        Args:
            session: Completed session
        """
        try:
            today = session.session_start.date()

            # Update escalation rate
            if session.escalated:
                metric, created = ChatbotAnalytics.objects.get_or_create(
                    restaurant_id=session.restaurant_id,
                    metric_type='escalation_rate',
                    date=today,
                    defaults={'value': 1.0, 'count': 1},
                )
                if not created:
                    metric.count += 1
                    metric.save()

            # Update satisfaction if provided
            if session.satisfaction_score:
                self._update_daily_analytics(
                    session.restaurant_id,
                    'response',
                    session.satisfaction_score,
                )

        except Exception as e:
            logger.error(f"Error updating session analytics: {str(e)}")

    def _update_interaction_cache(
        self,
        restaurant_id: int,
        menu_item_id: int,
        interaction_type: str,
    ) -> None:
        """
        Update interaction cache for real-time analytics.

        Args:
            restaurant_id: Restaurant ID
            menu_item_id: Menu item ID
            interaction_type: Type of interaction
        """
        try:
            cache_key = f'{self.CACHE_KEY_PREFIX}:interactions:{restaurant_id}:{menu_item_id}'

            # Get current counts
            counts = cache.get(cache_key, {})

            # Update count
            counts[interaction_type] = counts.get(interaction_type, 0) + 1

            # Save back to cache
            cache.set(cache_key, counts, timeout=self.CACHE_TTL)

        except Exception as e:
            logger.error(f"Error updating interaction cache: {str(e)}")


# Singleton instance
_feedback_service_instance = None


def get_feedback_service() -> FeedbackService:
    """
    Get or create the singleton FeedbackService instance.

    Returns:
        FeedbackService instance
    """
    global _feedback_service_instance
    if _feedback_service_instance is None:
        _feedback_service_instance = FeedbackService()
    return _feedback_service_instance
