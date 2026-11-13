"""
Exercise 4: Lifespan Example
=============================

Create an application with lifespan management that tracks request count.

Run with:
    uvicorn exercises.04_lifespan_example:app --reload

Test with:
    curl http://localhost:8000
    (Make multiple requests to see the counter increment)
"""


async def app(scope, receive, send):
    """
    Application with lifespan support and request counting.
    """
    
    if scope['type'] == 'lifespan':
        # Handle lifespan events
        while True:
            message = await receive()
            
            if message['type'] == 'lifespan.startup':
                print("🚀 Application starting up...")
                # Initialize request counter
                scope['state']['request_count'] = 0
                await send({'type': 'lifespan.startup.complete'})
            
            elif message['type'] == 'lifespan.shutdown':
                print("🛑 Application shutting down...")
                total = scope['state'].get('request_count', 0)
                print(f"   Total requests served: {total}")
                await send({'type': 'lifespan.shutdown.complete'})
                return
    
    elif scope['type'] == 'http':
        # Increment request counter
        state = scope.get('state', {})
        count = state.get('request_count', 0)
        count += 1
        state['request_count'] = count
        
        # Send response with count
        body = f'Request #{count}\n'.encode()
        
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'text/plain'],
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': body,
        })
    
    else:
        raise NotImplementedError(f"Unsupported scope type: {scope['type']}")


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)

