"""
Utility functions for Restaurant app
"""
import math


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

