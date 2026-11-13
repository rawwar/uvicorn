"""
Exercise 3b: Streaming Response
================================

Create a server that streams a countdown timer.

Run with:
    uvicorn exercises.03_streaming_response:app --reload

Test with:
    curl http://localhost:8000
"""

import asyncio


async def app(scope, receive, send):
    """
    Stream a countdown from 10 to 1 with delays.
    """
    if scope['type'] == 'http':
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'text/plain'],
            ],
        })
        
        # Stream countdown
        for i in range(10, 0, -1):
            chunk = f'{i}...\n'.encode()
            await send({
                'type': 'http.response.body',
                'body': chunk,
                'more_body': True,
            })
            await asyncio.sleep(1)
        
        # Final message
        await send({
            'type': 'http.response.body',
            'body': b'Blast off! 🚀\n',
            'more_body': False,
        })
    else:
        raise NotImplementedError(f"Unsupported scope type: {scope['type']}")


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)

