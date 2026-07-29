from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from chat import run_model_tool_loop
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version

ROOT = Path(__file__).parents[1]
ARTIFACTS = ROOT / "artifacts"


def main() -> None:
    provider = make_provider("openai")
    prompt = (ARTIFACTS / "system_prompt.md").read_text(encoding="utf-8")
    tools = to_openai_tools(load_tool_declarations(ARTIFACTS / "tools.yaml"))
    version = build_artifact_version("v3", ARTIFACTS / "system_prompt.md", ARTIFACTS / "tools.yaml")
    scenarios = [
        ("news_today", ["Tìm tin tức AI hôm nay"]),
        ("missing_account_then_fill", ["Lấy 3 bài đăng gần nhất", "Sam Altman"]),
        ("telegram_confirmation", ["Đăng bản tin AI này lên Telegram", "Không"]),
    ]
    out = ROOT / "transcripts"
    out.mkdir(exist_ok=True)
    for slug, user_turns in scenarios:
        history: list[dict[str, str]] = []
        turns = []
        for index, user_text in enumerate(user_turns, 1):
            messages = [{"role": "system", "content": prompt}, *history, {"role": "user", "content": user_text}]
            result = run_model_tool_loop(provider=provider, messages=messages, tools=tools, model="gpt-4o-mini", max_tool_rounds=4)
            turns.append({"turn_index": index, "user": user_text, **result})
            history.extend([{"role": "user", "content": user_text}, {"role": "assistant", "content": result.get("assistant_text", "")}])
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        transcript = {"transcript_id": f"v3_openai_{slug}_{stamp}", **artifact_version_dict(version), "provider": "openai", "model": "gpt-4o-mini", "turns": turns}
        path = out / f"{transcript['transcript_id']}.transcript.json"
        path.write_text(json.dumps(transcript, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
