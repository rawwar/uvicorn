# Module 7: Advanced ASGI Concepts

## Introduction

This module covers advanced ASGI features and patterns that go beyond the basics. These concepts are used in production applications for performance, reliability, and advanced functionality.

Topics covered:
- ASGI Extensions
- Advanced State Management
- HTTP/2 Server Push
- HTTP Trailers
- Flow Control and Backpressure
- Connection Events
- Multiple Applications
- Testing ASGI Applications

## ASGI Extensions

Extensions allow servers and applications to negotiate optional features. The `extensions` field in the scope dictionary indicates what extensions are available.

### Checking for Extensions

```python
async def app(scope, receive, send):
    if scope['type'] == 'http':
        extensions = scope.get('extensions', {})
        
        # Check if server push is available
        if 'http.response.push' in extensions:
            # Server push is supported
            print("Server push available!")
        
        # Check for other extensions
        if 'http.response.trailers' in extensions:
            print("Trailers supported!")
        
        # Normal response
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'text/plain']],
        })
        await send({
            'type': 'http.response.body',
            'body': b'Hello!',
        })
```

### Common Extensions

| Extension | Description |
|-----------|-------------|
| `http.response.push` | HTTP/2 server push support |
| `http.response.trailers` | HTTP trailers support |
| `websocket.http.response` | WebSocket HTTP response for rejecting connections |

## HTTP/2 Server Push

Server push allows the server to proactively send resources to the client:

```python
async def app(scope, receive, send):
    if scope['type'] == 'http':
        # Start response
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'text/html']],
        })
        
        # Push CSS file (if supported)
        extensions = scope.get('extensions', {})
        if 'http.response.push' in extensions:
            await send({
                'type': 'http.response.push',
                'path': '/static/style.css',
                'headers': [
                    [b'content-type', b'text/css'],
                ],
            })
        
        # Send HTML
        html = b'''
        <html>
        <head>
            <link rel="stylesheet" href="/static/style.css">
        </head>
        <body>
            <h1>Hello with Server Push!</h1>
        </body>
        </html>
        '''
        
        await send({
            'type': 'http.response.body',
            'body': html,
        })
```

**Type Definition** (from `uvicorn/_types.py` lines 130-133):
```python
class HTTPServerPushEvent(TypedDict):
    type: Literal["http.response.push"]
    path: str
    headers: Iterable[tuple[bytes, bytes]]
```

## HTTP Trailers

Trailers are headers sent after the body, useful for checksums or metadata calculated during streaming:

```python
import hashlib

async def app(scope, receive, send):
    if scope['type'] == 'http':
        # Check trailer support
        extensions = scope.get('extensions', {})
        supports_trailers = 'http.response.trailers' in extensions
        
        # Start response with trailer indication
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'text/plain'],
                [b'trailer', b'X-Checksum'],  # Announce trailer
            ],
            'trailers': supports_trailers,
        })
        
        # Stream body while calculating checksum
        hasher = hashlib.sha256()
        chunks = [b'Chunk 1\n', b'Chunk 2\n', b'Chunk 3\n']
        
        for i, chunk in enumerate(chunks):
            hasher.update(chunk)
            await send({
                'type': 'http.response.body',
                'body': chunk,
                'more_body': i < len(chunks) - 1 or supports_trailers,
            })
        
        # Send trailers
        if supports_trailers:
            checksum = hasher.hexdigest()
            await send({
                'type': 'http.response.trailers',
                'headers': [
                    [b'x-checksum', checksum.encode()],
                ],
                'more_trailers': False,
            })
```

**Type Definition** (from `uvicorn/_types.py` lines 124-127):
```python
class HTTPResponseTrailersEvent(TypedDict):
    type: Literal["http.response.trailers"]
    headers: Iterable[tuple[bytes, bytes]]
    more_trailers: bool
```

## Advanced State Management

### Sharing State Between Connections

