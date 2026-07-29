---
name: web_search
track: core
kind: live_api
provider: Tavily
requires_env: [TAVILY_API_KEY]
inputs: [query, topic, timeframe, max_results]
outputs: [items]
side_effect: false
---
# web_search

Searches the web via Tavily. Has a `topic` (`general` or `news`) and a
`timeframe` argument.

