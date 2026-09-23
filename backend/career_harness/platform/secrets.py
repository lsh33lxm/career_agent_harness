from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class SecretValue:
    _value: str

    def reveal(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "SecretValue([REDACTED])"

    def __str__(self) -> str:
        return "[REDACTED]"


class SecretProvider(Protocol):
    def get(self, name: str) -> SecretValue | None: ...


class EnvironmentSecretProvider:
    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
        self._environment = environment if environment is not None else os.environ

    def get(self, name: str) -> SecretValue | None:
        normalized = re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")
        value = self._environment.get(f"ACH_SECRET_{normalized}")
        return SecretValue(value) if value else None

    def require(self, name: str) -> SecretValue:
        value = self.get(name)
        if value is None:
            raise LookupError(f"required secret is not configured: {name}")
        return value
