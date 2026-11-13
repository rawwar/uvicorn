"""
Exercise 8: Complete Application
=================================

A complete ASGI application combining HTTP, WebSocket, and Lifespan.

Features:
- HTTP API for managing items
- WebSocket for real-time updates
- Lifespan for resource management
- Middleware for logging

Run with:
    uvicorn exercises.08_complete_app:app --reload

Test HTTP API:
    curl http://localhost:8000/items
    curl -X POST -H "Content-Type: application/json" -d '{"name":"Test"}' http://localhost:8000/items

Test WebSocket:
    const ws = new WebSocket('ws://localhost:8000/ws');
    ws.onmessage = (e) => console.log(e.data);
"""

import json
import time
from typing import Dict, List


class ItemStore:
    """Simple in-memory item storage."""
    
    def __init__(self):
        self.items: Dict[int, dict] = {}
        self.next_id = 1
        self.subscribers = []
    
    def add_item(self, name: str) -> dict:
        item = {'id': self.next_id, 'name': name}
        self.items[self.next_id] = item
        self.next_id += 1
        return item
    
    def get_items(self) -> List[dict]:
        return list(self.items.values())


class Application:
    """Complete ASGI application."""
    
    def __init__(self):
        self.store = None
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'lifespan':
            await self.handle_lifespan(scope, receive, send)
        elif scope['type'] == 'http':
            await self.handle_http(scope, receive, send)
        elif scope['type'] == 'websocket':
            await self.handle_websocket(scope, receive, send)
    
    async def handle_lifespan(self, scope, receive, send):
        while True:
            message = await receive()
            
            if message['type'] == 'lifespan.startup':
                print("🚀 Starting up...")
                self.store = ItemStore()
                scope['state']['store'] = self.store
                await send({'type': 'lifespan.startup.complete'})
            
            elif message['type'] == 'lifespan.shutdown':
                print("🛑 Shutting down...")
                await send({'type': 'lifespan.shutdown.complete'})
                return
    
    async def handle_http(self, scope, receive, send):
        path = scope['path']
        method = scope['method']
        store = scope['state'].get('store')
        
        if path == '/items' and method == 'GET':
            # List items
            items = store.get_items()
            body = json.dumps({'items': items}).encode()
            
            await send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [[b'content-type', b'application/json']],
            })
            await send({
                'type': 'http.response.body',
                'body': body,
            })
        
        elif path == '/items' and method == 'POST':
            # Add item
            body = b''
            more_body = True
            while more_body:
                msg = await receive()
                body += msg.get('body', b'')
                more_body = msg.get('more_body', False)
            
            data = json.loads(body.decode())
            item = store.add_item(data['name'])
            
            response = json.dumps(item).encode()
            await send({
                'type': 'http.response.start',
                'status': 201,
                'headers': [[b'content-type', b'application/json']],
            })
            await send({
                'type': 'http.response.body',
                'body': response,
            })
        
        else:
            await send({
                'type': 'http.response.start',
                'status': 404,
                'headers': [[b'content-type', b'text/plain']],
            })
            await send({
                'type': 'http.response.body',
                'body': b'Not Found',
            })
    
    async def handle_websocket(self, scope, receive, send):
        store = scope['state'].get('store')
        
        await send({'type': 'websocket.accept'})
        
        # Send current items
        items = store.get_items()
        await send({
            'type': 'websocket.send',
            'text': json.dumps({'items': items})
        })
        
        while True:
            message = await receive()
            if message['type'] == 'websocket.disconnect':
                break


class LoggingMiddleware:
    """Log requests."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            print(f"→ {scope['method']} {scope['path']}")
        await self.app(scope, receive, send)


# Create and wrap application
app = Application()
app = LoggingMiddleware(app)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)

