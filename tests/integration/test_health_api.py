import httpx
import pytest

from career_harness.api.app import create_app
from career_harness.config import Settings


@pytest.mark.asyncio
async def test_health_requires_ephemeral_token() -> None:
    settings = Settings.for_test(token="test-launch-token-value")
    transport = httpx.ASGITransport(app=create_app(settings))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/health")).status_code == 401
        response = await client.get(
            "/health", headers={"Authorization": "Bearer test-launch-token-value"}
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "agent-career-harness",
        "version": "0.1.0",
        "environment": "test",
    }


def test_non_loopback_bind_is_rejected() -> None:
    try:
        Settings(host="0.0.0.0", launch_token="long-enough-launch-token")
    except ValueError as error:
        assert "127.0.0.1" in str(error)
    else:
        raise AssertionError("non-loopback host was accepted")
