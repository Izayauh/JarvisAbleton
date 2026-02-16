# Research Budget Strategy (Phase A)

This project now supports explicit research cost controls for `research_vocal_chain`.

## What Was Added

1. Budget modes:
- `cheap`: lowest API spend, smaller source limits, no intent/reasoning LLM calls.
- `balanced`: default mix of quality and cost.
- `deep`: highest quality and highest budget.

2. Hard caps:
- Per-request LLM call budget (`max_total_llm_calls`).
- Source limits (YouTube videos, web articles).
- LLM extraction limits per source.
- Input truncation limits for transcripts/articles.

3. Cost-saving behavior:
- Fresh cache reuse (`prefer_cache`, `cache_max_age_days`).
- Short-circuit in low-cost paths (skip web when YouTube confidence is already high).
- In-memory prompt response cache in the Gemini LLM client.

4. Visibility:
- Research output now includes `chain_spec.meta` with budget and cache metadata.

## Tool Parameters

`research_vocal_chain` supports:
- `budget_mode`: `cheap|balanced|deep`
- `prefer_cache`: `true|false`
- `cache_max_age_days`: integer
- `max_total_llm_calls`: integer

## Recommended Defaults For Development

Use this during routine testing:
- `budget_mode="cheap"`
- `prefer_cache=true`
- `cache_max_age_days=21`
- `max_total_llm_calls=2`
- `max_sources=1`

Use `deep` only for final high-value queries you intend to execute.

## Environment Overrides

Optional env vars:
- `RESEARCH_BUDGET_MODE` (default mode)
- `RESEARCH_INTENT_MODEL`
- `RESEARCH_EXTRACTION_MODEL`
- `RESEARCH_REASONING_MODEL`

## Example Calls

Low-cost iteration:

```python
execute_ableton_function("research_vocal_chain", {
    "query": "Kanye Power vocal chain",
    "budget_mode": "cheap",
    "max_sources": 1,
    "max_total_llm_calls": 2,
    "prefer_cache": True
})
```

Higher quality pass:

```python
execute_ableton_function("research_vocal_chain", {
    "query": "Kanye Power vocal chain",
    "budget_mode": "deep",
    "max_sources": 3,
    "max_total_llm_calls": 10,
    "prefer_cache": True
})
```
