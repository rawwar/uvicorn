"""
Complete ASGI Simulation - Understanding How ASGI Works

This file demonstrates how ASGI works without any web server.
It simulates what uvicorn does behind the scenes.

Run this file to understand the ASGI contract:
    python asgi_simulation.py
"""

import asyncio


# =============================================================================
# PART 1: Server-Side Functions (What Uvicorn Provides)
# =============================================================================

async def make_receive(body: bytes):
    """
    Creates a receive callable that simulates receiving an HTTP request body.
    
    In a real ASGI server like uvicorn, this would read from the network socket.
    Here, we simulate it by returning pre-defined messages.
    
    Args:
        body: The request body bytes to simulate receiving
        
    Returns:
        An async callable that returns ASGI messages
    """
    body_sent = False
    
    async def receive():
        nonlocal body_sent
        if not body_sent:
            body_sent = True
            # First call returns the request body
            return {
                'type': 'http.request',
                'body': body,
                'more_body': False,  # No more chunks coming
            }
        else:
            # Subsequent calls return disconnect
            return {
                'type': 'http.disconnect',
            }
    
    return receive


async def make_send():
    """
    Creates a send callable that collects messages from the ASGI app.
    
    In a real ASGI server like uvicorn, this would write to the network socket.
    Here, we just print and collect messages for inspection.
    
    Returns:
        An async callable that accepts ASGI messages
    """
    messages = []
    
    async def send(message):
        messages.append(message)
        msg_type = message['type']
        print(f"[SERVER] Received message from app: {msg_type}")
        
        # In a real server, we'd write to the socket here
        if msg_type == 'http.response.start':
            status = message['status']
            headers = message.get('headers', [])
            print(f"  → Status: HTTP {status}")
            for name, value in headers:
                print(f"  → Header: {name.decode()}: {value.decode()}")
                
        elif msg_type == 'http.response.body':
            body = message.get('body', b'')
            more_body = message.get('more_body', False)
            print(f"  → Body: {body.decode()}")
            print(f"  → More chunks: {more_body}")
    
    # Attach messages list to the function for inspection
    send.messages = messages
    return send


async def run_asgi_app(app, scope, body=b''):
    """
    Simulates an ASGI server calling your app.
    
    This is essentially what uvicorn does when a request comes in!
    
    Args:
        app: The ASGI application callable
        scope: The scope dictionary describing the request
        body: The request body bytes
        
    Returns:
        List of messages sent by the app
    """
    print("[SERVER] Starting request handling")
    print(f"[SERVER] Scope: {scope['method']} {scope['path']}")
    
    # Create the receive and send callables
    receive = await make_receive(body)
    send = await make_send()
    
    # Call the ASGI app (this is the key line!)
    print("[SERVER] Calling ASGI app...")
    await app(scope, receive, send)
    
    print(f"[SERVER] Request complete. App sent {len(send.messages)} messages\n")
    return send.messages


# =============================================================================
# PART 2: ASGI Applications (What You Write)
# =============================================================================

async def simple_app(scope, receive, send):
    """
    A minimal ASGI application - the simplest possible example.
    """
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
            'body': b'Hello, ASGI World!',
        })


async def echo_app(scope, receive, send):
    """
    An ASGI app that echoes back the request body.
    Demonstrates reading from receive().
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


async def streaming_app(scope, receive, send):
    """
    An ASGI app that streams the response in chunks.
    Demonstrates the power of separating headers from body.
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
            await asyncio.sleep(0.1)  # Simulate slow data generation
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


async def router_app(scope, receive, send):
    """
    An ASGI app with simple routing.
    Demonstrates reading from scope.
    """
    if scope['type'] == 'http':
        path = scope['path']
        method = scope['method']
        
        # Simple routing
        if path == '/' and method == 'GET':
            status = 200
            body = b'Home Page'
        elif path == '/about' and method == 'GET':
            status = 200
            body = b'About Page'
        elif path == '/api/data' and method == 'GET':
            status = 200
            body = b'{"data": "some json"}'
        else:
            status = 404
            body = b'404 Not Found'
        
        await send({
            'type': 'http.response.start',
            'status': status,
            'headers': [[b'content-type', b'text/plain']],
        })
        await send({
            'type': 'http.response.body',
            'body': body,
        })


# =============================================================================
# PART 3: Demo / Test Runner
# =============================================================================

async def main():
    """
    Run various ASGI app examples to demonstrate how they work.
    """
    print("=" * 70)
    print("ASGI Simulation - Understanding How ASGI Works")
    print("=" * 70)
    print()
    
    # Example 1: Simple app
    print("Example 1: Simple Hello World App")
    print("-" * 70)
    scope = {
        'type': 'http',
        'method': 'GET',
        'path': '/hello',
        'query_string': b'',
        'headers': [],
    }
    await run_asgi_app(simple_app, scope)
    
    # Example 2: Echo app
    print("Example 2: Echo App (reads request body)")
    print("-" * 70)
    scope = {
        'type': 'http',
        'method': 'POST',
        'path': '/echo',
        'query_string': b'',
        'headers': [],
    }
    await run_asgi_app(echo_app, scope, body=b'Hello, Server!')
    
    # Example 3: Streaming app
    print("Example 3: Streaming Response")
    print("-" * 70)
    scope = {
        'type': 'http',
        'method': 'GET',
        'path': '/stream',
        'query_string': b'',
        'headers': [],
    }
    await run_asgi_app(streaming_app, scope)
    
    # Example 4: Router app
    print("Example 4: Router App (different paths)")
    print("-" * 70)
    for path in ['/', '/about', '/api/data', '/unknown']:
        print(f"\nRequest to: {path}")
        scope = {
            'type': 'http',
            'method': 'GET',
            'path': path,
            'query_string': b'',
            'headers': [],
        }
        await run_asgi_app(router_app, scope)
    
    print("=" * 70)
    print("Summary:")
    print("  - The server creates scope, receive, and send")
    print("  - The server calls: await app(scope, receive, send)")
    print("  - The app sends messages back through send()")
    print("  - This is the ASGI contract!")
    print("=" * 70)


if __name__ == '__main__':
    asyncio.run(main())

