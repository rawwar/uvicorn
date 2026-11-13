# Module 1: ASGI Fundamentals

## Introduction

ASGI (Asynchronous Server Gateway Interface) is a specification that defines how web servers communicate with Python web applications. In this module, we'll understand **why** it exists, **how** it works at a fundamental level, and build our own mini ASGI server to truly grasp the mechanics.

## The Problem: Why Does ASGI Exist?

To understand ASGI, we first need to understand what problem it solves. Let's look at WSGI.

### WSGI: The Synchronous World

WSGI (Web Server Gateway Interface) has been Python's standard since 2003. Here's its signature:

```python
# WSGI signature - synchronous, single response
def application(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [b'Hello World']
```

**Why is this limiting?**

#### Problem 1: Synchronous Blocking

```python
import time

def wsgi_app(environ, start_response):
    # This blocks the entire thread for 5 seconds!
    time.sleep(5)  # Simulating database query
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [b'Data loaded']
```

**Why this is bad:** While waiting for the database (or any I/O), the thread is completely blocked. It can't handle ANY other requests. To handle 100 concurrent requests, you need 100 threads/processes, which is expensive.

#### Problem 2: Request-Response Only

With WSGI, the pattern is rigid:
1. Request comes in
2. You return a response
3. Connection closes

**Why this is bad:** Modern web needs long-lived connections:
- **WebSockets:** Chat applications need to keep connections open
- **Server-Sent Events:** Push notifications to clients
- **HTTP/2:** Multiplexed streams on a single connection

WSGI simply can't model these patterns. The interface assumes one request → one response → done.

#### Problem 3: No Streaming Control

```python
def wsgi_app(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    # You must return ALL data at once (or use generators awkwardly)
    return [b'chunk1', b'chunk2', b'chunk3']
```

**Why this is bad:** You can't easily:
- Send headers first, then stream body based on client feedback
- Cancel streaming if client disconnects
- Handle backpressure (slow clients)

### ASGI: The Asynchronous Solution

ASGI solves these problems with a different design:

```python
async def application(scope, receive, send):
    # Asynchronous - can await I/O without blocking
    # Multiple protocols - scope['type'] tells us what protocol
    # Bidirectional - we can both receive AND send messages
    # Streaming control - we control when to send each piece
    pass
```

**Why this is better:**

1. **Async/await:** While waiting for I/O, the event loop can handle other requests
2. **Message-based:** Communication happens through message passing, not just function returns
3. **Protocol-agnostic:** The same interface works for HTTP, WebSocket, etc.
4. **Fine-grained control:** You decide when to send headers, body chunks, close connections

Let's see this in action.

## Understanding ASGI: Building a Mini Server

Let's understand how ASGI works by building our own mini ASGI server. This will show you exactly what uvicorn does behind the scenes.

### The ASGI Interface

Every ASGI application is an async callable with three parameters:

```python
async def app(scope, receive, send):
    pass
```

Let's understand what each parameter does by implementing them ourselves.

### Step 1: The Scope Dictionary

The `scope` is how the server tells your app what's happening. Let's create one:

```python
# What a server sends to your app for an HTTP request
scope = {
    'type': 'http',              # What protocol? (http, websocket, lifespan)
    'method': 'GET',             # HTTP method
    'path': '/hello',            # URL path
    'query_string': b'',         # Query parameters
    'headers': [                 # Request headers (as bytes!)
        [b'host', b'localhost:8000'],
        [b'user-agent', b'curl/7.64.1'],
    ],
    'server': ('127.0.0.1', 8000),  # Server address
    'client': ('127.0.0.1', 54321),  # Client address
    'asgi': {
        'version': '3.0',
    },
}
```

**Why is this a dictionary?** Because different protocols need different information. HTTP needs method/path. WebSocket needs a key. By using a dictionary, the same interface can handle many protocols.

### Step 2: The Receive Callable

The `receive` function lets your app receive messages from the client. For HTTP, there's usually just one message - the request body.

Let's implement a simple receive function:

```python
import asyncio

async def make_receive(body: bytes):
    """
    Creates a receive callable that simulates receiving an HTTP request body.
    This is what a real ASGI server would provide.
    """
    body_sent = False
    
    async def receive():
        nonlocal body_sent
        if not body_sent:
            body_sent = True
            return {
                'type': 'http.request',
                'body': body,
                'more_body': False,  # No more chunks coming
            }
        else:
            # Client has no more data to send
            return {
                'type': 'http.disconnect',
            }
    
    return receive
```

