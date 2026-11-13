"""
Simple HTTP Application
=======================

A complete HTTP application with routing, JSON API, and error handling.

Features:
- Multiple routes
- JSON API
- Query parameter parsing
- Error handling
- 404 responses

Run with:
    uvicorn examples.simple_http_app:app --reload

Test:
    curl http://localhost:8000/
    curl http://localhost:8000/api/users
    curl "http://localhost:8000/greet?name=Alice"
"""

import json
from urllib.parse import parse_qs


class HTTPApplication:
    """Simple HTTP application with routing."""
    
    def __init__(self):
        self.routes = {}
        self._register_routes()
    
    def route(self, path, method='GET'):
        """Decorator to register routes."""
        def decorator(handler):
            key = (method, path)
            self.routes[key] = handler
            return handler
        return decorator
    
    def _register_routes(self):
        """Register all routes."""
        
        @self.route('/', 'GET')
        async def home(scope, receive, send):
            body = b'''
Welcome to the Simple HTTP App!

Available endpoints:
- GET  /              - This page
- GET  /health        - Health check
- GET  /api/users     - List users
- GET  /greet?name=X  - Personalized greeting
            '''
            await self.send_response(send, 200, body, b'text/plain')
        
        @self.route('/health', 'GET')
        async def health(scope, receive, send):
            data = {'status': 'healthy', 'version': '1.0.0'}
            await self.send_json(send, data)
        
        @self.route('/api/users', 'GET')
        async def users(scope, receive, send):
            # Mock user data
            users = [
                {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'},
                {'id': 2, 'name': 'Bob', 'email': 'bob@example.com'},
                {'id': 3, 'name': 'Charlie', 'email': 'charlie@example.com'},
            ]
            await self.send_json(send, {'users': users})
        
        @self.route('/greet', 'GET')
        async def greet(scope, receive, send):
            # Parse query parameters
            query_string = scope['query_string'].decode('utf-8')
            params = parse_qs(query_string)
            name = params.get('name', ['Guest'])[0]
            
            greeting = f'Hello, {name}! Welcome to our API.'
            await self.send_json(send, {'greeting': greeting})
    
    async def __call__(self, scope, receive, send):
        """ASGI application entry point."""
        if scope['type'] == 'http':
            method = scope['method']
            path = scope['path']
            
            # Find matching route
            handler = self.routes.get((method, path))
            
            if handler:
                try:
                    await handler(scope, receive, send)
                except Exception as exc:
                    # Internal server error
                    error = {'error': 'Internal server error', 'detail': str(exc)}
                    await self.send_json(send, error, status=500)
            else:
                # 404 Not Found
                error = {'error': 'Not found', 'path': path}
                await self.send_json(send, error, status=404)
        else:
            raise NotImplementedError(f"Unsupported scope type: {scope['type']}")
    
    async def send_response(self, send, status, body, content_type=b'text/plain'):
        """Send HTTP response."""
        await send({
            'type': 'http.response.start',
            'status': status,
            'headers': [
                [b'content-type', content_type],
                [b'content-length', str(len(body)).encode()],
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': body,
        })
    
    async def send_json(self, send, data, status=200):
        """Send JSON response."""
        body = json.dumps(data, indent=2).encode('utf-8')
        await self.send_response(send, status, body, b'application/json')


# Create application instance
app = HTTPApplication()


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)

