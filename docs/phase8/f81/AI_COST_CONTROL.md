# AI cost control

Each conversation turn creates an `AiUsageRecord` with `feature_id=ai.addon.voice_calling`.

Organisation settings:

- `monthly_call_limit`
- `monthly_minutes_limit` (reserved for future duration rollup)

Hard rejection returns HTTP 429 when monthly call count exceeded.

Shares existing F3.3 budget dashboards when configured.
