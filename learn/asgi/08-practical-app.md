# Module 8: Building Complete Applications

## Introduction

This final module brings together everything you've learned to build complete, production-ready ASGI applications. We'll combine HTTP, WebSocket, Lifespan, middleware, and best practices into working examples.

## Project Structure

A well-organized ASGI project:

```
my_asgi_app/
├── app/
│   ├── __init__.py
│   ├── main.py           # Application entry point
│   ├── routes.py         # HTTP route handlers
│   ├── websockets.py     # WebSocket handlers
│   ├── middleware.py     # Custom middleware
│   ├── database.py       # Database connection
│   └── models.py         # Data models
├── tests/
│   ├── __init__.py
│   ├── test_http.py
│   └── test_websockets.py
├── requirements.txt      # Dependencies
├── pyproject.toml        # Project metadata
└── README.md
```

## Complete Example: Task Manager API

Let's build a full task manager with HTTP API and real-time WebSocket updates.

### 1. Application Structure

```python
# app/main.py
"""
Task Manager ASGI Application
- HTTP API for CRUD operations
- WebSocket for real-time updates
- In-memory storage with lifespan management
"""

import json
from typing import Dict, List, Any
from datetime import datetime
import asyncio


class TaskManager:
    """Central task storage and management."""
    
    def __init__(self):
        self.tasks: Dict[int, Dict[str, Any]] = {}
        self.next_id = 1
        self.subscribers = []  # WebSocket connections
    
    def create_task(self, title: str, description: str = "") -> Dict[str, Any]:
        """Create a new task."""
        task = {
            'id': self.next_id,
            'title': title,
            'description': description,
            'completed': False,
            'created_at': datetime.now().isoformat()
        }
        self.tasks[self.next_id] = task
        self.next_id += 1
        
        # Notify subscribers
        asyncio.create_task(self.broadcast({
            'type': 'task.created',
            'task': task
        }))
        
        return task
    
    def get_task(self, task_id: int) -> Dict[str, Any] | None:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def list_tasks(self) -> List[Dict[str, Any]]:
        """List all tasks."""
        return list(self.tasks.values())
    
    def update_task(self, task_id: int, **updates) -> Dict[str, Any] | None:
        """Update a task."""
        task = self.tasks.get(task_id)
        if task:
            task.update(updates)
            task['updated_at'] = datetime.now().isoformat()
            
            # Notify subscribers
            asyncio.create_task(self.broadcast({
                'type': 'task.updated',
                'task': task
            }))
            
            return task
        return None
    
    def delete_task(self, task_id: int) -> bool:
        """Delete a task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            
            # Notify subscribers
            asyncio.create_task(self.broadcast({
                'type': 'task.deleted',
                'task_id': task_id
            }))
            
            return True
        return False
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all WebSocket subscribers."""
        message_text = json.dumps(message)
        for send_func in self.subscribers[:]:  # Copy list to avoid modification during iteration
            try:
                await send_func({
                    'type': 'websocket.send',
                    'text': message_text
                })
            except Exception:
                # Remove failed subscribers
                self.subscribers.remove(send_func)


class Application:
    """Main ASGI application."""
    
    def __init__(self):
        self.task_manager = None
    
    async def __call__(self, scope, receive, send):
        """ASGI application entry point."""
        
        if scope['type'] == 'lifespan':
            await self.handle_lifespan(scope, receive, send)
        
        elif scope['type'] == 'http':
            await self.handle_http(scope, receive, send)
        
        elif scope['type'] == 'websocket':
            await self.handle_websocket(scope, receive, send)
        
        else:
            raise NotImplementedError(f"Unsupported scope type: {scope['type']}")
    
    async def handle_lifespan(self, scope, receive, send):
        """Handle application lifecycle."""
        while True:
            message = await receive()
            
            if message['type'] == 'lifespan.startup':
                # Initialize task manager
                self.task_manager = TaskManager()
                scope['state']['task_manager'] = self.task_manager
                print("✅ Task Manager initialized")
                await send({'type': 'lifespan.startup.complete'})
            
            elif message['type'] == 'lifespan.shutdown':
                print("🛑 Shutting down Task Manager")
                await send({'type': 'lifespan.shutdown.complete'})
                return
    
    async def handle_http(self, scope, receive, send):
        """Handle HTTP requests."""
        method = scope['method']
        path = scope['path']
        task_manager = scope['state'].get('task_manager')
        
        if not task_manager:
            await self.send_error(send, 500, "Task manager not initialized")
            return
        
        # Route requests
        if path == '/health':
            await self.health_check(scope, receive, send)
        
        elif path == '/tasks':
            if method == 'GET':
                await self.list_tasks(task_manager, receive, send)
            elif method == 'POST':
                await self.create_task(task_manager, receive, send)
            else:
                await self.send_error(send, 405, "Method not allowed")
        
        elif path.startswith('/tasks/'):
            # Extract task ID
            try:
                task_id = int(path.split('/')[-1])
            except ValueError:
                await self.send_error(send, 400, "Invalid task ID")
                return
            
            if method == 'GET':
                await self.get_task(task_manager, task_id, receive, send)
            elif method == 'PUT':
                await self.update_task(task_manager, task_id, receive, send)
            elif method == 'DELETE':
                await self.delete_task(task_manager, task_id, receive, send)
            else:
                await self.send_error(send, 405, "Method not allowed")
        
        else:
            await self.send_error(send, 404, "Not found")
    
    async def health_check(self, scope, receive, send):
        """Health check endpoint."""
        await self.send_json(send, {'status': 'healthy'})
    
    async def list_tasks(self, task_manager, receive, send):
        """GET /tasks - List all tasks."""
        tasks = task_manager.list_tasks()
        await self.send_json(send, {'tasks': tasks})
    
    async def create_task(self, task_manager, receive, send):
        """POST /tasks - Create a new task."""
        # Read request body
        body = await self.read_body(receive)
        
        try:
            data = json.loads(body.decode())
            title = data.get('title')
            description = data.get('description', '')
            
            if not title:
                await self.send_error(send, 400, "Title is required")
                return
            
            task = task_manager.create_task(title, description)
            await self.send_json(send, task, status=201)
        
        except json.JSONDecodeError:
            await self.send_error(send, 400, "Invalid JSON")
    
    async def get_task(self, task_manager, task_id, receive, send):
        """GET /tasks/{id} - Get a specific task."""
        task = task_manager.get_task(task_id)
        
        if task:
            await self.send_json(send, task)
        else:
            await self.send_error(send, 404, "Task not found")
    
    async def update_task(self, task_manager, task_id, receive, send):
        """PUT /tasks/{id} - Update a task."""
        body = await self.read_body(receive)
        
        try:
            updates = json.loads(body.decode())
            task = task_manager.update_task(task_id, **updates)
            
            if task:
                await self.send_json(send, task)
            else:
                await self.send_error(send, 404, "Task not found")
        
        except json.JSONDecodeError:
            await self.send_error(send, 400, "Invalid JSON")
    
    async def delete_task(self, task_manager, task_id, receive, send):
        """DELETE /tasks/{id} - Delete a task."""
        success = task_manager.delete_task(task_id)
        
        if success:
            await self.send_json(send, {'message': 'Task deleted'})
        else:
            await self.send_error(send, 404, "Task not found")
    
    async def handle_websocket(self, scope, receive, send):
        """Handle WebSocket connections for real-time updates."""
        task_manager = scope['state'].get('task_manager')
        
        if not task_manager:
            await send({'type': 'websocket.close', 'code': 1011})
            return
        
        # Accept connection
        await send({'type': 'websocket.accept'})
        
        # Add to subscribers
        task_manager.subscribers.append(send)
        
        # Send current tasks
        tasks = task_manager.list_tasks()
        await send({
            'type': 'websocket.send',
            'text': json.dumps({
                'type': 'initial_state',
                'tasks': tasks
            })
        })
        
        try:
            # Keep connection alive
            while True:
                message = await receive()
                
                if message['type'] == 'websocket.disconnect':
                    break
                
                elif message['type'] == 'websocket.receive':
                    # Echo received messages (could handle commands here)
                    text = message.get('text', '')
                    print(f"WebSocket received: {text}")
        
        finally:
            # Remove from subscribers
            if send in task_manager.subscribers:
                task_manager.subscribers.remove(send)
    
    # Helper methods
    
    async def read_body(self, receive):
        """Read full request body."""
        body = b''
        more_body = True
        
        while more_body:
            message = await receive()
            body += message.get('body', b'')
            more_body = message.get('more_body', False)
        
        return body
    
    async def send_json(self, send, data, status=200):
        """Send JSON response."""
        body = json.dumps(data).encode()
        
        await send({
            'type': 'http.response.start',
            'status': status,
            'headers': [
                [b'content-type', b'application/json'],
                [b'content-length', str(len(body)).encode()],
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': body,
        })
    
    async def send_error(self, send, status, message):
        """Send error response."""
        await self.send_json(send, {'error': message}, status=status)


# Create application instance
app = Application()
```

