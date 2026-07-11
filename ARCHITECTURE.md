---
title: ARCHITECTURE
project: smoke-test-hello-api
version: 1
created: 2026-07-08
---

# Architecture: Smoke Test — Hello API

## Overview

A minimal FastAPI application exposing two endpoints. Built as a smoke test to validate the FastAPI + pytest + httpx.AsyncClient stack. The entire system is a single-file app with a single-file test suite. No database. No middleware. No external dependencies beyond FastAPI and uvicorn.

---

## 1. System Diagram

```
                    ┌──────────────────────────┐
                    │     HTTP Client           │
                    │  (curl / browser / test)  │
                    └─────┬──────────┬──────────┘
                          │          │
                    GET /hello   GET /health
                          │          │
                          ▼          ▼
               ┌──────────────────────────────┐
               │       FastAPI Application     │
               │         (main.py)             │
               │                               │
               │  ┌─────────────────────────┐  │
               │  │ GET /hello               │  │
               │  │ → {"message":"hello       │  │
               │  │           world"}         │  │
               │  └─────────────────────────┘  │
               │  ┌─────────────────────────┐  │
               │  │ GET /health              │  │
               │  │ → {"status":"ok"}        │  │
               │  └─────────────────────────┘  │
               │  ┌─────────────────────────┐  │
               │  │ Any other route          │  │
               │  │ → 404 (FastAPI default)  │  │
               │  └─────────────────────────┘  │
               └──────────────────────────────┘
                          │
                          │ (in tests)
                          ▼
               ┌──────────────────────────────┐
               │  httpx.AsyncClient            │
               │  (ASGITransport, no server)   │
               │                               │
               │  test_hello_returns_200()     │
               │  test_hello_body()            │
               │  test_health_returns_200()    │
               │  test_health_body()           │
               │  test_unknown_route_404()     │
               │  test_wrong_method_405()      │
               └──────────────────────────────┘
```

**Data flow for `GET /hello`:**

```
Client                  FastAPI (main.py)               Response
  │                         │                              │
  │── GET /hello ──────────►│                              │
  │                         │  hello():                    │
  │                         │    return {"message":        │
  │                         │      "hello world"}          │
  │◄── 200 JSON ────────────│                              │
  │    {"message":           │                              │
  │     "hello world"}      │                              │
```

**Data flow for `GET /health`:**

```
Client                  FastAPI (main.py)               Response
  │                         │                              │
  │── GET /health ─────────►│                              │
  │                         │  health():                   │
  │                         │    return {"status": "ok"}   │
  │◄── 200 JSON ────────────│                              │
  │    {"status": "ok"}     │                              │
```

---

## 2. Directory Structure

```
smoke-test/
├── SPEC.md                    # Spec (already exists)
├── ARCHITECTURE.md            # This file
├── README.md                  # curl examples + setup instructions
├── requirements.txt           # Pinned dependencies
├── main.py                    # FastAPI app (single file)
└── test_main.py               # Pytest suite (httpx.AsyncClient)
```

**Rationale for single-file layout:** The SPEC defines exactly two endpoints with zero shared logic. Splitting into `app.py` + `routers/` + `schemas/` would be over-engineering. A single `main.py` is the correct scale for two trivial routes. If this grows beyond 5 endpoints, extract a `routers/` package and a `schemas.py`.

---

## 3. Module Dependency Graph

```
┌──────────────┐
│  fastapi     │  (PyPI, external)
└──────┬───────┘
       │ imported by
       ▼
┌──────────────┐     ┌──────────────┐
│   main.py    │     │  uvicorn     │  (dev server, not a code dependency)
│              │     └──────────────┘
│ app = FastAPI│
│              │
│ @app.get(    │
│   "/hello")  │
│ def hello()  │
│              │
│ @app.get(    │
│   "/health") │
│ def health() │
└──────┬───────┘
       │ imported by
       ▼
┌──────────────┐     ┌──────────────┐
│ test_main.py │────▶│   httpx      │  (PyPI, external)
│              │     └──────────────┘
│ import main  │
│ from main    │     ┌──────────────┐
│   import app │────▶│   pytest     │  (PyPI, external)
│              │     └──────────────┘
│ ASGITransport│
│ AsyncClient  │
└──────────────┘
```

**Key insight:** `test_main.py` imports the `app` object from `main.py` and passes it to `httpx.AsyncClient(transport=ASGITransport(app=app))`. This means tests talk to the app directly through the ASGI protocol — no port binding, no subprocess, no server lifecycle. This is the idiomatic FastAPI testing pattern.

---

## 4. Data Contracts