**Why async?** Because in a real server, reading from the network socket is I/O. We need to await it without blocking.

**Why messages?** This message-based approach allows:
- Streaming large request bodies in chunks
- Detecting when the client disconnects
- Supporting different protocols (WebSocket messages, HTTP/2 frames, etc.)

### Step 3: The Send Callable

The `send` function lets your app send messages back to the client. Let's implement one:

```python
async def make_send():
    """
    Creates a send callable that collects messages.
    A real ASGI server would send these over the network socket.
    """
    messages = []
    
    async def send(message):
        messages.append(message)
        print(f"Server received message from app: {message['type']}")
        
        # In a real server, we'd write to the socket here
        if message['type'] == 'http.response.start':
            status = message['status']
            headers = message.get('headers', [])
            print(f"  → HTTP {status}")
            for name, value in headers:
                print(f"  → {name.decode()}: {value.decode()}")
                
        elif message['type'] == 'http.response.body':
            body = message.get('body', b'')
            print(f"  → Body: {body.decode()}")
    
    send.messages = messages  # Store for inspection
    return send
```

**Why two messages for HTTP?** Because HTTP responses have:
1. A status line and headers (sent first)
2. A body (sent after)

Separating them gives you control. You can:
- Send headers immediately
- Stream the body in chunks
- Decide not to send a body for 304 Not Modified

### Step 4: Our First ASGI App

Now let's write a simple ASGI application:

```python
async def simple_app(scope, receive, send):
    """
    A minimal ASGI application.
    """
    # Check what protocol this is
    if scope['type'] == 'http':
        # Send the response headers
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'text/plain'],
            ],
        })
        
        # Send the response body
        await send({
            'type': 'http.response.body',
            'body': b'Hello, ASGI World!',
        })
```

### Step 5: Simulating the Server

Now let's simulate what an ASGI server (like uvicorn) does:

```python
import asyncio

async def run_asgi_app(app, scope, body=b''):
    """
    Simulates an ASGI server calling your app.
    This is essentially what uvicorn does!
    """
    # Create the receive and send callables
    receive = await make_receive(body)
    send = await make_send()
    
    # Call the ASGI app (this is the key line!)
    await app(scope, receive, send)
    
    return send.messages

# Run it!
async def main():
    scope = {
        'type': 'http',
        'method': 'GET',
        'path': '/hello',
        'query_string': b'',
        'headers': [],
    }
    
    messages = await run_asgi_app(simple_app, scope)
    print(f"\nApp sent {len(messages)} messages")

asyncio.run(main())
```

**Save this as `asgi_simulation.py` and run it:**

```bash
python asgi_simulation.py
```

**Output:**
```
Server received message from app: http.response.start
  → HTTP 200
  → content-type: text/plain
Server received message from app: http.response.body
  → Body: Hello, ASGI World!

App sent 2 messages
```

**This is ASGI!** You've just simulated what uvicorn does. The server:
1. Creates a scope with request info
2. Creates receive/send callables
3. Calls your app: `await app(scope, receive, send)`
4. Your app sends messages back through send()
5. The server translates those to HTTP responses

## Deep Dive: Why Async Matters

Let's see the difference between sync and async with a concrete example.

### Synchronous (Blocking)

```python
import time

def sync_handler():
    # Simulating database query - blocks the thread!
    time.sleep(1)
    return "Data"

# If 3 requests come in, they take 3 seconds total
# Request 1: 0s-1s
# Request 2: 1s-2s (has to wait!)
# Request 3: 2s-3s (has to wait!)
```

### Asynchronous (Non-blocking)

```python
import asyncio

async def async_handler():
    # Simulating database query - yields control to event loop!
    await asyncio.sleep(1)
    return "Data"

# If 3 requests come in, they take ~1 second total
# All three can run concurrently!
# Request 1: 0s-1s
# Request 2: 0s-1s (runs concurrently!)
# Request 3: 0s-1s (runs concurrently!)
```

**Why this works:** When you `await`, the event loop can switch to handling other requests. With ASGI:
- One thread can handle thousands of concurrent connections
- Perfect for I/O-bound operations (databases, APIs, file reads)
- Much more efficient than thread-per-request

## Streaming Responses

One powerful feature of ASGI is streaming. Let's see why separating headers and body matters:

