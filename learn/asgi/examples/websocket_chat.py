"""
WebSocket Chat Application
===========================

A complete WebSocket chat application with rooms and authentication.

Features:
- Multiple chat rooms
- User authentication via query parameter
- Broadcast messages to room
- Join/leave notifications
- User list tracking

Run with:
    uvicorn examples.websocket_chat:app --reload

Test with JavaScript (browser console):
    // User 1
    const ws1 = new WebSocket('ws://localhost:8000/ws?room=general&user=Alice&token=secret123');
    ws1.onmessage = (e) => console.log('Alice:', e.data);
    ws1.send('Hello everyone!');

    // User 2
    const ws2 = new WebSocket('ws://localhost:8000/ws?room=general&user=Bob&token=secret123');
    ws2.onmessage = (e) => console.log('Bob:', e.data);
    ws2.send('Hi Alice!');
"""

import json
import asyncio
from urllib.parse import parse_qs
from collections import defaultdict
from datetime import datetime


class ChatRoom:
    """Represents a chat room."""
    
    def __init__(self, name):
        self.name = name
        self.users = {}  # user_name -> send callable
        self.message_history = []
    
    async def join(self, username, send):
        """User joins the room."""
        self.users[username] = send
        
        # Send join notification
        await self.broadcast({
            'type': 'user_joined',
            'user': username,
            'timestamp': datetime.now().isoformat(),
            'user_count': len(self.users)
        }, exclude=username)
        
        # Send user list to new user
        await send({
            'type': 'websocket.send',
            'text': json.dumps({
                'type': 'user_list',
                'users': list(self.users.keys()),
                'room': self.name
            })
        })
        
        # Send recent message history
        for msg in self.message_history[-10:]:  # Last 10 messages
            await send({
                'type': 'websocket.send',
                'text': json.dumps(msg)
            })
    
    async def leave(self, username):
        """User leaves the room."""
        if username in self.users:
            del self.users[username]
            
            # Send leave notification
            await self.broadcast({
                'type': 'user_left',
                'user': username,
                'timestamp': datetime.now().isoformat(),
                'user_count': len(self.users)
            })
    
    async def broadcast(self, message, exclude=None):
        """Broadcast message to all users in room."""
        message_text = json.dumps(message)
        
        for username, send in list(self.users.items()):
            if username == exclude:
                continue
            
            try:
                await send({
                    'type': 'websocket.send',
                    'text': message_text
                })
            except Exception:
                # Remove disconnected user
                await self.leave(username)
    
    async def send_message(self, username, text):
        """Send a chat message from a user."""
        message = {
            'type': 'message',
            'user': username,
            'text': text,
            'timestamp': datetime.now().isoformat()
        }
        
        # Store in history
        self.message_history.append(message)
        if len(self.message_history) > 100:
            self.message_history.pop(0)
        
        # Broadcast to all users
        await self.broadcast(message)


class ChatApplication:
    """WebSocket chat application."""
    
    def __init__(self):
        self.rooms = {}  # room_name -> ChatRoom
        self.valid_token = 'secret123'  # Simple auth token
    
    def get_room(self, name):
        """Get or create a room."""
        if name not in self.rooms:
            self.rooms[name] = ChatRoom(name)
        return self.rooms[name]
    
    async def __call__(self, scope, receive, send):
        """ASGI application entry point."""
        
        if scope['type'] == 'websocket':
            await self.handle_websocket(scope, receive, send)
        
        elif scope['type'] == 'http':
            await self.handle_http(scope, receive, send)
        
        else:
            raise NotImplementedError(f"Unsupported scope type: {scope['type']}")
    
    async def handle_http(self, scope, receive, send):
        """Serve instructions for HTTP requests."""
        if scope['path'] == '/':
            body = b'''
WebSocket Chat Server

Connect with:
    const ws = new WebSocket('ws://localhost:8000/ws?room=ROOM&user=NAME&token=secret123');
    ws.onmessage = (e) => console.log(e.data);
    ws.send('Hello!');

Parameters:
    - room: Chat room name (default: lobby)
    - user: Your username (required)
    - token: Authentication token (required: secret123)
            '''
        elif scope['path'] == '/rooms':
            # List active rooms
            rooms_info = {
                name: {
                    'users': list(room.users.keys()),
                    'user_count': len(room.users)
                }
                for name, room in self.rooms.items()
            }
            body = json.dumps(rooms_info, indent=2).encode()
        else:
            body = b'Not Found'
        
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'text/plain']],
        })
        await send({
            'type': 'http.response.body',
            'body': body,
        })
    
    async def handle_websocket(self, scope, receive, send):
        """Handle WebSocket chat connections."""
        # Parse query parameters
        query_string = scope['query_string'].decode('utf-8')
        params = parse_qs(query_string)
        
        room_name = params.get('room', ['lobby'])[0]
        username = params.get('user', [None])[0]
        token = params.get('token', [None])[0]
        
        # Validate authentication
        if not username:
            await send({
                'type': 'websocket.close',
                'code': 1008,
                'reason': 'Username required'
            })
            return
        
        if token != self.valid_token:
            await send({
                'type': 'websocket.close',
                'code': 1008,
                'reason': 'Invalid token'
            })
            return
        
        # Accept connection
        await send({'type': 'websocket.accept'})
        
        # Join room
        room = self.get_room(room_name)
        await room.join(username, send)
        
        try:
            # Handle messages
            while True:
                message = await receive()
                
                if message['type'] == 'websocket.disconnect':
                    break
                
                elif message['type'] == 'websocket.receive':
                    text = message.get('text', '')
                    
                    if text:
                        # Parse message
                        try:
                            data = json.loads(text)
                            msg_type = data.get('type')
                            
                            if msg_type == 'message':
                                # Regular chat message
                                await room.send_message(username, data.get('text', ''))
                            
                            elif msg_type == 'ping':
                                # Heartbeat
                                await send({
                                    'type': 'websocket.send',
                                    'text': json.dumps({'type': 'pong'})
                                })
                        
                        except json.JSONDecodeError:
                            # Plain text message
                            await room.send_message(username, text)
        
        finally:
            # Leave room
            await room.leave(username)


# Create application instance
app = ChatApplication()


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)

