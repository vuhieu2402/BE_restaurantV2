"""
Escalation Service for Chatbot

This module handles detection of situations requiring human intervention
and manages the escalation process.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Q, Count, Avg
from django.conf import settings

from apps.chat.chatbot.feedback_service import get_feedback_service
from apps.chat.chatbot.context_manager import get_context_manager

logger = logging.getLogger(__name__)


class EscalationDetector:
    """
    Detect when conversations should be escalated to human staff.

    Escalation triggers:
    1. Low confidence classifications
    2. Repeat questions (user confusion)
    3. Negative feedback
    4. Frustration indicators
    5. Complex queries
    6. Long conversation without resolution
    """

    # Escalation triggers
    TRIGGERS = {
        'low_confidence': 0.4,  # Confidence threshold
        'repeat_questions': 3,  # Same question asked N times
        'negative_feedback': 2,  # N negative feedbacks
        'frustration_keywords': ['frustrated', 'annoying', 'terrible', 'worst', 'hate'],
        'max_messages': 15,  # Max messages without resolution
        'escalation_request': ['human', 'person', 'agent', 'speak to someone'],
    }

    def __init__(self):
        """Initialize the escalation detector"""
        self.feedback_service = get_feedback_service()
        self.context_manager = get_context_manager()

    def should_escalate(
        self,
        room_id: int,
        user_id: int,
        restaurant_id: int,
        message: str,
        intent: str,
        confidence: float,
        conversation_history: List[Dict[str, Any]],
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Determine if conversation should be escalated.

        Args:
            room_id: Chat room ID
            user_id: User ID
            restaurant_id: Restaurant ID
            message: Current user message
            intent: Classified intent
            confidence: Confidence score
            conversation_history: Recent conversation history

        Returns:
            Tuple of (should_escalate, reason, context_data)
        """
        escalation_reasons = []
        context_data = {}

        # Check 1: Low confidence
        if confidence < self.TRIGGERS['low_confidence']:
            escalation_reasons.append(f"Low confidence classification ({confidence:.2f})")
            context_data['low_confidence_count'] = self._count_low_confidence(room_id)

        # Check 2: Escalation request keywords
        message_lower = message.lower()
        for keyword in self.TRIGGERS['escalation_request']:
            if keyword in message_lower:
                escalation_reasons.append("User requested human assistance")
                return True, "User requested human", context_data

        # Check 3: Frustration indicators
        for keyword in self.TRIGGERS['frustration_keywords']:
            if keyword in message_lower:
                escalation_reasons.append("User frustration detected")
                context_data['frustration_keyword'] = keyword
                return True, "User frustrated", context_data

        # Check 4: Repeat questions
        repeat_count = self._count_repeat_questions(room_id, conversation_history)
        if repeat_count >= self.TRIGGERS['repeat_questions']:
            escalation_reasons.append(f"User asking repeat questions ({repeat_count} times)")
            context_data['repeat_count'] = repeat_count

        # Check 5: Too many messages without resolution
        message_count = len(conversation_history)
        if message_count >= self.TRIGGERS['max_messages']:
            escalation_reasons.append(f"Long conversation ({message_count} messages)")
            context_data['message_count'] = message_count

        # Check 6: Negative feedback in recent history
        negative_feedback_count = self._count_negative_feedback(room_id)
        if negative_feedback_count >= self.TRIGGERS['negative_feedback']:
            escalation_reasons.append(f"Multiple negative feedbacks ({negative_feedback_count})")
            context_data['negative_feedback_count'] = negative_feedback_count

        # Check 7: Complex/intent not handled
        if intent == 'general' and confidence < 0.6:
            escalation_reasons.append("Unable to understand user intent")
            context_data['unclassified_intent'] = True

        # Determine if should escalate
        should_escalate = len(escalation_reasons) >= 2  # Need 2+ reasons
        reason = "; ".join(escalation_reasons) if escalation_reasons else None

        if should_escalate:
            logger.info(f"Escalation triggered for room {room_id}: {reason}")

        return should_escalate, reason, context_data

    def _count_low_confidence(self, room_id: int) -> int:
        """Count recent low-confidence classifications"""
        try:
            context = self.context_manager.get_context(room_id, 0)
            # Check conversation history for low confidence
            count = 0
            for msg in context.conversation_history:
                # This would be tracked in the message metadata
                # For now, return 0
                pass
            return count
        except Exception:
            return 0

    def _count_repeat_questions(
        self,
        room_id: int,
        conversation_history: List[Dict[str, Any]],
    ) -> int:
        """Count how many times similar questions were asked"""
        try:
            if len(conversation_history) < 3:
                return 0

            # Get last few user messages
            user_messages = [
                msg.get('content', '').lower()
                for msg in conversation_history[-6:]
                if msg.get('role') == 'user'
            ]

            if len(user_messages) < 3:
                return 0

            # Check for similar messages
            # Simple approach: count exact duplicates
            # Better approach would use similarity scoring
            repeat_count = 0
            seen = set()

            for msg in user_messages:
                if msg in seen:
                    repeat_count += 1
                seen.add(msg)

            return repeat_count

        except Exception as e:
            logger.error(f"Error counting repeat questions: {str(e)}")
            return 0

    def _count_negative_feedback(self, room_id: int) -> int:
        """Count recent negative feedback"""
        try:
            from apps.chat.models_analytics import ChatbotFeedback

            cutoff_time = timezone.now() - timedelta(hours=1)

            count = ChatbotFeedback.objects.filter(
                room_id=room_id,
                created_at__gte=cutoff_time,
                rating__lte=2,  # Poor ratings
            ).count()

            return count

        except Exception as e:
            logger.error(f"Error counting negative feedback: {str(e)}")
            return 0


