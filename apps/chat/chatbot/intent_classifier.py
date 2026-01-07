"""
Intent Classifier for Chatbot

This module uses GLM to classify user intents and extract entities from messages.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import re

from apps.chat.chatbot.glm_client import get_glm_client, GLMClientError

logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    """
    Result of intent classification.

    Attributes:
        intent: The classified intent (e.g., 'faq_hours', 'recommendation', 'order_status')
        confidence: Confidence score (0.0 to 1.0)
        entities: Extracted entities (dish names, prices, etc.)
        raw_response: Raw response from GLM for debugging
    """
    intent: str
    confidence: float
    entities: Dict[str, Any]
    raw_response: Optional[str] = None


class IntentClassifier:
    """
    Classify user messages into intents and extract entities using GLM.

    Supported intents:
    - faq_hours: Questions about opening/closing hours
    - faq_location: Questions about address/location
    - faq_delivery: Questions about delivery
    - faq_contact: Questions about contact info
    - faq_menu: Questions about menu items
    - recommendation: Request for dish recommendations
    - order_status: Check order status
    - order_help: Help with ordering
    - general: General conversation
    - escalation: Requires human assistance
    """

    # Intents that don't need GLM (rule-based)
    RULE_BASED_INTENTS = {
        'escalation': ['complaint', 'refund', 'sue', 'lawyer', 'police', 'scam'],
    }

    INTENT_DESCRIPTIONS = """
    Supported intents:
    - faq_hours: Questions about restaurant hours, when open/close, time
    - faq_location: Questions about address, location, where is it
    - faq_delivery: Questions about delivery, shipping, delivery fee/radius
    - faq_contact: Questions about phone, email, contact
    - faq_menu: Questions about menu, food, dishes, categories
    - recommendation: Requests for suggestions, recommendations, what to eat
    - order_status: Checking order status, where is my order
    - order_help: Help with placing/modifying/canceling orders
    - general: General chat, greetings, unclear requests
    - escalation: Urgent issues requiring human staff
    """

    def __init__(self):
        """Initialize the intent classifier"""
        self.glm_client = get_glm_client()

    def classify(self, message: str, conversation_history: Optional[List[Dict]] = None) -> IntentResult:
        """
        Classify the intent of a user message.

        Args:
            message: User's message text
            conversation_history: Optional list of previous messages for context

        Returns:
            IntentResult with classified intent, confidence, and entities
        """
        # Check for escalation keywords first
        escalation_intent = self._check_escalation(message)
        if escalation_intent:
            return escalation_intent

        # Use GLM for intent classification
        return self._classify_with_glm(message, conversation_history)

    def _check_escalation(self, message: str) -> Optional[IntentResult]:
        """
        Check if message contains escalation keywords.

        Args:
            message: User's message

        Returns:
            IntentResult if escalation detected, None otherwise
        """
        message_lower = message.lower()

        for keyword in self.RULE_BASED_INTENTS['escalation']:
            if keyword in message_lower:
                logger.info(f"Escalation keyword detected: {keyword}")
                return IntentResult(
                    intent='escalation',
                    confidence=1.0,
                    entities={'keyword': keyword, 'reason': 'escalation_keyword'},
                )

        return None

    def _classify_with_glm(
        self,
        message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> IntentResult:
        """
        Use GLM to classify intent and extract entities.

        Args:
            message: User's message
            conversation_history: Previous messages for context

        Returns:
            IntentResult with classification
        """
        system_prompt = f"""You are an intent classifier for a restaurant chatbot. Your job is to:

1. Classify the user's message into ONE of these intents:
{self.INTENT_DESCRIPTIONS}

2. Extract relevant entities from the message:
   - dish_name: Name of a dish/food item mentioned
   - price: Price mentioned (as number, in VND)
   - quantity: Quantity mentioned (as number)
   - dietary: Dietary restrictions (vegetarian, vegan, gluten-free, no_spicy, etc.)
   - spice_tolerance: none, low, medium, high
   - meal_time: breakfast, lunch, dinner, snack, any
   - time_period: morning, afternoon, evening, night
   - order_id: Order number if mentioned
   - max_price: Maximum price budget
   - min_price: Minimum price budget

