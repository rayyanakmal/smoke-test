import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


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
