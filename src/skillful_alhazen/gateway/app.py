"""FastAPI surface for the skill query gateway.

Internal service only — it executes skill commands (including writes), so it must
be bound to the docker network / localhost and never exposed publicly.
"""

from __future__ import annotations

import asyncio
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import dispatcher

DEFAULT_TIMEOUT = float(os.getenv("GATEWAY_TIMEOUT", "120"))

app = FastAPI(title="Alhazen Skill Gateway", version="0.1.0")


class RunRequest(BaseModel):
    skill: str
    argv: list[str] = Field(default_factory=list)
    entrypoint: str | None = None
    timeout: float | None = None


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "skills": dispatcher.list_skills()}


@app.post("/run")
async def run(req: RunRequest):
    timeout = req.timeout or DEFAULT_TIMEOUT
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(dispatcher.run, req.skill, req.argv, req.entrypoint),
            timeout=timeout,
        )
    except dispatcher.DispatchError as exc:
        return JSONResponse(status_code=404, content={"ok": False, "error": str(exc)})
    except TimeoutError:
        return JSONResponse(
            status_code=504,
            content={"ok": False, "error": f"command timed out after {timeout}s"},
        )
