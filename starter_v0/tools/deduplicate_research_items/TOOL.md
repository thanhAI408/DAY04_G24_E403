# deduplicate_research_items

Deterministically merges duplicate research sources while preserving the first item as canonical.

Input is `items`, plus an optional `similarity_threshold` (0–1) and `remove_tracking_params`. URLs are normalized by lowercasing the domain, removing fragments/trailing slashes, and dropping common tracking parameters. Titles are normalized and compared with `SequenceMatcher`.

Output contains `unique_items`, `duplicate_groups`, `original_count`, `unique_count`, and `removed_count`. Missing URLs/titles are safe; invalid item shapes return a structured error. The tool uses only Python standard library and never calls an LLM or external API.

Use only when the user explicitly asks to deduplicate or merge duplicate sources. Do not call it automatically for ordinary search requests.

Example: two URLs differing only by `utm_source` are one canonical source.

