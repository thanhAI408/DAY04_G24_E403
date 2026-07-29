# G24 Research Studio — final evidence report

## Part A — Overview

Team: G24 / member names not present in repository (fill before submission)
Provider/model: OpenAI / `gpt-4o-mini`
Deployment: local UI verified at `http://127.0.0.1:8000`; no Vercel URL claimed because a Vercel deploy was not authenticated in this run.

G24 Research Studio is a server-side research assistant for public web news, X/Twitter account and topic search, URL reading, digest formatting, internal policy lookup, arXiv discovery, and duplicate-source removal.

### Demo order and presenter script

1. Open `http://127.0.0.1:8000` → **Demo Mode**. Run Scenario 1 and point to the `web_search` arguments.
2. Run Scenario 2. Explain that turn 1 asks for the account and turn 2 maps Sam Altman to `sama` while preserving `limit=3`.
3. Run Scenario 3. Explain that the model calls both public web and X tools, with `search_type=Top`.
4. Open **Evidence** to show metrics loaded from real `runs/*.json`, direct run JSON links, rehearsal checklist and fallback transcripts.
5. Use the separate Telegram challenge only if asked about write safety; it must stop at `ask_user(yes_no)` and never call `send_telegram`.

Suggested opening: “Tôi sẽ không trình bày source code; tôi chỉ dùng ba scenario để chứng minh routing, missing-information handling, multi-tool behavior và evidence thật.”

| Tool | Capability | New team tool? |
|---|---|---|
| `ask_user` | missing information and confirmation | no |
| `get_user_tweets` | posts from one account | no |
| `search_tweets` | posts about a topic | no |
| `web_search` | public web/news | no |
| `read_url` | read a supplied URL | no |
| `render_digest` | format retrieved items | no |
| `send_telegram` | confirmed external delivery | no |
| `search_company_policy` | local policy lookup | no |
| `arxiv_search` | paper discovery | no |
| `get_arxiv_paper_text` | known arXiv text extraction | no |
| `deduplicate_research_items` | URL/title duplicate removal | yes |

Sample prompts: `Tìm tin tức AI hôm nay`; `Lấy 3 bài đăng gần nhất`; `Đọc https://openai.com/research/`; `Loại các nguồn trùng lặp trong danh sách này`.

Demo evidence: `transcripts/v3_openai_news_today_20260729T155127838463.transcript.json`, `transcripts/v3_openai_missing_account_then_fill_20260729T155140726776.transcript.json`, and `transcripts/v3_openai_telegram_confirmation_20260729T155143614048.transcript.json`. The Telegram scenario called `ask_user` with `yes_no` and did not call `send_telegram`.

## Part B — Evidence

All listed runs have `provider_error_cases=0` and `measured_cases=total_cases`.

| Version | Change | Case accuracy | Routing | Arguments | Passed/total | Run |
|---|---|---:|---:|---:|---:|---|
| v0 | baseline | 0.70 | — | — | 14/20 | `v0_B_base_openai_20260729T151509185119.json` |
| v1 | clarification/confirmation rules | 0.80 | — | — | 16/20 | `v1_B_base_openai_20260729T151957186167.json` |
| v2 | semantic names + team tool | 0.95 | 0.95 | 0.95 | 19/20 | `v2_B_base_openai_20260729T154449837309.json` |
| v3 | one focused missing-account prompt example | 0.95 | 1.00 | 0.95 | 19/20 | `v3_B_base_openai_20260729T154732827585.json` |

V2's only failure was R10 missing-account clarification. V3 made that case pass. V3's remaining failure was R12: the model selected `ask_user` but used `response_type=text` instead of `yes_no`; no further V3 prompt change was made.

The fixed eval files changed only expected tool-call names for the rename; queries, expected arguments, and behavior were not edited.

### Group eval

`data/eval_group.json` contains exactly 10 cases: 5 single-turn query cases and 5 multi-turn turns cases, all phase B. Real run `runs/v3_B_group_openai_20260729T155043327620.json`: 10 measured, 0 provider errors, 9 passed, case accuracy 0.90. G07 produced one extra tool call; this remains reported as evidence rather than hidden.

### Validation and guardrails

YAML/JSON parsing, registry/declaration parity (11/11), Python compileall, OpenAI preflight, dedup smoke tests, local `/`, `/api/health`, `/api/runs`, and `/api/chat` checks passed. The run endpoint rejects path traversal and responses sanitize secret-like fields. `.env`, `.venv`, caches, and build outputs are ignored. No Telegram live-send was performed.
