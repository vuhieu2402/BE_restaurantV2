"""
Recommendation Engine for Chatbot

This module generates dish recommendations based on user preferences,
context, and multi-factor scoring.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from apps.chat.selectors import ChatbotSelector

logger = logging.getLogger(__name__)


@dataclass
class RecommendationResult:
    """
    Result of recommendation generation.

    Attributes:
        dishes: List of recommended dishes with metadata
        reasons: List of reasons for each recommendation
        confidence: Overall confidence score
        algorithm: Which algorithm was used
    """
    dishes: List[Dict[str, Any]]
    reasons: List[str]
    confidence: float
    algorithm: str


class RecommendationEngine:
    """
    Generate dish recommendations using multi-factor scoring.

    Factors considered:
    1. User Preferences (30%) - Past orders, dietary restrictions
    2. Rating (25%) - Customer ratings
    3. Popularity (20%) - Order frequency, featured status
    4. Price Fit (15%) - Match with user's typical spending
    5. Weather Relevance (10%) - Weather-appropriate dishes
    """

    def __init__(self):
        """Initialize the recommendation engine"""
        pass

    def generate_recommendations(
        self,
        restaurant_id: int,
        customer_id: int,
        num_recommendations: int = 3,
        dietary_preferences: Optional[List[str]] = None,
        spice_tolerance: str = 'medium',
        max_price: Optional[float] = None,
        meal_type: str = 'any',
        weather: Optional[Dict[str, Any]] = None,
        context_entities: Optional[Dict[str, Any]] = None,
    ) -> RecommendationResult:
        """
        Generate dish recommendations for a user.

        Args:
            restaurant_id: Restaurant ID
            customer_id: Customer ID
            num_recommendations: Number of recommendations to return
            dietary_preferences: Dietary restrictions (e.g., ['vegetarian'])
            spice_tolerance: none, low, medium, high
            max_price: Maximum price per item
            meal_type: breakfast, lunch, dinner, snack, any
            weather: Weather data (temp, condition)
            context_entities: Entities from conversation context

        Returns:
            RecommendationResult with dishes and reasons
        """
        try:
            # Get data
            menu_items = self._get_menu_items(restaurant_id)
            if not menu_items:
                return self._empty_result("No menu items available")

            customer_preferences = ChatbotSelector.get_customer_preferences(customer_id)

            # Score dishes
            scored_dishes = []
            for item in menu_items:
                score = self._calculate_score(
                    item=item,
                    customer_preferences=customer_preferences,
                    dietary_preferences=dietary_preferences,
                    spice_tolerance=spice_tolerance,
                    max_price=max_price,
                    meal_type=meal_type,
                    weather=weather,
                    context_entities=context_entities,
                )
                scored_dishes.append((item, score))

            # Sort by score and get top recommendations
            scored_dishes.sort(key=lambda x: x[1], reverse=True)
            top_dishes = scored_dishes[:num_recommendations]

            if not top_dishes:
                return self._empty_result("No dishes match the criteria")

            # Generate reasons
            dishes = [dish for dish, score in top_dishes]
            reasons = [self._generate_reason(dish, score, customer_preferences, weather)
                      for dish, score in top_dishes]

            avg_score = sum(score for _, score in top_dishes) / len(top_dishes)

            return RecommendationResult(
                dishes=dishes,
                reasons=reasons,
                confidence=min(avg_score / 10.0, 1.0),  # Normalize to 0-1
                algorithm='multi_factor_scoring',
            )

        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return self._empty_result(f"Error: {str(e)}")

    def _get_menu_items(self, restaurant_id: int) -> List[Dict[str, Any]]:
        """Get available menu items for a restaurant"""
        menu_summary = ChatbotSelector.get_menu_summary(restaurant_id)
        if not menu_summary:
            return []

        # Get featured items and additional items
        featured = menu_summary.get('featured_items', [])

        # If we don't have enough featured items, get more from search
        if len(featured) < 10:
            additional = ChatbotSelector.search_menu_items(
                restaurant_id=restaurant_id,
                limit=20
            )
            # Deduplicate
            seen_ids = {item['id'] for item in featured}
            for item in additional:
                if item['id'] not in seen_ids:
                    featured.append(item)

        return featured

    def _calculate_score(
        self,
        item: Dict[str, Any],
        customer_preferences: Dict[str, Any],
        dietary_preferences: Optional[List[str]],
        spice_tolerance: str,
        max_price: Optional[float],
        meal_type: str,
        weather: Optional[Dict[str, Any]],
        context_entities: Optional[Dict[str, Any]],
    ) -> float:
        """
        Calculate recommendation score for a dish.

        Score = (Preference × 0.3) + (Rating × 0.25) + (Popularity × 0.2) +
                (Price Fit × 0.15) + (Weather × 0.1)

        Returns:
            Float score (typically 0-10)
        """
        score = 0.0

        # 1. Preference Match (30%, max 3.0)
        pref_score = self._score_preferences(item, customer_preferences, dietary_preferences)
        score += pref_score * 3.0

        # 2. Rating (25%, max 2.5)
        rating = item.get('rating', 0)
        score += (rating / 5.0) * 2.5

        # 3. Popularity (20%, max 2.0)
        pop_score = self._score_popularity(item, customer_preferences)
        score += pop_score * 2.0

        # 4. Price Fit (15%, max 1.5)
        price_score = self._score_price(item, customer_preferences, max_price)
        score += price_score * 1.5

        # 5. Weather Relevance (10%, max 1.0)
        if weather:
            weather_score = self._score_weather(item, weather)
            score += weather_score * 1.0

        return score

    def _score_preferences(
        self,
        item: Dict[str, Any],
        customer_preferences: Dict[str, Any],
        dietary_preferences: Optional[List[str]],
    ) -> float:
        """
        Score preference match (0-1).

        Checks:
        - Dietary restrictions match
        - Favorite categories
        - Spice tolerance
        """
        score = 0.0

        # Dietary restrictions (hard filter)
        if dietary_preferences:
            if 'vegetarian' in dietary_preferences and not item.get('is_vegetarian', False):
                return 0.0  # Hard reject
            if 'no_spicy' in dietary_preferences and item.get('is_spicy', False):
                score -= 0.5

        # Customer's dietary preferences from history
        cust_dietary = customer_preferences.get('dietary_restrictions', [])
        if cust_dietary and 'vegetarian' in cust_dietary and item.get('is_vegetarian'):
            score += 0.4

        # Favorite categories
        favorite_categories = customer_preferences.get('favorite_categories', [])
        item_category = item.get('category', '')
        if item_category in favorite_categories:
            score += 0.3

        # Spice tolerance
        spice_tolerance = customer_preferences.get('spice_tolerance', 'medium')
        item_spicy = item.get('is_spicy', False)

        if not item_spicy:
            score += 0.2  # Non-spicy dishes get slight boost
        elif spice_tolerance == 'high' and item_spicy:
            score += 0.3
        elif spice_tolerance == 'low' and item_spicy:
            score -= 0.3
        elif spice_tolerance == 'none' and item_spicy:
            score -= 0.5

        return min(max(score, 0), 1.0)

    def _score_popularity(
        self,
        item: Dict[str, Any],
        customer_preferences: Dict[str, Any],
    ) -> float:
        """
        Score popularity (0-1).

        Factors:
        - Featured status
        - Number of reviews
        - Ordered before by customer
        """
        score = 0.0

        # Featured items
        if item.get('is_featured', False):
            score += 0.4

        # Review count (more reviews = more popular)
        total_reviews = item.get('total_reviews', 0)
        if total_reviews > 50:
            score += 0.3
        elif total_reviews > 20:
            score += 0.2
        elif total_reviews > 10:
            score += 0.1

        # High rating
        rating = item.get('rating', 0)
        if rating >= 4.5:
            score += 0.3
        elif rating >= 4.0:
            score += 0.2

        return min(score, 1.0)

    def _score_price(
        self,
        item: Dict[str, Any],
        customer_preferences: Dict[str, Any],
        max_price: Optional[float],
    ) -> float:
        """
        Score price fit (0-1).

        Checks:
        - Within max_price if specified
        - Close to customer's average order value
        """
        price = item.get('price', 0)
        avg_order = customer_preferences.get('average_order_value', 0)

        score = 0.5  # Base score

        # Hard max price constraint
        if max_price and price > max_price:
            return 0.0

        # Fit with customer's typical spending
        if avg_order > 0:
            # Assume single item is 30-50% of average order
            target_min = avg_order * 0.3
            target_max = avg_order * 0.5

            if target_min <= price <= target_max:
                score += 0.5
            elif price < target_min:
                score += 0.3  # Below range is ok
            elif price <= target_max * 1.2:
                score += 0.2  # Slightly above is acceptable

        return min(score, 1.0)

    def _score_weather(self, item: Dict[str, Any], weather: Dict[str, Any]) -> float:
        """
        Score weather relevance (0-1).

        Cold weather: Warm dishes (soups, stews, hot items)
        Hot weather: Light dishes (salads, cold items)
        """
        temp = weather.get('temp', 25)
        condition = weather.get('condition', 'clear').lower()
        name = item.get('name', '').lower()
        description = item.get('description', '').lower()

        score = 0.0

        # Cold weather (< 15°C)
        if temp < 15:
            # Warm dishes
            warm_keywords = ['soup', 'stew', 'hot', 'warm', 'pho', 'bun', 'mì']
            if any(kw in name or kw in description for kw in warm_keywords):
                score += 1.0
            elif not item.get('is_spicy', False):  # Non-spicy is good for cold too
                score += 0.5

        # Hot weather (> 30°C)
        elif temp > 30:
            # Light/refreshing dishes
            light_keywords = ['salad', 'cold', 'ice', 'refreshing', 'cool', 'drink']
            if any(kw in name or kw in description for kw in light_keywords):
                score += 1.0
            elif not item.get('is_spicy', False):  # Non-spicy for hot weather
                score += 0.6

        # Rainy weather
        elif 'rain' in condition:
            # Comfort food
            comfort_keywords = ['soup', 'stew', 'warm', 'hot', 'pho']
            if any(kw in name or kw in description for kw in comfort_keywords):
                score += 0.8

        # Pleasant weather (15-25°C)
        elif 15 <= temp <= 25 and condition == 'clear':
            score += 0.5  # Everything is good!

        return score

    def _generate_reason(
        self,
        dish: Dict[str, Any],
        score: float,
        customer_preferences: Dict[str, Any],
        weather: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Generate a human-readable reason for recommendation.

        Args:
            dish: Dish information
            score: Calculated score
            customer_preferences: Customer data
            weather: Weather data

        Returns:
            Reason string
        """
        reasons = []

        # Rating
        rating = dish.get('rating', 0)
        if rating >= 4.5:
            reasons.append(f"⭐ Excellent rating ({rating}/5)")

        # Featured
        if dish.get('is_featured'):
            reasons.append("🌟 Featured item")

        # Dietary
        if dish.get('is_vegetarian'):
            reasons.append("🥬 Vegetarian option")

        # Spicy
        if dish.get('is_spicy'):
            spice_tolerance = customer_preferences.get('spice_tolerance', 'medium')
            if spice_tolerance in ['high', 'medium']:
                reasons.append("🌶️ Spicy delight")
        else:
            reasons.append("Mild flavor")

        # Price
        price = dish.get('price', 0)
        avg_order = customer_preferences.get('average_order_value', 0)
        if avg_order > 0:
            if price <= avg_order * 0.4:
                reasons.append(f"💰 Great value at {price:,.0f} VND")

        # Weather
        if weather:
            temp = weather.get('temp', 25)
            if temp < 15:
                reasons.append("🍲 Perfect for cold weather")
            elif temp > 30:
                reasons.append("🥗 Light and refreshing")

        # Combine reasons
        if reasons:
            return " | ".join(reasons[:3])  # Max 3 reasons
        else:
            return f"Popular choice with {rating}⭐ rating"

    def _empty_result(self, message: str) -> RecommendationResult:
        """Create empty recommendation result"""
        return RecommendationResult(
            dishes=[],
            reasons=[message],
            confidence=0.0,
            algorithm='none',
        )

    def get_similar_dishes(
        self,
        restaurant_id: int,
        dish_id: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find dishes similar to a given dish.

        Args:
            restaurant_id: Restaurant ID
            dish_id: ID of the reference dish
            limit: Maximum number of results

        Returns:
            List of similar dishes
        """
        from apps.chat.selectors import ChatbotSelector

        # Get reference dish
        reference_dish = ChatbotSelector.get_dish_by_name_or_id(restaurant_id, str(dish_id))
        if not reference_dish:
            return []

        # Find similar dishes
        menu_items = ChatbotSelector.search_menu_items(
            restaurant_id=restaurant_id,
            limit=50,
        )

        # Calculate similarity
        similar_dishes = []
        for item in menu_items:
            if item['id'] == dish_id:
                continue  # Skip the reference dish itself

            similarity = self._calculate_similarity(reference_dish, item)
            if similarity > 0.3:  # Minimum similarity threshold
                similar_dishes.append((item, similarity))

        # Sort by similarity and return top results
        similar_dishes.sort(key=lambda x: x[1], reverse=True)
        return [dish for dish, _ in similar_dishes[:limit]]

    def _calculate_similarity(self, dish1: Dict[str, Any], dish2: Dict[str, Any]) -> float:
        """
        Calculate similarity between two dishes (0-1).

        Factors:
        - Same category
        - Similar price range
        - Same dietary attributes
        """
        similarity = 0.0

        # Same category
        if dish1.get('category') == dish2.get('category'):
            similarity += 0.4

        # Similar price (within 20%)
        price1 = dish1.get('price', 0)
        price2 = dish2.get('price', 0)
        if price1 > 0 and price2 > 0:
            price_ratio = min(price1, price2) / max(price1, price2)
            if price_ratio >= 0.8:
                similarity += 0.3

        # Same dietary attributes
        if dish1.get('is_vegetarian') == dish2.get('is_vegetarian'):
            similarity += 0.15

        if dish1.get('is_spicy') == dish2.get('is_spicy'):
            similarity += 0.15

        return similarity


# Singleton instance
_recommendation_engine_instance = None


def get_recommendation_engine() -> RecommendationEngine:
    """
    Get or create the singleton RecommendationEngine instance.

    Returns:
        RecommendationEngine instance
    """
    global _recommendation_engine_instance
    if _recommendation_engine_instance is None:
        _recommendation_engine_instance = RecommendationEngine()
    return _recommendation_engine_instance