Use the scope `state` dictionary to share data:

```python
class StatefulApp:
    def __init__(self):
        self.global_state = {
            'request_count': 0,
            'active_connections': 0,
        }
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'lifespan':
            while True:
                message = await receive()
                if message['type'] == 'lifespan.startup':
                    # Initialize state
                    scope['state']['app_state'] = self.global_state
                    await send({'type': 'lifespan.startup.complete'})
                elif message['type'] == 'lifespan.shutdown':
                    await send({'type': 'lifespan.shutdown.complete'})
                    return
        
        elif scope['type'] == 'http':
            # Access shared state
            app_state = scope['state'].get('app_state', {})
            app_state['request_count'] += 1
            
            body = f"Request #{app_state['request_count']}".encode()
            
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [[b'content-type', b'text/plain']],
            })
            await send({
                'type': 'http.response.body',
                'body': body,
            })


app = StatefulApp()
```

### Per-Request State

Add data to the scope for use downstream:

```python
class RequestIDMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            import uuid
            
            # Add request ID to scope state
            if 'state' not in scope:
                scope['state'] = {}
            scope['state']['request_id'] = str(uuid.uuid4())
        
        await self.app(scope, receive, send)


async def app(scope, receive, send):
    if scope['type'] == 'http':
        # Access request ID
        request_id = scope['state'].get('request_id', 'unknown')
        
        body = f"Request ID: {request_id}".encode()
        
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'text/plain'],
                [b'x-request-id', request_id.encode()],
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': body,
        })

# Apply middleware
app = RequestIDMiddleware(app)
```

## Flow Control and Backpressure

ASGI supports flow control to prevent overwhelming slower clients or servers.

### HTTP Disconnect Events

The server can send `http.disconnect` if the client disconnects:

```python
async def app(scope, receive, send):
    if scope['type'] == 'http':
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'text/plain']],
        })
        
        # Stream chunks with disconnect checking
        import asyncio
        for i in range(100):
            # Check for disconnect
            try:
                message = await asyncio.wait_for(receive(), timeout=0.001)
                if message['type'] == 'http.disconnect':
                    print("Client disconnected!")
                    return
            except asyncio.TimeoutError:
                pass
            
            # Send chunk
            await send({
                'type': 'http.response.body',
                'body': f'Chunk {i}\n'.encode(),
                'more_body': True,
            })
            await asyncio.sleep(0.1)
        
        # Final chunk
        await send({
            'type': 'http.response.body',
            'body': b'Done\n',
            'more_body': False,
        })
```

**Type Definition** (from `uvicorn/_types.py` lines 136-137):
```python
class HTTPDisconnectEvent(TypedDict):
    type: Literal["http.disconnect"]
```

### Uvicorn Flow Control

In `uvicorn/protocols/http/flow_control.py`, uvicorn implements flow control:

```python
class FlowControl:
    """
    Flow control to prevent overwhelming slow clients.
    Pauses reading when buffer is full.
    """
    
    def __init__(self, transport):
        self.transport = transport
        self._is_paused = False
    
    def pause_reading(self):
        if not self._is_paused:
            self._is_paused = True
            self.transport.pause_reading()
    
    def resume_reading(self):
        if self._is_paused:
            self._is_paused = False
            self.transport.resume_reading()
```

## Multiple Protocol Support

Handle multiple protocols in one application:

