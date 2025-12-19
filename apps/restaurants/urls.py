from django.urls import path
from . import views
from . import chain_views

# === Restaurant Management URLs ===
urlpatterns = [
    # ===== Restaurant Chain endpoints =====
    path('chains/', chain_views.RestaurantChainListView.as_view(), name='chain-list'),
    path('chains/<int:chain_id>/', chain_views.RestaurantChainDetailView.as_view(), name='chain-detail'),
    path('chains/slug/<slug:slug>/', chain_views.RestaurantChainBySlugView.as_view(), name='chain-by-slug'),
    path('chains/<int:chain_id>/branches/', chain_views.ChainBranchesView.as_view(), name='chain-branches'),
    path('chains/<int:chain_id>/nearest-branch/', chain_views.NearestBranchView.as_view(), name='nearest-branch'),
    
    # ===== Restaurant (Branch) endpoints =====
    path('', views.RestaurantListView.as_view(), name='restaurant-list'),
    path('<int:restaurant_id>/', views.RestaurantDetailView.as_view(), name='restaurant-detail'),
    path('slug/<slug:slug>/', views.RestaurantBySlugView.as_view(), name='restaurant-by-slug'),
    path('nearby/', views.NearbyRestaurantsView.as_view(), name='nearby-restaurants'),

    # ===== Table management endpoints =====
    path('<int:restaurant_id>/tables/', views.TableView.as_view(), name='restaurant-tables'),
    path('<int:restaurant_id>/tables/<int:table_id>/', views.TableDetailView.as_view(), name='restaurant-table-detail'),
    path('<int:restaurant_id>/tables/available/', views.AvailableTablesView.as_view(), name='available-tables'),
    path('<int:restaurant_id>/tables/layout/', views.TableLayoutView.as_view(), name='table-layout'),
    path('<int:restaurant_id>/tables/bulk/', views.BulkTableOperationView.as_view(), name='bulk-table-operations'),
]