# Module 3: HTTP Protocol

## Introduction

The HTTP protocol in ASGI allows you to handle HTTP requests and responses asynchronously. Unlike WSGI's simple request→response model, ASGI's HTTP protocol supports streaming requests and responses, allowing for more efficient handling of large payloads and real-time data.

## HTTP Request/Response Cycle

The HTTP cycle in ASGI consists of:

1. **Server creates scope** with HTTP request metadata
2. **Server sends `http.request` events** with body chunks
3. **Application sends `http.response.start`** with status and headers
4. **Application sends `http.response.body` events** with response data
5. **Connection closes** or kept alive for next request

```
Client → Server → App: scope (HTTP metadata)
Client → Server → App: http.request (body chunks)
App → Server → Client: http.response.start (status + headers)
App → Server → Client: http.response.body (response data)
```

## HTTP Messages

### Receiving Messages (http.request)

The `receive` callable returns `http.request` messages:

```python
{
    'type': 'http.request',
    'body': b'chunk of request body',
    'more_body': True  # False when body is complete
}
```

**Fields:**
- `type`: Always `"http.request"`
- `body`: Bytes of the body chunk (can be empty)
- `more_body`: Boolean indicating if more chunks are coming

### Sending Messages

#### 1. http.response.start

Must be sent **first**, contains status and headers:

```python
{
    'type': 'http.response.start',
    'status': 200,
    'headers': [
        [b'content-type', b'text/html; charset=utf-8'],
        [b'content-length', b'1234'],
    ],
    'trailers': False  # Optional, for HTTP trailers support
}
```

**Fields:**
- `type`: Always `"http.response.start"`
- `status`: HTTP status code (integer)
- `headers`: List of `[name, value]` pairs (both bytes)
- `trailers`: Optional boolean, indicates trailer support

#### 2. http.response.body

Can be sent **multiple times** for streaming:

```python
{
    'type': 'http.response.body',
    'body': b'chunk of response data',
    'more_body': True  # False for the last chunk
}
```

**Fields:**
- `type`: Always `"http.response.body"`
- `body`: Bytes of the body chunk
- `more_body`: Boolean, `True` if more chunks coming, `False` for last

## Basic HTTP Application

```python
async def app(scope, receive, send):
    """Simple HTTP application."""
    if scope['type'] == 'http':
        # Send response headers
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'text/plain'],
            ],
        })
        
        # Send response body
        await send({
            'type': 'http.response.body',
            'body': b'Hello, World!',
        })
```

Run it:
```bash
uvicorn module:app
curl http://localhost:8000
# Output: Hello, World!
```

## Reading Request Body

To read the request body, call `receive()` until `more_body` is `False`:

```python
async def read_body(receive):
    """Read the entire request body."""
    body = b''
    more_body = True
    
    while more_body:
        message = await receive()
        body += message.get('body', b'')
        more_body = message.get('more_body', False)
    
    return body


async def app(scope, receive, send):
    """Echo the request body back."""
    if scope['type'] == 'http':
        # Read the full body
        body = await read_body(receive)
        
        # Send response
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'text/plain'],
                [b'content-length', str(len(body)).encode()],
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': body,
        })
```

Test it:
```bash
echo "Hello from client" | curl -X POST -d @- http://localhost:8000
# Output: Hello from client
```

## Working with JSON

```python
import json

async def app(scope, receive, send):
    """JSON API endpoint."""
    if scope['type'] == 'http':
        if scope['method'] == 'POST':
            # Read request body
            body = b''
            more_body = True
            while more_body:
                message = await receive()
                body += message.get('body', b'')
                more_body = message.get('more_body', False)
            
            # Parse JSON
            try:
                data = json.loads(body.decode('utf-8'))
                name = data.get('name', 'Guest')
                
                # Create response
                response_data = {
                    'message': f'Hello, {name}!',
                    'received': data
                }
                response_body = json.dumps(response_data).encode('utf-8')
                
                await send({
                    'type': 'http.response.start',
                    'status': 200,
                    'headers': [
                        [b'content-type', b'application/json'],
                        [b'content-length', str(len(response_body)).encode()],
                    ],
                })
                await send({
                    'type': 'http.response.body',
                    'body': response_body,
                })
            except json.JSONDecodeError:
                # Invalid JSON
                error_body = b'{"error": "Invalid JSON"}'
                await send({
                    'type': 'http.response.start',
                    'status': 400,
                    'headers': [[b'content-type', b'application/json']],
                })
                await send({
                    'type': 'http.response.body',
                    'body': error_body,
                })
        else:
            # Method not allowed
            await send({
                'type': 'http.response.start',
                'status': 405,
                'headers': [[b'content-type', b'text/plain']],
            })
            await send({
                'type': 'http.response.body',
                'body': b'Method Not Allowed',
            })
```

Test:
```bash
curl -X POST -H "Content-Type: application/json" \
     -d '{"name": "Alice"}' \
     http://localhost:8000
# Output: {"message": "Hello, Alice!", "received": {"name": "Alice"}}
```

