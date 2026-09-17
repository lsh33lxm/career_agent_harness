from __future__ import annotations

import secrets
from dataclasses import dataclass

LOCALHOST = "127.0.0.1"


@dataclass(frozen=True, slots=True)
class Settings:
    host: str = LOCALHOST
    port: int = 8765
    launch_token: str | None = None
    environment: str = "development"
    allowed_origin: str | None = None

    def __post_init__(self) -> None:
        if self.host != LOCALHOST:
            raise ValueError("The local API may only bind to 127.0.0.1")
        if not 0 <= self.port <= 65535:
            raise ValueError("port must be between 0 and 65535")
        if self.environment != "test" and not self.launch_token:
            raise ValueError("A per-launch token is required outside tests")
        if self.launch_token is not None and len(self.launch_token) < 16:
            raise ValueError("launch token must contain at least 16 characters")

    @classmethod
    def for_test(cls, token: str | None = None) -> Settings:
        return cls(
            host=LOCALHOST,
            port=0,
            launch_token=token or secrets.token_urlsafe(32),
            environment="test",
            allowed_origin="http://127.0.0.1:5173",
        )

