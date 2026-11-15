# Combined financial intelligence review — V3 reconciliation

Date: 2026-11-15. Research-only draft; no production acceptance or commercial license established.

## Pinned inputs
- Existing fork main: 923c339902b23ae015ef1e42b9fbab957ffd0d86. Original HIVE files, attribution, proposal brief and ZIP preserved unchanged.
- PR #1: 9102f5f (full SHA recorded in Git history). Includes hardened S1, 44-test forecast/placebo replay, temporal evidence graph, fixtures, receipts and local verification script.
- PR #2: 1a69660 (full SHA recorded in Git history). Includes historical validator and revision-aware replay extension.
- Earlier combined review: dc1d3a626c2ba47b62d85e1adf2f8e8a84ad05f7, historical 38-test receipt.
- Private HIVE V2 PR #4 remains private; no code imported. Its reported 37 tests are not in the combined count.

## Naming conflict resolved without dropping either engine
Both source PRs used hive/financial_replay.py and tests/test_financial_replay.py for incompatible contracts.
- PR #1 forecast/holdout/placebo implementation retains financial_replay.py and its tests/fixture.
- PR #2 revision selector is preserved byte-for-byte as hive/financial_revision_replay.py. Its tests are tests/test_financial_revision_replay.py; only the import is changed to the new name.
- The original financial_history.assess/validate_snapshot APIs remain baseline per-row checks. Their eligible count includes separate revisions and MUST NOT be used as a deduplicated feature count. Use financial_revision_replay.replay_as_of and selected_observations for that contract.
- The revision selector and forecast engine retain different fixture schemas. No automatic adapter, interchangeability, or end-to-end real-data pipeline is claimed.
- Existing PR #2 documentation mentions its original financial_replay.py name; interpret those historical paths using the mapping above. Original receipts remain historical, not current verification.

## Verification
Combined local run: 185 tests passed. Original HIVE regressions, hardened company intelligence, both replay implementations, and temporal graph tests run together. Reproduce with pytest available:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. python -m pytest -q tests
bash scripts/verify_offline_review.sh
```
The verification script now discovers all tests and checks fictional graph/delta receipts. The 44 and 56 previously reported test counts overlap with suites in this tree; do not add historical receipts together. This 185-test count excludes private V2.

## Research findings and limits
The fictional forecast example reports PLACEBO_COMPETITIVE: a meaningless comparison nearly matches the planted candidate signal. The apparent 76.4% improvement is manufactured, not investment evidence. Source hashes check byte integrity, not semantic entailment, actual public availability, legal permissions or authenticated company identity.

The existing GLOBAL_FINANCE_START_HERE.md remains the full mission, provider-candidate list, system roles, staged acceptance and research design. Governing experiment: AI Network OS issue #13, historical shipment features versus lagged fundamentals/seasonality for next-quarter reported inventory growth. No forecasting advantage established.

## Unresolved gates
Lawfully reusable historical shipment data, independent issuer mappings, publication-time receipts and commercial derivative rights remain BLOCKED/UNKNOWN. Tony's unpublished laptop implementation, independent review, hosted CI and BROXSON acceptance remain unverified. Earlier S1 standalone archive reconciliation remains unresolved. No merge, deployment, live provider calls, spending, scraping, trading, rights transfer or integration with private governance systems is authorized by this test.

Next action: independent review of the exact combined commit and one lawful historical dataset. Stop architecture expansion while those gates remain blocked.
