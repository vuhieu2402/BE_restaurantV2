"""
Groq API Client for AI Model Integration

This module handles all communication with Groq API,
which provides ultra-fast AI inference using LPU (Language Processing Unit) technology.
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from decouple import config

# Groq client for ultra-fast inference
from groq import Groq, APIError, APIConnectionError, RateLimitError

logger = logging.getLogger(__name__)


@dataclass
class GLMMessage:
    """Data class for messages (legacy name for compatibility)"""
    role: str
    content: str


class GLMClientError(Exception):
    """Custom exception for AI client errors"""
    pass


class GLMClient:
    """
    Client for interacting with Groq API.

    Uses Groq's ultra-fast LPU technology for blazing fast inference.
    Supports multiple free models including Llama 3.3 70B.
    """

    def __init__(self):
        """Initialize Groq client with configuration from environment variables"""
        self.api_key = config('GROQ_API_KEY', default='')
        self.model = config('GROQ_MODEL', default='llama-3.3-70b-versatile')
        self.base_url = config(
            'GROQ_API_URL',
            default='https://api.groq.com/openai/v1'
        )
        self.max_tokens = config('GROQ_MAX_TOKENS', default=2000, cast=int)
        self.temperature = config('GROQ_TEMPERATURE', default=0.7, cast=float)
        self.timeout = config('GROQ_TIMEOUT', default=30, cast=int)

        if not self.api_key or self.api_key == 'your_groq_api_key_here':
            logger.warning("GROQ_API_KEY not configured. Chatbot will use fallback mode.")

        # Initialize Groq client
        try:
            self.client = Groq(
                api_key=self.api_key,
                timeout=self.timeout,
            )
            logger.info(f"Groq client initialized with model: {self.model}")
        except Exception as e:
            logger.error(f"Failed to initialize Groq client: {str(e)}")
            self.client = None

    def _validate_client(self) -> bool:
        """Validate that the client is properly initialized"""
        if not self.client or not self.api_key or self.api_key == 'your_groq_api_key_here':
            logger.error("Groq client is not initialized or API key is missing")
            return False
        return True

    def _filter_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Filter messages to only include valid fields for Groq API.

        Groq API only supports standard OpenAI message fields:
        - role: 'system', 'user', 'assistant'
        - content: Message content (string)
        - name: Optional name for the message sender
        - function_call: Optional function call data

        Args:
            messages: List of message dictionaries

        Returns:
            Filtered list of messages with only valid fields
        """
        valid_messages = []
        valid_fields = {'role', 'content', 'name', 'function_call'}

        for msg in messages:
            if not isinstance(msg, dict):
                logger.warning(f"Skipping invalid message (not a dict): {msg}")
                continue

            # Only keep valid fields
            filtered_msg = {k: v for k, v in msg.items() if k in valid_fields}

            # Ensure required fields exist
            if 'role' not in filtered_msg:
                logger.warning(f"Skipping message without 'role': {msg}")
                continue

            if 'content' not in filtered_msg:
                logger.warning(f"Skipping message without 'content': {msg}")
                continue

            valid_messages.append(filtered_msg)

        logger.debug(f"Filtered {len(messages)} messages to {len(valid_messages)} valid messages")
        return valid_messages

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        retry_attempts: int = 3,
    ) -> Optional[str]:
        """
        Send a chat completion request to Groq API.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            system_prompt: Optional system prompt to override default
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            retry_attempts: Number of retry attempts on failure (default: 3)

        Returns:
            str: The generated response text, or None if failed

        Raises:
            GLMClientError: If all retry attempts fail
        """
        if not self._validate_client():
            raise GLMClientError("Groq client is not properly initialized")

        # Filter messages to only include valid fields for Groq API
        valid_messages = self._filter_messages(messages)

        # Prepare messages with system prompt
        prepared_messages = []
        if system_prompt:
            prepared_messages.append({"role": "system", "content": system_prompt})
        prepared_messages.extend(valid_messages)

        # Prepare request parameters
        request_params = {
            "model": self.model,
            "messages": prepared_messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }

        # Retry logic
        last_error = None
        for attempt in range(retry_attempts):
            try:
                logger.debug(f"Sending request to Groq API (attempt {attempt + 1}/{retry_attempts})")

                response = self.client.chat.completions.create(**request_params)

                if response and response.choices:
                    result = response.choices[0].message.content
                    logger.debug(f"Received response from Groq API: {len(result)} chars")
                    return result
                else:
                    logger.error("Groq API returned empty response")
                    last_error = "Empty response from API"

            except RateLimitError as e:
                logger.warning(f"Groq API rate limit exceeded: {str(e)}")
                last_error = str(e)
                # Don't retry rate limit errors immediately
                if attempt < retry_attempts - 1:
                    import time
                    time.sleep(2 ** attempt)  # Exponential backoff

            except APIConnectionError as e:
                logger.warning(f"Groq API connection error: {str(e)}")
                last_error = str(e)
                if attempt < retry_attempts - 1:
                    import time
                    time.sleep(1)  # Brief pause before retry

            except APIError as e:
                logger.error(f"Groq API error: {str(e)}")
                last_error = str(e)
                # Don't retry API errors (they're likely request-related)
                break

            except Exception as e:
                logger.error(f"Unexpected error calling Groq API: {str(e)}")
                last_error = str(e)
                if attempt < retry_attempts - 1:
                    import time
                    time.sleep(1)

        # All retries failed
        raise GLMClientError(f"Failed to get response from Groq API after {retry_attempts} attempts: {last_error}")

    def chat_with_context(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        system_prompt: str,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Send a chat request with conversation context and additional data.

        Args:
            user_message: Current user message
            conversation_history: List of previous messages
            system_prompt: System prompt with role and instructions
            context_data: Optional additional context (restaurant info, menu, etc.)

        Returns:
            str: Generated response
        """
        # Build messages list
        messages = []

        # Add conversation history
        messages.extend(conversation_history)

        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })

        # Inject context into system prompt if provided
        enhanced_system_prompt = system_prompt
        if context_data:
            context_str = self._format_context(context_data)
            enhanced_system_prompt = f"{system_prompt}\n\nContext Information:\n{context_str}"

        # Call the chat API
        return self.chat(
            messages=messages,
            system_prompt=enhanced_system_prompt,
        )

    def _format_context(self, context_data: Dict[str, Any]) -> str:
        """
        Format context data into a readable string for the prompt.

        Args:
            context_data: Dictionary with context information

        Returns:
            str: Formatted context string
        """
        context_parts = []

        if 'restaurant' in context_data:
            restaurant = context_data['restaurant']
            context_parts.append(f"Restaurant: {restaurant.get('name', 'N/A')}")
            context_parts.append(f"Hours: {restaurant.get('opening_time', 'N/A')} - {restaurant.get('closing_time', 'N/A')}")
            context_parts.append(f"Address: {restaurant.get('address', 'N/A')}")
            context_parts.append(f"Phone: {restaurant.get('phone_number', 'N/A')}")
            context_parts.append(f"Rating: {restaurant.get('rating', 'N/A')}/5")

        if 'menu_summary' in context_data:
            menu = context_data['menu_summary']
            context_parts.append(f"\nAvailable Categories: {', '.join(menu.get('categories', []))}")
            if 'featured_items' in menu:
                featured = menu['featured_items'][:5]  # Limit to top 5
                context_parts.append("Featured Dishes:")
                for item in featured:
                    context_parts.append(f"  - {item.get('name', 'N/A')} ({item.get('price', 'N/A')} VND)")

        if 'user_preferences' in context_data:
            prefs = context_data['user_preferences']
            context_parts.append(f"\nCustomer Preferences:")
            if prefs.get('dietary_restrictions'):
                context_parts.append(f"  - Dietary: {', '.join(prefs['dietary_restrictions'])}")
            if prefs.get('favorite_categories'):
                context_parts.append(f"  - Favorite Categories: {', '.join(prefs['favorite_categories'])}")
            if prefs.get('average_order_value'):
                context_parts.append(f"  - Avg Order: {prefs['average_order_value']} VND")

        if 'weather' in context_data:
            weather = context_data['weather']
            context_parts.append(f"\nCurrent Weather: {weather.get('temp', 'N/A')}°C, {weather.get('condition', 'N/A')}")

        return '\n'.join(context_parts)

    def test_connection(self) -> bool:
        """
        Test the connection to Groq API.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            response = self.chat(
                messages=[{"role": "user", "content": "Hello"}],
                system_prompt="You are a helpful assistant.",
                retry_attempts=1,
            )
            return response is not None
        except Exception as e:
            logger.error(f"Groq API connection test failed: {str(e)}")
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model configuration.

        Returns:
            dict: Model information
        """
        return {
            "model": self.model,
            "api_url": self.base_url,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout": self.timeout,
            "is_configured": bool(self.api_key) and self.api_key != 'your_groq_api_key_here',
        }


# Singleton instance for reuse
_glm_client_instance = None


def get_glm_client() -> GLMClient:
    """
    Get or create the singleton client instance.

    Returns:
        GLMClient: The client instance
    """
    global _glm_client_instance
    if _glm_client_instance is None:
        _glm_client_instance = GLMClient()
    return _glm_client_instance
