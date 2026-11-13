# Module 4: Lifespan Protocol

## Introduction

The **Lifespan protocol** in ASGI provides a way to handle application startup and shutdown events. This is essential for:

- **Initializing resources** (database connections, caches, ML models)
- **Cleaning up resources** (closing connections, saving state)
- **Performing warmup** operations
- **Managing application state** across requests

The lifespan protocol runs **once per application instance**, before any HTTP or WebSocket connections are handled.

## Why Lifespan Matters

Without lifespan management, you might:
- ❌ Create a new database connection for every request (inefficient)
- ❌ Leave connections open when shutting down (resource leaks)
- ❌ Not properly initialize expensive resources (ML models, caches)
- ❌ Have no place to run startup/shutdown logic

With lifespan:
- ✅ Initialize resources once at startup
- ✅ Share resources across all requests
- ✅ Clean up properly on shutdown
- ✅ Graceful application lifecycle management

## Lifespan Scope

The lifespan connection has a minimal scope:

```python
{
    'type': 'lifespan',
    'asgi': {
        'version': '3.0',
        'spec_version': '2.0'
    },
    'state': {}  # Shared state dictionary
}
```

The `state` dictionary is important - it's shared across all connections (HTTP, WebSocket) in the same application instance.

## Lifespan Events

### Events Received (from server)

1. **lifespan.startup**
```python
{
    'type': 'lifespan.startup'
}
```
Sent when the server starts, before accepting connections.

2. **lifespan.shutdown**
```python
{
    'type': 'lifespan.shutdown'
}
```
Sent when the server is shutting down, after connections close.

### Events Sent (to server)

1. **lifespan.startup.complete**
```python
{
    'type': 'lifespan.startup.complete'
}
```
Sent when startup tasks are complete.

2. **lifespan.startup.failed**
```python
{
    'type': 'lifespan.startup.failed',
    'message': 'Error message describing what went wrong'
}
```
Sent if startup fails.

3. **lifespan.shutdown.complete**
```python
{
    'type': 'lifespan.shutdown.complete'
}
```
Sent when shutdown tasks are complete.

4. **lifespan.shutdown.failed**
```python
{
    'type': 'lifespan.shutdown.failed',
    'message': 'Error message describing what went wrong'
}
```
Sent if shutdown fails.

## Basic Lifespan Implementation

```python
async def app(scope, receive, send):
    """Application with lifespan support."""
    
    if scope['type'] == 'lifespan':
        while True:
            message = await receive()
            
            if message['type'] == 'lifespan.startup':
                # Perform startup tasks
                print("🚀 Application starting up...")
                # Initialize resources here
                await send({'type': 'lifespan.startup.complete'})
            
            elif message['type'] == 'lifespan.shutdown':
                # Perform shutdown tasks
                print("🛑 Application shutting down...")
                # Clean up resources here
                await send({'type': 'lifespan.shutdown.complete'})
                return  # Exit the lifespan loop
    
    elif scope['type'] == 'http':
        # Handle HTTP requests
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'text/plain']],
        })
        await send({
            'type': 'http.response.body',
            'body': b'Hello, World!',
        })
```

Run it and watch the console:
```bash
uvicorn module:app
# Output:
# 🚀 Application starting up...
# INFO:     Uvicorn running on http://127.0.0.1:8000
# (Press CTRL+C)
# 🛑 Application shutting down...
```

## Using State for Shared Resources

The `state` dictionary in the scope is shared across all connections:

