"""
Weather Service for Chatbot

This module integrates with OpenWeatherMap API to provide weather data
for weather-aware dish recommendations.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from decouple import config
import requests

logger = logging.getLogger(__name__)


class WeatherService:
    """
    Service for fetching weather data from OpenWeatherMap API.

    Provides current weather conditions for specific locations
    to enable weather-aware dish recommendations.
    """

    def __init__(self):
        """Initialize the weather service"""
        self.api_key = config('WEATHER_API_KEY', default='')
        self.base_url = config(
            'WEATHER_API_URL',
            default='https://api.openweathermap.org/data/2.5/weather'
        )
        self.cache_timeout = config('WEATHER_CACHE_TTL', default=3600, cast=int)  # 1 hour

        if not self.api_key:
            logger.warning("WEATHER_API_KEY not configured. Weather features will be disabled.")

    def get_weather_by_city(
        self,
        city: str,
        country_code: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Get current weather for a city.

        Args:
            city: City name (e.g., "Hanoi", "Ho Chi Minh City")
            country_code: Optional country code (e.g., "VN", "US")

        Returns:
            dict: Weather data or None if failed
        """
        if not self.api_key:
            logger.warning("Weather API key not configured")
            return None

        try:
            # Build query
            query = city
            if country_code:
                query = f"{city},{country_code}"

            # Make API request
            params = {
                'q': query,
                'appid': self.api_key,
                'units': 'metric',  # Celsius
            }

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Parse response
            weather_data = {
                'city': data.get('name', city),
                'country': data.get('sys', {}).get('country', ''),
                'temp': data.get('main', {}).get('temp', 25),
                'feels_like': data.get('main', {}).get('feels_like', 25),
                'humidity': data.get('main', {}).get('humidity', 60),
                'pressure': data.get('main', {}).get('pressure', 1013),
                'temp_min': data.get('main', {}).get('temp_min', 25),
                'temp_max': data.get('main', {}).get('temp_max', 25),
                'description': data.get('weather', [{}])[0].get('description', ''),
                'condition': data.get('weather', [{}])[0].get('main', 'clear'),
                'wind_speed': data.get('wind', {}).get('speed', 0),
                'clouds': data.get('clouds', {}).get('all', 0),
                'latitude': data.get('coord', {}).get('lat'),
                'longitude': data.get('coord', {}).get('lon'),
                'timestamp': datetime.now().isoformat(),
            }

            logger.info(
                f"Weather fetched for {query}: "
                f"{weather_data['temp']}°C, {weather_data['description']}"
            )

            return weather_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching weather data: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_weather_by_city: {str(e)}")
            return None

    def get_weather_by_coordinates(
        self,
        latitude: float,
        longitude: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Get current weather for specific coordinates.

        Args:
            latitude: Latitude
            longitude: Longitude

        Returns:
            dict: Weather data or None if failed
        """
        if not self.api_key:
            return None

        try:
            # Make API request
            params = {
                'lat': latitude,
                'lon': longitude,
                'appid': self.api_key,
                'units': 'metric',
            }

            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Parse response
            weather_data = {
                'city': data.get('name', 'Unknown'),
                'temp': data.get('main', {}).get('temp', 25),
                'feels_like': data.get('main', {}).get('feels_like', 25),
                'humidity': data.get('main', {}).get('humidity', 60),
                'description': data.get('weather', [{}])[0].get('description', ''),
                'condition': data.get('weather', [{}])[0].get('main', 'clear'),
                'timestamp': datetime.now().isoformat(),
            }

            logger.info(
                f"Weather fetched for coordinates ({latitude}, {longitude}): "
                f"{weather_data['temp']}°C"
            )

            return weather_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching weather by coordinates: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in get_weather_by_coordinates: {str(e)}")
            return None

    def get_weather_recommendation(
        self,
        weather_data: Dict[str, Any],
    ) -> str:
        """
        Get recommendation text based on weather.

        Args:
            weather_data: Weather data dictionary

        Returns:
            str: Recommendation text
        """
        temp = weather_data.get('temp', 25)
        condition = weather_data.get('condition', 'clear').lower()

        # Cold weather
        if temp < 15:
            if 'rain' in condition or 'drizzle' in condition:
                return "It's cold and rainy! Perfect weather for warm soups, stews, and hot dishes to comfort you."
            else:
                return "It's quite cold today! How about some warm soups, stews, or hot dishes to warm you up?"

        # Cool weather
        elif 15 <= temp < 20:
            return "The weather is cool and pleasant. Light warm dishes or comfort food would hit the spot!"

        # Pleasant weather
        elif 20 <= temp <= 25:
            if condition == 'clear':
                return "The weather is beautiful today! Any of our dishes would be perfect. Would you like our chef's special?"
            else:
                return "It's a pleasant day. Great weather for any meal! What are you in the mood for?"

        # Warm weather
        elif 25 < temp <= 30:
            return "It's getting warm! I recommend lighter meals, salads, or cold drinks to keep you cool and refreshed."

        # Hot weather
        elif temp > 30:
            if condition == 'clear':
                return "It's very hot and sunny today! Definitely go for light meals, salads, and plenty of cold drinks!"
            else:
                return "It's quite hot outside! I suggest light, refreshing dishes and cold beverages to stay cool."

        # Rainy weather (any temp)
        if 'rain' in condition or 'drizzle' in condition or 'thunderstorm' in condition:
            return "It's rainy outside! Nothing beats comfort food like warm soups and stews on a rainy day."

        # Cloudy/overcast
        if 'clouds' in condition or 'overcast' in condition:
            return "It's a bit cloudy today. Comfort food would be great for this mood!"

        return "Great day for a meal! What would you like?"

    def classify_weather(self, weather_data: Dict[str, Any]) -> str:
        """
        Classify weather into categories for recommendations.

        Args:
            weather_data: Weather data dictionary

        Returns:
            str: Weather category (cold, cool, pleasant, warm, hot)
        """
        temp = weather_data.get('temp', 25)

        if temp < 15:
            return 'cold'
        elif temp < 20:
            return 'cool'
        elif temp <= 25:
            return 'pleasant'
        elif temp <= 30:
            return 'warm'
        else:
            return 'hot'

    def get_dish_suggestions_by_weather(
        self,
        weather_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Get dish suggestions based on weather conditions.

        Args:
            weather_data: Weather data dictionary

        Returns:
            dict: Dish suggestions and filters
        """
        temp = weather_data.get('temp', 25)
        condition = weather_data.get('condition', 'clear').lower()
        weather_category = self.classify_weather(weather_data)

        suggestions = {
            'preferred_attributes': [],
            'avoid_attributes': [],
            'meal_suggestions': [],
            'reasoning': '',
        }

        # Cold weather
        if weather_category == 'cold':
            suggestions['preferred_attributes'] = ['warm', 'hot', 'soup', 'stew']
            suggestions['avoid_attributes'] = ['cold', 'salad', 'ice', 'frozen']
            suggestions['meal_suggestions'] = ['breakfast', 'dinner']
            suggestions['reasoning'] = f"It's cold ({temp}°C), so warm dishes are recommended"

        # Hot weather
        elif weather_category == 'hot':
            suggestions['preferred_attributes'] = ['cold', 'salad', 'light', 'refreshing']
            suggestions['avoid_attributes'] = ['heavy', 'spicy', 'hot']
            suggestions['meal_suggestions'] = ['lunch', 'snack']
            suggestions['reasoning'] = f"It's hot ({temp}°C), so light and refreshing dishes are recommended"

        # Rainy weather
        elif 'rain' in condition or 'drizzle' in condition:
            suggestions['preferred_attributes'] = ['warm', 'comfort', 'soup', 'stew']
            suggestions['meal_suggestions'] = ['dinner']
            suggestions['reasoning'] = f"It's rainy ({condition}), perfect for comfort food"

        return suggestions

    def test_connection(self) -> bool:
        """
        Test the connection to OpenWeatherMap API.

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.api_key:
            logger.warning("Cannot test weather API - no API key configured")
            return False

        try:
            # Test with a simple city (London, UK)
            params = {
                'q': 'London,GB',
                'appid': self.api_key,
                'units': 'metric',
            }

            response = requests.get(self.base_url, params=params, timeout=5)
            response.raise_for_status()

            logger.info("Weather API connection test successful")
            return True

        except Exception as e:
            logger.error(f"Weather API connection test failed: {str(e)}")
            return False


# Singleton instance
_weather_service_instance = None


def get_weather_service() -> WeatherService:
    """
    Get or create the singleton WeatherService instance.

    Returns:
        WeatherService instance
    """
    global _weather_service_instance
    if _weather_service_instance is None:
        _weather_service_instance = WeatherService()
    return _weather_service_instance
