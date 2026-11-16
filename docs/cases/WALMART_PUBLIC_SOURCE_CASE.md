# Case: Walmart FY2026 — Revenue to Net Income (Manual Public Source)

**Status:** REVIEW CANDIDATE. One real public filing, manually transcribed, processed offline.
Not automatically retrieved, not machine-verified against the filing, not production.

## 1. Practical question

How much of Walmart's fiscal 2026 revenue became net income attributable to Walmart?

## 2. Exact source and identity

| Field | Value |
| --- | --- |
| Entity | Walmart Inc. (incorporated in Delaware) |
| SEC CIK | `0000104169` |
| Filing | Form 10-K |
| Accession | `0000104169-26-000055` |
| Source URL | <https://www.sec.gov/Archives/edgar/data/104169/000010416926000055/wmt-20260131.htm> |
| Fiscal period | Fiscal year ended 2026-01-31 (`FISCAL_YEAR`) |
| Original units | USD, scale `millions` (values kept as stated in the filing; not converted) |
| Publication time | UNKNOWN (not transcribed) |
| Filing byte hash | UNKNOWN (filing was not fetched or hashed) |

The reader requires the same 10-digit CIK on the entity, the source filer, the EDGAR URL
path and every observation. It also requires the URL accession to equal the stated accession.

## 3. Recorded, calculated, interpreted

These three layers are kept separate on purpose.

### 3a. Recorded manual observations (transcribed by a person from the cited 10-K)

Packet: [`public_sources/walmart_10k_fy2026_manual.json`](../../public_sources/walmart_10k_fy2026_manual.json)

| ID | Metric | Concept | Value (USD millions) |
| --- | --- | --- | --- |
| OBS-01 | Total revenues | `REVENUE_TOTAL` | 713,163 |
| OBS-02 | Net sales | `SALES_COMPONENT_OF_REVENUE` | 706,413 |
| OBS-03 | Membership and other income | `NON_SALES_COMPONENT_OF_REVENUE` | 6,750 |
| OBS-04 | Consolidated net income attributable to Walmart | `NET_INCOME_NOT_REVENUE` | 21,893 |

All four have truth class `MANUALLY_TRANSCRIBED_FROM_CITED_SOURCE_NOT_MACHINE_VERIFIED`.

### 3b. Calculated results (arithmetic on the recorded values only)

- **Internal consistency (computed by the reader):** 706,413 + 6,750 = 713,163 → `consistent=True`.
  This checks only that the transcribed numbers agree with each other. It is not a check
  against the filing.
- **Answer to the question (computed for this case document, not emitted by the reader):**

  ```
  21,893 / 713,163 × 100 ≈ 3.07%
  ```

  (3.0698…, rounded to two decimals.) Numerator and denominator have the same unit,
  scale and fiscal period, and come from the same source.

### 3c. Interpretation (bounded)

On the transcribed figures, about **3 cents of each revenue dollar** in fiscal 2026 ended up
as net income attributable to Walmart. This describes one completed fiscal year only.
It does not describe Walmart's current position or later periods, and it is not a forecast
or an investment view. The ratio uses net income *attributable to Walmart* (it excludes
noncontrolling interests), so it is not the same as a ratio based on consolidated net income.

## 4. Source roots and hashes

- **Unique original source roots: 1** (`ROOT-SEC-EDGAR-0000104169-26-000055`). All four
  observations come from this single filing; they are not independent corroboration of
  each other.
- **Packet SHA-256:** `079385de97546688c6c3bc016e86a4fe8c4fa444afa15d2ebc1354816e60cb7f`.
  This is the hash of the **transcription packet** in this repository. **It is not the hash
  of the SEC filing**, which was never downloaded or hashed (`source_sha256: UNKNOWN`).

## 5. Report produced

The operator ran the reader locally. It wrote `company_brief.md` and `company_brief.json`
to a private, operator-only directory outside the repository (directory mode `0700`,
files `0600`). The generated report is **not published** in this repository; its
machine-specific location is recorded only in a local receipt.

Before this case was written, the reader was run again at the fix commit below. It produced
byte-identical output to the existing local report:

| File | SHA-256 |
| --- | --- |
| `company_brief.md` | `b89c9548599c80341de0273f7bf4082968258f16b55f2b13c154192a2d64b434` |
| `company_brief.json` | `53b0083861e81ccedf85b21c379b59997c9956b801d3d267aa078bfc71cf932c` |

To reproduce from a checkout (portable; choose any private output directory):

```bash
PYTHONPATH=. python -m hive.public_source_brief \
  --packet public_sources/walmart_10k_fy2026_manual.json \
  --output "$(mktemp -d)"
```

Omit `--output` to print the Markdown brief to stdout. Hashes should match on the same
packet and code. This was observed on one machine, not across platforms.

## 6. Commits

| Purpose | Commit |
| --- | --- |
| Implementation, example packet, tests, docs | `33b40e195166e7bcef816843f6448d84f39dee95` — Add offline real-public-source company brief |
| Fix: non-string `form`/`metric`/`unit`/`scale` give a validation error, not a `TypeError` | `2934ba3a23dc7c58b02fb1ea91666ff2ba3fe8ef` — Reject non-string form, metric, unit and scale with a validation error |

## 7. Test evidence (origin and limits)

| Run | Result | Origin |
| --- | --- | --- |
| `tests/test_public_source_brief.py` | 70 passed | Local operator machine, Python 3.14.4, working tree equal to the fix commit |
| Full repository suite (`pytest -q`) | 311 passed | Same machine and tree |
| New malformed-input tests with the fix reverted | 9 failed, 3 passed (the 3 `unit` cases did not crash before the fix either) | Same machine; confirms the regression tests detect the bug |

Limits:
- These are **local runs by the developer**. They are not independent verification and were
  not reproduced by a second party.
- **No hosted CI result is claimed by this document.** Any CI run on the pull request is
  separate evidence and should be read there.
- The tests check the reader's behavior: identity matching, units, provenance, malformed and
  untrusted input, determinism and no network use. They do **not** check that the four values
  match the filing.

## 8. What worked

- Real public-filing figures went through the reader without loosening the synthetic reader's
  boundaries. Each reader rejects the other's input.
- Identity, units, period and provenance were enforced exactly. Revenue, sales, non-sales
  revenue and net income stayed separate concepts.
- Unknowns (publication time, filing hash) stayed `UNKNOWN` instead of being filled in.
  Packet creation time was not presented as publication time.
- The output was deterministic and private, with zero network, model or provider calls.
- A malformed-input crash found during review was fixed with focused regression tests.

## 9. Remaining UNKNOWNs

- Filing publication timestamp.
- Byte hash of the filed 10-K.
- Independent, machine-checked confirmation that the four values match the filing.
- Walmart's financial position after 2026-01-31.
- Litigation, suppliers and shipments (out of scope for this packet).
- Predictive value for any future financial or market outcome.

## 10. Smallest useful follow-up

Have a second person independently re-read the four values (and the filing's acceptance
timestamp) from the cited 10-K and record agreement or differences. If retrieving the filing
is separately approved, hashing the exact filing bytes would replace `source_sha256: UNKNOWN`.
Neither step needs new infrastructure.

## 11. Explicit limits

- **Manual public-source input only.** A person transcribed the values; HIVE did not fetch them.
- **No automated source verification.** Nothing checks the values against the filing.
- **No live providers.** No network, API, model, provider or database access.
- **No forecasting.** One historical ratio; no prediction, signal or advice.
- **No production or recurring verification.** This is a single offline review candidate,
  not a scheduled, monitored or production process.

This is not a legal determination, credit recommendation, investment advice or trading signal.
