"""
Exercise 1: Hello World
=======================

Create a simple ASGI application that responds with "Hello, World!"

Run with:
    uvicorn exercises.01_hello_world:app --reload

Test with:
    curl http://localhost:8000
"""


async def app(scope, receive, send):
    """
    Simple Hello World ASGI application.
    
    Responds to HTTP requests with "Hello, World!"
    """
    if scope['type'] == 'http':
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'text/plain'],
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': b'Hello, World!',
        })
    else:
        raise NotImplementedError(f"Unsupported scope type: {scope['type']}")


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)

