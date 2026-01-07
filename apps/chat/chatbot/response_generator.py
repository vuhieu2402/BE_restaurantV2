"""
Response Generator for Chatbot

This module generates responses to user messages using GLM and templates.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from apps.chat.chatbot.glm_client import get_glm_client, GLMClientError
from apps.chat.chatbot.prompts import ChatbotPrompts
from apps.chat.selectors import ChatbotSelector

logger = logging.getLogger(__name__)


@dataclass
class GeneratedResponse:
    """
    Result of response generation.

    Attributes:
        content: The response text
        suggestions: Suggested dishes (if applicable)
        intent: The classified intent
        entities: Extracted entities
        is_escalated: Whether this was escalated to human
        confidence: Confidence score
        method: How the response was generated (glm, template, fallback)
    """
    content: str
    suggestions: List[Dict[str, Any]]
    intent: str
    entities: Dict[str, Any]
    is_escalated: bool
    confidence: float
    method: str


class ResponseGenerator:
    """
    Generate chatbot responses using GLM and template-based approaches.

    Strategies:
    1. GLM-powered: For complex queries requiring understanding
    2. Template-based: For simple FAQs (faster, more predictable)
    3. Fallback: When GLM is unavailable
    """

    def __init__(self):
        """Initialize the response generator"""
        self.glm_client = get_glm_client()
        self.prompts = ChatbotPrompts()

    def generate_response(
        self,
        user_message: str,
        intent: str,
        entities: Dict[str, Any],
        restaurant_id: int,
        conversation_history: List[Dict[str, Any]],
        context_data: Dict[str, Any],
    ) -> GeneratedResponse:
        """
        Generate a response to the user's message.

        Args:
            user_message: User's message text
            intent: Classified intent
            entities: Extracted entities
            restaurant_id: Restaurant ID
            conversation_history: Previous messages
            context_data: Additional context (weather, user preferences, etc.)

        Returns:
            GeneratedResponse object
        """
        logger.info(f"Generating response for intent: {intent}")

        # Route to appropriate generation method
        if intent == 'escalation':
            return self._generate_escalation_response(intent, entities)

        elif intent == 'recommendation':
            return self._generate_recommendation_response(
                user_message, intent, entities, restaurant_id, context_data
            )

        elif intent.startswith('faq_'):
            # Try template-based first for FAQs (faster)
            return self._generate_faq_response(
                user_message, intent, entities, restaurant_id, context_data
            )

        elif intent in ['order_status', 'order_help']:
            return self._generate_order_response(
                user_message, intent, entities, restaurant_id, context_data
            )

        else:
            # General conversation - use GLM
            return self._generate_general_response(
                user_message, intent, entities, restaurant_id,
                conversation_history, context_data
            )

    def _generate_escalation_response(
        self,
        intent: str,
        entities: Dict[str, Any],
    ) -> GeneratedResponse:
        """Generate escalation response"""
        content = """I understand this requires personal attention. Let me connect you with a human staff member who can better assist you.

In the meantime, please note:
- Our team typically responds within 5-10 minutes
- You can also call us directly for urgent matters
- Your conversation history will be preserved

Thank you for your patience!"""

        return GeneratedResponse(
            content=content,
            suggestions=[],
            intent=intent,
            entities=entities,
            is_escalated=True,
            confidence=1.0,
            method='template',
        )

    def _generate_recommendation_response(
        self,
        user_message: str,
        intent: str,
        entities: Dict[str, Any],
        restaurant_id: int,
        context_data: Dict[str, Any],
    ) -> GeneratedResponse:
        """Generate recommendation response"""
        from apps.chat.chatbot.recommendation_engine import get_recommendation_engine

        # Get recommendations
        engine = get_recommendation_engine()

        # Extract parameters
        customer_id = context_data.get('user_id', 0)
        dietary = entities.get('dietary', [])
        spice = entities.get('spice_tolerance', context_data.get('spice_tolerance', 'medium'))
        max_price = entities.get('price', context_data.get('max_price'))
        meal_type = entities.get('meal_time', 'any')
        weather = context_data.get('weather')

        # Get number of recommendations
        num_recs = min(int(entities.get('quantity', 3)), 5)  # Max 5

        # Generate recommendations
        result = engine.generate_recommendations(
            restaurant_id=restaurant_id,
            customer_id=customer_id,
            num_recommendations=num_recs,
            dietary_preferences=dietary if dietary else None,
            spice_tolerance=spice,
            max_price=max_price,
            meal_type=meal_type,
            weather=weather,
            context_entities=entities,
        )

        if not result.dishes:
            # No recommendations found
            content = "I couldn't find dishes matching your criteria. Would you like me to:\n• Show you our popular items instead?\n• Remove some filters?\n• Suggest dishes from a specific category?"
            return GeneratedResponse(
                content=content,
                suggestions=[],
                intent=intent,
                entities=entities,
                is_escalated=False,
                confidence=0.6,
                method='template',
            )

        # Build response with suggestions
        suggestions = []
        for dish in result.dishes:
            suggestions.append({
                'item_id': dish['id'],
                'name': dish['name'],
                'price': f"{dish['price']:,.0f}",
                'reason': result.reasons[result.dishes.index(dish)],
            })

        # Build natural language response
        intro = self._get_recommendation_intro(context_data, weather)

        dishes_text = "\n\n".join([
            f"🍽️ **{dish['name']}** - {dish['price']} VND\n{suggestions[i]['reason']}"
            for i, dish in enumerate(result.dishes)
        ])

        content = f"""{intro}

