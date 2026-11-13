# Module 5: WebSocket Protocol

## Introduction

WebSockets provide **full-duplex, bidirectional communication** between client and server over a single, long-lived connection. Unlike HTTP's request-response model, WebSockets allow both parties to send messages at any time.

Use cases for WebSockets:
- **Chat applications** - Real-time messaging
- **Live updates** - Stock prices, sports scores, notifications
- **Collaborative tools** - Shared documents, whiteboards
- **Gaming** - Multiplayer game state synchronization
- **IoT dashboards** - Real-time sensor data

## WebSocket Handshake

WebSocket connections start as HTTP requests that get "upgraded":

```
1. Client sends HTTP upgrade request
   ↓
2. Server responds with HTTP 101 (Switching Protocols)
   ↓
3. Connection upgraded to WebSocket
   ↓
4. Bidirectional message exchange
   ↓
5. Connection closed by either party
```

### HTTP Upgrade Request

```http
GET /ws HTTP/1.1
Host: localhost:8000
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==
Sec-WebSocket-Version: 13
```

### HTTP Upgrade Response

```http
HTTP/1.1 101 Switching Protocols
Upgrade: websocket
Connection: Upgrade
Sec-WebSocket-Accept: s3pPLMBiTxaQ9kYGzzhZRbK+xOo=
```

## WebSocket Events

### Events Received (from client)

1. **websocket.connect**
```python
{
    'type': 'websocket.connect'
}
```
Sent when client initiates WebSocket handshake.

2. **websocket.receive**
```python
# Text message
{
    'type': 'websocket.receive',
    'text': 'Hello, Server!'
}

# Binary message
{
    'type': 'websocket.receive',
    'bytes': b'\x00\x01\x02\x03'
}
```
Sent when a message is received from the client.

3. **websocket.disconnect**
```python
{
    'type': 'websocket.disconnect',
    'code': 1000  # Close code
}
```
Sent when connection is closed.

### Events Sent (to client)

1. **websocket.accept**
```python
{
    'type': 'websocket.accept',
    'subprotocol': None,  # Optional subprotocol
    'headers': []  # Optional additional headers
}
```
Accept the WebSocket connection.

2. **websocket.send**
```python
# Send text
{
    'type': 'websocket.send',
    'text': 'Hello, Client!'
}

# Send binary
{
    'type': 'websocket.send',
    'bytes': b'\x00\x01\x02\x03'
}
```
Send a message to the client.

3. **websocket.close**
```python
{
    'type': 'websocket.close',
    'code': 1000,  # Optional close code
    'reason': 'Goodbye'  # Optional close reason
}
```
Close the WebSocket connection.

## Basic WebSocket Echo Server

```python
async def app(scope, receive, send):
    """Simple WebSocket echo server."""
    
    if scope['type'] == 'websocket':
        # Accept the connection
        await send({
            'type': 'websocket.accept'
        })
        
        # Echo messages back
        while True:
            message = await receive()
            
            if message['type'] == 'websocket.disconnect':
                break
            
            elif message['type'] == 'websocket.receive':
                # Echo text messages
                if 'text' in message:
                    await send({
                        'type': 'websocket.send',
                        'text': f"Echo: {message['text']}"
                    })
                
                # Echo binary messages
                elif 'bytes' in message:
                    await send({
                        'type': 'websocket.send',
                        'bytes': message['bytes']
                    })
```

Test with JavaScript in browser console:
```javascript
const ws = new WebSocket('ws://localhost:8000');
ws.onmessage = (event) => console.log('Received:', event.data);
ws.send('Hello!');
// Output: Received: Echo: Hello!
```

Or with Python:
```python
import asyncio
import websockets

async def test():
    async with websockets.connect('ws://localhost:8000') as ws:
        await ws.send('Hello!')
        response = await ws.recv()
        print(f'Received: {response}')

asyncio.run(test())
```

## Accepting and Rejecting Connections

You can accept or reject connections based on authentication or other criteria:

```python
async def app(scope, receive, send):
    if scope['type'] == 'websocket':
        # Check for authentication token in query string
        query_string = scope['query_string'].decode()
        
        if 'token=secret123' in query_string:
            # Accept connection
            await send({
                'type': 'websocket.accept'
            })
            
            # Handle messages
            while True:
                message = await receive()
                if message['type'] == 'websocket.disconnect':
                    break
                elif message['type'] == 'websocket.receive':
                    await send({
                        'type': 'websocket.send',
                        'text': 'Authenticated!'
                    })
        else:
            # Reject connection with HTTP response
            await send({
                'type': 'websocket.close',
                'code': 1008,  # Policy Violation
                'reason': 'Authentication required'
            })
```

Test:
```bash
# Will be rejected
websocat ws://localhost:8000

# Will be accepted
websocat "ws://localhost:8000?token=secret123"
```

## WebSocket Close Codes

Standard close codes (from RFC 6455):

