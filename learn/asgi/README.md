# ASGI Learning Path

Welcome to the comprehensive ASGI learning materials! This guide will teach you **how ASGI works from first principles**, so you can build your own ASGI server like uvicorn.

## 🚀 Quick Start

**Don't start by using uvicorn!** Start by understanding the mechanics:

```bash
cd examples
python3 asgi_simulation.py
```

See the complete ASGI contract in action with pure Python. Then read the modules.

📖 **Full quick start guide:** [QUICK_START.md](QUICK_START.md)

## What is ASGI?

ASGI (Asynchronous Server Gateway Interface) is a specification that defines how web servers communicate with Python web applications. It's not magic - it's a simple contract:

```python
async def app(scope, receive, send):
    # scope: dict with request info
    # receive: async callable to get messages from client  
    # send: async callable to send messages to client
    pass
```

**That's it!** Everything else is implementation.

ASGI supports:
- **HTTP/1.1, HTTP/2, and HTTP/3** protocols
- **WebSockets** for real-time bidirectional communication
- **Long-lived connections** and background tasks
- **Application lifecycle** management (startup/shutdown)
- **Async/await** concurrency model

## Learning Philosophy

This guide is different from typical documentation:

❌ **Not this:** "Here are ASGI features, now use uvicorn"  
✅ **But this:** "Here's why ASGI exists, let's build it together, now you understand what uvicorn does"

You'll learn by:
1. **Understanding WHY** - What problems does ASGI solve?
2. **Building mechanics** - Implement ASGI concepts in pure Python
3. **Hands-on practice** - Complete exercises that build skills
4. **Real applications** - Use uvicorn after understanding the contract

## Prerequisites

### Essential (No Installation Required!)
- **Python 3.7+** - For the simulation and understanding
- Basic understanding of **async/await** in Python
- Familiarity with **HTTP** fundamentals

### For Real HTTP/WebSocket (Later)
- **Python 3.14** installed
- **uv** package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **uvicorn** installed: `uv pip install uvicorn`

### Setting Up Your Environment

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a virtual environment with Python 3.14
uv venv --python 3.14

# Activate the virtual environment
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows

# Install uvicorn
uv pip install uvicorn

# For WebSocket examples, also install:
uv pip install websockets
```

## Learning Path

This curriculum is organized into 8 progressive modules:

### 1. [Fundamentals](01-fundamentals.md) ⭐ **START HERE**

**New approach:** Learn by building, not just reading!

**What you'll do:**
- Understand WHY ASGI exists (with concrete examples of WSGI limitations)
- Build a complete ASGI server simulation in pure Python
- See exactly how `scope`, `receive`, and `send` work
- Complete hands-on exercises that run without uvicorn
- Learn when and why to use a real server

**Key deliverable:** Run `examples/asgi_simulation.py` and understand every line

**Time:** 1-2 hours (includes hands-on practice)

### 2. [ASGI Scopes](02-scopes.md)
Understand the scope dictionary and its structure for HTTP, WebSocket, and Lifespan protocols.

**Time:** 30 minutes

### 3. [HTTP Protocol](03-http-protocol.md)
Deep dive into HTTP request/response cycles, reading request bodies, sending responses, and streaming.

**Time:** 1-2 hours

### 4. [Lifespan Protocol](04-lifespan.md)
Master application lifecycle management with startup and shutdown events for resource initialization.

**Time:** 45 minutes

### 5. [WebSocket Protocol](05-websocket.md)
Learn WebSocket handshake, events, and build real-time communication applications.

**Time:** 1-2 hours

### 6. [ASGI Middleware](06-middleware.md)
Understand middleware patterns for wrapping applications and modifying scope, receive, and send.

**Time:** 1 hour

### 7. [Advanced Concepts](07-advanced.md)
Explore extensions, state management, server push, trailers, and flow control.

**Time:** 1 hour

### 8. [Building Complete Applications](08-practical-app.md)
Combine all concepts to build production-ready applications with routing, error handling, and testing.

**Time:** 2-3 hours

## Directory Structure

```
learn/asgi/
├── README.md                    # This file
├── QUICK_START.md              # Fast track to understanding ASGI ⭐
├── IMPROVEMENTS.md             # What changed and why
├── 01-fundamentals.md          # Module 1 (completely rewritten!)
├── 02-scopes.md                # Module 2
├── 03-http-protocol.md         # Module 3
├── 04-lifespan.md              # Module 4
├── 05-websocket.md             # Module 5
├── 06-middleware.md            # Module 6
├── 07-advanced.md              # Module 7
├── 08-practical-app.md         # Module 8
├── exercises/                   # Hands-on exercises
│   ├── 01_hello_world.py       # Build complete ASGI simulation
│   ├── 02_scope_inspector.py   # Read from scope
│   ├── 03_echo_server.py       # Use receive()
│   ├── 03_streaming_response.py # Stream with send()
│   ├── 04_lifespan_example.py
│   ├── 05_websocket_echo.py
│   ├── 06_logging_middleware.py
│   └── 08_complete_app.py
└── examples/                    # Complete reference applications
    ├── README.md               # Examples guide
    ├── asgi_simulation.py      # Pure Python ASGI demo ⭐ START HERE
    ├── simple_http_app.py      # First uvicorn app
    ├── websocket_chat.py       # Real-time chat
    └── full_application.py     # Production-ready app
