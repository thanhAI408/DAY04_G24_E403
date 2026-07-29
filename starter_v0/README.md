# G24 Research Studio — starter_v0

Server-side OpenAI research agent for public web news, X/Twitter posts, URL reading, digest formatting, internal policy lookup, arXiv discovery, and deterministic research-source deduplication. Semantic model-facing tool names are synchronized across declarations, registry, and eval datasets.

## Local Windows setup

```powershell
cd starter_v0
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Open `http://127.0.0.1:8000`. API calls and secrets stay server-side. Environment names are `OPENAI_API_KEY`, `TAVILY_API_KEY`, `FIRECRAWL_API_KEY`, `RAPIDAPI_KEY`, `RAPIDAPI_TWITTER_HOST`, plus optional `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Never commit `.env` or credentials.

## Evaluation and evidence

```powershell
python scripts/preflight_provider.py --provider openai --model "gpt-4o-mini"
python run_eval.py --provider openai --model "gpt-4o-mini" --version v3 --suite base --eval-cases data/eval_base.json
python run_eval.py --provider openai --model "gpt-4o-mini" --version v3 --suite group --eval-cases data/eval_group.json
python scripts/parse_runs.py runs/ --output analysis/base_runs.csv
```

Live demo transcripts are stored locally under `transcripts/`; deployed Vercel instances return the transcript in `/api/chat` instead of relying on persistent serverless filesystem writes.

## Vercel

The Vercel project root is `starter_v0`. `vercel.json` uses the root `app.py` FastAPI entrypoint. Run `vercel deploy --yes` only after authenticating and configuring environment variables in Vercel; use `--prod` only for an explicitly configured production project. No URL is claimed until a real deploy succeeds.

## Demo prompts

- `Tìm tin tức AI hôm nay`
- `Lấy 3 bài đăng gần nhất` (the agent asks for an account)
- `Đọc và tóm tắt https://openai.com/research/`
- `Loại các nguồn trùng lặp trong danh sách này`

The system prompt enforces missing-information clarification, external-send confirmation, out-of-scope refusal, argument preservation, and explicit routing boundaries.

## Demo Mode — 3–5 minute rehearsal

Open `http://127.0.0.1:8000` and select **Demo Mode**. The screen has exactly three live scenarios, a separate Telegram fallback challenge, expandable tool-trace cards, PASS/FAIL badges, loading/error states, and Reset.

1. Run **Scenario 1 — Tin tức AI hôm nay**. Say: “Đầu tiên tôi chứng minh main tool và query normalization.” Show `web_search` with `query=AI`, `topic=news`, `timeframe=day`.
2. Run **Scenario 2 — Thiếu thông tin**. Say: “Agent không tự đoán account.” Show turn 1 `ask_user(response_type=text)`, then turn 2 `get_user_tweets(screenname=sama, limit=3)`.
3. Run **Scenario 3 — Web + X phổ biến**. Say: “Một yêu cầu có hai nguồn nên trace có hai tool.” Show `web_search` and `search_tweets(search_type=Top)`.
4. Open **Evidence**. Show the real V0–V3 run links, the checklist, metrics, and the three fallback transcript links.
5. If asked about safety, run the separate **Telegram challenge**. It must show `ask_user(yes_no)` and no `send_telegram`.

Before presenting, verify API health, OpenAI/gpt-4o-mini, 11 tools, run files, 3 transcripts, no exposed secrets, and the three scenario readiness checks. Do not open source code during the demo.