## Streaming Responses

Send multiple `http.response.body` messages for streaming:

```python
import asyncio

async def app(scope, receive, send):
    """Stream a response over time."""
    if scope['type'] == 'http':
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'text/plain'],
            ],
        })
        
        # Send chunks over time
        for i in range(5):
            chunk = f'Chunk {i + 1}\n'.encode()
            await send({
                'type': 'http.response.body',
                'body': chunk,
                'more_body': True,  # More chunks coming
            })
            await asyncio.sleep(1)  # Simulate delay
        
        # Send final chunk
        await send({
            'type': 'http.response.body',
            'body': b'Done!\n',
            'more_body': False,  # This is the last chunk
        })
```

Test:
```bash
curl http://localhost:8000
# You'll see chunks appear one by one with 1-second delays
```

## Streaming Server-Sent Events (SSE)

```python
import asyncio
import datetime

async def app(scope, receive, send):
    """Server-Sent Events stream."""
    if scope['type'] == 'http' and scope['path'] == '/events':
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'text/event-stream'],
                [b'cache-control', b'no-cache'],
            ],
        })
        
        # Stream events
        for i in range(10):
            timestamp = datetime.datetime.now().isoformat()
            event = f'data: Event {i} at {timestamp}\n\n'.encode()
            
            await send({
                'type': 'http.response.body',
                'body': event,
                'more_body': True,
            })
            await asyncio.sleep(2)
        
        # Close stream
        await send({
            'type': 'http.response.body',
            'body': b'',
            'more_body': False,
        })
```

Test with browser or curl:
```bash
curl http://localhost:8000/events
```

## Handling Different HTTP Methods

```python
async def app(scope, receive, send):
    """Handle different HTTP methods."""
    if scope['type'] == 'http':
        method = scope['method']
        path = scope['path']
        
        if path == '/resource':
            if method == 'GET':
                await handle_get(scope, receive, send)
            elif method == 'POST':
                await handle_post(scope, receive, send)
            elif method == 'PUT':
                await handle_put(scope, receive, send)
            elif method == 'DELETE':
                await handle_delete(scope, receive, send)
            else:
                await send_error(send, 405, 'Method Not Allowed')
        else:
            await send_error(send, 404, 'Not Found')


async def handle_get(scope, receive, send):
    """Handle GET request."""
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [[b'content-type', b'text/plain']],
    })
    await send({
        'type': 'http.response.body',
        'body': b'GET request handled',
    })


async def handle_post(scope, receive, send):
    """Handle POST request."""
    body = await read_body(receive)
    response = f'Received: {body.decode()}'.encode()
    
    await send({
        'type': 'http.response.start',
        'status': 201,
        'headers': [[b'content-type', b'text/plain']],
    })
    await send({
        'type': 'http.response.body',
        'body': response,
    })


async def send_error(send, status, message):
    """Send error response."""
    await send({
        'type': 'http.response.start',
        'status': status,
        'headers': [[b'content-type', b'text/plain']],
    })
    await send({
        'type': 'http.response.body',
        'body': message.encode(),
    })


async def read_body(receive):
    """Helper to read full body."""
    body = b''
    more_body = True
    while more_body:
        message = await receive()
        body += message.get('body', b'')
        more_body = message.get('more_body', False)
    return body
```

## Setting Response Headers

Common headers you might want to set:

```python
async def app(scope, receive, send):
    if scope['type'] == 'http':
        body = b'Hello, World!'
        
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                # Content type
                [b'content-type', b'text/html; charset=utf-8'],
                
                # Content length
                [b'content-length', str(len(body)).encode()],
                
                # Caching
                [b'cache-control', b'public, max-age=3600'],
                
                # CORS
                [b'access-control-allow-origin', b'*'],
                [b'access-control-allow-methods', b'GET, POST, PUT, DELETE'],
                
                # Security
                [b'x-content-type-options', b'nosniff'],
                [b'x-frame-options', b'DENY'],
                
                # Custom header
                [b'x-custom-header', b'custom-value'],
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': body,
        })
```

## Handling File Uploads

```python
async def app(scope, receive, send):
    """Handle file upload."""
    if scope['type'] == 'http' and scope['method'] == 'POST':
        # Read uploaded file
        body = b''
        more_body = True
        while more_body:
            message = await receive()
            body += message.get('body', b'')
            more_body = message.get('more_body', False)
        
        # Save to file
        with open('uploaded_file.dat', 'wb') as f:
            f.write(body)
        
        response = f'Uploaded {len(body)} bytes'.encode()
        
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'text/plain']],
        })
        await send({
            'type': 'http.response.body',
            'body': response,
        })
```

Test:
```bash
curl -X POST --data-binary @largefile.dat http://localhost:8000
```

## Serving Static Files

