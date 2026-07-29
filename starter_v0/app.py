from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from chat import run_model_tool_loop
from env_loader import load_lab_env
from providers import make_provider
from tools import TOOL_FUNCTIONS, load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version

ROOT = Path(__file__).parent
ARTIFACTS = ROOT / "artifacts"
RUNS = ROOT / "runs"
load_lab_env(ROOT)
app = FastAPI(title="G24 Research Studio")
app.mount("/public", StaticFiles(directory=ROOT / "public"), name="public")


class ChatRequest(BaseModel):
    messages: list[dict[str, str]] | None = None
    message: str | None = None
    provider: str = "openai"
    model: str = "gpt-4o-mini"


def artifact() -> dict[str, str]:
    return artifact_version_dict(build_artifact_version("v3", ARTIFACTS / "system_prompt.md", ARTIFACTS / "tools.yaml"))


def sanitize(value: Any) -> Any:
    secret_words = ("key", "token", "secret", "authorization", "password")
    if isinstance(value, dict):
        return {k: ("[redacted]" if any(word in str(k).lower() for word in secret_words) else sanitize(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize(v) for v in value]
    if isinstance(value, str):
        return re.sub(r"(?i)(sk-[A-Za-z0-9_-]+|bot\d+:[A-Za-z0-9_-]+)", "[redacted]", value)
    return value


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "provider": "openai", "model": "gpt-4o-mini", **artifact(), "available_tools": list(TOOL_FUNCTIONS)}


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    messages = request.messages or ([{"role": "user", "content": request.message}] if request.message else [])
    if not messages:
        raise HTTPException(status_code=400, detail="message or messages is required")
    if request.provider != "openai":
        raise HTTPException(status_code=400, detail="Only the configured OpenAI provider is enabled for this demo")
    transcript_id = "ui_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    try:
        result = run_model_tool_loop(
            provider=make_provider("openai"),
            messages=[{"role": "system", "content": (ARTIFACTS / "system_prompt.md").read_text(encoding="utf-8")}, *messages],
            tools=to_openai_tools(load_tool_declarations(ARTIFACTS / "tools.yaml")),
            model=request.model or "gpt-4o-mini",
            max_tool_rounds=4,
        )
        return sanitize({"final_response": result.get("assistant_text", ""), "rounds": result.get("rounds", []), "tool_events": result.get("tool_events", []), "status": result.get("status"), **artifact(), "transcript_id": transcript_id, "timestamp": datetime.now(timezone.utc).isoformat()})
    except Exception as exc:
        return {"final_response": "Provider request failed.", "rounds": [], "tool_events": [], "status": "provider_error", "error": f"{type(exc).__name__}: {exc}", **artifact(), "transcript_id": transcript_id}


@app.get("/api/runs")
def runs() -> dict[str, Any]:
    result = []
    for path in sorted(RUNS.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            result.append(sanitize({"filename": path.name, "version": data.get("version"), "artifact_version": data.get("artifact_version"), "suite": data.get("suite"), "metrics": data.get("metrics", {})}))
        except (OSError, json.JSONDecodeError):
            continue
    return {"runs": result}


@app.get("/api/runs/{filename}")
def run_detail(filename: str) -> dict[str, Any]:
    if Path(filename).name != filename or not filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Invalid run filename")
    path = RUNS / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Run not found")
    try:
        return sanitize(json.loads(path.read_text(encoding="utf-8")))
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid run JSON")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (ROOT / "public" / "index.html").read_text(encoding="utf-8")
