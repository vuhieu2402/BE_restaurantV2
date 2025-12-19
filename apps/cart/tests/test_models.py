from django.test import TestCase
from decimal import Decimal
from datetime import time
from django.contrib.auth import get_user_model
from apps.restaurants.models import Restaurant
from apps.dishes.models import MenuItem, Category
from ..models import Cart, CartItem

User = get_user_model()


class CartModelTest(TestCase):
    """Test cases for Cart model"""

    def setUp(self):
        """Setup test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.cart = Cart.objects.create(user=self.user)

    def test_cart_creation(self):
        """Test cart creation"""
        self.assertEqual(self.cart.user, self.user)
        self.assertEqual(self.cart.subtotal, Decimal('0.00'))
        self.assertEqual(self.cart.total, Decimal('0.00'))
        self.assertTrue(str(self.cart).startswith('Giỏ hàng của testuser'))

    def test_get_restaurant_count(self):
        """Test get_restaurant_count method"""
        self.assertEqual(self.cart.get_restaurant_count(), 0)

    def test_get_total_items(self):
        """Test get_total_items method"""
        self.assertEqual(self.cart.get_total_items(), 0)

    def test_calculate_totals_empty_cart(self):
        """Test calculate_totals with empty cart"""
        self.cart.calculate_totals()
        self.assertEqual(self.cart.subtotal, Decimal('0.00'))
        self.assertEqual(self.cart.tax, Decimal('0.00'))
        self.assertEqual(self.cart.total, Decimal('0.00'))


class CartItemModelTest(TestCase):
    """Test cases for CartItem model"""

    def setUp(self):
        """Setup test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.restaurant = Restaurant.objects.create(
            name='Test Restaurant',
            slug='test-restaurant',
            address='Test Address',
            phone_number='1234567890',
            opening_time=time(9, 0),  # 9:00 AM
            closing_time=time(22, 0)  # 10:00 PM
        )
        self.category = Category.objects.create(
            restaurant=self.restaurant,
            name='Test Category',
            slug='test-category'
        )
        self.menu_item = MenuItem.objects.create(
            restaurant=self.restaurant,
            category=self.category,
            name='Test Item',
            slug='test-item',
            price=Decimal('10.00')
        )
        self.cart = Cart.objects.create(user=self.user)

    def test_cart_item_creation(self):
        """Test cart item creation"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            menu_item=self.menu_item,
            restaurant=self.restaurant,
            item_name=self.menu_item.name,
            item_price=self.menu_item.price,
            restaurant_name=self.restaurant.name,
            quantity=2
        )

        self.assertEqual(cart_item.cart, self.cart)
        self.assertEqual(cart_item.menu_item, self.menu_item)
        self.assertEqual(cart_item.quantity, 2)
        self.assertTrue(str(cart_item).startswith('2x Test Item'))

    def test_calculate_subtotal(self):
        """Test calculate_subtotal method"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            menu_item=self.menu_item,
            restaurant=self.restaurant,
            item_name=self.menu_item.name,
            item_price=Decimal('10.00'),
            restaurant_name=self.restaurant.name,
            quantity=3
        )

        cart_item.calculate_subtotal()
        self.assertEqual(cart_item.subtotal, Decimal('30.00'))

    def test_cart_total_calculation_with_items(self):
        """Test cart total calculation when items are added"""
        cart_item = CartItem.objects.create(
            cart=self.cart,
            menu_item=self.menu_item,
            restaurant=self.restaurant,
            item_name=self.menu_item.name,
            item_price=Decimal('10.00'),
            restaurant_name=self.restaurant.name,
            quantity=2
        )

        cart_item.calculate_subtotal()
        self.cart.calculate_totals()

        # Verify cart totals are updated
        self.assertEqual(self.cart.get_total_items(), 2)
        self.assertEqual(self.cart.get_restaurant_count(), 1)