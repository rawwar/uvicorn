"""
Exercise 5: WebSocket Echo Server
==================================

Create a WebSocket server that echoes messages back.

Run with:
    uvicorn exercises.05_websocket_echo:app --reload

Test with JavaScript in browser console:
    const ws = new WebSocket('ws://localhost:8000');
    ws.onmessage = (e) => console.log('Received:', e.data);
    ws.send('Hello!');
"""


async def app(scope, receive, send):
    """
    WebSocket echo server.
    """
    
    if scope['type'] == 'websocket':
        # Accept the WebSocket connection
        await send({
            'type': 'websocket.accept'
        })
        
        # Echo messages
        while True:
            message = await receive()
            
            if message['type'] == 'websocket.disconnect':
                break
            
            elif message['type'] == 'websocket.receive':
                # Echo text messages
                if 'text' in message:
                    await send({
                        'type': 'websocket.send',
                        'text': f"Echo: {message['text']}"
                    })
                
                # Echo binary messages
                elif 'bytes' in message:
                    await send({
                        'type': 'websocket.send',
                        'bytes': message['bytes']
                    })
    
    elif scope['type'] == 'http':
        # Provide instructions for HTTP requests
        body = b'''
WebSocket Echo Server

Connect with:
    const ws = new WebSocket('ws://localhost:8000');
    ws.onmessage = (e) => console.log(e.data);
    ws.send('Hello!');
        '''
        
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [[b'content-type', b'text/plain']],
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