### 2. Running the Application

```bash
uvicorn app.main:app --reload
```

### 3. Testing the API

```bash
# Health check
curl http://localhost:8000/health
# {"status": "healthy"}

# Create a task
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Learn ASGI", "description": "Complete all modules"}'
# {"id": 1, "title": "Learn ASGI", ...}

# List tasks
curl http://localhost:8000/tasks
# {"tasks": [{...}]}

# Get a specific task
curl http://localhost:8000/tasks/1
# {"id": 1, "title": "Learn ASGI", ...}

# Update a task
curl -X PUT http://localhost:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"completed": true}'
# {"id": 1, "title": "Learn ASGI", "completed": true, ...}

# Delete a task
curl -X DELETE http://localhost:8000/tasks/1
# {"message": "Task deleted"}
```

### 4. Testing WebSocket

```javascript
// In browser console
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
    console.log('Connected!');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};

// You'll see real-time updates when tasks change via the HTTP API!
```

## Adding Middleware

Enhance the application with middleware:

```python
# app/middleware.py

import time
import logging

logger = logging.getLogger(__name__)


class LoggingMiddleware:
    """Log all requests."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            method = scope['method']
            path = scope['path']
            start = time.time()
            
            logger.info(f"→ {method} {path}")
            
            try:
                await self.app(scope, receive, send)
            finally:
                duration = time.time() - start
                logger.info(f"← {method} {path} ({duration:.3f}s)")
        else:
            await self.app(scope, receive, send)


class CORSMiddleware:
    """Add CORS headers."""
    
    def __init__(self, app, allow_origins='*'):
        self.app = app
        self.allow_origins = allow_origins
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            async def send_wrapper(message):
                if message['type'] == 'http.response.start':
                    headers = list(message.get('headers', []))
                    headers.append([b'access-control-allow-origin', self.allow_origins.encode()])
                    headers.append([b'access-control-allow-methods', b'GET, POST, PUT, DELETE'])
                    headers.append([b'access-control-allow-headers', b'*'])
                    message['headers'] = headers
                await send(message)
            
            if scope['method'] == 'OPTIONS':
                await send_wrapper({
                    'type': 'http.response.start',
                    'status': 200,
                    'headers': [],
                })
                await send_wrapper({
                    'type': 'http.response.body',
                    'body': b'',
                })
            else:
                await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


# In main.py, wrap the app:
# app = CORSMiddleware(app)
# app = LoggingMiddleware(app)
```

