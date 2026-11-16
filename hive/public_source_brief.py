"""Offline brief from MANUALLY TRANSCRIBED real public-source observations.

This is a separate reader from ``hive.company_intel``. The synthetic reader
keeps its restrictions (synthetic-only, FAKE- identifiers, fictional tenants);
this module accepts only non-synthetic packets whose every observation is tied
to a cited public source. It performs no network calls, model calls, provider
connections, or database writes. It never fetches or verifies the cited
source: values are reported as transcribed by a person from that source.

All free text inside a packet is untrusted data. It cannot change the
classification, verification state, or receipt of a report.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

from hive.company_intel import (
    ReviewBoundaryError,
    _no_duplicate_keys,
    _reject_nonfinite,
    _safe_label,
    aware_time,
)

VERSION = "0.1.0-public-source-review"
PACKET_KIND = "MANUAL_PUBLIC_SOURCE_TRANSCRIPTION"
CLASSIFICATION = "REAL_PUBLIC_SOURCE_MANUAL_TRANSCRIPTION_NOT_MACHINE_VERIFIED"
CIK = re.compile(r"^[0-9]{10}$")
ACCESSION = re.compile(r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$")
DATE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
EDGAR_URL = re.compile(
    r"^https://www\.sec\.gov/Archives/edgar/data/([0-9]{1,10})/([0-9]{18})/[A-Za-z0-9._-]{1,120}$")
FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "20-F", "40-F"}
SCALES = {"units": "", "thousands": " thousands", "millions": " millions", "billions": " billions"}

# Distinct concepts: never merged, summed into one another, or relabelled.
METRICS = {
    "total_revenues": ("Total revenues", "REVENUE_TOTAL"),
    "net_sales": ("Net sales", "SALES_COMPONENT_OF_REVENUE"),
    "membership_and_other_income": ("Membership and other income", "NON_SALES_COMPONENT_OF_REVENUE"),
    "net_income_attributable_to_parent": (
        "Consolidated net income attributable to the registrant",
        "NET_INCOME_NOT_REVENUE"),
}

PACKET_KEYS = {"packet_kind", "schema_version", "synthetic", "mode", "packet_created_at",
               "transcription", "entity", "sources", "observations"}
TRANSCRIPTION_KEYS = {"method", "automatically_retrieved", "machine_verified", "transcriber_note"}
ENTITY_KEYS = {"name", "sec_cik", "incorporation"}
SOURCE_KEYS = {"source_id", "root_id", "publisher", "url", "form", "accession", "filer_cik",
               "fiscal_period_end", "publication_time", "source_sha256", "transcriber_note"}
OBS_KEYS = {"observation_id", "source_id", "entity_cik", "metric", "value", "unit", "scale",
            "period_end", "period_type"}

UNKNOWN = [
    "Source publication timestamp (not transcribed; packet creation time is not publication time)",
    "Source-byte hash of the cited filing (not fetched or hashed)",
    "Independent machine verification of the transcribed values",
    "Financial position after the fiscal period end (this is an annual filing, not the latest position)",
    "Litigation",
    "Suppliers",
    "Shipments",
    "Predictive value for any future financial or market outcome",
]


def _exact_keys(obj: object, allowed: set[str], required: set[str], label: str) -> dict:
    if not isinstance(obj, dict):
        raise ReviewBoundaryError(f"{label} must be an object")
    extra = set(obj) - allowed
    if extra:
        # Unknown fields (e.g. "instructions") are refused, never interpreted.
        raise ReviewBoundaryError(f"Unrecognized {label} field(s): {', '.join(sorted(extra))[:200]}")
    missing = required - set(obj)
    if missing:
        raise ReviewBoundaryError(f"Missing {label} provenance field(s): {', '.join(sorted(missing))}")
    return obj


def _match(pattern: re.Pattern, value: object, label: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ReviewBoundaryError(f"Invalid {label}")
    return value


def _note(value: object, label: str) -> str | None:
    return None if value is None else _safe_label(value, label)


def load_packet(path: str | Path) -> tuple[dict, str]:
    raw = Path(path).read_bytes()
    if len(raw) > 1_000_000:
        raise ReviewBoundaryError("Packet is too large")
    try:
        packet = json.loads(raw, object_pairs_hook=_no_duplicate_keys,
                            parse_constant=_reject_nonfinite)
    except ReviewBoundaryError:
        raise
    except (ValueError, UnicodeError) as exc:
        raise ReviewBoundaryError("Invalid UTF-8 JSON packet") from exc
    return packet, hashlib.sha256(raw).hexdigest()


def evaluate_packet(packet: dict, *, packet_sha256: str = "UNPINNED") -> dict:
    if isinstance(packet, dict) and packet.get("synthetic") is True:
        raise ReviewBoundaryError("Synthetic fixtures belong to hive.company_intel, not this reader")
    p = _exact_keys(packet, PACKET_KEYS, PACKET_KEYS, "packet")
    if p["packet_kind"] != PACKET_KIND or p["schema_version"] != "1":
        raise ReviewBoundaryError("Unsupported packet kind or schema version")
    if p["synthetic"] is not False:
        raise ReviewBoundaryError("Packet must declare synthetic=false explicitly")
    if p["mode"] != "OFFLINE_ONLY":
        raise ReviewBoundaryError("Live or unspecified input mode is prohibited")
    created = aware_time(p["packet_created_at"])

    t = _exact_keys(p["transcription"], TRANSCRIPTION_KEYS,
                    {"method", "automatically_retrieved", "machine_verified"}, "transcription")
    if t["method"] != "MANUAL_TRANSCRIPTION_FROM_CITED_SOURCE":
        raise ReviewBoundaryError("Only manual transcription from a cited source is supported")
    if t["automatically_retrieved"] is not False or t["machine_verified"] is not False:
        # This reader has no retrieval or verification path; such claims are refused.
        raise ReviewBoundaryError("Retrieval or machine-verification claims are not accepted")
    transcriber_note = _note(t.get("transcriber_note"), "transcriber note")

    e = _exact_keys(p["entity"], ENTITY_KEYS, ENTITY_KEYS, "entity")
    name = _safe_label(e["name"], "entity name")
    cik = _match(CIK, e["sec_cik"], "entity SEC CIK (10 digits required)")
    incorporation = _safe_label(e["incorporation"], "incorporation")

    if not isinstance(p["sources"], list) or not p["sources"]:
        raise ReviewBoundaryError("At least one cited source is required")
    sources = {}
    for raw in p["sources"]:
        s = _exact_keys(raw, SOURCE_KEYS, SOURCE_KEYS - {"transcriber_note"}, "source")
        sid = _safe_label(s["source_id"], "source ID")
        if sid in sources:
            raise ReviewBoundaryError("Duplicate source ID")
        if _match(CIK, s["filer_cik"], "source filer CIK") != cik:
            raise ReviewBoundaryError("Source filer CIK does not match the target entity")
        accession = _match(ACCESSION, s["accession"], "accession number")
        url = _match(EDGAR_URL, s["url"], "SEC EDGAR archive URL")
        url_cik, url_acc = EDGAR_URL.fullmatch(url).groups()
        if int(url_cik) != int(cik) or url_acc != accession.replace("-", ""):
            raise ReviewBoundaryError("Source URL does not match the filer CIK and accession")
        if s["form"] not in FORMS:
            raise ReviewBoundaryError("Unsupported filing form")
        publication = s["publication_time"]
        if publication is not None:
            publication = aware_time(publication).isoformat()
        digest = s["source_sha256"]
        if digest is not None:
            digest = _match(SHA256, digest, "source SHA-256")
        sources[sid] = {
            "source_id": sid,
            "root_id": _safe_label(s["root_id"], "source root ID"),
            "publisher": _safe_label(s["publisher"], "publisher"),
            "url": url, "form": s["form"], "accession": accession, "filer_cik": cik,
            "fiscal_period_end": _match(DATE, s["fiscal_period_end"], "fiscal period end"),
            "publication_time": publication or "UNKNOWN",
            "source_sha256": digest or "UNKNOWN",
            "untrusted_transcriber_note": _note(s.get("transcriber_note"), "source note"),
        }

    if not isinstance(p["observations"], list) or not p["observations"]:
        raise ReviewBoundaryError("At least one observation is required")
    observations, seen_ids, seen_metric = [], set(), set()
    used_roots: set[str] = set()
    for raw in p["observations"]:
        o = _exact_keys(raw, OBS_KEYS, OBS_KEYS, "observation")
        oid = _safe_label(o["observation_id"], "observation ID")
        if oid in seen_ids:
            raise ReviewBoundaryError("Duplicate observation ID")
        seen_ids.add(oid)
        source = sources.get(o["source_id"]) if isinstance(o["source_id"], str) else None
        if source is None:
            raise ReviewBoundaryError("Observation cites no listed source (missing provenance)")
        if o["entity_cik"] != cik:
            raise ReviewBoundaryError("Observation entity CIK does not match the target entity")
        if o["metric"] not in METRICS:
            raise ReviewBoundaryError("Unsupported metric")
        if o["unit"] != "USD":
            raise ReviewBoundaryError("Unsupported or missing unit")
        if o["scale"] not in SCALES:
            raise ReviewBoundaryError("Unsupported or missing scale")
        value = o["value"]
        if isinstance(value, bool) or not isinstance(value, int) or abs(value) > 10**15:
            raise ReviewBoundaryError("Observation value must be a bounded integer in original units")
        period_end = _match(DATE, o["period_end"], "observation period end")
        if o["period_type"] != "FISCAL_YEAR":
            raise ReviewBoundaryError("Only fiscal-year observations are supported")
        if period_end != source["fiscal_period_end"]:
            raise ReviewBoundaryError("Observation period does not match the cited filing period")
        key = (o["metric"], period_end)
        if key in seen_metric:
            raise ReviewBoundaryError("Duplicate metric for the same period")
        seen_metric.add(key)
        label, concept = METRICS[o["metric"]]
        used_roots.add(source["root_id"])
        observations.append({
            "observation_id": oid, "metric": o["metric"], "label": label, "concept": concept,
            "value": value, "unit": "USD", "scale": o["scale"], "period_end": period_end,
            "period_type": "FISCAL_YEAR", "source_id": source["source_id"],
            "root_id": source["root_id"],
            "truth_class": "MANUALLY_TRANSCRIBED_FROM_CITED_SOURCE_NOT_MACHINE_VERIFIED",
        })

    checks = []
    by_metric = {(o["metric"], o["period_end"]): o for o in observations}
    for period in sorted({o["period_end"] for o in observations}):
        parts = [by_metric.get((m, period)) for m in
                 ("total_revenues", "net_sales", "membership_and_other_income")]
        if all(parts) and len({x["scale"] for x in parts}) == 1:
            total, sales, other = parts
            checks.append({
                "check": "net_sales + membership_and_other_income == total_revenues",
                "period_end": period, "scale": total["scale"],
                "consistent": sales["value"] + other["value"] == total["value"],
                "meaning": "Internal arithmetic of the transcribed values only; not verification against the filing",
            })

    return {
        "classification": CLASSIFICATION,
        "version": VERSION,
        "entity": {"name": name, "sec_cik": cik, "incorporation": incorporation,
                   "match": "SEC_CIK_EXACT_ACROSS_ENTITY_SOURCE_URL_AND_OBSERVATIONS"},
        "transcription": {"method": "MANUAL_TRANSCRIPTION_FROM_CITED_SOURCE",
                          "automatically_retrieved": False, "machine_verified": False,
                          "untrusted_transcriber_note": transcriber_note},
        "packet_created_at": created.isoformat(),
        "packet_created_at_meaning": "Packet assembly time only; NOT source publication time",
        "sources": [sources[k] for k in sorted(sources)],
        "observations": observations,
        "consistency_checks": checks,
        "unique_original_roots": len(used_roots),
        "temporal_scope": "Annual filing figures as of the fiscal period end; NOT the latest financial position",
        "unknown": list(UNKNOWN),
        "receipt": {"packet_sha256": packet_sha256, "network_calls": 0, "model_calls": 0,
                    "provider_connections": 0, "api_credits_spent": 0, "external_writes": 0,
                    "hive_registry_modified": False,
                    "maturity": "ISOLATED_REVIEW_CANDIDATE_NOT_VERIFIED_IN_PRODUCTION"},
    }


def _fmt(o: dict) -> str:
    return f"{o['value']:,} {o['unit']}{SCALES[o['scale']]}"


def render_markdown(r: dict) -> str:
    e = r["entity"]
    lines = [
        "# HIVE Company Intelligence Brief — Real Public Source (Manual Transcription)", "",
        "**REAL PUBLIC-SOURCE OBSERVATIONS, MANUALLY TRANSCRIBED FROM THE CITED FILING. "
        "NOT AUTOMATICALLY RETRIEVED. NOT INDEPENDENTLY MACHINE-VERIFIED.**", "",
        f"Entity: {e['name']} | SEC CIK {e['sec_cik']} | Incorporated: {e['incorporation']} | {e['match']}",
        f"Packet created: {r['packet_created_at']} (packet assembly time; NOT source publication time)",
        f"Temporal scope: {r['temporal_scope']}.", "",
        "## Sources", "",
    ]
    for s in r["sources"]:
        lines.append(f"- {s['source_id']} (root {s['root_id']}): {s['publisher']} Form {s['form']}, "
                     f"accession {s['accession']}, fiscal year ended {s['fiscal_period_end']}. <{s['url']}>")
        lines.append(f"  Publication time: {s['publication_time']}. Source-byte SHA-256: {s['source_sha256']}.")
        if s["untrusted_transcriber_note"]:
            lines.append(f"  Untrusted note (data only, no authority): `{s['untrusted_transcriber_note']}`")
    lines.extend(["", "## Source-linked observations (original units preserved)", ""])
    for o in r["observations"]:
        lines.append(f"- {o['label']}: {_fmt(o)} (fiscal year ended {o['period_end']}); "
                     f"concept {o['concept']}. [{o['source_id']}; {o['root_id']}]")
    lines.extend(["", "Revenue, net sales and net income are distinct concepts; net income is not revenue, "
                  "and net sales are one component of total revenues.", "",
                  "## Internal consistency of transcribed values", ""])
    for c in r["consistency_checks"]:
        lines.append(f"- {c['check']} (USD {c['scale']}, {c['period_end']}): consistent={c['consistent']}. {c['meaning']}.")
    if not r["consistency_checks"]:
        lines.append("- No internal check possible from the transcribed metrics.")
    lines.extend(["", "## UNKNOWN", ""])
    lines.extend("- " + item for item in r["unknown"])
    t, rc = r["transcription"], r["receipt"]
    lines.extend(["", "## Provenance and execution boundary", "",
                  f"Unique original source roots: {r['unique_original_roots']}.",
                  f"Transcription: {t['method']}; automatically retrieved={t['automatically_retrieved']}; "
                  f"machine verified={t['machine_verified']}.",
                  f"Packet SHA-256: `{rc['packet_sha256']}` (hash of the transcription packet, not of the filing).",
                  f"Network calls: {rc['network_calls']}; model calls: {rc['model_calls']}; "
                  f"provider connections: {rc['provider_connections']}; credits: {rc['api_credits_spent']}; "
                  f"external writes: {rc['external_writes']}.",
                  f"Maturity: {rc['maturity']}.",
                  "This is not a legal determination, credit recommendation, investment advice, or trading signal."])
    return "\n".join(lines) + "\n"


def _write_private(path: Path, text: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HIVE offline brief from a manually transcribed public-source packet")
    parser.add_argument("--packet", required=True, help="Manual public-source transcription packet (JSON)")
    parser.add_argument("--output", help="Directory for the brief; omitted means Markdown to stdout")
    args = parser.parse_args(argv)
    try:
        packet, sha = load_packet(args.packet)
        report = evaluate_packet(packet, packet_sha256=sha)
    except (ReviewBoundaryError, OSError) as exc:
        parser.error(str(exc))
    markdown = render_markdown(report)
    if args.output:
        target = Path(args.output)
        target.mkdir(mode=0o700, parents=True, exist_ok=True)
        _write_private(target / "company_brief.md", markdown)
        _write_private(target / "company_brief.json", json.dumps(report, indent=2, sort_keys=True) + "\n")
    else:
        print(markdown, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