class EscalationService:
    """
    Manage escalation process from chatbot to human staff.

    Features:
    - Detect escalation needs
    - Notify staff
    - Preserve conversation context
    - Track escalation metrics
    """

    def __init__(self):
        """Initialize the escalation service"""
        self.detector = EscalationDetector()
        self.feedback_service = get_feedback_service()

    def check_and_escalate(
        self,
        room_id: int,
        user_id: int,
        restaurant_id: int,
        message: str,
        intent: str,
        confidence: float,
        conversation_history: List[Dict[str, Any]],
    ) -> bool:
        """
        Check if escalation is needed and process it.

        Args:
            room_id: Chat room ID
            user_id: User ID
            restaurant_id: Restaurant ID
            message: User message
            intent: Classified intent
            confidence: Confidence score
            conversation_history: Conversation history

        Returns:
            True if escalated, False otherwise
        """
        # Check if should escalate
        should_escalate, reason, context_data = self.detector.should_escalate(
            room_id=room_id,
            user_id=user_id,
            restaurant_id=restaurant_id,
            message=message,
            intent=intent,
            confidence=confidence,
            conversation_history=conversation_history,
        )

        if should_escalate:
            # Process escalation
            return self._escalate_conversation(
                room_id=room_id,
                user_id=user_id,
                restaurant_id=restaurant_id,
                reason=reason,
                context_data=context_data,
            )

        return False

    def _escalate_conversation(
        self,
        room_id: int,
        user_id: int,
        restaurant_id: int,
        reason: str,
        context_data: Dict[str, Any],
    ) -> bool:
        """
        Escalate conversation to human staff.

        Args:
            room_id: Chat room ID
            user_id: User ID
            restaurant_id: Restaurant ID
            reason: Reason for escalation
            context_data: Additional context

        Returns:
            True if successful
        """
        try:
            from apps.chat.models import ChatRoom, Message

            # Update room status
            room = ChatRoom.objects.filter(id=room_id).first()
            if not room:
                logger.error(f"Room {room_id} not found for escalation")
                return False

            # Update room to waiting for human
            room.status = 'waiting'
            room.save()

            # Add system message about escalation
            Message.objects.create(
                room=room,
                sender_id=user_id,
                message_type='system',
                content=f"Conversation escalated to human staff. Reason: {reason}",
                is_bot_response=True,
            )

            # Log escalation
            logger.info(
                f"Escalated room {room_id} to human staff. "
                f"Reason: {reason}, Context: {context_data}"
            )

            # Track escalation in feedback service
            # (In a real system, this would send notifications to staff)

            return True

        except Exception as e:
            logger.error(f"Error escalating conversation: {str(e)}")
            return False

    def get_escalation_stats(
        self,
        restaurant_id: int,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        Get escalation statistics for a restaurant.

        Args:
            restaurant_id: Restaurant ID
            days: Number of days to look back

        Returns:
            Statistics dictionary
        """
        try:
            from apps.chat.models import ChatRoom
            from apps.chat.models_analytics import ChatbotSession
            from django.db.models import Count, Q

            cutoff_date = timezone.now() - timedelta(days=days)

            # Get escalated sessions
            escalated_sessions = ChatbotSession.objects.filter(
                restaurant_id=restaurant_id,
                session_start__gte=cutoff_date,
                escalated=True,
            )

            # Total sessions
            total_sessions = ChatbotSession.objects.filter(
                restaurant_id=restaurant_id,
                session_start__gte=cutoff_date,
            ).count()

            # Calculate escalation rate
            escalation_count = escalated_sessions.count()
            escalation_rate = (
                escalation_count / total_sessions
                if total_sessions > 0
                else 0
            )

            # Average resolution time (calculate in Python to avoid SQL issues)
            resolved_sessions = escalated_sessions.filter(resolved=True)
            avg_resolution_time = None

            if resolved_sessions.exists():
                total_seconds = 0
                count = 0
                for session in resolved_sessions:
                    if session.session_end and session.session_start:
                        delta = session.session_end - session.session_start
                        total_seconds += delta.total_seconds()
                        count += 1
                if count > 0:
                    from datetime import timedelta
                    avg_resolution_time = timedelta(seconds=total_seconds / count)

            # Common reasons
            # (This would be tracked in the session metadata)

            return {
                'escalation_count': escalation_count,
                'total_sessions': total_sessions,
                'escalation_rate': escalation_rate,
                'avg_resolution_time_minutes': (
                    avg_resolution_time.total_seconds() / 60
                    if avg_resolution_time
                    else None
                ),
                'resolved_count': resolved_sessions.count(),
                'unresolved_count': escalated_sessions.filter(resolved=False).count(),
            }

        except Exception as e:
            logger.error(f"Error getting escalation stats: {str(e)}")
            return {}


# Singleton instance
_escalation_service_instance = None


def get_escalation_service() -> EscalationService:
    """
    Get or create the singleton EscalationService instance.

    Returns:
        EscalationService instance
    """
    global _escalation_service_instance
    if _escalation_service_instance is None:
        _escalation_service_instance = EscalationService()
    return _escalation_service_instance
