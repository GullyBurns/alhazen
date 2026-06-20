"""Run the gateway: ``python -m skillful_alhazen.gateway``."""

from __future__ import annotations

import os


def main() -> None:
    import uvicorn

    uvicorn.run(
        "skillful_alhazen.gateway.app:app",
        host=os.getenv("GATEWAY_HOST", "0.0.0.0"),
        port=int(os.getenv("GATEWAY_PORT", "8900")),
        workers=1,  # single worker: invocations serialize on a process-global lock
        log_level=os.getenv("GATEWAY_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
