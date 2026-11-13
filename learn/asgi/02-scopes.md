# Module 2: ASGI Scopes - Understanding the Information Highway

## Introduction

In Module 1, you saw that every ASGI application receives three parameters: `scope`, `receive`, and `send`. The scope dictionary is how the server tells your app **what's happening**. But why is it designed this way? Let's understand from first principles.

## The Problem: How Does Your App Know What to Do?

Imagine you're building a web server. A client sends this HTTP request:

```http
GET /users/123?format=json HTTP/1.1
Host: api.example.com
Authorization: Bearer abc123
User-Agent: curl/7.68.0
```

Your application needs to know:
- What method? (GET)
- What path? (/users/123)
- What query? (format=json)
- What headers? (Authorization, User-Agent, etc.)
- Who's the client? (IP address)
- Is it HTTP or HTTPS?

**The question:** How do you pass all this information to your app?

### Bad Approach #1: Separate Parameters

```python
async def app(method, path, query, headers, client_ip, scheme, ...):
    # What if we add HTTP/2? Need to change signature!
    # What about WebSockets? Different parameters!
    # Not flexible!
    pass
```

**Why this is bad:**
- Function signature changes when protocol changes
- Different signatures for HTTP vs WebSocket vs Lifespan
- Can't add new fields without breaking existing apps

### Bad Approach #2: Custom Object

```python
class Request:
    def __init__(self):
        self.method = "GET"
        self.path = "/users"
        # ...

async def app(request, receive, send):
    # What if server uses different Request class?
    # What about extensibility?
    pass
```

**Why this is bad:**
- Coupling between server and app
- Hard to extend
- Different servers need different classes

### ASGI's Solution: A Dictionary!

```python
scope = {
    'type': 'http',
    'method': 'GET',
    'path': '/users/123',
    'query_string': b'format=json',
    'headers': [...],
    # ... everything else
}

async def app(scope, receive, send):
    # Flexible: servers can add new fields
    # Protocol-agnostic: same pattern for HTTP, WebSocket, Lifespan
    # Extensible: just add keys to the dict
    pass
```

**Why this is good:**
1. **Flexible:** New fields don't break existing apps (they just ignore unknown keys)
2. **Protocol-agnostic:** Same pattern for all protocols (just change `type` field)
3. **Extensible:** Servers can add custom fields
4. **Simple:** Just a Python dictionary!

## Building a Scope from Scratch

Let's understand how a server creates a scope by building one ourselves from a raw HTTP request.

### Step 1: Parse Raw HTTP Request

```python
# Raw HTTP request (what arrives over TCP socket)
raw_http = b"""GET /users/123?format=json HTTP/1.1\r
Host: api.example.com\r
Authorization: Bearer abc123\r
User-Agent: curl/7.68.0\r
\r
"""

def parse_http_request(raw_http: bytes):
    """
    Parse raw HTTP into components.
    This is what a real server does!
    """
    lines = raw_http.split(b'\r\n')
    
    # Parse request line
    request_line = lines[0].decode('ascii')
    method, full_path, http_version = request_line.split(' ')
    
    # Split path and query
    if '?' in full_path:
        path, query_string = full_path.split('?', 1)
    else:
        path, query_string = full_path, ''
    
    # Parse headers
    headers = []
    for line in lines[1:]:
        if not line:  # Empty line marks end of headers
            break
        name, value = line.split(b': ', 1)
        headers.append([name.lower(), value])
    
    return {
        'method': method,
        'path': path,
        'query_string': query_string.encode(),
        'http_version': http_version.split('/')[-1],
        'headers': headers
    }

# Test it
parsed = parse_http_request(raw_http)
print(f"Method: {parsed['method']}")
print(f"Path: {parsed['path']}")
print(f"Query: {parsed['query_string']}")
print(f"Headers: {parsed['headers']}")
```

**Run this yourself!** See how HTTP parsing works.

### Step 2: Build ASGI Scope

Now let's turn parsed HTTP into an ASGI scope:

