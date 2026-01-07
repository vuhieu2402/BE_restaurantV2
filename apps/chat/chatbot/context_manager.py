"""
Context Manager for Chatbot Conversations

This module manages conversation context using Redis for short-term storage
and database for long-term history. Includes sliding window conversation
tracking and entity persistence.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class ConversationContext:
    """
    Data class for conversation context with sliding window history.
    """

    def __init__(
        self,
        room_id: int,
        user_id: int,
        restaurant_id: Optional[int] = None,
    ):
        self.room_id = room_id
        self.user_id = user_id
        self.restaurant_id = restaurant_id
        self.state = 'greeting'  # greeting, browsing, ordering, escalation
        self.last_intent = None
        self.entities = {}  # Persistent entities across conversation
        self.preferences = {}  # Learned preferences
        self.message_count = 0
        self.conversation_history = []  # Sliding window of recent messages
        self.max_history_size = 15  # Maximum messages in sliding window
        self.created_at = timezone.now()
        self.updated_at = timezone.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'room_id': self.room_id,
            'user_id': self.user_id,
            'restaurant_id': self.restaurant_id,
            'state': self.state,
            'last_intent': self.last_intent,
            'entities': self.entities,
            'preferences': self.preferences,
            'message_count': self.message_count,
            'conversation_history': self.conversation_history,
            'max_history_size': self.max_history_size,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        """Create from dictionary"""
        context = cls(
            room_id=data['room_id'],
            user_id=data['user_id'],
            restaurant_id=data.get('restaurant_id'),
        )
        context.state = data.get('state', 'greeting')
        context.last_intent = data.get('last_intent')
        context.entities = data.get('entities', {})
        context.preferences = data.get('preferences', {})
        context.message_count = data.get('message_count', 0)
        context.conversation_history = data.get('conversation_history', [])
        context.max_history_size = data.get('max_history_size', 15)
        if data.get('created_at'):
            context.created_at = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            context.updated_at = datetime.fromisoformat(data['updated_at'])
        return context

    def add_to_history(self, role: str, content: str, intent: Optional[str] = None):
        """
        Add a message to the conversation history (sliding window).

        Args:
            role: 'user' or 'assistant'
            content: Message content
            intent: Optional intent for the message
        """
        message_entry = {
            'role': role,
            'content': content,
            'timestamp': timezone.now().isoformat(),
        }

        if intent:
            message_entry['intent'] = intent

        # Add to history
        self.conversation_history.append(message_entry)

        # Maintain sliding window - remove oldest if exceeds max size
        if len(self.conversation_history) > self.max_history_size:
            # Remove oldest message
            removed = self.conversation_history.pop(0)
            logger.debug(f"Removed old message from history: {removed.get('content', '')[:30]}...")

    def get_recent_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get recent conversation history.

        Args:
            limit: Maximum number of messages to return

        Returns:
            list: Recent messages
        """
        history = self.conversation_history
        if limit:
            return history[-limit:]  # Get last N messages
        return history

    def get_full_history_text(self) -> str:
        """
        Get conversation history as formatted text for GLM prompt.

        Returns:
            str: Formatted conversation history
        """
        if not self.conversation_history:
            return "New conversation"

        lines = []
        for msg in self.conversation_history:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            intent = f" ({msg.get('intent', '')})" if msg.get('intent') else ""
            lines.append(f"{role.upper()}: {content}{intent}")

        return "\n".join(lines)


