# Chatbot API Testing with Postman

Complete guide for testing all chatbot endpoints using Postman.

## Table of Contents
1. [Setup & Authentication](#setup--authentication)
2. [Base URL](#base-url)
3. [API Endpoints](#api-endpoints)
4. [Testing Examples](#testing-examples)
5. [Common Issues](#common-issues)

---

## Setup & Authentication

### Step 1: Get JWT Token

The chatbot endpoints require authentication. First, obtain a JWT token:

**Request:**
```
POST {{base_url}}/api/auth/login/
Content-Type: application/json
```

**Body:**
```json
{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "username": "testuser",
      "email": "test@example.com"
    }
  }
}
```

### Step 2: Configure Authorization in Postman

1. Go to the **Authorization** tab
2. Type: **Bearer Token**
3. Token: Paste the `access` token from login response
4. Add prefix: `Bearer` (if not auto-added)

**Or add to Headers:**
- Key: `Authorization`
- Value: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

---

## Base URL

**Development:**
```
http://localhost:8000
```

**All endpoints:**
```
{{base_url}}/api/chat/chatbot/...
```

---

## API Endpoints

### 1. Send Message to Chatbot

Send a message and get intelligent response with recommendations.

**Endpoint:**
```
POST {{base_url}}/api/chat/chatbot/rooms/{room_id}/message/
```

**Request Headers:**
```
Authorization: Bearer {your_token}
Content-Type: application/json
```

**Path Parameters:**
- `room_id` (integer): Chat room ID

**Request Body:**
```json
{
  "message": "What do you recommend for lunch today?",
  "restaurant_id": 1,
  "context": {
    "weather": {
      "temp": 28,
      "condition": "sunny"
    }
  }
}
```

**Body Parameters:**
- `message` (string, required): User's message
- `restaurant_id` (integer, required): Restaurant ID
- `context` (object, optional): Additional context
  - `weather` (object): Weather data (temp, condition)

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "bot_message": {
      "content": "Good afternoon! Here are some satisfying midday options for lunch:\n\n🍽️ **Phở Bò Đặc Biệt** - 85000 VND\n⭐ Excellent rating (4.8/5) | 🌟 Featured item\n\nWould you like more details about any of these dishes?",
      "message_type": "text",
      "suggestions": [
        {
          "item_id": 5,
          "name": "Phở Bò Đặc Biệt",
          "price": "85000",
          "reason": "⭐ Excellent rating (4.8/5) | 🌟 Featured item"
        }
      ]
    },
    "intent": "recommendation",
    "confidence_score": 0.92,
    "is_escalated": false
  }
}
```

**Example Messages to Test:**

```json
// FAQ - Hours
{
  "message": "What are your opening hours?",
  "restaurant_id": 1
}

// FAQ - Location
{
  "message": "Where are you located?",
  "restaurant_id": 1
}

// FAQ - Delivery
{
  "message": "Do you deliver? What is the fee?",
  "restaurant_id": 1
}

// Recommendation
{
  "message": "What do you recommend for a cold rainy day?",
  "restaurant_id": 1,
  "context": {
    "weather": {
      "temp": 12,
      "condition": "rainy"
    }
  }
}

// Dietary preference
{
  "message": "I want something vegetarian for lunch under 100k",
  "restaurant_id": 1
}

// Order help
{
  "message": "How can I track my order?",
  "restaurant_id": 1
}
```

---

### 2. Get Conversation Context

Retrieve conversation context and history.

**Endpoint:**
```
GET {{base_url}}/api/chat/chatbot/rooms/{room_id}/context/
```

**Request Headers:**
```
Authorization: Bearer {your_token}
```

**Path Parameters:**
- `room_id` (integer): Chat room ID

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "room_id": 1,
    "room_status": "active",
    "room_type": "general",
    "message_count": 5,
    "conversation_history": [
      {
        "role": "user",
        "content": "What do you recommend?",
        "created_at": "2026-01-05T16:30:00Z"
      },
      {
        "role": "assistant",
        "content": "Based on your preferences...",
        "created_at": "2026-01-05T16:30:02Z"
      }
    ]
  }
}
```

---

### 3. Submit Feedback

Submit feedback on chatbot recommendations.

**Endpoint:**
```
POST {{base_url}}/api/chat/chatbot/feedback/
```

**Request Headers:**
```
Authorization: Bearer {your_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "room_id": 1,
  "restaurant_id": 1,
  "feedback_type": "recommendation",
  "rating": 5,
  "suggested_items": [5, 8, 12],
  "accepted_items": [5],
  "intent": "recommendation",
  "user_comment": "Great recommendations!"
}
```

**Body Parameters:**
- `room_id` (integer, required): Chat room ID
- `restaurant_id` (integer, required): Restaurant ID
- `feedback_type` (string, required): `recommendation`, `response`, or `escalation`
- `rating` (integer, required): 1-5 rating
- `suggested_items` (array, optional): List of suggested item IDs
- `accepted_items` (array, optional): List of accepted item IDs
- `intent` (string, optional): Intent that triggered the response
- `user_comment` (string, optional): User's feedback comment

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "feedback_type": "recommendation",
    "rating": 5,
    "created_at": "2026-01-05T16:30:00Z"
  },
  "message": "Feedback recorded successfully"
}
```

---

## Testing Examples

### Example 1: Complete Recommendation Flow

**Step 1: Send Lunch Recommendation Request**
```
POST /api/chat/chatbot/rooms/1/message/
```
```json
{
  "message": "What do you recommend for lunch?",
  "restaurant_id": 1
}
```

**Step 2: Check Context**
```
GET /api/chat/chatbot/rooms/1/context/
```

**Step 3: Submit Feedback**
```
POST /api/chat/chatbot/feedback/
```
```json
{
  "room_id": 1,
  "restaurant_id": 1,
  "feedback_type": "recommendation",
  "rating": 5,
  "suggested_items": [5],
  "accepted_items": [5]
}
```

### Example 2: Weather-Aware Recommendation

```
POST /api/chat/chatbot/rooms/1/message/
```
```json
{
  "message": "What do you recommend for this weather?",
  "restaurant_id": 1,
  "context": {
    "weather": {
      "temp": 35,
      "condition": "clear"
    }
  }
}
```

**Expected Response:** Light, refreshing dishes (salads, cold drinks)

### Example 3: Escalation Test

```
POST /api/chat/chatbot/rooms/1/message/
```
```json
{
  "message": "I want to speak to a human person",
  "restaurant_id": 1
}
```

**Expected Response:** Escalation message, `is_escalated: true`

### Example 4: FAQ Flow

**Test Opening Hours:**
```json
{
  "message": "What time do you open?",
  "restaurant_id": 1
}
```

**Test Location:**
```json
{
  "message": "Where is your restaurant?",
  "restaurant_id": 1
}
```

**Test Delivery:**
```json
{
  "message": "Do you deliver to my area?",
  "restaurant_id": 1
}
```

---

## Postman Collection

Import this collection to get started quickly:

**Collection JSON:**
```json
{
  "info": {
    "name": "Restaurant Chatbot API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "base_url",
      "value": "http://localhost:8000",
      "type": "string"
    },
    {
      "key": "token",
      "value": "your_jwt_token_here",
      "type": "string"
    }
  ],
  "item": [
    {
      "name": "Authentication",
      "item": [
        {
          "name": "Login",
          "request": {
            "method": "POST",
            "header": [],
            "url": {
              "raw": "{{base_url}}/api/auth/login/",
              "host": ["{{base_url}}"],
              "path": ["api", "auth", "login", ""]
            },
            "body": {
              "mode": "raw",
              "raw": "{\n  \"username\": \"test\",\n  \"password\": \"your_password\"\n}"
            }
          }
        }
      ]
    },
    {
      "name": "Chatbot Messages",
      "item": [
        {
          "name": "Send Message",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Authorization",
                "value": "Bearer {{token}}"
              }
            ],
            "url": {
              "raw": "{{base_url}}/api/chat/chatbot/rooms/1/message/",
              "host": ["{{base_url}}"],
              "path": ["api", "chat", "chatbot", "rooms", "1", "message", ""]
            },
            "body": {
              "mode": "raw",
              "raw": "{\n  \"message\": \"What do you recommend?\",\n  \"restaurant_id\": 1\n}"
            }
          }
        },
        {
          "name": "Get Context",
          "request": {
            "method": "GET",
            "header": [
              {
                "key": "Authorization",
                "value": "Bearer {{token}}"
              }
            ],
            "url": {
              "raw": "{{base_url}}/api/chat/chatbot/rooms/1/context/",
              "host": ["{{base_url}}"],
              "path": ["api", "chat", "chatbot", "rooms", "1", "context", ""]
            }
          }
        }
      ]
    },
    {
      "name": "Feedback",
      "item": [
        {
          "name": "Submit Feedback",
          "request": {
            "method": "POST",
            "header": [
              {
                "key": "Authorization",
                "value": "Bearer {{token}}"
              }
            ],
            "url": {
              "raw": "{{base_url}}/api/chat/chatbot/feedback/",
              "host": ["{{base_url}}"],
              "path": ["api", "chat", "chatbot", "feedback", ""]
            },
            "body": {
              "mode": "raw",
              "raw": "{\n  \"room_id\": 1,\n  \"restaurant_id\": 1,\n  \"feedback_type\": \"recommendation\",\n  \"rating\": 5\n}"
            }
          }
        }
      ]
    }
  ]
}
```

---

## Common Issues

### Issue 1: 401 Unauthorized

**Solution:** Make sure you have a valid JWT token and added it to Authorization header.

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Issue 2: 404 Chat Room Not Found

**Solution:** Create a chat room first or use an existing room ID.

**Create Room via Django Admin:**
1. Go to `http://localhost:8000/admin/`
2. Navigate to Chat Rooms
3. Create a new room for your user