## Dependencies File

Create `requirements.txt` for uv:

```txt
uvicorn>=0.30.0
```

Install with:
```bash
uv pip install -r requirements.txt
```

## Project Configuration

Create `pyproject.toml`:

```toml
[project]
name = "asgi-task-manager"
version = "0.1.0"
description = "Task manager built with pure ASGI"
requires-python = ">=3.14"
dependencies = [
    "uvicorn>=0.30.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]
```

## Testing

```python
# tests/test_http.py

import asyncio
import json
import pytest


async def call_asgi(app, method='GET', path='/', body=b''):
    """Helper to call ASGI app."""
    scope = {
        'type': 'http',
        'asgi': {'version': '3.0'},
        'method': method,
        'path': path,
        'query_string': b'',
        'headers': [[b'content-type', b'application/json']],
        'server': ('test', 80),
        'client': ('test', 12345),
        'state': {}
    }
    
    response_status = None
    response_body = b''
    
    async def receive():
        return {'type': 'http.request', 'body': body, 'more_body': False}
    
    async def send(message):
        nonlocal response_status, response_body
        if message['type'] == 'http.response.start':
            response_status = message['status']
        elif message['type'] == 'http.response.body':
            response_body += message.get('body', b'')
    
    # Initialize lifespan
    await app(
        {'type': 'lifespan', 'state': scope['state']},
        lambda: asyncio.coroutine(lambda: {'type': 'lifespan.startup'})(),
        lambda msg: asyncio.coroutine(lambda: None)()
    )
    
    await app(scope, receive, send)
    
    return response_status, response_body


@pytest.mark.asyncio
async def test_health_check():
    from app.main import Application
    
    app = Application()
    status, body = await call_asgi(app, 'GET', '/health')
    
    assert status == 200
    data = json.loads(body)
    assert data['status'] == 'healthy'


@pytest.mark.asyncio
async def test_create_task():
    from app.main import Application
    
    app = Application()
    
    task_data = json.dumps({'title': 'Test Task'}).encode()
    status, body = await call_asgi(app, 'POST', '/tasks', task_data)
    
    assert status == 201
    data = json.loads(body)
    assert data['title'] == 'Test Task'
    assert 'id' in data
```