```python
import asyncio

async def streaming_app(scope, receive, send):
    """
    Demonstrates streaming responses.
    """
    if scope['type'] == 'http':
        # Send headers FIRST
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'text/plain']],
        })
        
        # Now stream the body in chunks
        for i in range(5):
            await asyncio.sleep(0.5)  # Simulate slow data generation
            await send({
                'type': 'http.response.body',
                'body': f'Chunk {i}\n'.encode(),
                'more_body': True,  # More chunks coming!
            })
        
        # Final chunk
        await send({
            'type': 'http.response.body',
            'body': b'Done!',
            'more_body': False,  # No more chunks
        })

# Test with our simulator
async def test_streaming():
    scope = {'type': 'http', 'method': 'GET', 'path': '/stream'}
    await run_asgi_app(streaming_app, scope)

asyncio.run(test_streaming())
```

**Why this is powerful:**
- Client receives data as it's generated (better UX)
- Server doesn't need to buffer everything in memory
- Can handle huge responses (logs, exports, videos)
- Can cancel if client disconnects mid-stream

## Reading Request Bodies

Let's build an app that reads the request body using `receive`:

```python
async def echo_app(scope, receive, send):
    """
    Echoes back the request body.
    """
    if scope['type'] == 'http':
        # Read the request body
        body_parts = []
        while True:
            message = await receive()
            
            if message['type'] == 'http.request':
                body_parts.append(message.get('body', b''))
                
                # Are there more chunks?
                if not message.get('more_body', False):
                    break
            elif message['type'] == 'http.disconnect':
                # Client disconnected!
                return
        
        # Combine all body parts
        full_body = b''.join(body_parts)
        
        # Send response
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'text/plain']],
        })
        await send({
            'type': 'http.response.body',
            'body': b'You sent: ' + full_body,
        })

# Test it
async def test_echo():
    scope = {'type': 'http', 'method': 'POST', 'path': '/echo'}
    receive = await make_receive(b'Hello, Server!')
    send = await make_send()
    
    await echo_app(scope, receive, send)

asyncio.run(test_echo())
```

