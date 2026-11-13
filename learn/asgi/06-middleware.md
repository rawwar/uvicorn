# Module 6: ASGI Middleware

## Introduction

**Middleware** is a design pattern that allows you to wrap ASGI applications with additional functionality. Middleware sits between the server and your application, processing requests before they reach your app and responses before they reach the client.

Common use cases for middleware:
- **Logging** - Log all requests and responses
- **Authentication** - Validate tokens or sessions
- **CORS** - Add cross-origin resource sharing headers
- **Compression** - Gzip response bodies
- **Rate limiting** - Throttle requests
- **Error handling** - Catch and format exceptions
- **Request modification** - Add headers, modify scope
- **Metrics** - Track request timing and counts

## The Middleware Pattern

Middleware is simply an ASGI application that wraps another ASGI application:

```
Client → Server → Middleware → Your App
Client ← Server ← Middleware ← Your App
```

Basic structure:

```python
class Middleware:
    def __init__(self, app):
        self.app = app  # The wrapped application
    
    async def __call__(self, scope, receive, send):
        # Pre-processing: do something before calling app
        
        # Call the wrapped application
        await self.app(scope, receive, send)
        
        # Post-processing: do something after app returns
```

## Simple Logging Middleware

```python
import time

class LoggingMiddleware:
    """Log all incoming requests."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            # Log request
            method = scope['method']
            path = scope['path']
            start_time = time.time()
            
            print(f"→ {method} {path}")
            
            # Call the wrapped app
            await self.app(scope, receive, send)
            
            # Log response time
            duration = time.time() - start_time
            print(f"← {method} {path} - {duration:.3f}s")
        else:
            # Pass through non-HTTP requests
            await self.app(scope, receive, send)


# Your application
async def app(scope, receive, send):
    if scope['type'] == 'http':
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'text/plain']],
        })
        await send({
            'type': 'http.response.body',
            'body': b'Hello, World!',
        })


# Wrap app with middleware
wrapped_app = LoggingMiddleware(app)
```

Run it:
```bash
uvicorn module:wrapped_app
curl http://localhost:8000
# Console output:
# → GET /
# ← GET / - 0.001s
```

## Intercepting Send Messages

To modify responses, you need to intercept the `send` callable:

```python
class HeaderMiddleware:
    """Add custom header to all responses."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            async def send_wrapper(message):
                if message['type'] == 'http.response.start':
                    # Add custom header
                    headers = list(message.get('headers', []))
                    headers.append([b'x-custom-header', b'CustomValue'])
                    message['headers'] = headers
                
                await send(message)
            
            # Call app with wrapped send
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


# Usage
async def app(scope, receive, send):
    if scope['type'] == 'http':
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'text/plain']],
        })
        await send({
            'type': 'http.response.body',
            'body': b'Hello!',
        })

wrapped_app = HeaderMiddleware(app)
```

Test:
```bash
curl -i http://localhost:8000
# You'll see: X-Custom-Header: CustomValue
```

## Intercepting Receive Messages

You can also wrap `receive` to inspect or modify incoming messages:

```python
class RequestLoggingMiddleware:
    """Log request bodies."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            async def receive_wrapper():
                message = await receive()
                
                if message['type'] == 'http.request':
                    body = message.get('body', b'')
                    if body:
                        print(f"Request body: {body[:100]}")  # First 100 bytes
                
                return message
            
            await self.app(scope, receive_wrapper, send)
        else:
            await self.app(scope, receive, send)
```

## CORS Middleware

Add Cross-Origin Resource Sharing headers:

```python
class CORSMiddleware:
    """Add CORS headers to responses."""
    
    def __init__(self, app, allow_origin='*', allow_methods='*'):
        self.app = app
        self.allow_origin = allow_origin
        self.allow_methods = allow_methods
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            async def send_wrapper(message):
                if message['type'] == 'http.response.start':
                    headers = list(message.get('headers', []))
                    
                    # Add CORS headers
                    headers.append([
                        b'access-control-allow-origin',
                        self.allow_origin.encode()
                    ])
                    headers.append([
                        b'access-control-allow-methods',
                        self.allow_methods.encode()
                    ])
                    headers.append([
                        b'access-control-allow-headers',
                        b'*'
                    ])
                    
                    message['headers'] = headers
                
                await send(message)
            
            # Handle OPTIONS preflight requests
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


# Usage
app = CORSMiddleware(app, allow_origin='https://example.com')
```

## Authentication Middleware

