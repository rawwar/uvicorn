"""
Exercise 6: Logging Middleware
===============================

Create middleware that logs all requests and responses.

Run with:
    uvicorn exercises.06_logging_middleware:app --reload

Test with:
    curl http://localhost:8000
"""

import time


class LoggingMiddleware:
    """
    Middleware that logs HTTP requests and response times.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            # Log request
            method = scope['method']
            path = scope['path']
            start_time = time.time()
            
            print(f"→ {method} {path}")
            
            # Track response status
            response_status = None
            
            async def send_wrapper(message):
                nonlocal response_status
                if message['type'] == 'http.response.start':
                    response_status = message['status']
                await send(message)
            
            try:
                # Call the wrapped app
                await self.app(scope, receive, send_wrapper)
            finally:
                # Log response
                duration = time.time() - start_time
                print(f"← {method} {path} - {response_status} ({duration:.3f}s)")
        else:
            await self.app(scope, receive, send)


# Simple application
async def my_app(scope, receive, send):
    if scope['type'] == 'http':
        import asyncio
        
        # Simulate some processing time
        await asyncio.sleep(0.1)
        
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'text/plain']],
        })
        await send({
            'type': 'http.response.body',
            'body': b'Hello from logged app!',
        })


# Wrap with logging middleware
app = LoggingMiddleware(my_app)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)

