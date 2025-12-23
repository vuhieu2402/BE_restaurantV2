"""
Utility functions for Restaurant app
"""
import math
import requests
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


def calculate_distance_osrm(origin_lat, origin_lng, dest_lat, dest_lng):
    """
    Tính khoảng cách thực tế bằng OSRM (Open Source Routing Machine)
    
    Args:
        origin_lat, origin_lng: Tọa độ điểm xuất phát
        dest_lat, dest_lng: Tọa độ điểm đến
    
    Returns:
        dict: {
            'success': bool,
            'distance_km': Decimal,
            'duration_minutes': int,
            'source': str
        }
    """
    # OSRM API endpoint (public, free, no API key needed)
    url = f"http://router.project-osrm.org/route/v1/driving/{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
    
    params = {
        'overview': 'false',
        'alternatives': 'false',
        'steps': 'false'
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('code') == 'Ok' and data.get('routes'):
            route = data['routes'][0]
            
            # Distance in meters → convert to km
            distance_meters = route['distance']
            distance_km = Decimal(str(round(distance_meters / 1000, 2)))
            
            # Duration in seconds → convert to minutes
            duration_seconds = route['duration']
            duration_minutes = int(duration_seconds / 60)
            
            logger.info(f"OSRM calculated distance: {distance_km}km, duration: {duration_minutes}min")
            
            return {
                'success': True,
                'distance_km': distance_km,
                'duration_minutes': duration_minutes,
                'source': 'OSRM'
            }
        else:
            logger.warning(f"OSRM returned non-Ok code: {data.get('code')}")
            return {
                'success': False,
                'message': f"OSRM error: {data.get('code', 'Unknown')}"
            }
            
    except requests.exceptions.Timeout:
        logger.error("OSRM request timeout")
        return {
            'success': False,
            'message': 'OSRM request timeout'
        }
    except requests.exceptions.RequestException as e:
        logger.error(f"OSRM request failed: {str(e)}")
        return {
            'success': False,
            'message': f'OSRM request failed: {str(e)}'
        }
    except Exception as e:
        logger.error(f"Unexpected error in OSRM: {str(e)}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


def calculate_distance_with_fallback(origin_lat, origin_lng, dest_lat, dest_lng):
    """
    Tính khoảng cách với fallback strategy:
    1. Try OSRM (routing API - chính xác)
    2. Fallback to Haversine + routing factor
    
    Returns:
        dict: Same format as calculate_distance_osrm
    """
    # Try OSRM first
    result = calculate_distance_osrm(origin_lat, origin_lng, dest_lat, dest_lng)
    
    if result['success']:
        return result
    
    # Fallback: Haversine + routing factor
    logger.warning("OSRM failed, using Haversine fallback")
    
    haversine_distance = calculate_distance(origin_lat, origin_lng, dest_lat, dest_lng)
    
    # Apply routing factor based on distance
    if haversine_distance < 2:
        routing_factor = 1.4  # Nội thành, nhiều ngã tư
    elif haversine_distance < 5:
        routing_factor = 1.3
    elif haversine_distance < 10:
        routing_factor = 1.25
    else:
        routing_factor = 1.2  # Xa, đường thẳng hơn
    
    adjusted_distance = Decimal(str(round(haversine_distance * routing_factor, 2)))
    
    # Estimate time: 30km/h + 15min preparation
    travel_time = int((float(adjusted_distance) / 30) * 60)
    estimated_time = travel_time + 15
    
    logger.info(f"Haversine fallback: {adjusted_distance}km (factor: {routing_factor})")
    
    return {
        'success': True,
        'distance_km': adjusted_distance,
        'duration_minutes': estimated_time,
        'source': 'Haversine+Factor (Fallback)'
    }


def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Tính khoảng cách giữa 2 tọa độ theo công thức Haversine
    
    Args:
        lat1, lon1: Tọa độ điểm 1 (latitude, longitude)
        lat2, lon2: Tọa độ điểm 2 (latitude, longitude)
    
    Returns:
        Khoảng cách (km)
    """
    # Bán kính trái đất (km)
    R = 6371
    
    # Chuyển đổi sang radian
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    
    distance = R * c
    
    return round(distance, 2)


def get_nearest_restaurant_for_delivery(chain, delivery_latitude, delivery_longitude):
    """
    Tìm chi nhánh gần nhất có thể giao hàng đến địa chỉ
    
    Args:
        chain: RestaurantChain object hoặc None
        delivery_latitude: Vĩ độ địa chỉ giao hàng
        delivery_longitude: Kinh độ địa chỉ giao hàng
    
    Returns:
        (restaurant, distance) tuple hoặc (None, None)
    """
    if not chain:
        return None, None
    
    if not delivery_latitude or not delivery_longitude:
        return None, None
    
    available_restaurants = chain.restaurants.filter(
        is_active=True,
        is_open=True,
        latitude__isnull=False,
        longitude__isnull=False
    )
    
    if not available_restaurants.exists():
        return None, None
    
    # Tính khoảng cách cho từng chi nhánh
    restaurants_with_distance = []
    for restaurant in available_restaurants:
        distance = calculate_distance(
            float(delivery_latitude),
            float(delivery_longitude),
            float(restaurant.latitude),
            float(restaurant.longitude)
        )
        
        # Kiểm tra trong bán kính phục vụ
        if distance <= float(restaurant.delivery_radius):
            restaurants_with_distance.append((restaurant, distance))
    
    if not restaurants_with_distance:
        return None, None
    
    # Sắp xếp theo khoảng cách và trả về chi nhánh gần nhất
    restaurants_with_distance.sort(key=lambda x: x[1])
    return restaurants_with_distance[0]