```python
async def app(scope, receive, send):
    """Application supporting HTTP, WebSocket, and Lifespan."""
    
    if scope['type'] == 'http':
        await handle_http(scope, receive, send)
    
    elif scope['type'] == 'websocket':
        await handle_websocket(scope, receive, send)
    
    elif scope['type'] == 'lifespan':
        await handle_lifespan(scope, receive, send)
    
    else:
        raise NotImplementedError(f"Unsupported type: {scope['type']}")


async def handle_http(scope, receive, send):
    """Handle HTTP requests."""
    path = scope['path']
    
    if path == '/':
        body = b'Home Page'
    elif path == '/api/data':
        import json
        body = json.dumps({'data': [1, 2, 3]}).encode()
    else:
        body = b'Not Found'
        status = 404
    
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [[b'content-type', b'text/plain']],
    })
    await send({
        'type': 'http.response.body',
        'body': body,
    })


async def handle_websocket(scope, receive, send):
    """Handle WebSocket connections."""
    await send({'type': 'websocket.accept'})
    
    while True:
        message = await receive()
        if message['type'] == 'websocket.disconnect':
            break
        elif message['type'] == 'websocket.receive':
            text = message.get('text', '')
            await send({
                'type': 'websocket.send',
                'text': f'Echo: {text}'
            })


async def handle_lifespan(scope, receive, send):
    """Handle application lifecycle."""
    while True:
        message = await receive()
        if message['type'] == 'lifespan.startup':
            print("App starting...")
            await send({'type': 'lifespan.startup.complete'})
        elif message['type'] == 'lifespan.shutdown':
            print("App shutting down...")
            await send({'type': 'lifespan.shutdown.complete'})
            return
```

## Router Pattern

Build a simple router for HTTP:

```python
class Router:
    """Simple path-based router."""
    
    def __init__(self):
        self.routes = {}
    
    def route(self, path):
        """Decorator to register routes."""
        def decorator(handler):
            self.routes[path] = handler
            return handler
        return decorator
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            path = scope['path']
            handler = self.routes.get(path)
            
            if handler:
                await handler(scope, receive, send)
            else:
                # 404
                await send({
                    'type': 'http.response.start',
                    'status': 404,
                    'headers': [[b'content-type', b'text/plain']],
                })
                await send({
                    'type': 'http.response.body',
                    'body': b'Not Found',
                })


# Create router
app = Router()


@app.route('/')
async def home(scope, receive, send):
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [[b'content-type', b'text/plain']],
    })
    await send({
        'type': 'http.response.body',
        'body': b'Home Page',
    })


@app.route('/about')
async def about(scope, receive, send):
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [[b'content-type', b'text/plain']],
    })
    await send({
        'type': 'http.response.body',
        'body': b'About Page',
    })
```

## Testing ASGI Applications

### Basic Test Helper

```python
import asyncio

async def call_asgi_app(app, method='GET', path='/', body=b''):
    """Helper to call ASGI app in tests."""
    
    # Create scope
    scope = {
        'type': 'http',
        'asgi': {'version': '3.0', 'spec_version': '2.4'},
        'http_version': '1.1',
        'method': method,
        'scheme': 'http',
        'path': path,
        'query_string': b'',
        'root_path': '',
        'headers': [[b'host', b'testserver']],
        'server': ('testserver', 80),
        'client': ('testclient', 12345),
    }
    
    # Track received messages
    response_started = False
    response_status = None
    response_headers = None
    response_body = b''
    
    # Create receive callable
    async def receive():
        return {
            'type': 'http.request',
            'body': body,
            'more_body': False,
        }
    
    # Create send callable
    async def send(message):
        nonlocal response_started, response_status, response_headers, response_body
        
        if message['type'] == 'http.response.start':
            response_started = True
            response_status = message['status']
            response_headers = message.get('headers', [])
        
        elif message['type'] == 'http.response.body':
            response_body += message.get('body', b'')
    
    # Call app
    await app(scope, receive, send)
    
    # Return response
    return {
        'status': response_status,
        'headers': dict(response_headers),
        'body': response_body,
    }


# Example test
async def test_app():
    async def app(scope, receive, send):
        if scope['type'] == 'http':
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [[b'content-type', b'text/plain']],
            })
            await send({
                'type': 'http.response.body',
                'body': b'Hello, Test!',
            })
    
    response = await call_asgi_app(app)
    
    assert response['status'] == 200
    assert response['body'] == b'Hello, Test!'
    assert response['headers'][b'content-type'] == b'text/plain'
    print("✅ Test passed!")


# Run test
asyncio.run(test_app())
```

