# Smoke Test: Hello API

A minimal FastAPI application with two endpoints, built as a smoke test to validate the FastAPI + pytest + httpx stack.

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
uvicorn main:app --reload
```

Server starts at http://127.0.0.1:8000.

## Endpoints

### GET /hello

```bash
curl http://127.0.0.1:8000/hello
# {"message":"hello world"}
```

### GET /health

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

## Tests

```bash
pytest test_main.py -v --cov=main --cov-fail-under=80 --cov-report=term-missing
```
