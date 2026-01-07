# Realtime Live Chat - Implementation Complete

## Overview

Implemented WebSocket-based realtime chat between customers and staff using Django Channels. Any logged-in staff member can view and respond to any chat room.

## What Was Implemented

### 1. Dependencies & Configuration
- ✅ Django Channels installed
- ✅ Channels Redis configured (using existing Redis)
- ✅ ASGI application configured
- ✅ WebSocket routing set up

### 2. Database Models
- ✅ `OnlinePresence` model - tracks online users
- ✅ Migration created and applied

### 3. WebSocket Consumers
- ✅ `ChatConsumer` - Handles chat room messaging
- ✅ `OnlinePresenceConsumer` - Tracks online/offline status

### 4. REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/rooms/` | GET | List user's chat rooms |
| `/api/chat/rooms/` | POST | Create new chat room |
| `/api/chat/rooms/{id}/` | GET | Get room details |
| `/api/chat/rooms/{id}/messages/` | GET | Get message history |
| `/api/chat/rooms/{id}/join/` | POST | Staff joins room |
| `/api/chat/rooms/{id}/leave/` | POST | Staff leaves room |
| `/api/chat/rooms/{id}/close/` | POST | Close room |
| `/api/chat/rooms/{id}/send_message/` | POST | Send message via REST |
| `/api/chat/rooms/{id}/mark_read/` | POST | Mark messages as read |
| `/api/chat/online-staff/` | GET | List online staff |
| `/api/chat/active-rooms/` | GET | List active rooms (staff) |

### 5. WebSocket Endpoints

| Endpoint | Description |
|----------|-------------|
| `ws://host/ws/chat/{room_id}/?token={jwt}` | Connect to chat room |
| `ws://host/ws/presence/?token={jwt}` | Track online presence |

## WebSocket Events

### Send to Server:
```json
// Send message
{"type": "message", "content": "Hello"}

// Typing indicator
{"type": "typing", "is_typing": true}

// Mark as read
{"type": "read", "message_id": 123}
```

### Receive from Server:
```json
// New message
{"type": "message", "data": {...}}

// Typing indicator
{"type": "typing", "data": {"user_id": 1, "is_typing": true}}

// Read receipt
{"type": "read_receipt", "data": {"user_id": 1}}

// Presence update
{"type": "presence", "data": {"user_id": 1, "is_online": true}}

// Error
{"type": "error", "data": {"message": "Error message"}}
```

## How to Run

### 1. Start Redis (if not running)
```bash
redis-server
```

### 2. Start Django with ASGI
```bash
# Use daphne (recommended) for production:
pip install daphne
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# Or use runserver with ASGI (development only):
python manage.py runserver ASGI/HTTP/0.0.0.0:8000
```

### 3. Start Celery (optional, for background tasks)
```bash
celery -A config worker -l info
```

## Files Created/Modified

### New Files:
- `apps/chat/consumers.py` - WebSocket consumers
- `apps/chat/routing.py` - WebSocket URL routing
- `apps/chat/migrations/0008_add_online_presence.py` - OnlinePresence migration

### Modified Files:
- `config/settings/base.py` - Added Channels config
- `config/asgi.py` - Added WebSocket routing
- `apps/chat/models.py` - Added OnlinePresence model
- `apps/chat/serializers.py` - Added live chat serializers
- `apps/chat/views.py` - Added live chat views
- `apps/chat/urls.py` - Added live chat URLs
- `requirements/requirements.txt` - Add: `channels>=4.0.0, channels-redis>=4.0.0`

## Testing

### Create a Chat Room (Customer)
```bash
curl -X POST http://localhost:8000/api/chat/rooms/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"room_type": "general", "subject": "Help needed"}'
```

### Get Online Staff
```bash
curl http://localhost:8000/api/chat/online-staff/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Get Active Rooms (Staff)
```bash
curl http://localhost:8000/api/chat/active-rooms/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## WebSocket Client Example (JavaScript)

```javascript
// Connect to chat room
const token = 'YOUR_JWT_TOKEN';
const roomId = 1;
const ws = new WebSocket(`ws://localhost:8000/ws/chat/${roomId}/?token=${token}`);

// Connection opened
ws.onopen = () => {
    console.log('Connected to chat room');
};

// Receive messages
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);

    switch(data.type) {
        case 'message':
            displayMessage(data.data);
            break;
        case 'typing':
            showTypingIndicator(data.data);
            break;
        case 'read_receipt':
            markAsRead(data.data);
            break;
        case 'presence':
            updatePresence(data.data);
            break;
        case 'error':
            console.error('Error:', data.data.message);
            break;
    }
};

// Send message
function sendMessage(content) {
    ws.send(JSON.stringify({
        type: 'message',
        content: content
    }));
}

// Send typing indicator
function setTyping(isTyping) {
    ws.send(JSON.stringify({
        type: 'typing',
        is_typing: isTyping
    }));
}

// Mark messages as read
function markAsRead(messageId) {
    ws.send(JSON.stringify({
        type: 'read',
        message_id: messageId
    }));
}
```

## Access Control

### Customers:
- Can only see their own chat rooms
- Can create rooms, send messages, close rooms
- Cannot join other rooms

### Staff:
- Can see ALL chat rooms
- Can join any room to respond
- Can leave rooms
- Can close rooms
- No assignment needed - any staff can respond

## Next Steps

1. **Install daphne** for production WebSocket server:
   ```bash
   pip install daphne
   ```

2. **Test the WebSocket connection** using a WebSocket client or browser console

3. **Implement frontend** using the WebSocket client example above

4. **Consider SSL/TLS** for WebSocket in production (wss:// instead of ws://)

## Troubleshooting

### WebSocket connection refused
- Make sure Redis is running
- Check ASGI application is configured correctly
- Verify JWT token is valid

### Messages not delivered in real-time
- Check Redis is running
- Verify Channels layer is configured
- Check browser console for WebSocket errors

### Permission denied
- Verify user is authenticated
- Check if user is staff for staff-only endpoints

---

**Implementation complete!** The chat system is ready to use.
