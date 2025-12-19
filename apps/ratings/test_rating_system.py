#!/usr/bin/env python
"""
Quick test script to verify the rating system is working properly
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.ratings.models import RatingCategory, MenuItemRating
from apps.dishes.models import MenuItem
from apps.users.models import User
from django.contrib.auth import get_user_model

def test_rating_system():
    """Test the rating system functionality"""

    print("🧪 Testing Rating System...")
    print("=" * 50)

    # Test 1: Check if rating categories were created
    print("\n1. Checking Rating Categories:")
    categories = RatingCategory.objects.filter(is_active=True)
    for category in categories:
        print(f"   ✅ {category.name} ({category.code}) - Order: {category.display_order}")

    # Test 2: Check MenuItem model has new rating fields
    print("\n2. Checking MenuItem Model Fields:")
    try:
        menu_item_fields = MenuItem._meta.get_fields()
        rating_fields = []

        for field in menu_item_fields:
            if 'rating' in field.name or 'verified' in field.name:
                rating_fields.append(field.name)

        print(f"   ✅ Found rating fields: {', '.join(rating_fields)}")

        # Check if specific new fields exist
        new_fields = ['rating_distribution', 'last_rated_at', 'verified_purchase_percentage']
        for field in new_fields:
            if hasattr(MenuItem, field):
                print(f"   ✅ {field} field exists")
            else:
                print(f"   ❌ {field} field missing")

    except Exception as e:
        print(f"   ❌ Error checking MenuItem fields: {e}")

    # Test 3: Check if database tables were created
    print("\n3. Checking Database Tables:")
    try:
        # Test MenuItemRating table
        rating_count = MenuItemRating.objects.count()
        print(f"   ✅ MenuItemRating table exists ({rating_count} records)")

        # Test RatingCategory table
        category_count = RatingCategory.objects.count()
        print(f"   ✅ RatingCategory table exists ({category_count} records)")

    except Exception as e:
        print(f"   ❌ Database tables not properly created: {e}")

    # Test 4: Check model relationships
    print("\n4. Checking Model Relationships:")
    try:
        # Test MenuItemRating fields
        rating_fields = [f.name for f in MenuItemRating._meta.get_fields()]
        expected_fields = ['menu_item', 'user', 'rating', 'review_text', 'review_images']

        for field in expected_fields:
            if field in rating_fields:
                print(f"   ✅ MenuItemRating.{field} exists")
            else:
                print(f"   ❌ MenuItemRating.{field} missing")

    except Exception as e:
        print(f"   ❌ Error checking model relationships: {e}")

    # Test 5: Check if app is properly configured
    print("\n5. Checking App Configuration:")
    try:
        from django.apps import apps
        ratings_app = apps.get_app_config('ratings')
        print(f"   ✅ Ratings app loaded: {ratings_app.name}")
        print(f"   ✅ Verbose name: {ratings_app.verbose_name}")

    except Exception as e:
        print(f"   ❌ Error loading ratings app: {e}")

    print("\n" + "=" * 50)
    print("🎉 Rating System Test Complete!")
    print("\n📋 Next Steps:")
    print("   1. Create some test menu items")
    print("   2. Create test users")
    print("   3. Test API endpoints")
    print("   4. Test rating creation and display")
    print("\n🔗 API Endpoints Available:")
    print("   GET/POST /api/restaurants/chains/{chain_id}/menu-items/{item_id}/ratings/")
    print("   GET /api/restaurants/chains/{chain_id}/menu-items/{item_id}/ratings/summary/")
    print("   GET /api/restaurants/users/me/ratings/")

if __name__ == "__main__":
    test_rating_system()