{dishes_text}

Would you like more details about any of these dishes, or would you like different recommendations?"""

        return GeneratedResponse(
            content=content,
            suggestions=suggestions,
            intent=intent,
            entities=entities,
            is_escalated=False,
            confidence=result.confidence,
            method='recommendation_engine',
        )

    def _get_recommendation_intro(self, context_data: Dict[str, Any], weather: Optional[Dict]) -> str:
        """Get intro text for recommendations"""
        # Time-based intros
        time_of_day = context_data.get('time_of_day', '')
        current_hour = context_data.get('current_hour', 12)

        if time_of_day == 'morning':
            return "Good morning! Here are some great dishes to start your day:"
        elif time_of_day == 'lunch':
            return "Perfect for lunch! Here are some satisfying midday options:"
        elif time_of_day == 'afternoon':
            return "Good afternoon! Here are some dishes that would hit the spot:"
        elif time_of_day == 'dinner':
            return "Good evening! Here are some hearty dinner options for you:"
        elif time_of_day == 'night':
            return "It's getting late! Here are some lighter options for tonight:"

        # Weather-based intros
        intros = [
            "Based on your preferences, here are my top recommendations:",
            "I've found some great dishes for you:",
            "Here are some dishes I think you'll enjoy:",
        ]

        if weather:
            temp = weather.get('temp', 25)
            if temp < 15:
                intros.append("Since it's quite cold, here are some warming dishes:")
                return intros[-1]
            elif temp > 30:
                intros.append("Given the hot weather, here are some lighter options:")
                return intros[-1]

        return intros[0]  # Default intro

    def _generate_faq_response(
        self,
        user_message: str,
        intent: str,
        entities: Dict[str, Any],
        restaurant_id: int,
        context_data: Dict[str, Any],
    ) -> GeneratedResponse:
        """Generate FAQ response (template-based for speed)"""
        restaurant_context = ChatbotSelector.get_restaurant_context(restaurant_id)

        if not restaurant_context:
            return GeneratedResponse(
                content="I'm having trouble accessing restaurant information. Please try again later.",
                suggestions=[],
                intent=intent,
                entities=entities,
                is_escalated=False,
                confidence=0.3,
                method='fallback',
            )

        # Route to specific FAQ handler
        if intent == 'faq_hours':
            content = f"""📍 **{restaurant_context['name']}**

⏰ **Opening Hours:**
{restaurant_context['opening_time']} - {restaurant_context['closing_time']}

📊 **Current Status:** {'🟢 Open' if restaurant_context['is_open'] else '🔴 Closed'}