| Code | Meaning |
|------|---------|
| 1000 | Normal Closure |
| 1001 | Going Away |
| 1002 | Protocol Error |
| 1003 | Unsupported Data |
| 1007 | Invalid frame payload data |
| 1008 | Policy Violation |
| 1009 | Message Too Big |
| 1010 | Mandatory Extension |
| 1011 | Internal Server Error |
| 1012 | Service Restart |
| 1013 | Try Again Later |
| 1015 | TLS Handshake |

## Chat Room Example

```python
import asyncio
import json
from collections import defaultdict

# Store active connections by room
rooms = defaultdict(list)


async def broadcast(room, message, exclude=None):
    """Broadcast message to all clients in a room."""
    for send_func in rooms[room]:
        if send_func != exclude:
            await send_func({
                'type': 'websocket.send',
                'text': json.dumps(message)
            })


async def app(scope, receive, send):
    """Multi-room chat application."""
    
    if scope['type'] == 'websocket':
        # Parse query string for room and username
        from urllib.parse import parse_qs
        query_string = scope['query_string'].decode()
        params = parse_qs(query_string)
        
        room = params.get('room', ['lobby'])[0]
        username = params.get('user', ['Anonymous'])[0]
        
        # Accept connection
        await send({
            'type': 'websocket.accept'
        })
        
        # Add to room
        rooms[room].append(send)
        
        # Notify others
        await broadcast(room, {
            'type': 'join',
            'user': username,
            'message': f'{username} joined the room'
        }, exclude=send)
        
        try:
            while True:
                message = await receive()
                
                if message['type'] == 'websocket.disconnect':
                    break
                
                elif message['type'] == 'websocket.receive':
                    text = message.get('text', '')
                    
                    # Broadcast message to room
                    await broadcast(room, {
                        'type': 'message',
                        'user': username,
                        'message': text
                    })
        
        finally:
            # Remove from room
            rooms[room].remove(send)
            
            # Notify others
            await broadcast(room, {
                'type': 'leave',
                'user': username,
                'message': f'{username} left the room'
            })
```

Test with multiple clients:
```javascript
// Client 1
const ws1 = new WebSocket('ws://localhost:8000?room=chat&user=Alice');
ws1.onmessage = (e) => console.log('Alice:', e.data);
ws1.send('Hello from Alice!');

// Client 2
const ws2 = new WebSocket('ws://localhost:8000?room=chat&user=Bob');
ws2.onmessage = (e) => console.log('Bob:', e.data);
ws2.send('Hi Alice!');
```

## Handling Binary Data

```python
async def app(scope, receive, send):
    """Handle binary WebSocket data."""
    
    if scope['type'] == 'websocket':
        await send({'type': 'websocket.accept'})
        
        while True:
            message = await receive()
            
            if message['type'] == 'websocket.disconnect':
                break
            
            elif message['type'] == 'websocket.receive':
                if 'bytes' in message:
                    data = message['bytes']
                    
                    # Process binary data
                    # Example: reverse the bytes
                    reversed_data = data[::-1]
                    
                    await send({
                        'type': 'websocket.send',
                        'bytes': reversed_data
                    })
                
                elif 'text' in message:
                    # Convert text to binary
                    await send({
                        'type': 'websocket.send',
                        'bytes': message['text'].encode('utf-8')
                    })
```

## Ping/Pong Heartbeat

Keep connection alive with periodic pings:

```python
import asyncio

async def heartbeat(send):
    """Send periodic pings to keep connection alive."""
    while True:
        await asyncio.sleep(30)
        try:
            await send({
                'type': 'websocket.send',
                'text': '{"type": "ping"}'
            })
        except:
            break


async def app(scope, receive, send):
    """WebSocket with heartbeat."""
    
    if scope['type'] == 'websocket':
        await send({'type': 'websocket.accept'})
        
        # Start heartbeat task
        heartbeat_task = asyncio.create_task(heartbeat(send))
        
        try:
            while True:
                message = await receive()
                
                if message['type'] == 'websocket.disconnect':
                    break
                
                elif message['type'] == 'websocket.receive':
                    text = message.get('text', '')
                    
                    # Handle pong responses
                    if text == '{"type": "pong"}':
                        continue
                    
                    # Echo other messages
                    await send({
                        'type': 'websocket.send',
                        'text': f'Echo: {text}'
                    })
        finally:
            heartbeat_task.cancel()
```

## SubProtocols

WebSockets support subprotocols for standardized message formats:

```python
async def app(scope, receive, send):
    """WebSocket with subprotocol negotiation."""
    
    if scope['type'] == 'websocket':
        # Check requested subprotocols
        subprotocols = scope.get('subprotocols', [])
        
        # Choose a subprotocol
        chosen_subprotocol = None
        if 'json' in subprotocols:
            chosen_subprotocol = 'json'
        elif 'msgpack' in subprotocols:
            chosen_subprotocol = 'msgpack'
        
        # Accept with chosen subprotocol
        await send({
            'type': 'websocket.accept',
            'subprotocol': chosen_subprotocol
        })
        
        # Handle messages based on subprotocol
        while True:
            message = await receive()
            
            if message['type'] == 'websocket.disconnect':
                break
            
            elif message['type'] == 'websocket.receive':
                if chosen_subprotocol == 'json':
                    # Handle JSON messages
                    import json
                    data = json.loads(message['text'])
                    response = json.dumps({'echo': data})
                    await send({
                        'type': 'websocket.send',
                        'text': response
                    })
```