```

## How to Use These Materials

### The Right Way to Learn ASGI

**Step 0: Run the Simulation** (15 minutes)
```bash
cd examples
python3 asgi_simulation.py
```
See ASGI in action before reading anything. This makes everything concrete.

### Step 1: Understand Fundamentals (1-2 hours)
Read `01-fundamentals.md` while referring to `asgi_simulation.py`. You'll learn:
- WHY ASGI exists (problems with WSGI)
- HOW the contract works (scope, receive, send)
- WHAT each component does (with implementations)

### Step 2: Build It Yourself (30-60 minutes)
Complete the exercises in `exercises/`:
1. `01_hello_world.py` - Basic ASGI app
2. `02_path_router.py` - Routing
3. `03_echo_server.py` - Reading requests
4. `04_streaming.py` - Streaming responses
5. `05_complete_app.py` - Full application

**Important:** These run with pure Python, no uvicorn!

### Step 3: Use a Real Server (10 minutes)
Now that you understand the mechanics, use uvicorn:
```bash
uvicorn examples.simple_http_app:app
```
You'll know exactly what uvicorn is doing.

### Step 4: Advanced Topics (Continue through modules)
Work through modules 2-8 with deep understanding of the foundation.

### Step 5: Explore Uvicorn Code
With understanding from steps 1-3, read uvicorn source code and it will make sense.

## Running ASGI Applications

To run any ASGI application with uvicorn:

```bash
# Basic usage
uvicorn module_name:app

# With auto-reload for development
uvicorn module_name:app --reload

# With custom host and port
uvicorn module_name:app --host 0.0.0.0 --port 8080

# With log level
uvicorn module_name:app --log-level debug
```

For exercises in this learning path:

```bash
# From the exercises directory
cd learn/asgi/exercises
uvicorn 01_hello_world:app --reload

# From the project root
uvicorn learn.asgi.exercises.01_hello_world:app --reload
```

## Testing Your Applications

You can test HTTP applications using:

```bash
# Using curl
curl http://localhost:8000

# Using httpie
http GET http://localhost:8000

# Using Python requests
python -c "import requests; print(requests.get('http://localhost:8000').text)"
```

For WebSocket applications, you can use:

```bash
# Using websocat (install with: cargo install websocat)
websocat ws://localhost:8000

# Or use JavaScript in browser console:
# const ws = new WebSocket('ws://localhost:8000');
# ws.onmessage = (event) => console.log(event.data);
# ws.send('Hello');
```

## Additional Resources

### Official Documentation
- [ASGI Specification](https://asgi.readthedocs.io/)
- [Uvicorn Documentation](https://www.uvicorn.org/)

### ASGI Frameworks
After completing this learning path, explore these frameworks built on ASGI:
- [Starlette](https://www.starlette.io/) - Lightweight ASGI framework
- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework
- [Quart](https://pgjones.gitlab.io/quart/) - Flask-like ASGI framework
- [Django Channels](https://channels.readthedocs.io/) - Django async support

### Uvicorn Source Code
- [uvicorn GitHub](https://github.com/encode/uvicorn)
- Key files referenced in this learning path:
  - `uvicorn/_types.py` - ASGI type definitions
  - `uvicorn/protocols/http/` - HTTP protocol implementations
  - `uvicorn/protocols/websockets/` - WebSocket implementations
  - `uvicorn/lifespan/` - Lifespan protocol
  - `uvicorn/middleware/` - Middleware examples

## Learning Goals

By the end of this learning path, you will:

✅ **Understand the ASGI contract deeply** - Not just use it, but truly understand it  
✅ **Explain WHY ASGI exists** - The problems it solves and design decisions  
✅ **Write ASGI applications from scratch** - Without any framework  
✅ **Implement a basic ASGI server** - You'll know how uvicorn works  
✅ **Handle HTTP, WebSocket, and Lifespan protocols** - All major ASGI types  
✅ **Create middleware** - Wrap and modify ASGI applications  
✅ **Read uvicorn source code** - With complete understanding  
✅ **Build production-ready applications** - With proper patterns  
✅ **Debug ASGI applications effectively** - Know what's happening under the hood

## What Makes This Different

Traditional documentation: "Here's how to use ASGI"  
**This guide:** "Here's how ASGI works - now you can build anything"

You'll transition from **user** to **builder**.  

## Getting Help

If you encounter issues or have questions:

1. Review the module content carefully
2. Check the uvicorn source code references
3. Read the [ASGI specification](https://asgi.readthedocs.io/)
4. Consult the [uvicorn documentation](https://www.uvicorn.org/)

## Package Management with uv

All examples in this learning path use `uv` for package management. Benefits of uv:

- **Blazing fast** - 10-100x faster than pip
- **Reliable** - Consistent dependency resolution
- **Compatible** - Drop-in replacement for pip
- **Modern** - Built for Python 3.14+

### Common uv Commands

```bash
# Install packages
uv pip install package_name

# Install from requirements.txt
uv pip install -r requirements.txt

# Create requirements.txt
uv pip freeze > requirements.txt

# Run a script with dependencies
uv run script.py
```

## Ready to Start?

### For the impatient: Quick path to understanding

```bash
# 1. See it in action (5 minutes)
cd examples
python3 asgi_simulation.py

# 2. Read the quick start (10 minutes)
# Open QUICK_START.md

# 3. Deep dive (1-2 hours)
# Read 01-fundamentals.md
# Do the exercises

# 4. Build your own server (optional, advanced)
# You'll have everything you need!
```

### For the thorough: Complete learning path

Begin your journey with [Module 1: ASGI Fundamentals](01-fundamentals.md)!

**Remember:** Don't just read - run the simulation, do the exercises, build it yourself. That's how you'll truly understand ASGI.

