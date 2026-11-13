# ASGI Examples

This directory contains complete ASGI applications from beginner to production-ready. **Start with the simulation to understand the fundamentals before using uvicorn!**

## Learning Path 📚

Follow this order for the best learning experience:

1. **asgi_simulation.py** ⭐ **START HERE** - Pure Python (no server!)
2. **simple_http_app.py** - First real HTTP app with uvicorn
3. **websocket_chat.py** - WebSocket real-time chat
4. **full_application.py** - Production-ready complete app

## Setup

### For the Simulation (No Setup Needed!)

The simulation requires only Python 3.7+, no additional dependencies:

```bash
python asgi_simulation.py
```

### For Real HTTP/WebSocket Examples

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment with Python 3.14
uv venv --python 3.14
source .venv/bin/activate  # On Unix/macOS

# Install uvicorn
uv pip install uvicorn
```

## Examples

### asgi_simulation.py ⭐ **START HERE**

**Why start here:** Understand ASGI fundamentals without web server complexity!

A complete simulation showing how ASGI works using pure Python. You'll see:
- How a server creates `scope`, `receive`, and `send`
- How your app uses these to handle requests
- What messages are exchanged
- The complete ASGI contract in action

**Features:**
- No uvicorn needed - pure Python!
- Multiple example apps (hello world, echo, streaming, routing)
- Detailed logging of all ASGI messages
- Shows exactly what happens behind the scenes

**Run:**
```bash
python asgi_simulation.py
```

**Output:** You'll see the complete message flow between server and app:
```
Example 1: Simple Hello World App
[SERVER] Starting request handling
[SERVER] Scope: GET /hello
[SERVER] Calling ASGI app...
[SERVER] Received message from app: http.response.start
  → Status: HTTP 200
  → Header: content-type: text/plain
[SERVER] Received message from app: http.response.body
  → Body: Hello, ASGI World!
```

**What you'll learn:**
- The ASGI contract is just: `async def app(scope, receive, send)`
- How servers and apps communicate through messages
- Why ASGI is protocol-agnostic
- How streaming works with `more_body`

---

### simple_http_app.py

A simple HTTP application with routing and JSON API.

**Features:**
- Multiple routes
- JSON responses
- Query parameter parsing
- Error handling

**Run:**
```bash
uvicorn examples.simple_http_app:app --reload
```

**Test:**
```bash
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/api/users
curl "http://localhost:8000/greet?name=Alice"
```

---

### websocket_chat.py

A complete WebSocket chat application with rooms.

**Features:**
- Multiple chat rooms
- User authentication
- Join/leave notifications
- Message history
- User list

**Run:**
```bash
uvicorn examples.websocket_chat:app --reload
```

**Test (JavaScript in browser console):**
```javascript
// User 1
const ws1 = new WebSocket('ws://localhost:8000/ws?room=general&user=Alice&token=secret123');
ws1.onmessage = (e) => console.log('Alice:', e.data);
ws1.send('Hello!');

// User 2
const ws2 = new WebSocket('ws://localhost:8000/ws?room=general&user=Bob&token=secret123');
ws2.onmessage = (e) => console.log('Bob:', e.data);
ws2.send('Hi Alice!');
```

**HTTP Endpoints:**
```bash
# View instructions
curl http://localhost:8000/

# List active rooms
curl http://localhost:8000/rooms
```

---

### full_application.py

A complete production-ready application combining all ASGI concepts.

**Features:**
- HTTP REST API (CRUD)
- WebSocket real-time updates
- Lifespan management
- Middleware stack (logging, CORS, errors)
- Authentication
- Database simulation

**Run:**
```bash
uvicorn examples.full_application:app --reload
```

**HTTP API (with authentication):**
```bash
# Health check (no auth required)
curl http://localhost:8000/health

# Create task
curl -X POST http://localhost:8000/api/tasks \
  -H "Authorization: Bearer secret-token" \
  -H "Content-Type: application/json" \
  -d '{"title": "Learn ASGI", "description": "Complete all modules"}'

# List tasks
curl http://localhost:8000/api/tasks \
  -H "Authorization: Bearer secret-token"

# Get task
curl http://localhost:8000/api/tasks/1 \
  -H "Authorization: Bearer secret-token"

# Update task
curl -X PUT http://localhost:8000/api/tasks/1 \
  -H "Authorization: Bearer secret-token" \
  -H "Content-Type: application/json" \
  -d '{"completed": true}'

# Delete task
curl -X DELETE http://localhost:8000/api/tasks/1 \
  -H "Authorization: Bearer secret-token"
```

**WebSocket (real-time updates):**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Update:', data);
};

// You'll receive real-time updates when tasks change!
```

## Key Concepts Demonstrated

### asgi_simulation.py
- ✅ The ASGI contract (`scope`, `receive`, `send`)
- ✅ Message-based communication
- ✅ How servers call apps
- ✅ Request body reading with `receive()`
- ✅ Response streaming with `send()`
- ✅ The `more_body` flag
- ✅ Pure Python - no network complexity

### simple_http_app.py
- ✅ HTTP routing
- ✅ JSON API
- ✅ Query parameters
- ✅ Error handling
- ✅ Status codes

### websocket_chat.py
- ✅ WebSocket connections
- ✅ Broadcast messaging
- ✅ Connection management
- ✅ Authentication
- ✅ Room-based chat
- ✅ Message history

### full_application.py
- ✅ Complete CRUD API
- ✅ WebSocket integration
- ✅ Lifespan management
- ✅ Middleware stack
- ✅ Authentication
- ✅ Database operations
- ✅ Real-time updates
- ✅ Error handling
- ✅ CORS support
- ✅ Logging

## Testing Tips

1. **Use curl** for HTTP endpoints
2. **Use browser console** for WebSocket testing
3. **Check server logs** for debugging
4. **Use --reload** during development
5. **Test error cases** (invalid auth, missing fields, etc.)

## Production Considerations

When deploying these applications:

1. **Use environment variables** for secrets
2. **Replace in-memory storage** with real database
3. **Add rate limiting**
4. **Enable HTTPS**
5. **Use multiple workers**
6. **Add monitoring and metrics**
7. **Implement proper authentication** (JWT, OAuth, etc.)
8. **Add input validation**
9. **Set up logging** to files or services
10. **Use a reverse proxy** (nginx, caddy)

## Next Steps

After exploring these examples:

1. **Build your own application** combining concepts
2. **Explore ASGI frameworks** like Starlette or FastAPI
3. **Read uvicorn source code** to understand implementation
4. **Contribute to open source** ASGI projects
5. **Deploy to production** with proper configuration

## Resources

- [ASGI Specification](https://asgi.readthedocs.io/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [Starlette Framework](https://www.starlette.io/)
- [FastAPI Framework](https://fastapi.tiangolo.com/)