### 4.1 `GET /hello`

**Request:** None (no path params, no query params, no body)

**Response — 200 OK:**

```json
{
    "message": "hello world"
}
```

**Python type (Pydantic not needed — plain dict):**

```python
# Return type of hello() — inferred by FastAPI from the dict
# Equivalent to:
# class HelloResponse(BaseModel):
#     message: str
# But a BaseModel is unnecessary for a single static field.
```

**DECISION:** No Pydantic model. The response is a static dict literal. Adding a `BaseModel` for `{"message": "hello world"}` adds zero value and inflates the codebase. FastAPI serializes plain dicts to JSON automatically. If the response ever gains optional fields or nested objects, introduce a model at that point.

### 4.2 `GET /health`

**Request:** None

**Response — 200 OK:**

```json
{
    "status": "ok"
}
```

**Python type:** Same rationale — plain `dict`, no Pydantic model.

### 4.3 `GET /nonexistent` (any undefined route)

**Response — 404 Not Found (FastAPI default):**

```json
{
    "detail": "Not Found"
}
```

This is FastAPI's built-in behavior. No code needed.

### 4.4 `POST /hello` (wrong method on defined route)

**Response — 405 Method Not Allowed (FastAPI default):**

```json
{
    "detail": "Method Not Allowed"
}
```

This is FastAPI's built-in behavior. No code needed.

### 4.5 Accept header behavior

FastAPI defaults to `application/json`. If a client sends `Accept: text/html`, FastAPI still returns JSON (its default response class). This is acceptable for a smoke test — no content negotiation is specified in the SPEC.

---

## 5. Edge Case Handling Strategy

