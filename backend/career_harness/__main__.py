from __future__ import annotations

import argparse
import os

import uvicorn

from career_harness.api.runtime import create_runtime_app
from career_harness.config import LOCALHOST, Settings


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Agent Career Harness local API")
    parser.add_argument("--host", default=os.getenv("ACH_HOST", LOCALHOST))
    parser.add_argument("--port", type=int, default=int(os.getenv("ACH_PORT", "8765")))
    parser.add_argument("--token", default=os.getenv("ACH_LAUNCH_TOKEN"))
    parser.add_argument("--environment", default=os.getenv("ACH_ENV", "development"))
    parser.add_argument("--allowed-origin", default=os.getenv("ACH_ALLOWED_ORIGIN"))
    return parser


def main() -> None:
    args = _parser().parse_args()
    settings = Settings(
        host=args.host,
        port=args.port,
        launch_token=args.token or None,
        environment=args.environment,
        allowed_origin=args.allowed_origin,
    )
    uvicorn.run(create_runtime_app(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()

