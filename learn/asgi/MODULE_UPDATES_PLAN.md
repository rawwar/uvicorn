# Module Updates Plan - Applying New Pedagogy

## Philosophy

Transform all modules from **"what ASGI does"** to **"why it works this way, how to build it yourself"**.

## Core Principles for Each Module

1. **Start with WHY** - What problem does this solve?
2. **Show the mechanics** - Build it in pure Python first
3. **Make it concrete** - Runnable examples before theory
4. **Hands-on exercises** - Build, don't just read
5. **Connect to uvicorn** - Only after understanding

## Module-by-Module Transformation

### Module 02: ASGI Scopes ✏️ IN PROGRESS

**Current problem:** Lists scope fields without explaining WHY they're structured this way.

**New approach:**
1. WHY: Explain why scope is a dictionary (flexibility, protocol-agnostic)
2. WHY: Explain why headers are list of tuples not dict (multiple headers with same name)
3. WHY: Explain why paths are both string and bytes (encoding issues)
4. Build a scope parser from scratch (show how servers create scopes)
5. Interactive scope inspector (pure Python, no uvicorn)
6. Then show uvicorn's implementation

**Key additions:**
- Pure Python HTTP request parser → scope builder
- Show why each design decision matters
- Hands-on: Build your own scope from raw HTTP

### Module 03: HTTP Protocol

**Current problem:** Shows message format without explaining the request-response cycle mechanics.

**New approach:**
1. WHY: Explain why separate response.start and response.body (HTTP protocol reality)
2. WHY: Explain why streaming matters (memory, UX)
3. Build: Implement receive() that reads from socket
4. Build: Implement send() that writes to socket  
5. Pure Python HTTP server using ASGI interface
6. Only then use uvicorn

**Key additions:**
- Socket-level HTTP example showing why ASGI works this way
- Build complete HTTP echo server from scratch
- Show what happens at network level

### Module 04: Lifespan Protocol

**Current problem:** States "use lifespan for startup/shutdown" without explaining WHY this is separate.

**New approach:**
1. WHY: Explain the problem (where do you initialize DB connections in WSGI? globals? bad!)
2. WHY: Explain why lifespan is a separate scope type (runs once, not per-request)
3. WHY: Explain why state dict is in scope (sharing across requests)
4. Build: Simulate lifespan cycle in pure Python
5. Show: What happens if you use globals vs lifespan
6. Common mistakes and why they happen

**Key additions:**
- Problem without lifespan (globals, race conditions)
- Pure Python lifespan simulation
- Side-by-side comparison: bad (globals) vs good (lifespan)

### Module 05: WebSocket Protocol

**Current problem:** Lists WebSocket events without explaining the protocol mechanics.

**New approach:**
1. WHY: Explain HTTP → WebSocket upgrade (it's still HTTP at first!)
2. WHY: Explain bidirectional vs request-response
3. WHY: Explain frame-based communication
4. Build: WebSocket handshake from scratch
5. Build: Frame encoding/decoding
6. Simulate: Complete WebSocket in pure Python
7. Then use uvicorn

**Key additions:**
- HTTP upgrade request analysis  
- WebSocket frame structure explanation
- Pure Python WebSocket simulator
- Why accept/send/receive pattern exists

### Module 06: Middleware

**Current problem:** Shows middleware pattern without explaining WHY this pattern is powerful.

**New approach:**
1. WHY: Explain the problem (cross-cutting concerns, don't repeat yourself)
2. WHY: Explain why wrapping works (ASGI apps are just callables)
3. Build: Middleware from scratch (step by step)
4. Show: How wrapping receive/send gives you power
5. Common patterns and why they work
6. Middleware composition (why order matters)

**Key additions:**
- Problem without middleware (repeated code everywhere)
- Build middleware step-by-step
- Visual diagram of middleware stack
- Debugging middleware chains

### Module 07: Advanced Concepts

**Current problem:** Lists advanced features without showing when/why you'd use them.

**New approach:**
1. Extensions: WHY they exist (optional features, negotiation)
2. Server Push: WHY it helps (eliminate round trips)
3. Trailers: WHY needed (streaming + checksums)
4. Flow Control: WHY critical (backpressure, slow clients)
5. Build each concept from scratch
6. Real-world scenarios where you need them

**Key additions:**
- Problem scenarios showing why each feature exists
- Pure Python implementation of each advanced feature
- Performance comparisons (with vs without)

### Module 08: Building Complete Applications

**Current problem:** Dumps complete code without showing incremental building process.

**New approach:**
1. Start simple: Basic HTTP server
2. Add: Routing (step 1)
3. Add: Request body parsing (step 2)
4. Add: WebSocket (step 3)
5. Add: Lifespan (step 4)
6. Add: Middleware (step 5)
7. Add: Error handling (step 6)
8. Refactor: Extract components (step 7)

**Key additions:**
- Incremental building (each step adds one concept)
- Commit-by-commit style guide
- Testing at each step
- Refactoring patterns

## Success Criteria

For each module, readers should be able to:
- ✅ Explain WHY the design works this way
- ✅ Build a basic version themselves in pure Python
- ✅ Understand what uvicorn adds on top
- ✅ Debug ASGI apps effectively
- ✅ Make informed design decisions

## Timeline

Due to the large scope:
1. Module 02: In progress
2. Modules 03-08: Sequential updates
3. Each module: ~1-2 hours of transformation

## Notes

- Keep existing good examples, enhance with WHY/HOW
- Add "Common Mistakes" sections (learn from failures)
- Add "Design Decisions" sections (understand trade-offs)
- Cross-reference between modules (build on previous understanding)