```python
import os
import mimetypes

async def app(scope, receive, send):
    """Serve static files."""
    if scope['type'] == 'http':
        # Get file path from URL
        path = scope['path'].lstrip('/')
        
        # Security: prevent directory traversal
        if '..' in path:
            await send_error(send, 403, 'Forbidden')
            return
        
        # Build full path
        file_path = os.path.join('static', path)
        
        if os.path.isfile(file_path):
            # Determine content type
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = 'application/octet-stream'
            
            # Read and send file
            with open(file_path, 'rb') as f:
                content = f.read()
            
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [
                    [b'content-type', content_type.encode()],
                    [b'content-length', str(len(content)).encode()],
                ],
            })
            await send({
                'type': 'http.response.body',
                'body': content,
            })
        else:
            await send_error(send, 404, 'File Not Found')


async def send_error(send, status, message):
    await send({
        'type': 'http.response.start',
        'status': status,
        'headers': [[b'content-type', b'text/plain']],
    })
    await send({
        'type': 'http.response.body',
        'body': message.encode(),
    })
```

## How Uvicorn Handles HTTP

### Protocol Implementation

Uvicorn implements the HTTP protocol in `uvicorn/protocols/http/h11_impl.py`.

Key parts:

1. **Creating HTTP Scope** (lines ~130-180):
```python
self.scope: HTTPScope = {
    "type": "http",
    "asgi": {"version": self.config.asgi_version, "spec_version": "2.4"},
    "http_version": http_version,
    "method": method.decode("ascii"),
    "scheme": self.scheme,
    "path": path,
    "raw_path": raw_path,
    "query_string": query_string,
    "root_path": self.root_path,
    "headers": headers,
    "server": self.server,
    "client": self.client,
}
```

2. **Calling the ASGI App**:
```python
task = self.loop.create_task(self.run_asgi(app))
```

3. **Request Body Handling**:
The protocol receives data from the network and provides it through the `receive()` callable.

4. **Response Handling**:
The `send()` callable processes `http.response.start` and `http.response.body` messages and writes them to the network.

### Type Definitions

In `uvicorn/_types.py`:

```python
# HTTP Request Event (lines 100-103)
class HTTPRequestEvent(TypedDict):
    type: Literal["http.request"]
    body: bytes
    more_body: bool

# HTTP Response Start Event (lines 111-115)
class HTTPResponseStartEvent(TypedDict):
    type: Literal["http.response.start"]
    status: int
    headers: NotRequired[Iterable[tuple[bytes, bytes]]]
    trailers: NotRequired[bool]

# HTTP Response Body Event (lines 118-121)
class HTTPResponseBodyEvent(TypedDict):
    type: Literal["http.response.body"]
    body: bytes
    more_body: NotRequired[bool]
```

## Exercises

### Exercise 1: Echo Server

Create an HTTP server that echoes back the request method, path, and body:

```python
async def app(scope, receive, send):
    # Read body
    # Create response showing method, path, and body
    pass
```

### Exercise 2: Form Handler

Create a form handler that accepts POST requests with URL-encoded form data:

```python
from urllib.parse import parse_qs

async def app(scope, receive, send):
    # Read form data
    # Parse it
    # Return JSON response with parsed data
    pass
```

### Exercise 3: Streaming Response

Create a countdown timer that streams numbers:

```python
async def app(scope, receive, send):
    # Stream numbers from 10 to 1 with 1-second delays
    # Send "Blast off!" at the end
    pass
```

### Exercise 4: Simple Router

Create a router with multiple endpoints:
- GET `/` → "Home Page"
- GET `/api/time` → Current time as JSON
- POST `/api/echo` → Echo request body
- GET `/health` → "OK"
- Others → 404

```python
async def app(scope, receive, send):
    # Implement routing logic
    pass
```

### Exercise 5: File Server

Create a simple file server that serves files from a directory:

```python
async def app(scope, receive, send):
    # Serve files from ./public directory
    # Handle 404 for missing files
    # Set proper content-type headers
    pass
```

## Key Takeaways

1. ✅ HTTP cycle: **scope → request → response.start → response.body**
2. ✅ **http.response.start** must be sent before **http.response.body**
3. ✅ **Stream responses** by sending multiple `http.response.body` messages
4. ✅ **Read body** by calling `receive()` until `more_body` is False
5. ✅ Headers must be **list of byte pairs**: `[[b'name', b'value']]`
6. ✅ **Status codes** are integers: 200, 404, 500, etc.
7. ✅ Set `more_body=False` in the **last body chunk**
8. ✅ Handle different **HTTP methods** (GET, POST, PUT, DELETE)

## Next Steps

Now that you understand HTTP in ASGI, proceed to:

➡️ [Module 4: Lifespan Protocol](04-lifespan.md) - Application lifecycle management

## Additional Resources

- [ASGI HTTP Specification](https://asgi.readthedocs.io/en/latest/specs/www.html#http)
- [Uvicorn HTTP Implementation](../../uvicorn/protocols/http/h11_impl.py)
- [HTTP Type Definitions](../../uvicorn/_types.py)
- [Uvicorn ASGI Documentation](../../docs/concepts/asgi.md)

