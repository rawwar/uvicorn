# Quick Start: Understanding ASGI

**Goal:** Learn how ASGI works from first principles so you can build your own ASGI server.

## The Right Way to Learn ASGI

❌ **Don't start here:**
```bash
uvicorn app:main  # You won't understand what's happening!
```

✅ **Start here:**
```bash
python3 examples/asgi_simulation.py  # Pure Python - see the mechanics!
```

## 3-Step Learning Path

### Step 1: Understand the Mechanics (15 minutes)

**Run the simulation:**
```bash
cd /Users/kalyanreddy.kasireddy/g/uvicorn/learn/asgi/examples
python3 asgi_simulation.py
```

**What you'll see:**
- How a server creates `scope`, `receive`, and `send`
- How your app uses these to communicate
- The exact messages exchanged
- No network complexity - just the contract

**Read:** `01-fundamentals.md` alongside the simulation

### Step 2: Build It Yourself (30 minutes)

**Do the exercises in order:**

1. `exercises/01_hello_world.py` - Complete the ASGI contract
2. `exercises/02_path_router.py` - Read from scope
3. `exercises/03_echo_server.py` - Use receive()
4. `exercises/04_streaming.py` - Multiple send() calls
5. `exercises/05_complete_app.py` - Put it all together

**Each exercise:**
- Has starter code with TODOs
- Runs with pure Python (no uvicorn)
- Teaches one specific concept

### Step 3: Use a Real Server (10 minutes)

**Now use uvicorn:**
```bash
# Create a simple app
cat > hello.py << 'EOF'
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
EOF

# Run with uvicorn
uvicorn hello:app

# Test
curl http://localhost:8000
```

**You'll understand:**
- Uvicorn does the SAME thing as your simulation
- It just adds real TCP socket I/O
- The ASGI contract is identical

## What You'll Understand

After this path, you'll know:

1. **The ASGI Contract**
   - `async def app(scope, receive, send)`
   - Three parameters: scope dict, receive callable, send callable
   - Message-based communication

2. **How Servers Work**
   - Parse HTTP → create scope
   - Implement receive/send that talk to sockets
   - Call: `await app(scope, receive, send)`

3. **How to Build Your Own Server**
   - Accept TCP connections
   - Parse HTTP into scope
   - Create receive/send callables
   - Call the ASGI app
   - Done!

## Building Your Own ASGI Server

Now that you understand the contract, here's what you need:

```python
import asyncio

async def simple_asgi_server(app, host='127.0.0.1', port=8000):
    """
    A minimal ASGI server - what uvicorn does!
    """
    async def handle_client(reader, writer):
        # 1. Read HTTP request from socket
        data = await reader.read(1024)
        
        # 2. Parse HTTP → create scope
        # (Use a library like h11 or httptools for this)
        scope = parse_http_request(data)
        
        # 3. Create receive/send callables
        async def receive():
            # Read more data from socket
            pass
        
        async def send(message):
            # Write HTTP response to socket
            pass
        
        # 4. Call the ASGI app
        await app(scope, receive, send)
        
        writer.close()
    
    # Start TCP server
    server = await asyncio.start_server(handle_client, host, port)
    await server.serve_forever()
```

The ASGI contract you learned is the boundary. Everything else is implementation!

## Key Insight

**ASGI isn't magic - it's a simple contract:**

```python
Server provides: scope, receive, send
App uses them to: handle requests
That's it!
```

Uvicorn, Hypercorn, Daphne - they all implement the same contract. You can too!

## Resources

- **Documentation:** `01-fundamentals.md` - Why ASGI exists and how it works
- **Simulation:** `examples/asgi_simulation.py` - See it in action
- **Exercises:** `exercises/` - Build it yourself
- **Examples:** `examples/` - Production patterns

## Common Questions

**Q: Why start with simulation instead of uvicorn?**
A: You need to understand the contract before using a framework. The simulation shows you exactly what uvicorn does behind the scenes.

**Q: Can I skip the exercises?**
A: You could, but you won't really *understand* ASGI. Building it yourself is key.

**Q: When should I use uvicorn?**
A: After you understand the mechanics. Then uvicorn's role is clear - it handles the network complexity.

**Q: Can I really build my own ASGI server?**
A: Yes! After this learning path, you'll understand:
- The ASGI contract (scope, receive, send)
- How to parse HTTP
- How to implement receive/send
- That's 90% of what you need!

## Next Steps

1. ✅ Run the simulation
2. ✅ Read `01-fundamentals.md`
3. ✅ Complete the exercises
4. ✅ Study `examples/asgi_simulation.py` code
5. ⏭️ Move to Module 02: Scopes
6. ⏭️ Study uvicorn source code
7. ⏭️ Build your own ASGI server!

Happy learning! 🚀

