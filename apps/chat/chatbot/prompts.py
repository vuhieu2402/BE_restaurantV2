"""
Prompt Templates for GLM Chatbot

This module contains all prompt templates used by the chatbot,
including system prompts, FAQ responses, and recommendation templates.
"""

from typing import Dict, Any, List


class ChatbotPrompts:
    """Collection of prompt templates for the restaurant chatbot"""

    # Base System Prompt
    SYSTEM_PROMPT = """You are a helpful and friendly restaurant assistant for an online food delivery system. Your role is to assist customers with:

1. Answering questions about restaurant information (hours, location, contact details)
2. Providing menu information and dish descriptions
3. Making personalized dish recommendations based on preferences
4. Helping with order-related inquiries
5. Assisting with reservation questions

Guidelines for your responses:
- Be friendly, professional, and helpful
- Provide concise but informative answers
- Use natural, conversational language
- If you don't know something, be honest and offer to connect the customer with a human staff member
- When recommending dishes, explain WHY you're recommending them
- Consider the customer's preferences, current weather, and time of day
- Prices should be mentioned in VND (Vietnamese Dong)

Remember: You're representing the restaurant, so maintain a positive and helpful attitude at all times."""

    # FAQ-specific prompts
    FAQ_RESTAURANT_INFO = """When answering questions about restaurant information, use the provided context data.
Include:
- Restaurant name and address
- Operating hours
- Phone number and email
- Rating and reviews
- Delivery radius and fees

Format your response in a friendly, easy-to-read manner."""

    FAQ_MENU_INFO = """When providing menu information:
- Organize by categories
- Highlight popular or featured items
- Include prices in VND
- Mention dietary attributes (vegetarian, spicy, etc.)
- Note preparation times for items that take longer
- Describe dishes briefly but appetizingly

If the customer asks about specific dishes, provide detailed information including:
- Full description
- Price
- Key attributes (spicy level, vegetarian status, calories)
- Customer rating if available"""

    FAQ_DELIVERY_INFO = """When answering delivery-related questions:
- Explain delivery radius and coverage area
- Mention delivery fees
- Provide estimated delivery times
- Note any minimum order requirements
- Explain delivery process briefly"""

    # Recommendation prompts
    RECOMMENDATION_SYSTEM_PROMPT = """You are a restaurant recommendation specialist. Your goal is to suggest dishes that customers will love based on:

1. Customer Preferences:
   - Past order history
   - Dietary restrictions (vegetarian, allergies, spice tolerance)
   - Favorite categories
   - Price range preferences

2. Contextual Factors:
   - Current weather (hot soup on cold days, salads on hot days)
   - Time of day (breakfast, lunch, dinner, late night)
   - Meal type preferences

3. Dish Quality:
   - Customer ratings and reviews
   - Popularity and order frequency
   - Featured items

When making recommendations:
- Suggest 2-4 dishes maximum
- Explain WHY each dish is recommended
- Personalize your reasoning based on what you know about the customer
- Consider variety (don't suggest 4 similar dishes)
- Include prices and key attributes
- Ask follow-up questions to refine recommendations if needed

Format each recommendation as:
🍽️ **[Dish Name]** - [Price] VND
[Why you're recommending it]
[Key attributes: vegetarian/spicy/calories/etc.]"""

    # Order assistance prompts
    ORDER_HELP_SYSTEM_PROMPT = """You are an ordering assistant. Help customers with:
- Checking order status
- Explaining the ordering process
- Modifying orders (if possible)
- Canceling orders (explain the policy)
- Understanding delivery tracking

For order status inquiries, use the provided order context to give accurate information.
For order modifications, explain what's possible and what's not, and offer to connect with staff if needed."""

    # General conversation prompts
    GENERAL_SYSTEM_PROMPT = """You are a conversational restaurant assistant. Engage naturally with customers while:
- Maintaining a friendly and professional tone
- Being helpful but not overly formal
- Keeping responses concise and to the point
- Recognizing when to escalate to human staff
- Keeping track of conversation context

If a customer asks something outside your capabilities:
- Acknowledge their question
- Explain what you can and cannot do
- Offer to connect them with a human staff member who can better assist"""

    # Escalation prompts
    ESCALATION_PROMPT = """The following query requires human assistance. Please acknowledge the customer's request
and let them know you're connecting them with a staff member who can better help them.

Common reasons for escalation:
- Complex complaints or issues
- Requests outside your capabilities
- Urgent or sensitive matters
- When the customer explicitly asks to speak with a human"""

    @staticmethod
    def build_context_prompt(context_data: Dict[str, Any]) -> str:
        """
        Build a context-aware system prompt with injected data.

        Args:
            context_data: Dictionary containing restaurant, menu, user, and weather data

        Returns:
            str: Complete system prompt with context
        """
        base_prompt = ChatbotPrompts.SYSTEM_PROMPT

        context_sections = []

        # Add restaurant context
        if 'restaurant' in context_data:
            restaurant = context_data['restaurant']
            context_sections.append(f"""
You are representing: {restaurant.get('name', 'our restaurant')}

Restaurant Details:
- Address: {restaurant.get('address', 'N/A')}
- Hours: {restaurant.get('opening_time', 'N/A')} - {restaurant.get('closing_time', 'N/A')}
- Phone: {restaurant.get('phone_number', 'N/A')}
- Rating: {restaurant.get('rating', 'N/A')}/5 ({restaurant.get('total_reviews', 0)} reviews)
- Delivery: {restaurant.get('delivery_radius', 'N/A')} km radius, {restaurant.get('delivery_fee', 'N/A')} VND fee
""")

        # Add menu context
        if 'menu_summary' in context_data:
            menu = context_data['menu_summary']
            categories = menu.get('categories', [])
            featured = menu.get('featured_items', [])[:5]

            context_sections.append(f"""
Menu Information:
- Categories: {', '.join(categories) if categories else 'Various'}
- Featured Items: {', '.join([item.get('name', 'N/A') for item in featured])}
""")

        # Add user preference context
        if 'user_preferences' in context_data:
            prefs = context_data['user_preferences']
            context_sections.append(f"""
Customer Profile:
- Dietary: {', '.join(prefs.get('dietary_restrictions', ['None']))}
- Favorite Categories: {', '.join(prefs.get('favorite_categories', ['Various']))}
- Average Order: {prefs.get('average_order_value', 'N/A')} VND
- Previous Orders: {prefs.get('total_orders', 0)} orders
""")

        # Add weather context
        if 'weather' in context_data:
            weather = context_data['weather']
            context_sections.append(f"""
Current Conditions: {weather.get('temp', 'N/A')}°C, {weather.get('condition', 'N/A')}
Consider this when making recommendations (e.g., warm food on cold days, light meals on hot days).
""")

        # Combine all sections
        if context_sections:
            return base_prompt + "\n\n" + "\n".join(context_sections)
        return base_prompt

    @staticmethod
    def format_recommendation(dish: Dict[str, Any], reason: str) -> str:
        """
        Format a single dish recommendation.

        Args:
            dish: Dictionary containing dish information
            reason: Reason for recommending this dish

        Returns:
            str: Formatted recommendation
        """
        name = dish.get('name', 'Unknown Dish')
        price = dish.get('price', 0)
        rating = dish.get('rating', 0)
        description = dish.get('description', '')
        is_vegetarian = dish.get('is_vegetarian', False)
        is_spicy = dish.get('is_spicy', False)
        calories = dish.get('calories', None)

        attributes = []
        if is_vegetarian:
            attributes.append('🥬 Vegetarian')
        if is_spicy:
            attributes.append('🌶️ Spicy')
        if calories:
            attributes.append(f'🔥 {calories} cal')
        if rating:
            attributes.append(f'⭐ {rating}/5')

        attributes_str = ' | '.join(attributes) if attributes else ''

        return f"""🍽️ **{name}** - {price:,.0f} VND
{reason}
{description if description else ''}
{attributes_str}"""

    @staticmethod
    def format_multiple_recommendations(dishes: List[Dict[str, Any]], reasons: List[str]) -> str:
        """
        Format multiple dish recommendations.

        Args:
            dishes: List of dish dictionaries
            reasons: List of reasons for each recommendation

        Returns:
            str: Formatted recommendations
        """
        if len(dishes) != len(reasons):
            raise ValueError("Number of dishes must match number of reasons")

        recommendations = []
        for dish, reason in zip(dishes, reasons):
            recommendations.append(ChatbotPrompts.format_recommendation(dish, reason))

        return "\n\n".join(recommendations)

    @staticmethod
    def get_weather_recommendation_prompt(weather: Dict[str, Any]) -> str:
        """
        Get weather-aware recommendation prompt.

        Args:
            weather: Dictionary with temperature and condition

        Returns:
            str: Weather-specific prompt
        """
        temp = weather.get('temp', 25)
        condition = weather.get('condition', 'clear').lower()

        if temp < 15:
            return "It's quite cold today. Consider recommending warm, hearty dishes like soups, stews, and hot meals."
        elif temp > 30:
            return "It's very hot today. Suggest light, refreshing dishes, salads, cold drinks, and items that aren't too heavy or spicy."
        elif 'rain' in condition or 'drizzle' in condition:
            return "It's rainy today. Comfort food and warm dishes would be especially appealing."
        elif condition == 'clear' and temp >= 20 and temp <= 28:
            return "The weather is pleasant. Any menu items would be good, but you might highlight refreshing options or outdoor dining if available."
        else:
            return "Consider the current weather when making recommendations to enhance the dining experience."

    @staticmethod
    def get_time_based_prompt(hour: int) -> str:
        """
        Get time-of-day specific prompt.

        Args:
            hour: Current hour (0-23)

        Returns:
            str: Time-specific prompt
        """
        if 5 <= hour < 11:
            return "Good morning! Feel free to suggest breakfast items or lighter options for the start of the day."
        elif 11 <= hour < 14:
            return "It's lunch time! Recommend satisfying but not overly heavy meals suitable for a midday break."
        elif 14 <= hour < 17:
            return "It's afternoon. Suggest lighter fare, snacks, or early dinner options."
        elif 17 <= hour < 22:
            return "Good evening! This is dinner time - recommend hearty, satisfying meals."
        else:
            return "It's late at night. Suggest lighter options that won't disrupt sleep, and mention if the restaurant is about to close."


