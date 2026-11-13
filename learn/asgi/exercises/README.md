# ASGI Exercises

This directory contains hands-on exercises for learning ASGI.

## Setup

Make sure you have Python 3.14 and uv installed:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv --python 3.14
source .venv/bin/activate  # On Unix/macOS

# Install uvicorn
uv pip install uvicorn
```

## Running Exercises

Each exercise can be run with uvicorn:

```bash
# From the learn/asgi directory
uvicorn exercises.01_hello_world:app --reload

# Or from the project root
uvicorn learn.asgi.exercises.01_hello_world:app --reload
```

## Exercise List

### 01_hello_world.py
Basic HTTP "Hello, World!" application.

**Concepts:** Basic ASGI interface, HTTP response

```bash
uvicorn exercises.01_hello_world:app --reload
curl http://localhost:8000
```

### 02_scope_inspector.py
Display scope information as JSON.

**Concepts:** Scope dictionary, JSON responses

```bash
uvicorn exercises.02_scope_inspector:app --reload
curl http://localhost:8000
```

### 03_echo_server.py
Echo back the request body.

**Concepts:** Reading request body, receive callable

```bash
uvicorn exercises.03_echo_server:app --reload
echo "Hello" | curl -X POST -d @- http://localhost:8000
```

### 03_streaming_response.py
Stream a countdown timer.

**Concepts:** Streaming responses, async delays

```bash
uvicorn exercises.03_streaming_response:app --reload
curl http://localhost:8000
```

### 04_lifespan_example.py
Request counter with lifespan management.

**Concepts:** Lifespan protocol, state management

```bash
uvicorn exercises.04_lifespan_example:app --reload
curl http://localhost:8000
```

### 05_websocket_echo.py
WebSocket echo server.

**Concepts:** WebSocket protocol, bidirectional communication

```bash
uvicorn exercises.05_websocket_echo:app --reload
# Test in browser console:
# const ws = new WebSocket('ws://localhost:8000');
# ws.onmessage = (e) => console.log(e.data);
# ws.send('Hello!');
```

### 06_logging_middleware.py
Request/response logging middleware.

**Concepts:** Middleware pattern, wrapping send

```bash
uvicorn exercises.06_logging_middleware:app --reload
curl http://localhost:8000
```

### 08_complete_app.py
Complete application with HTTP, WebSocket, and Lifespan.

**Concepts:** All ASGI concepts combined

```bash
uvicorn exercises.08_complete_app:app --reload
curl http://localhost:8000/items
curl -X POST -H "Content-Type: application/json" -d '{"name":"Test"}' http://localhost:8000/items
```

## Tips

1. **Use --reload** during development for auto-restart on file changes
2. **Check logs** in the terminal for debugging
3. **Test with curl** for HTTP endpoints
4. **Use browser console** for WebSocket testing
5. **Read the code comments** for implementation details

## Next Steps

After completing exercises, check out the `examples/` directory for more complete applications.