```python
class AuthMiddleware:
    """Require authentication token."""
    
    def __init__(self, app, secret_token):
        self.app = app
        self.secret_token = secret_token
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            # Check for Authorization header
            headers = dict(scope['headers'])
            auth_header = headers.get(b'authorization', b'').decode()
            
            if auth_header == f'Bearer {self.secret_token}':
                # Authenticated - proceed
                await self.app(scope, receive, send)
            else:
                # Not authenticated - return 401
                await send({
                    'type': 'http.response.start',
                    'status': 401,
                    'headers': [[b'content-type', b'text/plain']],
                })
                await send({
                    'type': 'http.response.body',
                    'body': b'Unauthorized',
                })
        else:
            await self.app(scope, receive, send)


# Usage
app = AuthMiddleware(app, secret_token='my-secret-token')
```

Test:
```bash
# Without token - 401
curl http://localhost:8000

# With token - 200
curl -H "Authorization: Bearer my-secret-token" http://localhost:8000
```

## Modifying Scope

Middleware can modify the scope before passing it to the app:

```python
class PathPrefixMiddleware:
    """Strip a prefix from the path."""
    
    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            path = scope['path']
            
            if path.startswith(self.prefix):
                # Remove prefix from path
                new_path = path[len(self.prefix):] or '/'
                
                # Create modified scope
                scope = dict(scope)
                scope['path'] = new_path
                scope['raw_path'] = new_path.encode()
            
            await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, send)


# Usage: /api/users → /users
app = PathPrefixMiddleware(app, prefix='/api')
```

## Stacking Multiple Middleware

Middleware can be composed:

```python
# Your application
async def app(scope, receive, send):
    if scope['type'] == 'http':
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'text/plain']],
        })
        await send({
            'type': 'http.response.body',
            'body': b'Hello!',
        })

# Stack middleware (applied in reverse order)
app = LoggingMiddleware(app)
app = CORSMiddleware(app)
app = AuthMiddleware(app, secret_token='secret')

# Request flow:
# Client → AuthMiddleware → CORSMiddleware → LoggingMiddleware → App
```

## Error Handling Middleware

Catch exceptions and return proper error responses:

```python
import traceback

class ErrorHandlerMiddleware:
    """Catch exceptions and return 500 responses."""
    
    def __init__(self, app, debug=False):
        self.app = app
        self.debug = debug
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            try:
                await self.app(scope, receive, send)
            except Exception as exc:
                # Log the error
                print(f"Error: {exc}")
                
                # Prepare error response
                if self.debug:
                    body = f"Error: {exc}\n\n{traceback.format_exc()}".encode()
                else:
                    body = b"Internal Server Error"
                
                # Send error response
                try:
                    await send({
                        'type': 'http.response.start',
                        'status': 500,
                        'headers': [[b'content-type', b'text/plain']],
                    })
                    await send({
                        'type': 'http.response.body',
                        'body': body,
                    })
                except:
                    # Response already started
                    pass
        else:
            await self.app(scope, receive, send)
```

## Response Buffering Middleware

Buffer response to modify it:

```python
class ResponseBufferingMiddleware:
    """Buffer response to modify content."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            # Buffer for response
            response_started = False
            response_status = None
            response_headers = None
            response_body = b''
            
            async def send_wrapper(message):
                nonlocal response_started, response_status, response_headers, response_body
                
                if message['type'] == 'http.response.start':
                    response_started = True
                    response_status = message['status']
                    response_headers = list(message.get('headers', []))
                
                elif message['type'] == 'http.response.body':
                    response_body += message.get('body', b'')
                    
                    # If this is the last chunk, process and send
                    if not message.get('more_body', False):
                        # Modify response (example: add footer)
                        modified_body = response_body + b'\n\n<!-- Powered by ASGI -->'
                        
                        # Update content-length
                        response_headers = [
                            h for h in response_headers
                            if h[0].lower() != b'content-length'
                        ]
                        response_headers.append([
                            b'content-length',
                            str(len(modified_body)).encode()
                        ])
                        
                        # Send actual response
                        await send({
                            'type': 'http.response.start',
                            'status': response_status,
                            'headers': response_headers,
                        })
                        await send({
                            'type': 'http.response.body',
                            'body': modified_body,
                        })
            
            await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)
```

## How Uvicorn Uses Middleware

### ProxyHeadersMiddleware

In `uvicorn/middleware/proxy_headers.py` (lines 8-60):

