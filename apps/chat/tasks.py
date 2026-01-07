"""
Celery Tasks for Chatbot Async Processing

This module contains Celery tasks for asynchronous chatbot operations,
including GLM API calls and response generation.
"""

import logging
from celery import shared_task
from typing import Dict, Any, Optional

from apps.chat.services import get_chatbot_service, ChatbotProcessResult
from apps.chat.models import ChatRoom, Message

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    queue='chatbot',
    max_retries=3,
    default_retry_delay=60,
)
def generate_chatbot_response(
    self,
    room_id: int,
    user_message_id: int,
    user_id: int,
    restaurant_id: int,
    user_message: str,
    additional_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Async task to generate chatbot response.

    This task handles the CPU-intensive work of:
    - Intent classification
    - Context management
    - GLM API calls
    - Response generation

    Args:
        self: Celery task instance
        room_id: Chat room ID
        user_message_id: ID of the user's message
        user_id: User ID
        restaurant_id: Restaurant ID
        user_message: The user's message text
        additional_context: Optional additional context (weather, etc.)

    Returns:
        dict: Result containing response data

    Raises:
        Exception: If processing fails after retries
    """
    try:
        logger.info(
            f"Generating chatbot response for room {room_id}, "
            f"user_message {user_message_id}"
        )

        # Get chatbot service
        chatbot_service = get_chatbot_service()

        # Process the message
        result = chatbot_service.process_message(
            user_message=user_message,
            room_id=room_id,
            user_id=user_id,
            restaurant_id=restaurant_id,
            additional_context=additional_context,
        )

        # Save bot response to database
        try:
            room = ChatRoom.objects.get(id=room_id)

            # Create bot message
            bot_message = Message.objects.create(
                room=room,
                sender_id=user_id,  # Bot messages use system user
                message_type='text',
                content=result.response_content,
                is_bot_response=True,
                intent=result.intent,
                entities=result.entities,
                confidence_score=result.confidence,
            )

            # Update room's last message time
            room.last_message_at = bot_message.created_at
            room.save()

            logger.info(
                f"Bot response saved: message_id={bot_message.id}, "
                f"intent={result.intent}"
            )

            # Return result for potential further processing
            return {
                'success': True,
                'room_id': room_id,
                'user_message_id': user_message_id,
                'bot_message_id': bot_message.id,
                'intent': result.intent,
                'is_escalated': result.is_escalated,
                'suggestions': result.suggestions,
            }

        except ChatRoom.DoesNotExist:
            logger.error(f"Chat room {room_id} not found")
            raise
        except Exception as e:
            logger.error(f"Error saving bot response: {str(e)}")
            raise

    except Exception as e:
        logger.error(
            f"Error in generate_chatbot_response task: {str(e)}",
            exc_info=True
        )

        # Retry if possible
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e)

        # Final failure - create fallback response
        logger.error("Task failed after all retries, creating fallback response")
        return _create_fallback_response(
            room_id=room_id,
            user_id=user_id,
            error_message=str(e),
        )


@shared_task(
    queue='chatbot',
)
def update_user_preferences_from_conversation(
    room_id: int,
    user_id: int,
) -> Dict[str, Any]:
    """
    Async task to analyze conversation and update user preferences.

    This task runs after a conversation ends to extract insights
    about user preferences based on their interactions.

    Args:
        room_id: Chat room ID
        user_id: User ID

    Returns:
        dict: Updated preferences
    """
    try:
        from apps.chat.selectors import ChatbotSelector
        from apps.chat.chatbot.context_manager import get_context_manager

        logger.info(f"Analyzing conversation for room {room_id}")

        # Get conversation context
        context_manager = get_context_manager()
        context = context_manager.get_context(room_id, user_id)

        # Get conversation history
        history = context_manager.get_conversation_history(room_id, limit=50)

        # Extract preferences
        learned_preferences = _extract_preferences_from_history(history)

        # Merge with existing preferences in context
        for key, value in learned_preferences.items():
            context_manager.add_preference(room_id, user_id, key, value)

        logger.info(f"Updated preferences: {learned_preferences}")

        return {
            'success': True,
            'room_id': room_id,
            'preferences': learned_preferences,
        }

    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        return {
            'success': False,
            'error': str(e),
        }


@shared_task(
    queue='chatbot',
)
def cleanup_old_conversation_context(
    days_old: int = 7,
) -> Dict[str, Any]:
    """
    Scheduled task to clean up old conversation contexts from Redis cache.

    Args:
        days_old: Remove contexts older than this many days

    Returns:
        dict: Cleanup results
    """
    try:
        from apps.chat.chatbot.context_manager import get_context_manager
        from apps.chat.models import ChatRoom
        from django.utils import timezone
        from datetime import timedelta

        logger.info(f"Starting cleanup of contexts older than {days_old} days")

        # Find rooms that haven't been updated recently
        cutoff_date = timezone.now() - timedelta(days=days_old)
        old_rooms = ChatRoom.objects.filter(
            last_message_at__lt=cutoff_date,
            status='closed'
        ).values_list('id', flat=True)

        cleaned_count = 0
        for room_id in old_rooms:
            context_manager = get_context_manager()
            context_manager.clear_context(room_id)
            cleaned_count += 1

        logger.info(f"Cleaned up {cleaned_count} old contexts")

        return {
            'success': True,
            'cleaned_count': cleaned_count,
            'days_old': days_old,
        }

    except Exception as e:
        logger.error(f"Error in cleanup task: {str(e)}")
        return {
            'success': False,
            'error': str(e),
        }


@shared_task(
    queue='chatbot',
)
def send_proactive_recommendations(
    user_id: int,
    restaurant_id: int,
) -> Dict[str, Any]:
    """
    Send proactive recommendations to a user based on their preferences.

    This could be triggered periodically for users who haven't ordered recently.

    Args:
        user_id: User ID
        restaurant_id: Restaurant ID

    Returns:
        dict: Recommendation results
    """
    try:
        from apps.chat.models import ChatRoom, Message
        from apps.chat.chatbot.recommendation_engine import get_recommendation_engine
        from apps.users.models import User

        logger.info(f"Sending proactive recommendations to user {user_id}")

        # Get or create chat room
        user = User.objects.get(id=user_id)
        room, created = ChatRoom.objects.get_or_create(
            customer=user,
            room_type='general',
            defaults={'status': 'active'}
        )

        # Generate recommendations
        engine = get_recommendation_engine()
        result = engine.generate_recommendations(
            restaurant_id=restaurant_id,
            customer_id=user_id,
            num_recommendations=3,
        )

        if result.dishes:
            # Format recommendations
            dishes_text = "\n".join([
                f"• {dish['name']} - {dish['price']:,.0f} VND"
                for dish in result.dishes
            ])

            message = f"""Hi! We thought you might like these dishes:

{dishes_text}

Would you like to place an order?"""

            # Send message
            Message.objects.create(
                room=room,
                sender_id=user_id,  # Bot
                message_type='text',
                content=message,
                is_bot_response=True,
                intent='recommendation',
            )

            return {
                'success': True,
                'room_id': room.id,
                'recommendations': len(result.dishes),
            }
        else:
            return {
                'success': False,
                'reason': 'No recommendations generated',
            }

    except Exception as e:
        logger.error(f"Error sending proactive recommendations: {str(e)}")
        return {
            'success': False,
            'error': str(e),
        }


def _create_fallback_response(
    room_id: int,
    user_id: int,
    error_message: str,
) -> Dict[str, Any]:
    """
    Create a fallback response when task fails.

    Args:
        room_id: Chat room ID
        user_id: User ID
        error_message: Error message

    Returns:
        dict: Fallback response data
    """
    try:
        room = ChatRoom.objects.get(id=room_id)

        fallback_content = """I apologize, but I'm experiencing technical difficulties right now.

Our team has been notified and is working to resolve this.

In the meantime, you can:
• Browse our menu directly
• Call our restaurant
• Try again in a moment

Thank you for your patience!"""

        bot_message = Message.objects.create(
            room=room,
            sender_id=user_id,
            message_type='text',
            content=fallback_content,
            is_bot_response=True,
            intent='error',
            entities={'error': error_message},
            confidence_score=0.0,
        )

        return {
            'success': False,
            'room_id': room_id,
            'bot_message_id': bot_message.id,
            'fallback': True,
            'error': error_message,
        }

    except Exception as e:
        logger.error(f"Error creating fallback response: {str(e)}")
        return {
            'success': False,
            'error': f"Critical failure: {str(e)}",
        }


def _extract_preferences_from_history(history: list) -> Dict[str, Any]:
    """
    Extract user preferences from conversation history.

    Args:
        history: List of message dictionaries

    Returns:
        dict: Extracted preferences
    """
    preferences = {}

    # Simple extraction based on message content
    # In production, you might use more sophisticated NLP
    for msg in history:
        if msg.get('role') == 'user':
            content = msg.get('content', '').lower()

            # Check for spice preference
            if 'not spicy' in content or 'mild' in content:
                preferences['spice_tolerance'] = 'low'
            elif 'very spicy' in content or 'extra spicy' in content:
                preferences['spice_tolerance'] = 'high'

            # Check for dietary preferences
            if 'vegetarian' in content:
                if 'dietary' not in preferences:
                    preferences['dietary'] = []
                if 'vegetarian' not in preferences['dietary']:
                    preferences['dietary'].append('vegetarian')

    return preferences