3. Return your response in this exact JSON format:
{{
    "intent": "intent_name",
    "confidence": 0.95,
    "entities": {{
        "dish_name": "example dish",
        "dietary": ["vegetarian"],
        "spice_tolerance": "medium",
        "meal_time": "lunch",
        "max_price": 150000,
        "reasoning": "brief explanation"
    }}
}}

Rules:
- intent must be one of the supported intents listed above
- confidence must be between 0.0 and 1.0
- entities should only contain information actually mentioned in the message
- dietary should be an array of dietary restrictions
- spice_tolerance values: none, low, medium, high
- meal_time values: breakfast, lunch, dinner, snack, any
- if an entity is not mentioned, don't include it or set to null
- reasoning should be brief (max 20 words)
- respond ONLY with valid JSON, no additional text
"""

        try:
            # Build conversation context
            messages = []
            if conversation_history:
                # Add last few messages for context (max 5)
                recent_history = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
                for msg in recent_history:
                    messages.append({
                        'role': msg.get('role', 'user'),
                        'content': msg.get('content', '')
                    })

            # Add current message
            messages.append({
                'role': 'user',
                'content': f"Classify this message: {message}"
            })

            # Call GLM
            response = self.glm_client.chat(
                messages=messages,
                system_prompt=system_prompt,
                temperature=0.3,  # Lower temperature for more deterministic classification
                max_tokens=500,
                retry_attempts=2,
            )

            if not response:
                logger.warning("Empty response from GLM for intent classification")
                return self._fallback_classification(message)

            # Parse JSON response
            import json
            try:
                # Extract JSON from response (in case there's extra text)
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                else:
                    result = json.loads(response)

                # Validate result
                intent = result.get('intent', 'general')
                confidence = float(result.get('confidence', 0.5))
                entities = result.get('entities', {})

                logger.info(f"Classified message as '{intent}' with confidence {confidence}")
                return IntentResult(
                    intent=intent,
                    confidence=confidence,
                    entities=entities,
                    raw_response=response,
                )

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse GLM response as JSON: {e}")
                logger.debug(f"Response was: {response}")
                return self._fallback_classification(message)

        except GLMClientError as e:
            logger.error(f"GLM API error during intent classification: {e}")
            return self._fallback_classification(message)
        except Exception as e:
            logger.error(f"Unexpected error during intent classification: {e}")
            return self._fallback_classification(message)

    def _fallback_classification(self, message: str) -> IntentResult:
        """
        Fallback rule-based classification when GLM fails.

        Args:
            message: User's message

        Returns:
            IntentResult with best-guess classification
        """
        message_lower = message.lower()
        entities = {'method': 'rule_based_fallback'}

        # Extract meal time
        if any(word in message_lower for word in ['breakfast', 'morning', 'early']):
            entities['meal_time'] = 'breakfast'
        elif any(word in message_lower for word in ['lunch', 'noon', 'midday']):
            entities['meal_time'] = 'lunch'
        elif any(word in message_lower for word in ['dinner', 'evening', 'night']):
            entities['meal_time'] = 'dinner'
        elif any(word in message_lower for word in ['snack', 'afternoon']):
            entities['meal_time'] = 'snack'

        # Extract dietary preferences
        dietary = []
        if 'vegetarian' in message_lower or 'veggie' in message_lower:
            dietary.append('vegetarian')
        if 'vegan' in message_lower:
            dietary.append('vegan')
        if 'gluten' in message_lower or 'gluten-free' in message_lower:
            dietary.append('gluten-free')
        if 'no spicy' in message_lower or 'not spicy' in message_lower:
            dietary.append('no_spicy')
            entities['spice_tolerance'] = 'none'
        elif 'very spicy' in message_lower or 'extremely spicy' in message_lower:
            entities['spice_tolerance'] = 'high'

        if dietary:
            entities['dietary'] = dietary

        # Extract price range
        price_range = self.extract_price_range(message)
        if price_range:
            entities.update(price_range)

        # Rule-based classification
        if any(word in message_lower for word in ['hour', 'open', 'close', 'time', 'when']):
            return IntentResult(
                intent='faq_hours',
                confidence=0.7,
                entities=entities
            )
        elif any(word in message_lower for word in ['where', 'address', 'location', 'located', 'find']):
            return IntentResult(
                intent='faq_location',
                confidence=0.7,
                entities=entities
            )
        elif any(word in message_lower for word in ['delivery', 'deliver', 'ship']):
            return IntentResult(
                intent='faq_delivery',
                confidence=0.7,
                entities=entities
            )
        elif any(word in message_lower for word in ['phone', 'call', 'contact', 'email']):
            return IntentResult(
                intent='faq_contact',
                confidence=0.7,
                entities=entities
            )
        elif any(word in message_lower for word in ['menu', 'food', 'eat', 'dish']):
            return IntentResult(
                intent='faq_menu',
                confidence=0.7,
                entities=entities
            )
        elif any(word in message_lower for word in ['recommend', 'suggest', 'best', 'good', 'popular']):
            return IntentResult(
                intent='recommendation',
                confidence=0.7,
                entities=entities
            )
        elif any(word in message_lower for word in ['order', 'status', 'where']):
            return IntentResult(
                intent='order_status',
                confidence=0.6,
                entities=entities
            )
        else:
            return IntentResult(
                intent='general',
                confidence=0.5,
                entities=entities
            )

    def extract_dish_names(self, message: str, menu_items: List[Dict[str, Any]]) -> List[str]:
        """
        Extract dish names mentioned in the message.

        Args:
            message: User's message
            menu_items: List of available menu items

        Returns:
            List of dish names found in the message
        """
        message_lower = message.lower()
        found_dishes = []

        for item in menu_items:
            dish_name = item.get('name', '').lower()
            if dish_name and dish_name in message_lower:
                found_dishes.append(item['name'])

        return found_dishes

    def extract_price_range(self, message: str) -> Optional[Dict[str, float]]:
        """
        Extract price range from message.

        Args:
            message: User's message

        Returns:
            Dict with 'min' and 'max' prices, or None
        """
        # Look for price patterns like "under 100k", "between 50k and 100k"
        price_pattern = r'(\d+)\s*[kK]'

        matches = re.findall(price_pattern, message.lower())
        if matches:
            prices = [int(m) * 1000 for m in matches]  # Convert 'k' to actual value

            if len(prices) == 1:
                # Could be "under 100k" or "around 100k"
                if any(word in message.lower() for word in ['under', 'less', 'below', 'cheap']):
                    return {'max': prices[0]}
                elif any(word in message.lower() for word in ['over', 'above', 'more', 'expensive']):
                    return {'min': prices[0]}
                else:
                    # Assume around this price (±20%)
                    return {'min': prices[0] * 0.8, 'max': prices[0] * 1.2}
            elif len(prices) >= 2:
                return {'min': min(prices), 'max': max(prices)}

        return None

    def should_escalate(self, intent_result: IntentResult, message: str) -> bool:
        """
        Determine if a message should be escalated to human staff.

        Args:
            intent_result: Result of intent classification
            message: Original user message

        Returns:
            True if should escalate, False otherwise
        """
        # Already classified as escalation
        if intent_result.intent == 'escalation':
            return True

        # Low confidence classification
        if intent_result.confidence < 0.5:
            logger.info(f"Low confidence ({intent_result.confidence}), may need human review")
            return False  # Don't auto-escalate, but flag for review

        # Check for frustration indicators
        frustration_words = ['frustrated', 'annoying', 'terrible', 'horrible', 'worst']
        if any(word in message.lower() for word in frustration_words):
            return True

        return False


# Singleton instance
_intent_classifier_instance = None


def get_intent_classifier() -> IntentClassifier:
    """
    Get or create the singleton IntentClassifier instance.

    Returns:
        IntentClassifier instance
    """
    global _intent_classifier_instance
    if _intent_classifier_instance is None:
        _intent_classifier_instance = IntentClassifier()
    return _intent_classifier_instance
