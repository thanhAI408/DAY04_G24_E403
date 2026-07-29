from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from chat import now_iso, run_model_tool_loop, safe_slug, write_transcript
from providers import make_provider
from tools import load_tool_declarations, to_openai_tools
from versioning import artifact_version_dict, build_artifact_version

ROOT = Path(__file__).parent
VERSIONS_DIR = ROOT / "versions"
ARTIFACTS_DIR = ROOT / "artifacts"
TRANSCRIPTS_DIR = ROOT / "transcripts"

SAMPLE_PROMPTS = [
    ("Case gọi tool chính", "Tweet mới nhất của Sam Altman là gì?"),
    ("Case thiếu thông tin", "Tóm tắt 5 tweet mới nhất giúp mình"),
    ("Case multi-tool", "Tìm trên web tin AI hôm nay và tìm thêm tweet về AI."),
]


def discover_versions() -> dict[str, tuple[Path, Path]]:
    versions: dict[str, tuple[Path, Path]] = {}
    if VERSIONS_DIR.exists():
        for child in sorted(VERSIONS_DIR.iterdir()):
            prompt_path = child / "system_prompt.md"
            tools_path = child / "tools.yaml"
            if prompt_path.exists() and tools_path.exists():
                versions[child.name] = (prompt_path, tools_path)
    versions["live (artifacts/)"] = (ARTIFACTS_DIR / "system_prompt.md", ARTIFACTS_DIR / "tools.yaml")
    return versions


def init_state() -> None:
    st.session_state.setdefault("history", [])
    st.session_state.setdefault("turns", [])
    st.session_state.setdefault("transcript_id", None)


def reset_conversation() -> None:
    st.session_state.history = []
    st.session_state.turns = []
    st.session_state.transcript_id = None


st.set_page_config(page_title="Research Agent", page_icon="🔎", layout="wide")
init_state()

available_versions = discover_versions()
version_labels = list(available_versions.keys())
default_index = version_labels.index("v2") if "v2" in version_labels else len(version_labels) - 1

with st.sidebar:
    st.header("Cấu hình")
    provider_name = st.selectbox("Provider", ["gemini", "openrouter", "openai", "anthropic"], index=0)
    version_label = st.selectbox(
        "Version (optional — prompt/tools snapshot)",
        version_labels,
        index=default_index,
        help="Chọn snapshot artifacts/system_prompt.md + tools.yaml để so sánh hành vi qua các version.",
    )
    model_override = st.text_input("Model override (để trống = default provider)", value="")
    max_tool_rounds = st.number_input("Max tool rounds", min_value=1, max_value=10, value=4)
    history_window = st.number_input("History window (số cặp lượt giữ lại)", min_value=0, max_value=20, value=5)

    if st.button("🔄 Reset hội thoại", use_container_width=True):
        reset_conversation()
        st.rerun()

    st.divider()
    st.caption("Câu hỏi mẫu (chạy cùng scenario qua nhiều version để so sánh):")
    sample_clicked: str | None = None
    for label, prompt in SAMPLE_PROMPTS:
        if st.button(f"▶ {label}", use_container_width=True, key=f"sample_{label}"):
            sample_clicked = prompt

system_prompt_path, tools_path = available_versions[version_label]
system_prompt_text = system_prompt_path.read_text(encoding="utf-8")
tool_declarations = load_tool_declarations(tools_path)
openai_tools = to_openai_tools(tool_declarations)
provider = make_provider(provider_name)
selected_model = model_override.strip() or getattr(provider, "default_model", None)
artifact_version = build_artifact_version(version_label, system_prompt_path, tools_path)

st.title("🔎 Research Agent")
st.caption(
    f"**artifact_version:** `{artifact_version.artifact_version}`  |  "
    f"**provider:** `{provider_name}`  |  **model:** `{selected_model}`"
)

if st.session_state.transcript_id is None:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    st.session_state.transcript_id = "_".join([safe_slug(version_label), safe_slug(provider_name), timestamp])

transcript_path = TRANSCRIPTS_DIR / f"{st.session_state.transcript_id}.transcript.json"


def render_tool_trace(rounds: list[dict[str, Any]]) -> None:
    for round_record in rounds:
        status_bits = []
        for call, result in zip(round_record["tool_calls"], round_record["tool_results"]):
            result_payload = result.get("result", {})
            is_error = isinstance(result_payload, dict) and "error" in result_payload
            icon = "❌" if is_error else "✅"
            with st.expander(f"{icon} round {round_record['round']} · `{call['name']}`", expanded=is_error):
                st.markdown("**args**")
                st.code(json.dumps(call["args"], ensure_ascii=False, indent=2), language="json")
                st.markdown("**result**")
                st.code(json.dumps(result_payload, ensure_ascii=False, indent=2, default=str), language="json")


def send_user_message(user_text: str) -> None:
    turn_index = len(st.session_state.turns) + 1
    trimmed = st.session_state.history[-history_window * 2:] if history_window > 0 else []
    messages = [
        {"role": "system", "content": system_prompt_text},
        *trimmed,
        {"role": "user", "content": user_text},
    ]

    turn_record: dict[str, Any] = {
        "turn_index": turn_index,
        "started_at": now_iso(),
        "user": user_text,
        "status": "started",
        "assistant_text": None,
        "rounds": [],
        "tool_events": [],
    }

    with st.spinner("Đang xử lý..."):
        try:
            result = run_model_tool_loop(
                provider=provider,
                messages=messages,
                tools=openai_tools,
                model=model_override.strip() or None,
                max_tool_rounds=max_tool_rounds,
            )
            turn_record.update(result)
            assistant_text = result["assistant_text"]
            st.session_state.history.append({"role": "user", "content": user_text})
            st.session_state.history.append({"role": "assistant", "content": assistant_text})
        except Exception as exc:
            turn_record.update({
                "status": "provider_error",
                "assistant_text": f"{type(exc).__name__}: {exc}",
            })

    turn_record["ended_at"] = now_iso()
    st.session_state.turns.append(turn_record)

    transcript = {
        "transcript_id": st.session_state.transcript_id,
        **artifact_version_dict(artifact_version),
        "provider": provider_name,
        "model": selected_model,
        "system_prompt": str(system_prompt_path),
        "tools": str(tools_path),
        "history_window": history_window,
        "max_tool_rounds": max_tool_rounds,
        "created_at": st.session_state.turns[0]["started_at"],
        "turns": st.session_state.turns,
    }
    write_transcript(transcript_path, transcript)


for turn in st.session_state.turns:
    with st.chat_message("user"):
        st.write(turn["user"])
    with st.chat_message("assistant"):
        status = turn.get("status", "answered")
        if status == "provider_error":
            st.error(turn["assistant_text"])
        else:
            st.write(turn["assistant_text"])
            if status == "waiting_for_user":
                st.info("⏸ Agent đang chờ bạn bổ sung thông tin (clarify).")
        render_tool_trace(turn.get("rounds", []))

user_input = st.chat_input("Nhập yêu cầu nghiên cứu...")
if sample_clicked:
    send_user_message(sample_clicked)
    st.rerun()
elif user_input:
    send_user_message(user_input)
    st.rerun()

if st.session_state.turns:
    st.caption(f"Transcript: `{transcript_path}`")