Is there anything else you'd like to know?"""

        elif intent == 'faq_location':
            content = f"""📍 **{restaurant_context['name']}**

🏠 **Address:**
{restaurant_context['address']}
{restaurant_context['district']}, {restaurant_context['city']}

📞 **Contact:** {restaurant_context['phone_number']}

⭐ **Rating:** {restaurant_context['rating']}/5 ({restaurant_context['total_reviews']} reviews)

Would you like directions or delivery information?"""

        elif intent == 'faq_delivery':
            content = f"""🚚 **Delivery Information**

📏 **Delivery Area:** {restaurant_context['delivery_radius']} km radius
💰 **Delivery Fee:** {restaurant_context['delivery_fee']:,.0f} VND
📦 **Minimum Order:** {restaurant_context['minimum_order']:,.0f} VND

We'll deliver right to your door! What would you like to order?"""

        elif intent == 'faq_contact':
            content = f"""📞 **Contact Us**

📱 **Phone:** {restaurant_context['phone_number']}
📧 **Email:** {restaurant_context['email'] or 'N/A'}

⭐ **Our Rating:** {restaurant_context['rating']}/5 based on {restaurant_context['total_reviews']} reviews

Feel free to reach out with any questions!"""

        elif intent == 'faq_menu':
            menu_summary = ChatbotSelector.get_menu_summary(restaurant_id)
            if menu_summary:
                categories = menu_summary.get('categories', [])[:6]
                content = f"""🍽️ **Our Menu**

**Categories:** {', '.join(categories)}

**Total Dishes:** {menu_summary.get('total_items', 0)} items available

Would you like recommendations from a specific category, or should I suggest our most popular dishes?"""
            else:
                content = "We have a variety of delicious dishes available! Would you like me to recommend some popular items?"

        else:
            content = "How can I help you today?"

        return GeneratedResponse(
            content=content,
            suggestions=[],
            intent=intent,
            entities=entities,
            is_escalated=False,
            confidence=0.9,
            method='template',
        )

    def _generate_order_response(
        self,
        user_message: str,
        intent: str,
        entities: Dict[str, Any],
        restaurant_id: int,
        context_data: Dict[str, Any],
    ) -> GeneratedResponse:
        """Generate order-related response"""
        if intent == 'order_status':
            # For order status, we'd need to look up the actual order
            order_id = entities.get('order_id')
            if order_id:
                content = f"""I'd be happy to help you check on order #{order_id}.

To get your order status, I can:
• Check the current status in our system
• Provide estimated delivery time
• Connect you with support if there are any issues

Would you like me to look that up for you?"""
            else:
                content = """I can help you check your order status! Could you please provide:
• Your order number, or
• The phone number used for the order

Once I have that information, I'll get you the latest updates."""

        elif intent == 'order_help':
            content = """I'm here to help with your order! I can assist with:

📋 **Placing an order:** Browse our menu and let me know what you'd like
✏️ **Modifying an order:** I can help if it hasn't been confirmed yet
❌ **Canceling an order:** I can explain the cancellation policy
❓ **Order issues:** I'll connect you with support for complex problems

What would you like help with?"""

        else:
            content = "How can I help you with your order today?"

        return GeneratedResponse(
            content=content,
            suggestions=[],
            intent=intent,
            entities=entities,
            is_escalated=False,
            confidence=0.8,
            method='template',
        )

    def _generate_general_response(
        self,
        user_message: str,
        intent: str,
        entities: Dict[str, Any],
        restaurant_id: int,
        conversation_history: List[Dict[str, Any]],
        context_data: Dict[str, Any],
    ) -> GeneratedResponse:
        """Generate general conversational response using GLM"""
        try:
            # Build system prompt with context
            system_prompt = ChatbotPrompts.build_context_prompt(context_data)

            # Add time-aware prompt addition
            current_hour = context_data.get('current_hour')
            if current_hour is not None:
                time_prompt = ChatbotPrompts.get_time_based_prompt(current_hour)
                system_prompt += f"\n\n{time_prompt}"

            # Add weather-aware prompt addition
            weather = context_data.get('weather')
            if weather:
                weather_prompt = ChatbotPrompts.get_weather_recommendation_prompt(weather)
                system_prompt += f"\n\n{weather_prompt}"

            # Call GLM
            response = self.glm_client.chat_with_context(
                user_message=user_message,
                conversation_history=conversation_history,
                system_prompt=system_prompt,
                context_data=context_data,
            )

            if response:
                return GeneratedResponse(
                    content=response,
                    suggestions=[],
                    intent=intent,
                    entities=entities,
                    is_escalated=False,
                    confidence=0.7,
                    method='glm',
                )
            else:
                # Fallback if GLM fails
                return self._generate_fallback_response(intent, entities)

        except GLMClientError as e:
            logger.error(f"GLM error in general response: {e}")
            return self._generate_fallback_response(intent, entities)

    def _generate_fallback_response(
        self,
        intent: str,
        entities: Dict[str, Any],
    ) -> GeneratedResponse:
        """Generate fallback response when GLM is unavailable"""
        fallback_messages = [
            "I'm here to help! You can ask me about our menu, restaurant hours, location, delivery, or I can suggest dishes you might enjoy.",
            "Hello! How can I assist you today? I can help with menu recommendations, restaurant information, delivery details, and more.",
            "Welcome! I'm your virtual assistant. Feel free to ask about our dishes, get recommendations, or learn about our restaurant.",
        ]

        import random
        content = random.choice(fallback_messages)

        return GeneratedResponse(
            content=content,
            suggestions=[],
            intent=intent,
            entities=entities,
            is_escalated=False,
            confidence=0.5,
            method='fallback',
        )


# Singleton instance
_response_generator_instance = None


def get_response_generator() -> ResponseGenerator:
    """
    Get or create the singleton ResponseGenerator instance.

    Returns:
        ResponseGenerator instance
    """
    global _response_generator_instance
    if _response_generator_instance is None:
        _response_generator_instance = ResponseGenerator()
    return _response_generator_instance