```python
# Simulated database connection
class Database:
    def __init__(self):
        self.connected = False
    
    async def connect(self):
        print("📡 Connecting to database...")
        # Simulate connection delay
        import asyncio
        await asyncio.sleep(1)
        self.connected = True
        print("✅ Database connected!")
    
    async def disconnect(self):
        print("📡 Disconnecting from database...")
        self.connected = False
        print("✅ Database disconnected!")
    
    def query(self, sql):
        if not self.connected:
            raise RuntimeError("Database not connected")
        return f"Results for: {sql}"


async def app(scope, receive, send):
    """Application with database connection."""
    
    if scope['type'] == 'lifespan':
        while True:
            message = await receive()
            
            if message['type'] == 'lifespan.startup':
                # Create and connect database
                db = Database()
                await db.connect()
                
                # Store in state for use in HTTP handlers
                scope['state']['db'] = db
                
                await send({'type': 'lifespan.startup.complete'})
            
            elif message['type'] == 'lifespan.shutdown':
                # Get database and disconnect
                db = scope['state'].get('db')
                if db:
                    await db.disconnect()
                
                await send({'type': 'lifespan.shutdown.complete'})
                return
    
    elif scope['type'] == 'http':
        # Get database from state
        db = scope['state'].get('db')
        
        if db:
            result = db.query("SELECT * FROM users")
            body = f"Query result: {result}".encode()
        else:
            body = b"Database not available"
        
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'text/plain']],
        })
        await send({
            'type': 'http.response.body',
            'body': body,
        })
```

## Handling Startup Failures

If startup fails, send `lifespan.startup.failed`:

```python
async def app(scope, receive, send):
    if scope['type'] == 'lifespan':
        while True:
            message = await receive()
            
            if message['type'] == 'lifespan.startup':
                try:
                    # Attempt to initialize resources
                    db = Database()
                    await db.connect()
                    
                    if not db.connected:
                        raise RuntimeError("Failed to connect to database")
                    
                    scope['state']['db'] = db
                    await send({'type': 'lifespan.startup.complete'})
                
                except Exception as exc:
                    # Report startup failure
                    await send({
                        'type': 'lifespan.startup.failed',
                        'message': str(exc)
                    })
                    return  # Exit - server won't start
            
            elif message['type'] == 'lifespan.shutdown':
                db = scope['state'].get('db')
                if db:
                    await db.disconnect()
                await send({'type': 'lifespan.shutdown.complete'})
                return
```

## Complete Example with Multiple Resources

```python
import asyncio

class AppResources:
    """Container for application resources."""
    
    def __init__(self):
        self.db = None
        self.cache = None
        self.http_client = None
    
    async def startup(self):
        """Initialize all resources."""
        print("🚀 Starting up application resources...")
        
        # Initialize database
        print("  📊 Initializing database...")
        self.db = {"connected": True, "data": {}}
        await asyncio.sleep(0.5)
        print("  ✅ Database ready")
        
        # Initialize cache
        print("  💾 Initializing cache...")
        self.cache = {}
        await asyncio.sleep(0.3)
        print("  ✅ Cache ready")
        
        # Initialize HTTP client
        print("  🌐 Initializing HTTP client...")
        self.http_client = {"session": "active"}
        await asyncio.sleep(0.2)
        print("  ✅ HTTP client ready")
        
        print("✅ All resources initialized!")
    
    async def shutdown(self):
        """Clean up all resources."""
        print("🛑 Shutting down application resources...")
        
        if self.http_client:
            print("  🌐 Closing HTTP client...")
            self.http_client = None
        
        if self.cache:
            print("  💾 Clearing cache...")
            self.cache = None
        
        if self.db:
            print("  📊 Disconnecting database...")
            self.db = None
        
        print("✅ All resources cleaned up!")


async def app(scope, receive, send):
    """Application with complete resource management."""
    
    if scope['type'] == 'lifespan':
        resources = AppResources()
        
        while True:
            message = await receive()
            
            if message['type'] == 'lifespan.startup':
                try:
                    await resources.startup()
                    scope['state']['resources'] = resources
                    await send({'type': 'lifespan.startup.complete'})
                except Exception as exc:
                    await send({
                        'type': 'lifespan.startup.failed',
                        'message': f'Startup failed: {exc}'
                    })
                    return
            
            elif message['type'] == 'lifespan.shutdown':
                try:
                    await resources.shutdown()
                    await send({'type': 'lifespan.shutdown.complete'})
                except Exception as exc:
                    await send({
                        'type': 'lifespan.shutdown.failed',
                        'message': f'Shutdown failed: {exc}'
                    })
                finally:
                    return
    
    elif scope['type'] == 'http':
        resources = scope['state'].get('resources')
        
        if resources and resources.db:
            status = "✅ All systems operational"
            data_count = len(resources.db.get('data', {}))
            cache_size = len(resources.cache)
            
            body = f"""
Application Status: {status}
Database: Connected
Database Records: {data_count}
Cache Size: {cache_size}
HTTP Client: {resources.http_client['session']}
            """.strip().encode()
        else:
            body = b"❌ Resources not initialized"
        
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'text/plain']],
        })
        await send({
            'type': 'http.response.body',
            'body': body,
        })
```