**Key insight:** The message-based approach lets you:
- Stream large request bodies without loading everything into memory
- Detect client disconnections mid-upload
- Apply backpressure (slow down reading if you're overwhelmed)

## Class-Based Applications

You can also use classes for ASGI apps. This is useful when you need to maintain configuration or state:

```python
class App:
    def __init__(self, message: str):
        # Configuration stored in instance
        self.message = message
        self.request_count = 0
    
    async def __call__(self, scope, receive, send):
        """
        The __call__ method makes instances callable like functions.
        """
        if scope['type'] == 'http':
            # Access instance variables
            self.request_count += 1
            
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [[b'content-type', b'text/plain']],
            })
            await send({
                'type': 'http.response.body',
                'body': f'{self.message} (Request #{self.request_count})'.encode(),
            })

# Create an instance with configuration
app = App(message="Hello from a class!")

# Now 'app' is a callable: app(scope, receive, send)
```

**Why use classes?**
- Store configuration (database connections, API keys, etc.)
- Share state across requests (caching, metrics)
- Organize complex applications with methods
- Dependency injection patterns

**Note on ASGI 2.0:** There's an older ASGI 2.0 spec that splits scope from receive/send. You may see it in legacy code, but ASGI 3.0 (all three parameters together) is the current standard.

## Common Patterns and Best Practices

### 1. Always Check Scope Type (and understand why)

```python
async def app(scope, receive, send):
    if scope['type'] == 'http':
        # Handle HTTP
        pass
    elif scope['type'] == 'websocket':
        # Handle WebSocket
        pass
    elif scope['type'] == 'lifespan':
        # Handle lifecycle (startup/shutdown)
        pass
    else:
        # Gracefully handle unknown protocols
        raise NotImplementedError(f"Unsupported scope type: {scope['type']}")
```

**Why?** Your app will receive different scope types. If you only support HTTP but a server tries to establish a WebSocket connection, you need to handle it gracefully.

### 2. Error Handling - The Right Way

```python
async def safe_app(scope, receive, send):
    if scope['type'] == 'http':
        try:
            # Your application logic
            result = await some_database_operation()
            
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [[b'content-type', b'application/json']],
            })
            await send({
                'type': 'http.response.body',
                'body': result.encode(),
            })
            
        except ValueError as exc:
            # Client error (400)
            await send({
                'type': 'http.response.start',
                'status': 400,
                'headers': [[b'content-type', b'text/plain']],
            })
            await send({
                'type': 'http.response.body',
                'body': f'Bad Request: {exc}'.encode(),
            })
            
        except Exception as exc:
            # Server error (500)
            await send({
                'type': 'http.response.start',
                'status': 500,
                'headers': [[b'content-type', b'text/plain']],
            })
            await send({
                'type': 'http.response.body',
                'body': b'Internal Server Error',
            })
            # Log the actual exception
            print(f"Error: {exc}")
```

**Why handle errors?** Without error handling, an exception will crash the connection. The client gets a broken connection instead of a proper error response.

### 3. Headers and Body Must Be Bytes (not strings)

```python
# ✅ Correct
headers = [[b'content-type', b'text/plain']]
body = b'Hello World'

# ❌ Wrong - will cause errors!
headers = [['content-type', 'text/plain']]  # Must be bytes!
body = 'Hello World'  # Must be bytes!
```

**Why bytes?** HTTP is a binary protocol. Headers and body are transmitted as bytes over the network. ASGI enforces this to:
- Prevent encoding bugs (is it UTF-8? Latin-1? Binary?)
- Force you to think about encoding explicitly
- Match the reality of network protocols

### 4. Always Send response.start Before response.body

```python
# ✅ Correct order
await send({'type': 'http.response.start', 'status': 200, 'headers': [...]})
await send({'type': 'http.response.body', 'body': b'...'})

# ❌ Wrong order - will fail!
await send({'type': 'http.response.body', 'body': b'...'})
await send({'type': 'http.response.start', 'status': 200, 'headers': [...]})
```

**Why?** This mirrors how HTTP works: status line and headers must be sent before the body. The server needs to know what headers to send before sending any body content.

## Hands-On Exercises

Now that you understand the fundamentals, let's build some ASGI applications from scratch. Run these with pure Python first to understand the mechanics.

### Exercise 1: Complete ASGI Simulation

Create a complete working simulation including the server parts and the app:

**File:** `exercises/01_hello_world.py`

**Goal:** Build everything from scratch to understand the full picture.

```python
import asyncio

# PART 1: Build the helper functions (server-side)
async def make_receive(body: bytes):
    """Simulates receiving data from a client."""
    body_sent = False
    async def receive():
        nonlocal body_sent
        if not body_sent:
            body_sent = True
            return {'type': 'http.request', 'body': body, 'more_body': False}
        return {'type': 'http.disconnect'}
    return receive

async def make_send():
    """Simulates sending data to a client."""
    messages = []
    async def send(message):
        messages.append(message)
        print(f"[SERVER] Received: {message['type']}")
        if message['type'] == 'http.response.body':
            print(f"[SERVER] Body: {message.get('body', b'').decode()}")
    send.messages = messages
    return send

# PART 2: Build your ASGI app
async def app(scope, receive, send):
    """Your ASGI application - implement this!"""
    # TODO: Check if scope['type'] == 'http'
    # TODO: Send response.start with status 200
    # TODO: Send response.body with b'Hello, World!'
    pass

# PART 3: Run the simulation
async def main():
    scope = {'type': 'http', 'method': 'GET', 'path': '/'}
    receive = await make_receive(b'')
    send = await make_send()
    await app(scope, receive, send)

if __name__ == '__main__':
    asyncio.run(main())
```

**Run it:** `python exercises/01_hello_world.py`

**What you'll learn:** How the server and app communicate through scope/receive/send.

---

### Exercise 2: Path Router

Build a simple router that responds differently based on the path:

**File:** `exercises/02_path_router.py`

**Goal:** Understand how to read from the scope dictionary.

```python
async def app(scope, receive, send):
    """
    Route requests based on path:
    - GET / → "Home Page"
    - GET /about → "About Page"  
    - GET /contact → "Contact Page"
    - Other → "404 Not Found" (with status 404)
    """
    if scope['type'] == 'http':
        path = scope['path']
        
        # TODO: Check the path and set appropriate status and body
        # TODO: Remember to send response.start then response.body
        pass
```

**Test it:**
```python
async def test():
    for path in ['/', '/about', '/contact', '/unknown']:
        print(f"\nTesting {path}")
        scope = {'type': 'http', 'method': 'GET', 'path': path}
        receive = await make_receive(b'')
        send = await make_send()
        await app(scope, receive, send)

asyncio.run(test())
```

**What you'll learn:** How to route requests and return different status codes.

---

### Exercise 3: Echo Server

Build an app that echoes back the request body:

**File:** `exercises/03_echo_server.py`

**Goal:** Learn to use the `receive` callable to read request bodies.

```python
async def app(scope, receive, send):
    """
    Read the request body and echo it back.
    """
    if scope['type'] == 'http':
        # TODO: Read from receive() in a loop until more_body is False
        # TODO: Combine all body chunks
        # TODO: Send back "You sent: <body>"
        pass

# Test it
async def test():
    scope = {'type': 'http', 'method': 'POST', 'path': '/echo'}
    receive = await make_receive(b'Hello, ASGI!')
    send = await make_send()
    await app(scope, receive, send)

asyncio.run(test())
```

**What you'll learn:** How to read request bodies using the message-based receive() function.

---

### Exercise 4: Streaming Response

Build an app that streams data in chunks:

**File:** `exercises/04_streaming.py`

**Goal:** Understand how to stream responses and use `more_body`.

```python
async def app(scope, receive, send):
    """
    Stream 5 chunks of data with a delay between each.
    """
    if scope['type'] == 'http':
        # TODO: Send response.start
        # TODO: Send 5 chunks with 'more_body': True
        # TODO: Send final chunk with 'more_body': False
        pass

asyncio.run(test_app())
```

**What you'll learn:** How streaming works and why separating headers/body matters.

---

### Exercise 5: Complete Application

Combine everything into a full application:

**File:** `exercises/05_complete_app.py`

**Goal:** Build a complete ASGI app with routing, error handling, and request reading.

**Requirements:**
- `GET /` → Return "Welcome!" 
- `GET /time` → Return current timestamp
- `POST /echo` → Echo the request body
- Other paths → 404 error
- Handle exceptions with 500 errors

**What you'll learn:** How to build a complete, production-ready ASGI application structure.

## Moving to a Real ASGI Server: Uvicorn

Now that you understand how ASGI works at a fundamental level, let's understand what uvicorn adds on top.

### What We Built vs What Uvicorn Does

Our simulation:
```python
# We manually created scope
scope = {'type': 'http', 'method': 'GET', 'path': '/'}

# We manually created receive/send
receive = await make_receive(b'')
send = await make_send()

# We manually called the app
await app(scope, receive, send)
```

Uvicorn does the same thing, but:
1. **Listens on a real TCP socket** (instead of manual scope creation)
2. **Parses HTTP requests** from raw bytes into scope dictionaries
3. **Implements real receive/send** that read/write to the socket
4. **Handles multiple connections concurrently** using asyncio
5. **Manages the event loop** and error handling
6. **Supports multiple protocols** (HTTP/1.1, HTTP/2, WebSockets)

### Running Your ASGI App with Uvicorn

Once you understand the mechanics, using uvicorn is simple:

**Your app (hello.py):**
```python
async def app(scope, receive, send):
    if scope['type'] == 'http':
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'text/plain']],
        })
        await send({
            'type': 'http.response.body',
            'body': b'Hello from real HTTP!',
        })
```

**Run with uvicorn:**
```bash
uvicorn hello:app --host 0.0.0.0 --port 8000
```

**Test with real HTTP:**
```bash
curl http://localhost:8000
# Output: Hello from real HTTP!
```

**What uvicorn does behind the scenes:**
1. Binds to port 8000
2. Accepts TCP connections
3. Parses incoming HTTP requests into `scope` dictionaries
4. Creates `receive` and `send` callables for each request
5. Calls: `await app(scope, receive, send)`
6. Translates your send() messages back to HTTP responses
7. Writes to the TCP socket

### How Uvicorn Implements ASGI

Let's look at uvicorn's internals to understand how it works:

#### Type Definitions (`uvicorn/_types.py`)

```python
# This is how uvicorn defines an ASGI 3 application
ASGI3Application = Callable[
    [
        Scope,                  # The scope dictionary
        ASGIReceiveCallable,    # The receive function
        ASGISendCallable,       # The send function
    ],
    Awaitable[None],           # Returns an awaitable (async function)
]
```

This type signature matches exactly what we built! An ASGI app is just a callable that takes scope, receive, and send.

#### HTTP Protocol Handler (`uvicorn/protocols/http/h11_impl.py`)

Uvicorn has protocol handlers that implement the real receive/send:

```python
# Simplified from uvicorn's actual code
class HttpProtocol:
    async def handle_request(self):
        # 1. Parse HTTP request → create scope
        scope = {
            'type': 'http',
            'method': self.method,
            'path': self.path,
            # ... more fields from parsing
        }
        
        # 2. Call the ASGI app (just like we did!)
        await self.app(scope, self.receive, self.send)
    
    async def receive(self):
        # Read from the actual socket
        data = await self.transport.read()
        return {'type': 'http.request', 'body': data}
    
    async def send(self, message):
        # Write to the actual socket
        if message['type'] == 'http.response.start':
            self.write_headers(message['status'], message['headers'])
        elif message['type'] == 'http.response.body':
            self.write_body(message['body'])
```

**See?** It's the same pattern we built, just with real network I/O!

### When to Use Pure Python vs Uvicorn

**Use pure Python simulation (what we built) when:**
- Learning ASGI fundamentals
- Testing your ASGI app in unit tests
- Debugging application logic without network complexity
- Building your own ASGI server (like uvicorn!)

**Use uvicorn (or other ASGI servers) when:**
- Running in production
- Need real HTTP/WebSocket connections
- Want performance optimizations (HTTP/2, protocol implementations)
- Need process management and auto-reloading

### Key Insight for Building Your Own Server

If you want to build your own ASGI server like uvicorn, you now know what's required:

1. **Accept TCP connections** (using Python's asyncio server)
2. **Parse HTTP requests** (using http library or h11/httptools)
3. **Create scope dictionaries** from parsed request data
4. **Implement receive()** that reads from the socket
5. **Implement send()** that writes HTTP responses to the socket
6. **Call the ASGI app:** `await app(scope, receive, send)`

The ASGI interface we learned is the boundary between your server and applications. Everything else is implementation details!

## Key Takeaways

Now you understand ASGI at a fundamental level:

### The Problems ASGI Solves

1. **Synchronous Blocking:** WSGI blocks threads during I/O. ASGI uses async/await to handle thousands of concurrent connections efficiently.

2. **Request-Response Only:** WSGI can't handle long-lived connections. ASGI's message-based design supports WebSockets, streaming, and bidirectional communication.

3. **No Streaming Control:** WSGI requires returning all data at once. ASGI separates headers from body and supports chunked streaming.

### The ASGI Contract

1. **Three parameters:** Every ASGI app is `async def app(scope, receive, send)`

2. **scope:** A dictionary with connection info (type, method, path, headers, etc.)

3. **receive:** An async callable to receive messages from the client (request body, disconnect events, etc.)

4. **send:** An async callable to send messages to the client (response headers, body chunks, etc.)

### The Mechanics

1. **Server creates scope, receive, send** from network requests
2. **Server calls your app:** `await app(scope, receive, send)`
3. **Your app communicates through messages** (http.response.start, http.response.body, etc.)
4. **Server translates messages** back to HTTP responses on the wire

### Implementation Path

1. **Learn by building:** Start with pure Python simulations (no uvicorn) to understand the mechanics
2. **Understand the boundary:** ASGI is the interface between servers and apps - both sides just need to implement the contract
3. **Use real servers:** Once you understand the fundamentals, uvicorn (or any ASGI server) handles the network complexity

You now have the foundation to:
- Build ASGI applications from scratch
- Understand how ASGI servers like uvicorn work
- Build your own ASGI server if needed
- Debug ASGI applications effectively

## Next Steps

Now that you understand ASGI fundamentals, proceed to:

➡️ **[Module 2: ASGI Scopes](02-scopes.md)** - Deep dive into the scope dictionary and all its fields

Then continue with:
- **Module 3:** HTTP Protocol - Request/response handling in detail
- **Module 4:** Lifespan - Startup/shutdown hooks
- **Module 5:** WebSockets - Real-time bidirectional communication
- **Module 6:** Middleware - Wrapping and modifying ASGI apps
- **Module 7:** Advanced Patterns - Building production applications

## Additional Resources

- [ASGI Specification](https://asgi.readthedocs.io/) - The official spec
- [PEP 3333 (WSGI)](https://www.python.org/dev/peps/pep-3333/) - Understanding the predecessor
- [Uvicorn Source Code](../../uvicorn/) - See a real ASGI server implementation
  - `uvicorn/_types.py` - Type definitions for ASGI
  - `uvicorn/protocols/http/h11_impl.py` - HTTP protocol implementation
  - `uvicorn/server.py` - Server orchestration
- [ASGI Examples in this repo](examples/) - Working examples to study

## Summary

ASGI isn't just a spec - it's a thoughtful design that solves real problems with synchronous web frameworks. By understanding:
- **Why** the problems exist (WSGI limitations)
- **How** ASGI solves them (async, messages, protocols)
- **What** the interface looks like (scope, receive, send)

You're now equipped to build anything from simple apps to full-featured ASGI servers. The exercises will help cement this understanding through hands-on practice.

Happy coding! 🚀