## How Uvicorn Handles WebSockets

### WebSocket Scope Creation

In `uvicorn/protocols/websockets/wsproto_impl.py` (lines 165-191):

```python
def handle_connect(self, event: events.Request) -> None:
    headers = [(b"host", event.host.encode())]
    headers += [(key.lower(), value) for key, value in event.extra_headers]
    raw_path, _, query_string = event.target.partition("?")
    path = unquote(raw_path)
    full_path = self.root_path + path
    full_raw_path = self.root_path.encode("ascii") + raw_path.encode("ascii")
    
    self.scope: WebSocketScope = {
        "type": "websocket",
        "asgi": {"version": self.config.asgi_version, "spec_version": "2.4"},
        "http_version": "1.1",
        "scheme": self.scheme,
        "server": self.server,
        "client": self.client,
        "root_path": self.root_path,
        "path": full_path,
        "raw_path": full_raw_path,
        "query_string": query_string.encode("ascii"),
        "headers": headers,
        "subprotocols": event.subprotocols,
        "state": self.app_state.copy(),
        "extensions": {"websocket.http.response": {}},
    }
    
    self.queue.put_nowait({"type": "websocket.connect"})
```

### Type Definitions

In `uvicorn/_types.py`:

```python
# WebSocket Scope (lines 73-87)
class WebSocketScope(TypedDict):
    type: Literal["websocket"]
    asgi: ASGIVersions
    http_version: str
    scheme: str
    path: str
    raw_path: bytes
    query_string: bytes
    root_path: str
    headers: Iterable[tuple[bytes, bytes]]
    client: tuple[str, int] | None
    server: tuple[str, int | None] | None
    subprotocols: Iterable[str]
    state: NotRequired[dict[str, Any]]
    extensions: NotRequired[dict[str, dict[object, object]]]

# WebSocket Events (lines 140-202)
class WebSocketConnectEvent(TypedDict):
    type: Literal["websocket.connect"]

class WebSocketReceiveEvent(Union[...]):
    type: Literal["websocket.receive"]
    bytes: bytes | text: str

class WebSocketSendEvent(Union[...]):
    type: Literal["websocket.send"]
    bytes: bytes | text: str

class WebSocketDisconnectEvent(TypedDict):
    type: Literal["websocket.disconnect"]
    code: int

class WebSocketCloseEvent(TypedDict):
    type: Literal["websocket.close"]
    code: NotRequired[int]
    reason: NotRequired[str | None]
```

## Exercises

### Exercise 1: Echo Server

Create a simple WebSocket echo server:

```python
async def app(scope, receive, send):
    # Accept connection
    # Echo all messages back
    # Handle disconnect
    pass
```

### Exercise 2: Uppercase Service

Create a WebSocket that converts messages to uppercase:

```python
async def app(scope, receive, send):
    # Accept connection
    # Receive text messages
    # Send back uppercase version
    pass
```

### Exercise 3: Counter

Create a WebSocket that counts messages:

```python
async def app(scope, receive, send):
    # Track number of messages received
    # Send count with each message
    # Example: "Message 1: Hello"
    pass
```

### Exercise 4: Authenticated Chat

Create a chat room with token authentication:

```python
async def app(scope, receive, send):
    # Check for token in query string
    # Reject if missing/invalid
    # Accept if valid
    # Broadcast messages to all connected clients
    pass
```

### Exercise 5: Binary Image Server

Create a WebSocket that:
- Receives binary image data
- Processes it (e.g., inverts colors)
- Sends processed image back

```python
async def app(scope, receive, send):
    # Accept connection
    # Receive binary data
    # Process bytes
    # Send back processed data
    pass
```

## Key Takeaways

1. ✅ WebSockets provide **bidirectional** communication
2. ✅ Must **accept connection** before sending messages
3. ✅ Can send **text** or **bytes** messages
4. ✅ Handle **websocket.disconnect** to cleanup
5. ✅ Use **websocket.close** to gracefully close
6. ✅ Can **reject connections** based on criteria
7. ✅ **Subprotocols** enable standardized formats
8. ✅ Use **close codes** to communicate close reason

## Next Steps

Now that you understand WebSockets, proceed to:

➡️ [Module 6: ASGI Middleware](06-middleware.md) - Wrap applications with middleware

## Additional Resources

- [WebSocket Protocol RFC 6455](https://datatracker.ietf.org/doc/html/rfc6455)
- [ASGI WebSocket Specification](https://asgi.readthedocs.io/en/latest/specs/www.html#websocket)
- [Uvicorn WebSocket Implementation](../../uvicorn/protocols/websockets/wsproto_impl.py)
- [Uvicorn WebSocket Documentation](../../docs/concepts/websockets.md)
- [WebSocket Type Definitions](../../uvicorn/_types.py)

