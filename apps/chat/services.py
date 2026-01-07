"""
Business Logic Layer for Chatbot

This module contains service classes for chatbot operations,
following the existing service layer pattern in the codebase.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from apps.chat.chatbot.intent_classifier import get_intent_classifier, IntentResult
from apps.chat.chatbot.context_manager import get_context_manager, ConversationContext
from apps.chat.chatbot.response_generator import get_response_generator, GeneratedResponse
from apps.chat.chatbot.glm_client import GLMClientError
from apps.chat.chatbot.weather_service import get_weather_service
from apps.chat.selectors import ChatbotSelector

logger = logging.getLogger(__name__)


@dataclass
class ChatbotProcessResult:
    """
    Result of processing a chatbot message.

    Attributes:
        response_content: The bot's response text
        suggestions: Suggested dishes (if any)
        intent: Classified intent
        entities: Extracted entities
        is_escalated: Whether escalated to human
        confidence: Confidence score
        context: Updated conversation context
    """
    response_content: str
    suggestions: List[Dict[str, Any]]
    intent: str
    entities: Dict[str, Any]
    is_escalated: bool
    confidence: float
    context: ConversationContext


class ChatbotService:
    """
    Main service class for chatbot functionality.

    Orchestrates intent classification, context management,
    and response generation.
    """

    def __init__(self):
        """Initialize the chatbot service"""
        self.intent_classifier = get_intent_classifier()
        self.context_manager = get_context_manager()
        self.response_generator = get_response_generator()
        self.weather_service = get_weather_service()

    def process_message(
        self,
        user_message: str,
        room_id: int,
        user_id: int,
        restaurant_id: int,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> ChatbotProcessResult:
        """
        Process a user message and generate a chatbot response.

        Args:
            user_message: The user's message text
            room_id: Chat room ID
            user_id: User ID
            restaurant_id: Restaurant ID
            additional_context: Optional additional context (weather, location, etc.)

        Returns:
            ChatbotProcessResult with response and metadata
        """
        try:
            logger.info(f"Processing message for room {room_id}, user {user_id}")

            # Step 1: Get conversation context
            context = self.context_manager.get_context(room_id, user_id)
            context.restaurant_id = restaurant_id

            # Step 2: Get conversation history
            conversation_history = self.context_manager.get_conversation_history(room_id)

            # Step 3: Classify intent
            intent_result = self.intent_classifier.classify(user_message, conversation_history)

            logger.info(f"Intent classified as: {intent_result.intent} (confidence: {intent_result.confidence})")

            # Step 4: Check if should escalate
            should_escalate = self.intent_classifier.should_escalate(intent_result, user_message)

            if should_escalate:
                intent_result.intent = 'escalation'

            # Step 5: Update context with new information
            context = self.context_manager.update_context(
                room_id=room_id,
                user_id=user_id,
                intent=intent_result.intent,
                entities=intent_result.entities,
            )

            # Step 6: Build complete context data for response generation
            response_context = self._build_response_context(
                restaurant_id=restaurant_id,
                user_id=user_id,
                context=context,
                additional_context=additional_context or {},
                conversation_history=conversation_history,
            )

            # Step 7: Generate response
            response = self.response_generator.generate_response(
                user_message=user_message,
                intent=intent_result.intent,
                entities=intent_result.entities,
                restaurant_id=restaurant_id,
                conversation_history=conversation_history,
                context_data=response_context,
            )

            # Step 8: Update context with learned preferences
            if response.suggestions:
                # User got recommendations - track this
                self.context_manager.add_preference(
                    room_id=room_id,
                    user_id=user_id,
                    key='last_recommendation_time',
                    value=str(context.updated_at),
                )

            logger.info(f"Response generated successfully (method: {response.method}, escalated: {response.is_escalated})")

            return ChatbotProcessResult(
                response_content=response.content,
                suggestions=response.suggestions,
                intent=response.intent,
                entities=response.entities,
                is_escalated=response.is_escalated,
                confidence=response.confidence,
                context=context,
            )

        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            # Return fallback response
            return self._fallback_result(user_message, room_id, user_id, restaurant_id)

    def _build_response_context(
        self,
        restaurant_id: int,
        user_id: int,
        context: ConversationContext,
        additional_context: Dict[str, Any],
        conversation_history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Build complete context data for response generation.

        Args:
            restaurant_id: Restaurant ID
            user_id: User ID
            context: Conversation context
            additional_context: Additional context from request
            conversation_history: Conversation history

        Returns:
            Complete context dictionary
        """
        response_context = {
            'user_id': user_id,
            'restaurant_id': restaurant_id,
            'conversation_state': context.state,
            'last_intent': context.last_intent,
            'message_count': context.message_count,
        }

        # Add restaurant context
        restaurant_context = ChatbotSelector.get_restaurant_context(restaurant_id)
        if restaurant_context:
            response_context['restaurant'] = restaurant_context

        # Add menu context
        menu_summary = ChatbotSelector.get_menu_summary(restaurant_id)
        if menu_summary:
            response_context['menu_summary'] = menu_summary

        # Add user preferences
        user_preferences = ChatbotSelector.get_customer_preferences(user_id)
        if user_preferences:
            response_context['user_preferences'] = user_preferences

        # Add conversation context
        response_context['conversation_context'] = context.to_dict()

        # Fetch weather data if not provided in additional_context
        if additional_context and 'weather' in additional_context:
            # Use provided weather data
            response_context['weather'] = additional_context['weather']
        else:
            # Auto-fetch weather based on restaurant location
            if restaurant_context and restaurant_context.get('city'):
                weather_data = self._fetch_weather_for_restaurant(restaurant_context)
                if weather_data:
                    response_context['weather'] = weather_data
                    logger.info(f"Weather data fetched: {weather_data.get('temp')}°C, {weather_data.get('condition')}")

        # Add time-of-day context
        from datetime import datetime
        current_hour = datetime.now().hour
        response_context['time_of_day'] = self._get_time_period(current_hour)
        response_context['current_hour'] = current_hour

        # Add additional context (location, etc.)
        if additional_context:
            # Merge additional context, but don't override weather we just fetched
            for key, value in additional_context.items():
                if key not in response_context:
                    response_context[key] = value

        # Add conversation history
        if conversation_history:
            response_context['conversation_history'] = conversation_history

        return response_context

    def _fetch_weather_for_restaurant(self, restaurant_context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Fetch weather data for restaurant location.

        Args:
            restaurant_context: Restaurant data dictionary

        Returns:
            Weather data dictionary or None
        """
        try:
            city = restaurant_context.get('city', '')
            if not city:
                return None

            # Try to get weather by city
            weather_data = self.weather_service.get_weather_by_city(city)
            if weather_data:
                return weather_data

            # If city lookup fails, try coordinates
            latitude = restaurant_context.get('latitude')
            longitude = restaurant_context.get('longitude')
            if latitude and longitude:
                weather_data = self.weather_service.get_weather_by_coordinates(latitude, longitude)
                if weather_data:
                    return weather_data

            return None

        except Exception as e:
            logger.warning(f"Failed to fetch weather data: {str(e)}")
            return None

    def _get_time_period(self, hour: int) -> str:
        """
        Get time period from hour.

        Args:
            hour: Hour (0-23)

        Returns:
            Time period string
        """
        if 5 <= hour < 11:
            return 'morning'
        elif 11 <= hour < 14:
            return 'lunch'
        elif 14 <= hour < 17:
            return 'afternoon'
        elif 17 <= hour < 22:
            return 'dinner'
        else:
            return 'night'

    def _fallback_result(
        self,
        user_message: str,
        room_id: int,
        user_id: int,
        restaurant_id: int,
    ) -> ChatbotProcessResult:
        """
        Generate fallback result when processing fails.

        Args:
            user_message: User's message
            room_id: Chat room ID
            user_id: User ID
            restaurant_id: Restaurant ID

        Returns:
            ChatbotProcessResult with fallback response
        """
        context = self.context_manager.get_context(room_id, user_id)

        fallback_content = """I apologize, but I'm having trouble processing your request right now.

Please try:
• Rephrasing your question
• Asking about our menu, hours, or location
• Contacting our support team directly

I'm here to help with:
🍽️ Menu recommendations
⏰ Restaurant hours
📍 Location and delivery
📞 General inquiries

How else can I assist you?"""

        return ChatbotProcessResult(
            response_content=fallback_content,
            suggestions=[],
            intent='general',
            entities={},
            is_escalated=False,
            confidence=0.3,
            context=context,
        )

    def get_conversation_summary(
        self,
        room_id: int,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        Get a summary of the conversation.

        Args:
            room_id: Chat room ID
            user_id: User ID

        Returns:
            Conversation summary
        """
        return self.context_manager.get_context_summary(room_id, user_id)

    def clear_conversation_context(self, room_id: int, user_id: int) -> bool:
        """
        Clear conversation context for a room.

        Args:
            room_id: Chat room ID
            user_id: User ID

        Returns:
            True if successful
        """
        self.context_manager.clear_context(room_id)
        logger.info(f"Cleared conversation context for room {room_id}")
        return True

    def escalate_to_human(
        self,
        room_id: int,
        user_id: int,
        reason: str,
    ) -> bool:
        """
        Escalate conversation to human staff.

        Args:
            room_id: Chat room ID
            user_id: User ID
            reason: Reason for escalation

        Returns:
            True if successful
        """
        from apps.chat.models import ChatRoom

        try:
            # Update chat room status
            room = ChatRoom.objects.filter(id=room_id).first()
            if room:
                room.status = 'waiting'
                room.save()

                # Add system message about escalation
                from apps.chat.models import Message
                Message.objects.create(
                    room=room,
                    sender_id=user_id,  # System user
                    message_type='system',
                    content=f"Conversation escalated to human staff. Reason: {reason}",
                    is_bot_response=True,
                )

            logger.info(f"Escalated room {room_id} to human staff: {reason}")
            return True

        except Exception as e:
            logger.error(f"Error escalating conversation: {str(e)}")
            return False


# Singleton instance
_chatbot_service_instance = None


def get_chatbot_service() -> ChatbotService:
    """
    Get or create the singleton ChatbotService instance.

    Returns:
        ChatbotService instance
    """
    global _chatbot_service_instance
    if _chatbot_service_instance is None:
        _chatbot_service_instance = ChatbotService()
    return _chatbot_service_instance
