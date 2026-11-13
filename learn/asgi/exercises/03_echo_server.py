"""
Exercise 3: Echo Server
=======================

Create an HTTP server that echoes back the request body.

Run with:
    uvicorn exercises.03_echo_server:app --reload

Test with:
    echo "Hello, Echo!" | curl -X POST -d @- http://localhost:8000
"""


async def read_body(receive):
    """Read the full request body."""
    body = b''
    more_body = True
    
    while more_body:
        message = await receive()
        body += message.get('body', b'')
        more_body = message.get('more_body', False)
    
    return body


async def app(scope, receive, send):
    """
    Echo server that returns the request body.
    """
    if scope['type'] == 'http':
        # Read the request body
        body = await read_body(receive)
        
        # Echo it back
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'text/plain'],
                [b'content-length', str(len(body)).encode()],
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