## Lifespan Architecture in Uvicorn

According to the uvicorn docs (`docs/concepts/lifespan.md`), the lifespan runs as a **sibling task** alongside the main application:

```
┌─────────────────────────────────────────────┐
│           Uvicorn Server                    │
├─────────────────────────────────────────────┤
│                                             │
│  ┌─────────────┐      ┌─────────────────┐  │
│  │  Lifespan   │      │   Application   │  │
│  │    Task     │      │      Task       │  │
│  │             │      │  (HTTP/WS)      │  │
│  │  - startup  │      │                 │  │
│  │  - running  │      │  - Handle       │  │
│  │  - shutdown │      │    requests     │  │
│  └─────────────┘      └─────────────────┘  │
│                                             │
└─────────────────────────────────────────────┘
```

Both tasks run concurrently. The lifespan task:
1. Starts first, runs startup
2. Keeps running (maintains state)
3. Application task starts serving requests
4. On shutdown signal, stops accepting new requests
5. Lifespan runs shutdown
6. Server exits

## How Uvicorn Implements Lifespan

### Lifespan Handler

In `uvicorn/lifespan/on.py` (lines 31-138), you can see the `LifespanOn` class:

```python
class LifespanOn:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.startup_event = asyncio.Event()
        self.shutdown_event = asyncio.Event()
        self.receive_queue: Queue[LifespanReceiveMessage] = asyncio.Queue()
        self.state: dict[str, Any] = {}
    
    async def startup(self) -> None:
        # Create lifespan task
        loop = asyncio.get_event_loop()
        main_lifespan_task = loop.create_task(self.main())
        
        # Send startup event
        startup_event: LifespanStartupEvent = {"type": "lifespan.startup"}
        await self.receive_queue.put(startup_event)
        await self.startup_event.wait()
    
    async def shutdown(self) -> None:
        # Send shutdown event
        shutdown_event: LifespanShutdownEvent = {"type": "lifespan.shutdown"}
        await self.receive_queue.put(shutdown_event)
        await self.shutdown_event.wait()
    
    async def main(self) -> None:
        # Call the ASGI app with lifespan scope
        app = self.config.loaded_app
        scope: LifespanScope = {
            "type": "lifespan",
            "asgi": {"version": self.config.asgi_version, "spec_version": "2.0"},
            "state": self.state,
        }
        await app(scope, self.receive, self.send)
```

### Type Definitions

In `uvicorn/_types.py`:

```python
# Lifespan Scope (lines 90-93)
class LifespanScope(TypedDict):
    type: Literal["lifespan"]
    asgi: ASGIVersions
    state: NotRequired[dict[str, Any]]

# Lifespan Events (lines 204-228)
class LifespanStartupEvent(TypedDict):
    type: Literal["lifespan.startup"]

class LifespanShutdownEvent(TypedDict):
    type: Literal["lifespan.shutdown"]

class LifespanStartupCompleteEvent(TypedDict):
    type: Literal["lifespan.startup.complete"]

class LifespanStartupFailedEvent(TypedDict):
    type: Literal["lifespan.startup.failed"]
    message: str

class LifespanShutdownCompleteEvent(TypedDict):
    type: Literal["lifespan.shutdown.complete"]

class LifespanShutdownFailedEvent(TypedDict):
    type: Literal["lifespan.shutdown.failed"]
    message: str
```