```python
def build_http_scope(parsed, client_addr, server_addr):
    """
    Build an ASGI HTTP scope from parsed data.
    This is what uvicorn does!
    """
    return {
        # Protocol type
        'type': 'http',
        
        # ASGI metadata
        'asgi': {
            'version': '3.0',
            'spec_version': '2.4'
        },
        
        # HTTP info
        'http_version': parsed['http_version'],
        'method': parsed['method'],
        'scheme': 'https',  # Would check TLS in real server
        
        # Path info
        'path': parsed['path'],
        'raw_path': parsed['path'].encode(),
        'query_string': parsed['query_string'],
        'root_path': '',  # For mounted apps
        
        # Headers
        'headers': parsed['headers'],
        
        # Connection info
        'server': server_addr,
        'client': client_addr,
        
        # Extension point
        'state': {},
        'extensions': {}
    }

# Build scope
scope = build_http_scope(
    parsed,
    client_addr=('192.168.1.100', 54321),
    server_addr=('10.0.0.1', 443)
)

print("Complete ASGI Scope:")
import json
print(json.dumps(scope, indent=2, default=str))
```

**You just built an ASGI scope!** This is fundamentally what every ASGI server does.

## Why Design Decisions Matter

### Why is `path` a String but `raw_path` is Bytes?

```python
# URL with special characters
raw_http = b"GET /users/%E4%B8%AD%E6%96%87 HTTP/1.1\r\n\r\n"

# The problem:
# - URL is percent-encoded bytes over the wire
# - Application usually wants decoded string
# - But what if encoding is ambiguous?

scope = {
    'path': '/users/中文',       # Decoded, convenient
    'raw_path': b'/users/%E4%B8%AD%E6%96%87',  # Original bytes, precise
}
```

**Why both?**
- `path`: Convenient for 99% of cases (already decoded)
- `raw_path`: Precise for edge cases (what if percent-encoding is malformed?)

### Why are Headers a List of Tuples, Not a Dict?

```python
# Multiple headers with same name (valid in HTTP!)
headers_list = [
    [b'set-cookie', b'session=abc'],
    [b'set-cookie', b'token=xyz'],  # Same name!
]

# If it was a dict:
headers_dict = {
    b'set-cookie': b'token=xyz'  # Lost the first one!
}
```

**Why list of tuples?**
- HTTP allows multiple headers with the same name
- Dict would lose duplicates
- List preserves order and duplicates

### Why is `query_string` Bytes, Not Parsed Dict?

```python
# Query string
query_string = b'name=Alice&age=30&tags=python&tags=asgi'

# Why not parse it?
# - Different parsing rules (& vs ;, encoding, etc.)
# - Application might want custom parsing
# - Keep scope simple, let app decide

# Application can parse however it wants:
from urllib.parse import parse_qs
params = parse_qs(query_string.decode())
# {'name': ['Alice'], 'age': ['30'], 'tags': ['python', 'asgi']}
```

**Why bytes?**
- Let application choose how to parse
- Different apps have different needs
- Keeps ASGI server simple

## Scope Inspector: See It in Action

Let's build a tool to inspect scopes:

```python
import asyncio
import json

async def scope_inspector(scope, receive, send):
    """
    ASGI app that shows you the scope dictionary.
    Great for learning and debugging!
    """
    if scope['type'] == 'http':
        # Format scope for display
        display_scope = {
            'type': scope['type'],
            'method': scope['method'],
            'path': scope['path'],
            'query_string': scope['query_string'].decode(),
            'headers': [
                [name.decode(), value.decode()]
                for name, value in scope['headers']
            ],
            'server': scope['server'],
            'client': scope['client'],
        }
        
        # Send as JSON response
        body = json.dumps(display_scope, indent=2).encode()
        
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'application/json'],
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': body,
        })

# Save as scope_inspector.py and run:
# uvicorn scope_inspector:scope_inspector
# Then visit: http://localhost:8000/test?foo=bar
```

You'll see your scope dictionary as JSON! Try different paths, query strings, and headers.

## HTTP Scope Deep Dive

Now that you understand WHY, let's see every field:

### Complete HTTP Scope

