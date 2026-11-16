# Real Public-Source Brief (Manual Transcription) — Review Candidate

`hive.public_source_brief` builds an offline Markdown/JSON brief from a packet of
**real public-source observations manually transcribed by a person** from a cited
SEC EDGAR filing. It is a separate reader from the synthetic `hive.company_intel`,
whose restrictions are unchanged (each reader rejects the other's input).

Packets live in `public_sources/`, not `fixtures/`, so real observations are never
presented as fictional fixtures.

Worked example: [Walmart FY2026 public-source case](cases/WALMART_PUBLIC_SOURCE_CASE.md).

## What it enforces
- `synthetic: false`, `mode: OFFLINE_ONLY`, method `MANUAL_TRANSCRIPTION_FROM_CITED_SOURCE`;
  `automatically_retrieved` and `machine_verified` must be `false` (no self-promotion).
- Exact 10-digit SEC CIK matching across entity, source filer, EDGAR URL path and
  every observation; URL accession must equal the stated accession.
- Explicit `unit` (USD) and `scale`; values kept in original units and never converted.
  Revenue, sales, non-sales revenue and net income are distinct, fixed concepts.
- Every observation must cite a listed source with full provenance fields; the
  observation period must equal the filing's fiscal period end.
- Unique original roots are counted only over sources actually cited.
- Unknown fields are refused; free-text notes are bounded, markup-free, and rendered
  as untrusted data with no effect on classification or receipt.
- `publication_time` / `source_sha256` may be `null` and are then reported `UNKNOWN`.
  `packet_created_at` is assembly time, never publication time.

## What it does not do
No network, model, provider or database access. It does not fetch, hash or verify the
cited filing; an internal arithmetic check covers only the transcribed numbers.
An annual filing is not presented as the latest financial position.

```bash
PYTHONPATH=. .venv/bin/python -m hive.public_source_brief \
  --packet public_sources/walmart_10k_fy2026_manual.json --output <private-dir>
```