## Best Practices Summary

### 1. Error Handling

```python
# Always wrap in try/except
try:
    await self.app(scope, receive, send)
except Exception as exc:
    logger.error(f"Error: {exc}")
    # Send error response if not already started
```

### 2. Resource Management

```python
# Use lifespan for initialization/cleanup
# Store shared resources in scope['state']
# Use connection pools, not per-request connections
```

### 3. Validation

```python
# Validate input data
if not title or len(title) > 200:
    return error_response("Invalid title")
```

### 4. Logging

```python
# Log important events
logger.info(f"Task {task_id} created by {user_id}")
logger.error(f"Failed to process request: {exc}")
```

### 5. Security

```python
# Validate authentication
# Sanitize input
# Use HTTPS in production
# Set security headers
```

## Deployment

For production deployment with uvicorn:

```bash
# With multiple workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# With Unix socket
uvicorn app.main:app --uds /tmp/uvicorn.sock

# Behind nginx/caddy
# Use --proxy-headers to trust X-Forwarded-* headers
uvicorn app.main:app --proxy-headers --forwarded-allow-ips='*'
```

## Key Takeaways

1. ✅ **Structure code** into modules (routes, models, middleware)
2. ✅ **Use lifespan** for resource initialization
3. ✅ **Combine protocols** (HTTP + WebSocket) in one app
4. ✅ **Share state** via scope['state']
5. ✅ **Add middleware** for cross-cutting concerns
6. ✅ **Test thoroughly** with helper functions
7. ✅ **Handle errors** gracefully
8. ✅ **Use uv** for dependency management

## Congratulations! 🎉

You've completed the ASGI learning path! You now have a solid understanding of:

- ✅ ASGI fundamentals and interface
- ✅ HTTP, WebSocket, and Lifespan protocols
- ✅ Scope, receive, and send callables
- ✅ Middleware patterns
- ✅ Advanced features and extensions
- ✅ Building complete applications

## Next Steps

1. **Explore frameworks** like Starlette or FastAPI (built on ASGI)
2. **Build your own projects** using pure ASGI
3. **Contribute to uvicorn** - you understand how it works now!
4. **Read the ASGI spec** in detail for edge cases
5. **Study production apps** to see patterns in action

## Additional Resources

- [ASGI Specification](https://asgi.readthedocs.io/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [Starlette](https://www.starlette.io/) - ASGI framework
- [FastAPI](https://fastapi.tiangolo.com/) - API framework on ASGI
- [Uvicorn Source Code](https://github.com/encode/uvicorn)

Thank you for learning ASGI! 🚀