```python
{
    # === Required Fields ===
    
    'type': 'http',  # Always 'http' for HTTP requests
    
    # ASGI version info
    'asgi': {
        'version': '3.0',         # ASGI version (2.0 or 3.0)
        'spec_version': '2.4'     # ASGI HTTP spec version
    },
    
    # HTTP protocol version
    'http_version': '1.1',  # '1.0', '1.1', or '2'
    
    # Request method
    'method': 'GET',  # GET, POST, PUT, DELETE, etc.
    
    # URL scheme
    'scheme': 'https',  # 'http' or 'https'
    
    # URL path (decoded Unicode string)
    'path': '/users/123',
    
    # URL path (raw bytes, percent-encoded)
    'raw_path': b'/users/123',
    
    # Query string (raw bytes after ?)
    'query_string': b'format=json&limit=10',
    
    # Root path for mounted apps
    'root_path': '',  # Usually empty, used for sub-apps
    
    # Headers (list of [name, value] pairs, both bytes, lowercase names)
    'headers': [
        [b'host', b'api.example.com'],
        [b'user-agent', b'curl/7.68.0'],
        [b'authorization', b'Bearer abc123'],
    ],
    
    # === Connection Info ===
    
    # Server address (host, port) or None
    'server': ('10.0.0.1', 443),
    
    # Client address (host, port) or None  
    'client': ('192.168.1.100', 54321),
    
    # === Optional Fields ===
    
    # Shared state dictionary
    'state': {},
    
    # Protocol extensions
    'extensions': {
        'http.response.push': {},  # HTTP/2 server push
    }
}
```

### Working with Headers

Headers are tricky because they're bytes. Here's a helper:

```python
def get_header(headers: list, name: str) -> str | None:
    """
    Get header value by name (case-insensitive).
    
    Returns None if header not found.
    """
    name_lower = name.lower().encode()
    
    for header_name, header_value in headers:
        if header_name.lower() == name_lower:
            return header_value.decode('utf-8')
    
    return None

# Usage
async def app(scope, receive, send):
    if scope['type'] == 'http':
        auth = get_header(scope['headers'], 'Authorization')
        user_agent = get_header(scope['headers'], 'User-Agent')
        
        print(f"Auth: {auth}")
        print(f"User-Agent: {user_agent}")
```

**Why this helper is needed:**
- Header names are case-insensitive in HTTP
- Headers are bytes in ASGI
- Need to compare lowercase versions

## WebSocket Scope

WebSockets start as HTTP but upgrade. The scope reflects this:

```python
{
    'type': 'websocket',  # Not 'http'!
    
    'asgi': {
        'version': '3.0',
        'spec_version': '2.4'
    },
    
    # Still has HTTP fields (from upgrade request)
    'http_version': '1.1',
    'scheme': 'wss',  # 'ws' or 'wss'
    'path': '/chat',
    'raw_path': b'/chat',
    'query_string': b'room=general&user=alice',
    'headers': [
        [b'upgrade', b'websocket'],
        [b'connection', b'Upgrade'],
        [b'sec-websocket-key', b'...'],
        [b'sec-websocket-version', b'13'],
    ],
    
    # WebSocket-specific
    'subprotocols': ['chat', 'superchat'],  # Requested subprotocols
    
    'server': ('10.0.0.1', 443),
    'client': ('192.168.1.100', 54322),
    'state': {},
    'extensions': {
        'websocket.http.response': {}  # Can reject with HTTP response
    }
}
```

**Why it looks like HTTP:**
- WebSocket handshake IS an HTTP request
- Then "upgrades" to WebSocket protocol
- Scope captures the initial HTTP request info

## Lifespan Scope

