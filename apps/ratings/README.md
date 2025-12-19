# Ratings App Documentation

## Overview

The Ratings app provides a comprehensive rating and review system for menu items in the restaurant management system. It allows customers to rate dishes, leave reviews, and enables restaurant owners to respond and analyze feedback.

## Features

### Core Functionality
- **Star Ratings**: 1-5 star rating system for menu items
- **Text Reviews**: Optional detailed review text (10-2000 characters)
- **Review Images**: Support for up to 5 images per review
- **Verified Purchase Indicators**: Shows if reviewer actually ordered the item
- **Helpful Voting**: Users can mark reviews as helpful or not helpful
- **Review Reporting**: Report inappropriate content
- **Moderation System**: Built-in moderation workflow

### Advanced Features
- **Rating Analytics**: Comprehensive analytics for restaurant chains
- **Owner Responses**: Restaurant owners can respond to reviews
- **Auto-approval**: Smart auto-approval for verified purchases
- **Rating Distribution**: Detailed breakdown of rating statistics
- **Pagination**: Efficient pagination for large datasets

## API Endpoints

### Menu Item Ratings

#### Get Ratings for Menu Item
```
GET /api/restaurants/chains/{chain_id}/menu-items/{item_id}/ratings/
```

**Query Parameters:**
- `rating` (int, optional): Filter by specific rating (1-5)
- `verified_only` (bool, optional): Show only verified purchase reviews
- `has_review` (bool, optional): Show only reviews with text content
- `page` (int, optional): Page number
- `page_size` (int, optional): Items per page (max 100)

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "user_name": "John Doe",
      "rating": 5,
      "review_text": "Amazing dish!",
      "review_images": ["image1.jpg"],
      "helpful_count": 12,
      "not_helpful_count": 1,
      "is_verified_purchase": true,
      "time_ago": "2 days ago",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "pagination": {
    "count": 156,
    "next": "http://api.example.com/page/2/",
    "previous": null,
    "current_page": 1,
    "total_pages": 8
  }
}
```

#### Create/Update Rating
```
POST /api/restaurants/chains/{chain_id}/menu-items/{item_id}/ratings/
```

**Request Body:**
```json
{
  "rating": 4,
  "review_text": "Great pasta, could use more sauce though",
  "review_images": ["image1.jpg", "image2.jpg"]
}
```

#### Get Rating Summary
```
GET /api/restaurants/chains/{chain_id}/menu-items/{item_id}/ratings/summary/
```

**Response:**
```json
{
  "data": {
    "average_rating": 4.2,
    "total_reviews": 156,
    "verified_purchase_percentage": 87.5,
    "rating_distribution": {
      "5_star": 80,
      "4_star": 45,
      "3_star": 20,
      "2_star": 8,
      "1_star": 3
    },
    "recent_reviews": [...],
    "top_positive_reviews": [...],
    "top_critical_reviews": [...]
  }
}
```

### Rating Interactions

#### Mark as Helpful/Not Helpful
```
POST /api/restaurants/chains/{chain_id}/menu-items/{item_id}/ratings/{rating_id}/helpful/
```

**Request Body:**
```json
{
  "is_helpful": true
}
```

#### Report Rating
```
POST /api/restaurants/chains/{chain_id}/menu-items/{item_id}/ratings/{rating_id}/report/
```

**Request Body:**
```json
{
  "reason": "spam",
  "description": "This looks like a fake review"
}
```

### User Ratings

#### Get User's Ratings
```
GET /api/restaurants/users/me/ratings/
```

**Query Parameters:**
- `rating` (int, optional): Filter by specific rating
- `chain_id` (int, optional): Filter by restaurant chain
- `has_review` (bool, optional): Show only reviews with text

### Analytics

#### Get Chain Analytics
```
GET /api/restaurants/chains/{chain_id}/ratings/analytics/
```

**Response:**
```json
{
  "data": {
    "overall_stats": {
      "total_ratings": 1234,
      "average_rating": 4.1,
      "five_star": 567,
      "verified_ratings": 1089
    },
    "rating_trends": [...],
    "top_rated_items": [...],
    "top_reviewers": [...],
    "recent_ratings": [...]
  }
}
```

## Database Schema

### Core Models

#### MenuItemRating
Main rating model storing user reviews and ratings.

**Key Fields:**
- `menu_item`: ForeignKey to MenuItem
- `user`: ForeignKey to User
- `rating`: Integer (1-5)
- `review_text`: Text field (optional)
- `review_images`: JSON array of image URLs
- `is_verified_purchase`: Boolean
- `is_approved`: Boolean
- `helpful_count`: Integer
- `not_helpful_count`: Integer

#### RatingCategory
Categories for detailed rating aspects (Taste, Presentation, etc.).

#### RatingResponse
Responses from restaurant owners to reviews.

#### RatingHelpful
Track which users marked reviews as helpful/not helpful.

### Enhanced MenuItem Fields

The MenuItem model has been enhanced with:
- `rating_distribution`: JSON field storing rating breakdown
- `last_rated_at`: Timestamp of last rating
- `verified_purchase_percentage`: Percentage of verified purchase ratings

## Business Rules

### Rating Eligibility
- Users can rate any available menu item (configurable to verified purchases only)
- One rating per user per menu item
- Ratings can be edited within 30 days of creation
- Users can delete their own ratings within 30 days

### Auto-Approval
- Verified purchases with 3+ stars are auto-approved
- Users with order history and 3+ stars are auto-approved
- 1-2 star ratings and new users may require manual moderation

### Anti-Spam Measures
- Rate limiting on rating submissions
- IP address tracking
- Suspicious pattern detection
- User helpful voting to surface quality reviews

## Performance Optimizations

### Database Indexes
- Composite indexes on frequently queried fields
- Indexes on rating filtering and sorting
- Optimized queries for rating statistics

### Caching
- Rating summary caching
- Background task processing for statistics updates
- Pagination for large result sets

## Background Tasks

Using Celery for asynchronous processing:

### Tasks Available
- `update_menu_item_rating_stats`: Update menu item rating statistics
- `cleanup_old_rating_helpful_votes`: Cleanup old helpful votes
- `calculate_rating_trends`: Calculate rating trends for analytics
- `send_rating_notifications`: Send notifications to restaurant owners

## Configuration

### Environment Variables
- `STANDARD_PAGINATION_PAGE_SIZE`: Default pagination page size (default: 20)
- `STANDARD_PAGINATION_MAX_PAGE_SIZE`: Maximum pagination page size (default: 100)

### Setup Commands

```bash
# Create rating categories
python manage.py create_rating_categories

# Run migrations
python manage.py migrate

# Test the system
python manage.py shell
```

## Security Features

### Access Control
- Role-based permissions for analytics
- Ownership validation for rating modifications
- Restaurant owner response permissions

### Data Protection
- Anonymous rating options
- Right to delete own ratings
- Moderation workflow for inappropriate content

## Integration Points

### Order System
- Verified purchase tracking
- Post-order rating prompts
- Order history for rating eligibility

### User System
- User profile integration
- Authentication required for rating
- User rating history

### Analytics System
- Rating trend analysis
- Customer satisfaction metrics
- Performance dashboards

## Frontend Integration

### Rating Components
- Star rating display/input
- Review text editor
- Image upload support
- Helpful voting buttons

### Display Components
- Rating summary cards
- Review lists with pagination
- Rating distribution charts
- Analytics dashboards

## Testing

### Unit Tests
- Model validations
- Service business logic
- Serializer validations

### Integration Tests
- API endpoint testing
- Database operations
- Background task processing

### Performance Tests
- Large dataset handling
- Query optimization
- Cache performance

## Monitoring

### Metrics to Track
- Rating submission rates
- Average response times
- Moderation queue sizes
- User engagement metrics

### Alerts
- High spam detection rates
- Database performance issues
- Background task failures