## Best Practices

### 1. Always Handle Both Events

```python
# ✅ Good: Handle both startup and shutdown
if message['type'] == 'lifespan.startup':
    # Initialize
    await send({'type': 'lifespan.startup.complete'})
elif message['type'] == 'lifespan.shutdown':
    # Cleanup
    await send({'type': 'lifespan.shutdown.complete'})
    return

# ❌ Bad: Only handle startup
if message['type'] == 'lifespan.startup':
    await send({'type': 'lifespan.startup.complete'})
# Missing shutdown handling!
```

### 2. Use Try/Except for Robust Error Handling

```python
# ✅ Good: Catch and report errors
try:
    await initialize_resources()
    await send({'type': 'lifespan.startup.complete'})
except Exception as exc:
    await send({
        'type': 'lifespan.startup.failed',
        'message': str(exc)
    })
```

### 3. Store Resources in State

```python
# ✅ Good: Use state dict
scope['state']['db'] = db_connection

# ❌ Bad: Use global variables
global db_connection
db_connection = create_connection()
```

### 4. Cleanup in Finally Blocks

```python
# ✅ Good: Ensure cleanup happens
try:
    await send({'type': 'lifespan.shutdown.complete'})
except Exception as exc:
    await send({'type': 'lifespan.shutdown.failed', 'message': str(exc)})
finally:
    return  # Always exit lifespan loop
```

## Exercises

### Exercise 1: Simple Lifespan

Create an app that prints startup and shutdown messages:

```python
async def app(scope, receive, send):
    # Print "Starting..." on startup
    # Print "Stopping..." on shutdown
    # Handle HTTP with "OK" response
    pass
```

### Exercise 2: Request Counter

Use lifespan state to track request count:

```python
async def app(scope, receive, send):
    # On startup: Initialize counter in state
    # On HTTP: Increment counter, return count
    # On shutdown: Print total requests
    pass
```

### Exercise 3: Resource Pool

Simulate a connection pool with startup/shutdown:

```python
async def app(scope, receive, send):
    # Startup: Create 5 "connections" in a pool
    # HTTP: Show available connections
    # Shutdown: Close all connections
    pass
```

### Exercise 4: Configuration Loader

Load configuration on startup:

```python
import json

async def app(scope, receive, send):
    # Startup: Load config from config.json
    # Store in state
    # HTTP: Display config values
    # Shutdown: Save any modified config
    pass
```

## Key Takeaways

1. ✅ Lifespan runs **once per application instance**
2. ✅ Use **lifespan.startup** for initialization
3. ✅ Use **lifespan.shutdown** for cleanup
4. ✅ Store resources in **scope['state']** for sharing
5. ✅ Always send **complete** or **failed** responses
6. ✅ Lifespan runs as a **sibling task**, not parent
7. ✅ `ContextVar` from lifespan **won't be available** in requests
8. ✅ Handle errors gracefully with try/except

## Next Steps

Now that you understand lifespan, proceed to:

➡️ [Module 5: WebSocket Protocol](05-websocket.md) - Real-time bidirectional communication

## Additional Resources

- [ASGI Lifespan Specification](https://asgi.readthedocs.io/en/latest/specs/lifespan.html)
- [Uvicorn Lifespan Implementation](../../uvicorn/lifespan/on.py)
- [Uvicorn Lifespan Documentation](../../docs/concepts/lifespan.md)
- [Lifespan Type Definitions](../../uvicorn/_types.py)