Lifespan has the simplest scope (it's not a request!):

```python
{
    'type': 'lifespan',  # Indicates lifecycle management
    
    'asgi': {
        'version': '3.0',
        'spec_version': '2.0'
    },
    
    # Shared state (important!)
    'state': {}  # Same dict shared with HTTP/WebSocket scopes
}
```

**Why so simple?**
- Lifespan isn't handling a request
- It's just managing application lifecycle
- The `state` dict is key - it's shared across ALL connections

## How Uvicorn Creates Scopes

Let's see how uvicorn actually does it. In `uvicorn/protocols/http/h11_impl.py`:

```python
# Simplified from actual uvicorn code
class H11Protocol:
    def handle_request(self, event):
        # Parse HTTP request using h11 library
        method = event.method
        target = event.target  # path + query
        
        # Split path and query
        path_bytes, _, query_bytes = target.partition(b'?')
        path = path_bytes.decode('ascii')
        
        # Build scope
        self.scope = {
            'type': 'http',
            'asgi': {
                'version': self.config.asgi_version,
                'spec_version': '2.4'
            },
            'http_version': self.http_version,
            'method': method.decode('ascii'),
            'scheme': 'https' if self.transport.get_extra_info('ssl_object') else 'http',
            'path': path,
            'raw_path': path_bytes,
            'query_string': query_bytes,
            'root_path': self.root_path,
            'headers': self.headers,
            'server': self.server,
            'client': self.client,
            'state': self.app_state.copy(),
            'extensions': {'http.response.push': {}}
        }
        
        # Call ASGI app
        await self.app(self.scope, self.receive, self.send)
```

**See?** It's exactly what we built earlier! Just with more production polish.

## Exercises

### Exercise 1: HTTP Request Parser

Build a complete HTTP request parser:

```python
def parse_http_to_scope(raw_http: bytes, client_addr, server_addr):
    """
    Parse raw HTTP request into ASGI scope.
    
    Handle:
    - Request line (method, path, version)
    - Headers
    - Query string
    - Return complete scope dict
    """
    # Your code here
    pass

# Test with:
raw = b"""GET /api/users?page=2 HTTP/1.1\r
Host: api.example.com\r
Authorization: Bearer token123\r
\r
"""

scope = parse_http_to_scope(raw, ('1.2.3.4', 12345), ('10.0.0.1', 80))
print(scope)
```

### Exercise 2: Header Helper Functions

Create utilities for working with headers:

```python
def get_header(headers, name: str) -> str | None:
    """Get single header value."""
    pass

def get_all_headers(headers, name: str) -> list[str]:
    """Get all values for a header (e.g., multiple Set-Cookie)."""
    pass

def has_header(headers, name: str) -> bool:
    """Check if header exists."""
    pass
```

### Exercise 3: Query String Parser

Build a query string parser:

```python
def parse_query_string(query_string: bytes) -> dict:
    """
    Parse query string into dict.
    
    Handle:
    - Multiple values for same key
    - URL decoding
    - Empty values
    
    Example:
    b'name=Alice&tags=python&tags=asgi&empty='
    -> {'name': ['Alice'], 'tags': ['python', 'asgi'], 'empty': ['']}
    """
    pass
```

### Exercise 4: Scope Validator

Create a function that validates ASGI scopes:

```python
def validate_http_scope(scope: dict) -> list[str]:
    """
    Validate HTTP scope has all required fields.
    Returns list of errors (empty if valid).
    """
    errors = []
    
    # Check required fields
    # Check types
    # Check values
    
    return errors

# Test
scope = {'type': 'http'}  # Missing fields
errors = validate_http_scope(scope)
for error in errors:
    print(f"Error: {error}")
```

## Key Takeaways

### Design Decisions

1. ✅ **Dictionary** - Flexible, extensible, protocol-agnostic
2. ✅ **Type field** - Distinguish HTTP/WebSocket/Lifespan
3. ✅ **Bytes for wire format** - Precise, no encoding assumptions
4. ✅ **Strings for convenience** - Decoded path, method, etc.
5. ✅ **List of tuples for headers** - Preserve duplicates and order
6. ✅ **State dict** - Share data across connections

### Why Each Field Exists

1. **`path` (string) + `raw_path` (bytes)** - Convenience + precision
2. **`query_string` (bytes)** - App decides how to parse
3. **`headers` (list)** - HTTP allows duplicates
4. **`client` and `server`** - Know who's talking
5. **`state`** - Share resources initialized in lifespan
6. **`extensions`** - Optional features, graceful degradation

### Common Patterns

```python
# Extract path parameters
path = scope['path']  # '/users/123'
user_id = path.split('/')[-1]  # '123'

# Parse query string
from urllib.parse import parse_qs
params = parse_qs(scope['query_string'].decode())

# Get header
headers_dict = dict(scope['headers'])
auth = headers_dict.get(b'authorization', b'').decode()

# Check request method
if scope['method'] == 'POST':
    # Handle POST
    pass
```

## Next Steps

Now that you deeply understand scopes:

➡️ **[Module 3: HTTP Protocol](03-http-protocol.md)** - Use scopes to handle HTTP requests/responses

## Additional Resources

- **[ASGI Scope Specification](https://asgi.readthedocs.io/en/latest/specs/main.html#connection-scope)** - Official spec
- **[Uvicorn Type Definitions](../../uvicorn/_types.py)** - See TypedDict definitions
- **[HTTP RFC 7230](https://tools.ietf.org/html/rfc7230)** - Understand HTTP protocol

You now understand not just WHAT scopes are, but WHY they're designed this way! 🎯
