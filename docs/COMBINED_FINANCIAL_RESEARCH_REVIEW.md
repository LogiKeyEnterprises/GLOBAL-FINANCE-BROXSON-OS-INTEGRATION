# Combined HIVE × BROXSON financial research review

Date: 2026-11-15. Status: IMPLEMENTED ON REVIEW BRANCH / LOCALLY TESTED.
Not merged, deployed, commercially licensed, independently verified, or accepted by BROXSON.

## Start here
Read [the existing full integration brief](../GLOBAL_FINANCE_START_HERE.md) for the mission, seven candidate providers, system roles, C01–C14 acceptance scenarios, research stages, and source/data gates. That original proposal is preserved unchanged; its historical "not implemented" statements describe its preparation baseline. This receipt updates only the isolated candidates listed below.

## Combined sources
| Material | Pinned source | Treatment |
| --- | --- | --- |
| Existing HIVE, inspector, tests and integration brief | main 923c339902b23ae015ef1e42b9fbab957ffd0d86 | All existing bytes preserved, including the public proposal ZIP |
| Company Intelligence S1 | PR #1, 1ab79660d6be89b7d6fa7666e124ebc06367f465 | Four additive files copied unchanged |
| Historical admissibility validator | PR #2, e1b84de7ad87c6ca908fb8d0d844c27d341ce52d | Three additive files copied unchanged |
| Newer financial as-of V2 | Separate private HIVE PR #4 | Remains private; not copied or tested in this public fork |

Original PRs #1 and #2 remain intact. Their receipts are historical evidence, not overwritten test results.

## What is combined
- hive/company_intel.py and fictional fixtures/cedar_arc.json: source-linked fictional company brief, source distinctions, exclusions and simulated provider errors.
- hive/financial_history.py: assess(record, cutoff) and validate_snapshot(records, cutoff), checking supplied timing, identity assertions, revisions and research-rights labels.
- Both sets of tests alongside original HIVE core/inspector regression tests.
- Existing research architecture and acceptance criteria linked above.

This is one reviewable tree, not a new unified API. The modules retain distinct contracts. Company brief output is NOT automatically fed into the historical validator; there is no implicit schema conversion. The historical validator retains distinct revisions; it does not select a unique latest vintage. Do not combine their eligibility counts or treat them as interchangeable. Future adapter work needs explicit tests and a demonstrated need.

## Current reproducible receipt
From the combined repository root, with pytest available:
```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. python -m pytest -q
```
Observed locally: **38 passed** (8 original + 18 company-intelligence + 12 financial-history), 2026-11-15. Test dependencies installed in an isolated temporary directory; runtime dependencies unchanged. No provider requests, production records, financial operations, or remote CI execution were involved. This tests coexistence and individual contracts, not an end-to-end live pipeline.

## Separate private V2 candidate
The owner supplied a report of 37 local tests for a later private as-of validator. That count is REPORTED, not rerun here and NOT part of 38. It addresses a related contract (including vintage selection) and must be compared before building another overlapping validator. Its source remains outside this public fork. Private source, research documents, IP negotiations and archives are not imported.

## Governing experiment and blockers
[Phase Zero tracker](https://github.com/LogiKeyEnterprises/ai-network-os/issues/13): whether historically eligible importer shipment activity improves next-quarter reported inventory-growth forecasts against lagged fundamentals/seasonality. This remains a proposed experiment, not a result.
- Lawful historical shipment data and reuse rights: BLOCKED / not established here.
- Independent issuer-to-importer mappings and first-publication receipts: UNKNOWN.
- Predictive improvement, profitability, real-data validity: UNKNOWN / not tested.
- Tony's unpublished laptop build: compatibility UNKNOWN.
- Earlier standalone S1 archive reconciliation: unresolved; the existing public proposal ZIP contains a brief and description, not that source package.
- Commercial derivative authorization: not established; proprietary upstream declaration preserved.
- Independent review, exact-head CI and BROXSON acceptance: pending.

Input fields claiming approved rights or verified identity are assertions only. Passing synthetic tests cannot authenticate legal rights, identity or real historical publication.

## Next gate
Review this exact combined tree and compare the separate private V2 contract in its authorized location. Obtain lawful data, identity/time evidence and applicable written rights before the inventory-growth experiment or commercial use. No additional infrastructure or live providers are needed for this review.
