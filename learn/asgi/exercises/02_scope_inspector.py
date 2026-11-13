"""
Exercise 2: Scope Inspector
============================

Create an application that displays all scope information as JSON.

Run with:
    uvicorn exercises.02_scope_inspector:app --reload

Test with:
    curl http://localhost:8000
"""

import json


async def app(scope, receive, send):
    """
    Inspect and display ASGI scope information.
    """
    if scope['type'] == 'http':
        # Convert scope to JSON-serializable format
        scope_info = {
            'type': scope['type'],
            'method': scope['method'],
            'path': scope['path'],
            'query_string': scope['query_string'].decode('utf-8'),
            'headers': [
                [name.decode('latin-1'), value.decode('latin-1')]
                for name, value in scope['headers']
            ],
            'server': scope.get('server'),
            'client': scope.get('client'),
            'scheme': scope['scheme'],
            'http_version': scope['http_version'],
        }
        
        # Pretty-print JSON
        body = json.dumps(scope_info, indent=2).encode('utf-8')
        
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'application/json'],
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