| Scenario | Trigger | Behavior | Where handled |
|----------|---------|----------|---------------|
| Unknown route | `GET /foobar` | 404 `{"detail": "Not Found"}` | FastAPI default routing |
| Wrong HTTP method | `POST /hello` | 405 `{"detail": "Method Not Allowed"}` | FastAPI default routing |
| Malformed JSON body | `POST /hello` with bad JSON | 422 (if body is expected; but GET doesn't expect a body, so this is irrelevant) | N/A for GET endpoints |
| Server startup failure | Port already in use | `OSError: [Errno 48] Address already in use` | uvicorn — user fixes manually |
| Missing dependency | `import fastapi` fails | `ModuleNotFoundError` | User runs `pip install -r requirements.txt` |
| Test isolation | Tests share app state | No shared state exists (stateless endpoints) | Architecture invariant — endpoints are pure functions |
| AsyncClient timeout | App hangs | `httpx.TimeoutException` after default 5s | httpx default; no custom config needed |

**DECISION:** No custom exception handlers. For a two-endpoint smoke test, FastAPI's built-in error handling is sufficient. Custom handlers would add lines of code for scenarios that are already handled correctly by the framework.

**REJECTED:** Adding a global exception handler (`@app.exception_handler`) because it provides no benefit over FastAPI defaults for this scope and adds maintenance surface.

---

## 6. Build Order

Files must be created in this exact sequence. Each file depends only on files above it.

| Step | File | Depends on | Rationale |
|------|------|-----------|-----------|
| 1 | `requirements.txt` | Nothing | Must exist before `pip install` |
| 2 | `main.py` | `requirements.txt` (fastapi installed) | App is the build target; tests depend on it |
| 3 | `test_main.py` | `main.py` | Imports `app` from `main.py` |
| 4 | `README.md` | `main.py` (endpoints defined) | Documents curl commands for actual endpoints |
| 5 | `ARCHITECTURE.md` | All of the above | Documents the final system |

**Build commands (in order):**

```bash
# Step 1: Create requirements.txt
# Step 2: pip install -r requirements.txt
# Step 3: Create main.py
# Step 4: Verify: uvicorn main:app --reload → curl localhost:8000/hello
# Step 5: Create test_main.py
# Step 6: Verify: pytest test_main.py -v
# Step 7: Verify coverage: pytest test_main.py --cov=main --cov-report=term
# Step 8: Create README.md
# Step 9: Create ARCHITECTURE.md
```

---

## 7. Effort Estimate

| User Story | Description | Files | Effort (min) | Notes |
|------------|-------------|-------|-------------|-------|
| **US-1** | GET /hello returns `{"message": "hello world"}` | `main.py` (4 lines) | 5 | Trivial decorator + dict return |
| **US-2** | GET /health returns `{"status": "ok"}` | `main.py` (4 lines) | 3 | Identical pattern to US-1 |
| **US-3** | Tests at 80%+ coverage | `test_main.py` (~30 lines) | 15 | 6 test cases + AsyncClient setup; coverage threshold is trivial to hit with 2 endpoints |
| **US-4** | README with curl examples | `README.md` (~20 lines) | 5 | Setup instructions + 2 curl commands |
| **Setup** | requirements.txt, pip install | `requirements.txt` | 2 | 3 lines of pinned deps |
| **Total** | | | **30 min** | |

### Test coverage breakdown (US-3)

With exactly two endpoints returning static dicts, the following 6 tests achieve **100% branch coverage:**

| Test | Lines exercised | Type |
|------|----------------|------|
| `test_hello_returns_200` | `@app.get("/hello")`, `def hello()` | Happy path |
| `test_hello_returns_correct_body` | `return {"message": "hello world"}` | Value assertion |
| `test_health_returns_200` | `@app.get("/health")`, `def health()` | Happy path |
| `test_health_returns_correct_body` | `return {"status": "ok"}` | Value assertion |
| `test_unknown_route_returns_404` | FastAPI routing layer | Edge case |
| `test_wrong_method_returns_405` | FastAPI routing layer | Edge case |

**DECISION:** Use `pytest-cov` with `--cov=main --cov-fail-under=80`. The 80% threshold is intentionally low for a two-endpoint app. In practice, 6 tests will hit 100% because there are no conditional branches in the app code.

---

## Appendix A: `requirements.txt`

```
fastapi==0.115.6
uvicorn==0.34.0
httpx==0.28.1
pytest==8.3.4
pytest-cov==6.0.0
```

**DECISION:** Pin exact versions. For a smoke test that should be reproducible forever, `==` is safer than `>=`. Bumps can be done deliberately later.

---

## Appendix B: `main.py` skeleton

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/hello")
async def hello():
    return {"message": "hello world"}


@app.get("/health")
async def health():
    return {"status": "ok"}
```

**DECISION:** Use `async def` even though the functions are synchronous. FastAPI handles both. `async def` is the idiomatic default and costs nothing. If a future endpoint needs `await`, the pattern is already consistent.

---

## Appendix C: `test_main.py` skeleton

```python
import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_hello_returns_200(client):
    response = await client.get("/hello")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_hello_returns_correct_body(client):
    response = await client.get("/hello")
    assert response.json() == {"message": "hello world"}


@pytest.mark.asyncio
async def test_health_returns_200(client):
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_returns_correct_body(client):
    response = await client.get("/health")
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_unknown_route_returns_404(client):
    response = await client.get("/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_wrong_method_returns_405(client):
    response = await client.post("/hello")
    assert response.status_code == 405
```

**DECISION:** Use `pytest.mark.asyncio` + `AsyncClient` instead of `TestClient` (Starlette's synchronous client). This is the idiomatic FastAPI testing approach per the official docs. `ASGITransport` means no server socket — the test talks directly to the ASGI app in-process.

**REJECTED:** `fastapi.testclient.TestClient` because it wraps the app synchronously and adds an unnecessary abstraction layer. `httpx.AsyncClient` with `ASGITransport` is the recommended modern pattern.

---

## Appendix D: `pytest` configuration

Add to `pyproject.toml` or `pytest.ini`:

```ini
[pytest]
asyncio_mode = "auto"
```

Or run with:

```bash
pytest test_main.py -v --cov=main --cov-fail-under=80 --cov-report=term-missing
```

**DECISION:** No `setup.cfg` or `pyproject.toml` for this project. The test command is a single line in the README. Adding a config file for one setting (`asyncio_mode`) is unnecessary — `pytest.mark.asyncio` decorators are explicit and self-documenting.

---

## Appendix E: Extension Points

While this is a smoke test with no planned growth, the architecture supports these natural extensions:

| Extension | How to add | What changes |
|-----------|------------|--------------|
| Third endpoint (e.g., `GET /version`) | Add `@app.get("/version")` to `main.py` | 1 new function in `main.py`, 2 new tests in `test_main.py` |
| Request with path params | Add `@app.get("/hello/{name}")` | 1 new function; Pydantic not needed for a single str param |
| Request with query params | Add `async def hello(name: str = "world")` | FastAPI auto-validates; no schema needed |
| POST with JSON body | Add `from pydantic import BaseModel` + `@app.post("/echo")` | 1 model class + 1 endpoint + 2 tests |
| Extract routers | Move endpoints to `routers/hello.py` | `main.py` shrinks to `app.include_router()` calls |
| Dockerize | Add `Dockerfile` | `COPY main.py`, `CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]` |

No extension requires modifying existing code beyond adding new lines — the existing endpoints and tests remain untouched.