```python
class ProxyHeadersMiddleware:
    """Trust proxy headers for client IP and scheme."""
    
    def __init__(self, app, trusted_hosts='127.0.0.1'):
        self.app = app
        self.trusted_hosts = _TrustedHosts(trusted_hosts)
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            return await self.app(scope, receive, send)
        
        client_addr = scope.get("client")
        client_host = client_addr[0] if client_addr else None
        
        if client_host in self.trusted_hosts:
            headers = dict(scope["headers"])
            
            # Handle X-Forwarded-Proto
            if b"x-forwarded-proto" in headers:
                x_forwarded_proto = headers[b"x-forwarded-proto"].decode("latin1").strip()
                if x_forwarded_proto in {"http", "https", "ws", "wss"}:
                    scope["scheme"] = x_forwarded_proto
            
            # Handle X-Forwarded-For
            if b"x-forwarded-for" in headers:
                x_forwarded_for = headers[b"x-forwarded-for"].decode("latin1")
                host = self.trusted_hosts.get_trusted_client_host(x_forwarded_for)
                if host:
                    port = 0
                    scope["client"] = (host, port)
        
        return await self.app(scope, receive, send)
```

### MessageLoggerMiddleware

In `uvicorn/middleware/message_logger.py` (lines 36-87):

```python
class MessageLoggerMiddleware:
    """Log all ASGI messages for debugging."""
    
    def __init__(self, app):
        self.task_counter = 0
        self.app = app
        self.logger = logging.getLogger("uvicorn.asgi")
    
    async def __call__(self, scope, receive, send):
        self.task_counter += 1
        task_counter = self.task_counter
        
        # Wrap receive
        async def inner_receive():
            message = await receive()
            logged_message = message_with_placeholders(message)
            log_text = "%s [%d] Receive %s"
            self.logger.trace(log_text, prefix, task_counter, logged_message)
            return message
        
        # Wrap send
        async def inner_send(message):
            logged_message = message_with_placeholders(message)
            log_text = "%s [%d] Send %s"
            self.logger.trace(log_text, prefix, task_counter, logged_message)
            await send(message)
        
        # Log scope
        logged_scope = message_with_placeholders(scope)
        log_text = "%s [%d] Started scope=%s"
        self.logger.trace(log_text, prefix, task_counter, logged_scope)
        
        await self.app(scope, inner_receive, inner_send)
```

## Exercises

### Exercise 1: Timing Middleware

Create middleware that times requests and adds a header:

```python
class TimingMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        # Measure request duration
        # Add X-Response-Time header
        pass
```

### Exercise 2: User-Agent Logger

Log the User-Agent header of all requests:

```python
class UserAgentMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        # Extract User-Agent from headers
        # Log it
        # Call app
        pass
```

### Exercise 3: Request ID

Add a unique request ID to each request:

```python
import uuid

class RequestIDMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        # Generate UUID
        # Add to scope['state']
        # Add X-Request-ID header to response
        pass
```

### Exercise 4: Rate Limiter

Simple rate limiting based on IP:

```python
from time import time
from collections import defaultdict

class RateLimitMiddleware:
    def __init__(self, app, max_requests=10, window=60):
        self.app = app
        self.max_requests = max_requests
        self.window = window
        self.requests = defaultdict(list)
    
    async def __call__(self, scope, receive, send):
        # Track requests by IP
        # Return 429 if rate exceeded
        # Otherwise call app
        pass
```

### Exercise 5: Compression

Gzip compress responses:

```python
import gzip

class CompressionMiddleware:
    def __init__(self, app, min_size=1024):
        self.app = app
        self.min_size = min_size
    
    async def __call__(self, scope, receive, send):
        # Buffer response
        # Compress if > min_size
        # Add Content-Encoding header
        pass
```

## Key Takeaways

1. ✅ Middleware **wraps** ASGI applications
2. ✅ Middleware is just an ASGI app that calls another ASGI app
3. ✅ Wrap **send** to intercept outgoing messages
4. ✅ Wrap **receive** to intercept incoming messages
5. ✅ Modify **scope** to change request context
6. ✅ Middleware can be **stacked** (composed)
7. ✅ Always handle **all scope types** (http, websocket, lifespan)
8. ✅ Use middleware for **cross-cutting concerns**

## Next Steps

Now that you understand middleware, proceed to:

➡️ [Module 7: Advanced Concepts](07-advanced.md) - Extensions, state, and advanced features

## Additional Resources

- [ASGI Middleware Patterns](https://asgi.readthedocs.io/en/latest/middleware.html)
- [Uvicorn ProxyHeadersMiddleware](../../uvicorn/middleware/proxy_headers.py)
- [Uvicorn MessageLoggerMiddleware](../../uvicorn/middleware/message_logger.py)
- [Starlette Middleware](https://www.starlette.io/middleware/)

