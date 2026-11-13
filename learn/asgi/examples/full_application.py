"""
Full-Featured ASGI Application
================================

A complete production-ready ASGI application combining all concepts.

Features:
- HTTP REST API (CRUD operations)
- WebSocket real-time updates
- Lifespan management
- Middleware stack (logging, CORS, error handling)
- Authentication
- Database simulation
- Comprehensive error handling

Run with:
    uvicorn examples.full_application:app --reload

HTTP API Endpoints:
    GET    /health              - Health check
    GET    /api/tasks           - List all tasks
    POST   /api/tasks           - Create task
    GET    /api/tasks/{id}      - Get task
    PUT    /api/tasks/{id}      - Update task
    DELETE /api/tasks/{id}      - Delete task

WebSocket:
    ws://localhost:8000/ws      - Real-time task updates

Authentication:
    Use header: Authorization: Bearer secret-token
"""

import json
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional


# --- Database Simulation ---

class Database:
    """Simulated database with async operations."""
    
    def __init__(self):
        self.tasks: Dict[int, dict] = {}
        self.next_id = 1
        self._lock = asyncio.Lock()
    
    async def create_task(self, title: str, description: str = '') -> dict:
        """Create a new task."""
        async with self._lock:
            task = {
                'id': self.next_id,
                'title': title,
                'description': description,
                'completed': False,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            self.tasks[self.next_id] = task
            self.next_id += 1
            return task.copy()
    
    async def get_task(self, task_id: int) -> Optional[dict]:
        """Get a task by ID."""
        return self.tasks.get(task_id, {}).copy() if task_id in self.tasks else None
    
    async def list_tasks(self) -> List[dict]:
        """List all tasks."""
        return [task.copy() for task in self.tasks.values()]
    
    async def update_task(self, task_id: int, **updates) -> Optional[dict]:
        """Update a task."""
        async with self._lock:
            if task_id in self.tasks:
                self.tasks[task_id].update(updates)
                self.tasks[task_id]['updated_at'] = datetime.now().isoformat()
                return self.tasks[task_id].copy()
            return None
    
    async def delete_task(self, task_id: int) -> bool:
        """Delete a task."""
        async with self._lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                return True
            return False


# --- Middleware ---

class LoggingMiddleware:
    """Log all HTTP requests."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            start_time = time.time()
            method = scope['method']
            path = scope['path']
            
            print(f"→ {method} {path}")
            
            status_code = None
            
            async def send_wrapper(message):
                nonlocal status_code
                if message['type'] == 'http.response.start':
                    status_code = message['status']
                await send(message)
            
            try:
                await self.app(scope, receive, send_wrapper)
            finally:
                duration = time.time() - start_time
                print(f"← {method} {path} - {status_code} ({duration:.3f}s)")
        else:
            await self.app(scope, receive, send)


class CORSMiddleware:
    """Add CORS headers."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            async def send_wrapper(message):
                if message['type'] == 'http.response.start':
                    headers = list(message.get('headers', []))
                    headers.extend([
                        [b'access-control-allow-origin', b'*'],
                        [b'access-control-allow-methods', b'GET, POST, PUT, DELETE, OPTIONS'],
                        [b'access-control-allow-headers', b'*'],
                    ])
                    message['headers'] = headers
                await send(message)
            
            if scope['method'] == 'OPTIONS':
                await send_wrapper({
                    'type': 'http.response.start',
                    'status': 200,
                    'headers': [],
                })
                await send_wrapper({
                    'type': 'http.response.body',
                    'body': b'',
                })
            else:
                await self.app(scope, receive, send_wrapper)
        else:
            await self.app(scope, receive, send)


class ErrorHandlerMiddleware:
    """Catch and handle exceptions."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            try:
                await self.app(scope, receive, send)
            except Exception as exc:
                print(f"❌ Error: {exc}")
                
                error_body = json.dumps({
                    'error': 'Internal Server Error',
                    'detail': str(exc)
                }).encode()
                
                try:
                    await send({
                        'type': 'http.response.start',
                        'status': 500,
                        'headers': [[b'content-type', b'application/json']],
                    })
                    await send({
                        'type': 'http.response.body',
                        'body': error_body,
                    })
                except:
                    pass  # Response already started
        else:
            await self.app(scope, receive, send)


# --- Main Application ---

class Application:
    """Main ASGI application."""
    
    def __init__(self):
        self.db = None
        self.ws_connections = []
        self.auth_token = 'secret-token'
    
    async def __call__(self, scope, receive, send):
        """ASGI entry point."""
        
        if scope['type'] == 'lifespan':
            await self.handle_lifespan(scope, receive, send)
        
        elif scope['type'] == 'http':
            await self.handle_http(scope, receive, send)
        
        elif scope['type'] == 'websocket':
            await self.handle_websocket(scope, receive, send)
        
        else:
            raise NotImplementedError(f"Unsupported scope type: {scope['type']}")
    
    # --- Lifespan ---
    
    async def handle_lifespan(self, scope, receive, send):
        """Handle application lifecycle."""
        while True:
            message = await receive()
            
            if message['type'] == 'lifespan.startup':
                print("🚀 Application starting up...")
                self.db = Database()
                scope['state']['db'] = self.db
                scope['state']['app'] = self
                print("✅ Database initialized")
                await send({'type': 'lifespan.startup.complete'})
            
            elif message['type'] == 'lifespan.shutdown':
                print("🛑 Application shutting down...")
                print(f"   Total tasks: {len(self.db.tasks)}")
                await send({'type': 'lifespan.shutdown.complete'})
                return
    
    # --- HTTP ---
    
    async def handle_http(self, scope, receive, send):
        """Handle HTTP requests."""
        method = scope['method']
        path = scope['path']
        db = scope['state'].get('db')
        
        # Authentication check (except for health endpoint)
        if path != '/health':
            if not await self.check_auth(scope):
                await self.send_json(send, {'error': 'Unauthorized'}, status=401)
                return
        
        # Route requests
        if path == '/health':
            await self.send_json(send, {
                'status': 'healthy',
                'tasks_count': len(db.tasks),
                'ws_connections': len(self.ws_connections)
            })
        
        elif path == '/api/tasks':
            if method == 'GET':
                tasks = await db.list_tasks()
                await self.send_json(send, {'tasks': tasks})
            
            elif method == 'POST':
                body = await self.read_body(receive)
                data = json.loads(body.decode())
                
                task = await db.create_task(
                    title=data.get('title', ''),
                    description=data.get('description', '')
                )
                
                # Notify WebSocket clients
                await self.notify_ws({'type': 'task_created', 'task': task})
                
                await self.send_json(send, task, status=201)
            
            else:
                await self.send_json(send, {'error': 'Method not allowed'}, status=405)
        
        elif path.startswith('/api/tasks/'):
            try:
                task_id = int(path.split('/')[-1])
            except ValueError:
                await self.send_json(send, {'error': 'Invalid task ID'}, status=400)
                return
            
            if method == 'GET':
                task = await db.get_task(task_id)
                if task:
                    await self.send_json(send, task)
                else:
                    await self.send_json(send, {'error': 'Task not found'}, status=404)
            
            elif method == 'PUT':
                body = await self.read_body(receive)
                updates = json.loads(body.decode())
                
                task = await db.update_task(task_id, **updates)
                if task:
                    await self.notify_ws({'type': 'task_updated', 'task': task})
                    await self.send_json(send, task)
                else:
                    await self.send_json(send, {'error': 'Task not found'}, status=404)
            
            elif method == 'DELETE':
                success = await db.delete_task(task_id)
                if success:
                    await self.notify_ws({'type': 'task_deleted', 'task_id': task_id})
                    await self.send_json(send, {'message': 'Task deleted'})
                else:
                    await self.send_json(send, {'error': 'Task not found'}, status=404)
            
            else:
                await self.send_json(send, {'error': 'Method not allowed'}, status=405)
        
        else:
            await self.send_json(send, {'error': 'Not found'}, status=404)
    
    # --- WebSocket ---
    
    async def handle_websocket(self, scope, receive, send):
        """Handle WebSocket connections."""
        db = scope['state'].get('db')
        
        # Accept connection
        await send({'type': 'websocket.accept'})
        
        # Add to connections
        self.ws_connections.append(send)
        
        try:
            # Send current tasks
            tasks = await db.list_tasks()
            await send({
                'type': 'websocket.send',
                'text': json.dumps({
                    'type': 'initial_state',
                    'tasks': tasks
                })
            })
            
            # Keep connection alive
            while True:
                message = await receive()
                if message['type'] == 'websocket.disconnect':
                    break
        
        finally:
            # Remove from connections
            if send in self.ws_connections:
                self.ws_connections.remove(send)
    
    # --- Helper Methods ---
    
    async def check_auth(self, scope) -> bool:
        """Check authentication."""
        headers = dict(scope['headers'])
        auth = headers.get(b'authorization', b'').decode()
        return auth == f'Bearer {self.auth_token}'
    
    async def read_body(self, receive) -> bytes:
        """Read full request body."""
        body = b''
        more_body = True
        while more_body:
            message = await receive()
            body += message.get('body', b'')
            more_body = message.get('more_body', False)
        return body
    
    async def send_json(self, send, data, status=200):
        """Send JSON response."""
        body = json.dumps(data).encode()
        await send({
            'type': 'http.response.start',
            'status': status,
            'headers': [
                [b'content-type', b'application/json'],
                [b'content-length', str(len(body)).encode()],
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': body,
        })
    
    async def notify_ws(self, message: dict):
        """Notify all WebSocket clients."""
        message_text = json.dumps(message)
        for send_func in self.ws_connections[:]:
            try:
                await send_func({
                    'type': 'websocket.send',
                    'text': message_text
                })
            except Exception:
                if send_func in self.ws_connections:
                    self.ws_connections.remove(send_func)


# --- Application Setup ---

# Create application
base_app = Application()

# Apply middleware (in reverse order of execution)
app = base_app
app = ErrorHandlerMiddleware(app)
app = CORSMiddleware(app)
app = LoggingMiddleware(app)


if __name__ == '__main__':
    import uvicorn
    
    print("""
╔══════════════════════════════════════════════════════════╗
║  Full-Featured ASGI Application                          ║
║                                                          ║
║  HTTP API:  http://localhost:8000                       ║
║  WebSocket: ws://localhost:8000/ws                       ║
║                                                          ║
║  Auth Token: Bearer secret-token                         ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(app, host='127.0.0.1', port=8000)

