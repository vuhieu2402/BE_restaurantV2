from django.urls import path, include
from . import views
from . import chain_views

# === Dishes Management URLs ===
urlpatterns = [
    # ===== Chain Menu endpoints (NEW) =====
    path('chains/<int:chain_id>/categories/', chain_views.ChainCategoriesView.as_view(), name='chain-categories'),
    path('chains/<int:chain_id>/categories/<int:category_id>/', chain_views.ChainCategoryDetailView.as_view(), name='chain-category-detail'),
    path('chains/<int:chain_id>/categories/<int:category_id>/items/', chain_views.ChainCategoryMenuItemsView.as_view(), name='chain-category-items'),
    
    path('chains/<int:chain_id>/menu-items/', chain_views.ChainMenuItemsView.as_view(), name='chain-menu-items'),
    path('chains/<int:chain_id>/menu-items/<int:item_id>/', chain_views.ChainMenuItemDetailView.as_view(), name='chain-menu-item-detail'),
    
    # ===== Restaurant Category endpoints =====
    path('<int:restaurant_id>/categories/', views.CategoryListView.as_view(), name='category-list'),
    path('<int:restaurant_id>/categories/<int:category_id>/', views.CategoryDetailView.as_view(), name='category-detail'),
    path('<int:restaurant_id>/categories/reorder/', views.CategoryReorderView.as_view(), name='category-reorder'),

    # Menu item endpoints
    path('<int:restaurant_id>/menu-items/', views.MenuItemListView.as_view(), name='menu-item-list'),
    path('menu-items/<int:item_id>/', views.MenuItemDetailView.as_view(), name='menu-item-detail'),
    path('<int:restaurant_id>/menu-items/<int:item_id>/', views.MenuItemUpdateDeleteView.as_view(), name='menu-item-update-delete'),
    path('<int:restaurant_id>/menu-items/<int:item_id>/images/', views.MenuItemImageView.as_view(), name='menu-item-images'),
    path('<int:restaurant_id>/menu-items/<int:item_id>/images/<int:image_id>/', views.MenuItemImageDetailView.as_view(), name='menu-item-image-detail'),
    path('<int:restaurant_id>/menu-items/featured/', views.FeaturedMenuItemsView.as_view(), name='featured-menu-items'),
    path('<int:restaurant_id>/menu-items/search/', views.MenuSearchView.as_view(), name='menu-item-search'),
    path('<int:restaurant_id>/menu-items/toggle-availability/', views.MenuToggleView.as_view(), name='toggle-item-availability'),
    path('<int:restaurant_id>/menu-items/toggle-featured/', views.MenuToggleView.as_view(), name='toggle-item-featured'),
    path('<int:restaurant_id>/menu-items/bulk-price-update/', views.BulkPriceUpdateView.as_view(), name='bulk-price-update'),

    # Menu organization endpoints
    path('<int:restaurant_id>/menu/', views.MenuByCategoriesView.as_view(), name='menu-by-categories'),
    path('<int:restaurant_id>/menu/analytics/', views.MenuAnalyticsView.as_view(), name='menu-analytics'),

    # ===== Ratings endpoints (include from ratings app) =====
    path('', include('apps.ratings.urls')),
]