## Performance Considerations

### 1. Avoid Buffering Large Responses

```python
# ❌ Bad: Buffers entire response in memory
async def bad_app(scope, receive, send):
    large_data = b'x' * 10_000_000  # 10MB
    await send({'type': 'http.response.start', 'status': 200, 'headers': []})
    await send({'type': 'http.response.body', 'body': large_data})

# ✅ Good: Stream in chunks
async def good_app(scope, receive, send):
    await send({'type': 'http.response.start', 'status': 200, 'headers': []})
    
    chunk_size = 64 * 1024  # 64KB chunks
    for i in range(0, 10_000_000, chunk_size):
        chunk = b'x' * min(chunk_size, 10_000_000 - i)
        await send({
            'type': 'http.response.body',
            'body': chunk,
            'more_body': i + chunk_size < 10_000_000,
        })
```

### 2. Use Connection Pooling

```python
# Share database connections via lifespan state
async def app(scope, receive, send):
    if scope['type'] == 'lifespan':
        import asyncpg
        
        while True:
            message = await receive()
            if message['type'] == 'lifespan.startup':
                # Create connection pool
                pool = await asyncpg.create_pool(
                    'postgresql://localhost/db',
                    min_size=10,
                    max_size=20
                )
                scope['state']['db_pool'] = pool
                await send({'type': 'lifespan.startup.complete'})
            
            elif message['type'] == 'lifespan.shutdown':
                pool = scope['state'].get('db_pool')
                if pool:
                    await pool.close()
                await send({'type': 'lifespan.shutdown.complete'})
                return
    
    elif scope['type'] == 'http':
        # Use pool from state
        pool = scope['state'].get('db_pool')
        async with pool.acquire() as conn:
            data = await conn.fetch('SELECT * FROM users')
            # ... handle response
```

## Exercises

### Exercise 1: Request Timing with Trailers

Create an app that uses trailers to send processing time:

```python
async def app(scope, receive, send):
    # Use trailers to send X-Processing-Time header
    # after response completes
    pass
```

### Exercise 2: Stateful Counter

Track total requests and active connections:

```python
async def app(scope, receive, send):
    # Use lifespan to initialize counters
    # Increment on each request
    # Track active connections
    pass
```

### Exercise 3: Multi-Protocol App

Create an app with HTTP API and WebSocket chat:

```python
async def app(scope, receive, send):
    # HTTP: JSON API at /api/data
    # WebSocket: Chat at /ws
    # Lifespan: Initialize shared state
    pass
```

### Exercise 4: Simple Router

Implement a regex-based router:

```python
import re

class RegexRouter:
    # Match patterns like /users/(\d+)
    # Extract path parameters
    # Call handlers with parameters
    pass
```

## Key Takeaways

1. ✅ **Extensions** enable optional features (push, trailers)
2. ✅ **HTTP/2 Server Push** proactively sends resources
3. ✅ **Trailers** send headers after body
4. ✅ **State management** shares data across requests
5. ✅ **Flow control** prevents overwhelming clients
6. ✅ **http.disconnect** signals client disconnection
7. ✅ **Multiple protocols** can share one app
8. ✅ **Stream large responses** instead of buffering

## Next Steps

Now that you understand advanced concepts, proceed to:

➡️ [Module 8: Building Complete Applications](08-practical-app.md) - Put it all together

## Additional Resources

- [ASGI Extensions Specification](https://asgi.readthedocs.io/en/latest/extensions.html)
- [HTTP/2 Server Push](https://developers.google.com/web/fundamentals/performance/http2#server_push)
- [Uvicorn Flow Control](../../uvicorn/protocols/http/flow_control.py)
- [ASGI Type Definitions](../../uvicorn/_types.py)