class ContextManager:
    """
    Manage conversation context for chatbot interactions.

    Uses Redis for fast access to recent context (short-term memory)
    and database for persistent history (long-term memory).
    """

    CACHE_KEY_PREFIX = 'chatbot:context'
    CACHE_TTL = 86400  # 24 hours

    MAX_HISTORY_MESSAGES = 10  # Number of messages to keep in context

    def __init__(self):
        """Initialize the context manager"""
        pass

    def get_context(self, room_id: int, user_id: int) -> ConversationContext:
        """
        Get conversation context for a room.

        Args:
            room_id: Chat room ID
            user_id: User ID

        Returns:
            ConversationContext object
        """
        cache_key = f'{self.CACHE_KEY_PREFIX}:{room_id}'

        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.debug(f"Context cache hit for room {room_id}")
            return ConversationContext.from_dict(cached_data)

        # Create new context
        logger.debug(f"Creating new context for room {room_id}")
        context = ConversationContext(room_id=room_id, user_id=user_id)
        self.save_context(context)

        return context

    def save_context(self, context: ConversationContext):
        """
        Save conversation context to cache.

        Args:
            context: ConversationContext to save
        """
        cache_key = f'{self.CACHE_KEY_PREFIX}:{context.room_id}'
        context.updated_at = timezone.now()

        cache.set(cache_key, context.to_dict(), timeout=self.CACHE_TTL)
        logger.debug(f"Saved context for room {context.room_id}")

    def update_context(
        self,
        room_id: int,
        user_id: int,
        intent: str,
        entities: Dict[str, Any],
        message_count: Optional[int] = None,
        user_message: Optional[str] = None,
        bot_response: Optional[str] = None,
    ) -> ConversationContext:
        """
        Update conversation context with new information and sliding window history.

        Args:
            room_id: Chat room ID
            user_id: User ID
            intent: Classified intent
            entities: Extracted entities
            message_count: Optional message count
            user_message: Optional user message text
            bot_response: Optional bot response text

        Returns:
            Updated ConversationContext
        """
        context = self.get_context(room_id, user_id)

        # Update basic fields
        context.last_intent = intent
        context.message_count = message_count or (context.message_count + 1)

        # Add to sliding window history
        if user_message:
            context.add_to_history('user', user_message, intent=None)

        if bot_response:
            context.add_to_history('assistant', bot_response, intent=intent)

        # Merge entities (persistent entities survive across messages)
        for key, value in entities.items():
            if value is not None and value != '':
                # Special handling for lists - append instead of replace
                if key.endswith('[]') and isinstance(value, list):
                    list_key = key[:-2]
                    if list_key not in context.entities:
                        context.entities[list_key] = []
                    # Add to list if not already present
                    for item in value:
                        if item not in context.entities[list_key]:
                            context.entities[list_key].append(item)
                else:
                    context.entities[key] = value

        # Update state based on intent
        context.state = self._determine_new_state(intent, context)

        # Save and return
        self.save_context(context)
        return context

    def _determine_new_state(self, intent: str, context: ConversationContext) -> str:
        """
        Determine conversation state based on intent.

        Args:
            intent: Classified intent
            context: Current context

        Returns:
            New state string
        """
        state_transitions = {
            'greeting': ['general', 'greeting'],
            'browsing': ['faq_menu', 'faq_hours', 'faq_location', 'faq_contact', 'faq_delivery'],
            'ordering': ['order_help', 'order_status'],
            'escalation': ['escalation'],
        }

        for state, intents in state_transitions.items():
            if intent in intents:
                return state

        # Special case: recommendation depends on context
        if intent == 'recommendation':
            if context.state in ['greeting', 'browsing']:
                return 'browsing'
            else:
                return context.state

        # Default: keep current state
        return context.state

    def add_preference(self, room_id: int, user_id: int, key: str, value: Any):
        """
        Add or update a learned preference.

        Args:
            room_id: Chat room ID
            user_id: User ID
            key: Preference key (e.g., 'spice_tolerance', 'favorite_category')
            value: Preference value
        """
        context = self.get_context(room_id, user_id)
        context.preferences[key] = value
        self.save_context(context)
        logger.debug(f"Added preference {key}={value} for room {room_id}")

    def get_preferences(self, room_id: int, user_id: int) -> Dict[str, Any]:
        """
        Get learned preferences for a conversation.

        Args:
            room_id: Chat room ID
            user_id: User ID

        Returns:
            Dictionary of preferences
        """
        context = self.get_context(room_id, user_id)
        return context.preferences

    def get_conversation_history(
        self,
        room_id: int,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history from database.

        Args:
            room_id: Chat room ID
            limit: Maximum number of messages (default: MAX_HISTORY_MESSAGES)

        Returns:
            List of message dictionaries
        """
        from apps.chat.selectors import ChatbotSelector

        limit = limit or self.MAX_HISTORY_MESSAGES
        return ChatbotSelector.get_conversation_history(room_id, limit=limit)

    def clear_context(self, room_id: int):
        """
        Clear conversation context for a room.

        Args:
            room_id: Chat room ID
        """
        cache_key = f'{self.CACHE_KEY_PREFIX}:{room_id}'
        cache.delete(cache_key)
        logger.info(f"Cleared context for room {room_id}")

    def get_context_summary(self, room_id: int, user_id: int) -> Dict[str, Any]:
        """
        Get a summary of the conversation context.

        Args:
            room_id: Chat room ID
            user_id: User ID

        Returns:
            Dictionary with context summary
        """
        context = self.get_context(room_id, user_id)
        history = self.get_conversation_history(room_id)

        return {
            'room_id': context.room_id,
            'user_id': context.user_id,
            'restaurant_id': context.restaurant_id,
            'state': context.state,
            'last_intent': context.last_intent,
            'message_count': context.message_count,
            'entities': context.entities,
            'preferences': context.preferences,
            'conversation_age_minutes': (timezone.now() - context.created_at).total_seconds() / 60,
            'recent_messages_count': len(history),
        }

    def format_context_for_prompt(self, context: ConversationContext) -> str:
        """
        Format conversation context for inclusion in GLM prompt.

        Args:
            context: ConversationContext object

        Returns:
            Formatted context string
        """
        parts = []

        if context.state:
            parts.append(f"Conversation State: {context.state}")

        if context.last_intent:
            parts.append(f"Last Intent: {context.last_intent}")

        if context.message_count > 0:
            parts.append(f"Message Count: {context.message_count}")

        if context.entities:
            entities_str = ', '.join([f"{k}={v}" for k, v in context.entities.items() if v])
            if entities_str:
                parts.append(f"Remembered Information: {entities_str}")

        if context.preferences:
            prefs_str = ', '.join([f"{k}={v}" for k, v in context.preferences.items() if v])
            if prefs_str:
                parts.append(f"Learned Preferences: {prefs_str}")

        return '\n'.join(parts) if parts else "New conversation"

    def is_conversation_stale(self, room_id: int, user_id: int, stale_minutes: int = 30) -> bool:
        """
        Check if a conversation has gone stale (no recent activity).

        Args:
            room_id: Chat room ID
            user_id: User ID
            stale_minutes: Minutes before considering conversation stale

        Returns:
            True if stale, False otherwise
        """
        cache_key = f'{self.CACHE_KEY_PREFIX}:{room_id}'
        cached_data = cache.get(cache_key)

        if not cached_data:
            return True  # No context = stale

        context = ConversationContext.from_dict(cached_data)
        age_minutes = (timezone.now() - context.updated_at).total_seconds() / 60

        return age_minutes > stale_minutes

    def merge_entities(
        self,
        room_id: int,
        user_id: int,
        new_entities: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge new entities with existing context entities.

        Args:
            room_id: Chat room ID
            user_id: User ID
            new_entities: New entities to merge

        Returns:
            Merged entities dictionary
        """
        context = self.get_context(room_id, user_id)

        # Merge strategy: new entities override old ones
        for key, value in new_entities.items():
            if value is not None and value != '':
                # Special handling for lists (append instead of replace)
                if key.endswith('[]') and isinstance(value, list):
                    list_key = key[:-2]
                    if list_key not in context.entities:
                        context.entities[list_key] = []
                    context.entities[list_key].extend(value)
                    # Remove duplicates
                    context.entities[list_key] = list(set(context.entities[list_key]))
                else:
                    context.entities[key] = value

        self.save_context(context)
        return context.entities.copy()


# Singleton instance
_context_manager_instance = None


def get_context_manager() -> ContextManager:
    """
    Get or create the singleton ContextManager instance.

    Returns:
        ContextManager instance
    """
    global _context_manager_instance
    if _context_manager_instance is None:
        _context_manager_instance = ContextManager()
    return _context_manager_instance