# Helper functions for common prompt building
def build_faq_response(question_type: str, context: Dict[str, Any]) -> str:
    """
    Build a FAQ response based on question type.

    Args:
        question_type: Type of FAQ (restaurant, menu, delivery, etc.)
        context: Context data for the response

    Returns:
        str: Formatted FAQ response
    """
    prompts = {
        'restaurant': ChatbotPrompts.FAQ_RESTAURANT_INFO,
        'menu': ChatbotPrompts.FAQ_MENU_INFO,
        'delivery': ChatbotPrompts.FAQ_DELIVERY_INFO,
    }

    base_prompt = prompts.get(question_type, ChatbotPrompts.SYSTEM_PROMPT)

    # Add context
    if question_type == 'restaurant' and 'restaurant' in context:
        restaurant = context['restaurant']
        return f"""{base_prompt}

Restaurant: {restaurant.get('name', 'N/A')}
Address: {restaurant.get('address', 'N/A')}
Hours: {restaurant.get('opening_time', 'N/A')} - {restaurant.get('closing_time', 'N/A')}
Phone: {restaurant.get('phone_number', 'N/A')}
Rating: {restaurant.get('rating', 'N/A')}/5"""

    elif question_type == 'delivery' and 'restaurant' in context:
        restaurant = context['restaurant']
        return f"""{base_prompt}

Delivery Area: {restaurant.get('delivery_radius', 'N/A')} km
Delivery Fee: {restaurant.get('delivery_fee', 'N/A')} VND
Minimum Order: {restaurant.get('minimum_order', 'N/A')} VND"""

    return base_prompt
