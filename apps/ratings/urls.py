from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API URL patterns for ratings
app_name = 'ratings'

urlpatterns = [
    # ===== Menu Item Ratings =====
    # Get ratings for a specific menu item / Create new rating
    path(
        'chains/<int:chain_id>/menu-items/<int:item_id>/ratings/',
        views.MenuItemRatingView.as_view(),
        name='menu-item-ratings'
    ),

    # Get/update/delete specific rating
    path(
        'chains/<int:chain_id>/menu-items/<int:item_id>/ratings/<int:rating_id>/',
        views.MenuItemRatingDetailView.as_view(),
        name='menu-item-rating-detail'
    ),

    # Get rating summary for a menu item
    path(
        'chains/<int:chain_id>/menu-items/<int:item_id>/ratings/summary/',
        views.MenuItemRatingSummaryView.as_view(),
        name='menu-item-rating-summary'
    ),

    
    path(
        'users/me/ratings/',
        views.UserRatingsView.as_view(),
        name='user-ratings'
    ),

    # ===== Chain Rating Analytics =====
    # Get rating analytics for a chain
    path(
        'chains/<int:chain_id>/ratings/analytics/',
        views.ChainRatingAnalyticsView.as_view(),
        name='chain-rating-analytics'
    ),
]