**Or use the test script to auto-create:**
```bash
python test_real_http.py
```

### Issue 3: 429 Too Many Requests

**Solution:** Rate limiting is active. Wait before sending more requests.

**Rate Limits:**
- Burst: 10 requests/minute
- Sustained: 100 requests/hour
- Per-room: 20 requests/minute

### Issue 4: No Recommendations Returned

**Possible Causes:**
- No menu items in database for the restaurant
- All filters too restrictive (e.g., vegetarian + spicy + under 50k)

**Solution:** Check menu data exists:
```
GET {{base_url}}/api/dishes/menu-items/?restaurant_id=1
```

---

## Quick Test Checklist

- [ ] Login and get JWT token
- [ ] Add token to Authorization header
- [ ] Test FAQ: Opening hours
- [ ] Test FAQ: Location
- [ ] Test FAQ: Delivery
- [ ] Test Recommendation: General
- [ ] Test Recommendation: Weather context
- [ ] Test Recommendation: Dietary preferences
- [ ] Test Escalation: "I want to speak to human"
- [ ] Check conversation context
- [ ] Submit feedback

---

## Tips for Testing

1. **Use Environment Variables**: Set `base_url` and `token` in Postman environment
2. **Save Responses**: Enable "Save responses" to see full response history
3. **Use Tests Tab**: Add automated tests to verify responses
4. **Test Edge Cases**: Empty messages, very long messages, special characters
5. **Verify Rate Limiting**: Send rapid requests to test throttling
6. **Check Admin Panel**: View recorded data at `/admin/`

---

## Response Time Expectations

- FAQ responses: < 1 second (template-based)
- Recommendations: 2-5 seconds (database queries + GLM API)
- Context retrieval: < 500ms
- Feedback submission: < 500ms

**Note:** First request might be slower due to cold start.

---

## Need Help?

Check these resources:
- **Admin Panel**: `http://localhost:8000/admin/`
- **API Root**: `http://localhost:8000/api/`
- **Test Scripts**: `test_real_http.py`, `test_phase3_features.py`, `test_phase4_features.py`
