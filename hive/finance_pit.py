"""Offline point-in-time eligibility check for proposed financial observations.

No network, database, subprocess, financial order, or model execution. A passing
result means structurally eligible for *human research review*, not proof of
provider rights, source authenticity, issuer identity, or predictive performance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "finance-pit.v1"
MAX_INPUT_BYTES = 2_000_000
ALLOWED_UNITS = frozenset({"shipment_count", "kg", "TEU", "customs_declared_usd"})
REQUIRED_FIELDS = frozenset({
    "source_id", "source_root_id", "record_id", "provider", "source_locator",
    "source_sha256", "issuer_cik", "importer_id", "mapping_proof", "event_date",
    "first_publication_time", "available_as_of", "revision_id",
    "revision_published_at", "retrieved_at", "usage_rights", "units", "value",
    "synthetic",
})
SOURCE_POLICY_FIELDS = frozenset({
    "source_root_id", "usage_rights", "rights_evidence_locator", "synthetic",
})
IDENTITY_POLICY_FIELDS = frozenset({"issuer_cik", "importer_id", "mapping_proof"})


class ValidationInputError(ValueError):
    """Unusable envelope or policy; no observation may be accepted."""


def _iso_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def _required_text(value: Any) -> bool:
    return isinstance(value, str) and 0 < len(value.strip()) <= 1024


def _clean_policy(policy: Any) -> tuple[dict[str, Mapping[str, Any]], set[tuple[str, str, str]]]:
    if not isinstance(policy, dict) or set(policy) != {"source_approvals", "identity_approvals"}:
        raise ValidationInputError("Policy requires only source_approvals and identity_approvals")
    sources = policy["source_approvals"]
    identities = policy["identity_approvals"]
    if not isinstance(sources, list) or not isinstance(identities, list):
        raise ValidationInputError("Policy approvals must be lists")

    source_map: dict[str, Mapping[str, Any]] = {}
    for item in sources:
        if not isinstance(item, dict) or set(item) != SOURCE_POLICY_FIELDS:
            raise ValidationInputError("Invalid source-approval schema")
        if not all(_required_text(item[name]) for name in (
            "source_root_id", "usage_rights", "rights_evidence_locator"
        )) or type(item["synthetic"]) is not bool:
            raise ValidationInputError("Invalid source-approval value")
        if item["usage_rights"] != "research_permitted":
            raise ValidationInputError("Policy cannot approve unknown or restricted rights")
        source_id = item["source_root_id"]
        if source_id in source_map:
            raise ValidationInputError("Duplicate source-approval identity")
        source_map[source_id] = item

    verified: set[tuple[str, str, str]] = set()
    for item in identities:
        if not isinstance(item, dict) or set(item) != IDENTITY_POLICY_FIELDS:
            raise ValidationInputError("Invalid identity-approval schema")
        if not all(_required_text(item[k]) for k in IDENTITY_POLICY_FIELDS):
            raise ValidationInputError("Invalid identity-approval value")
        if not re.fullmatch(r"[0-9]{10}", item["issuer_cik"]):
            raise ValidationInputError("Issuer CIK must be exactly ten digits")
        key = (item["issuer_cik"], item["importer_id"], item["mapping_proof"])
        if key in verified:
            raise ValidationInputError("Duplicate identity approval")
        verified.add(key)
    return source_map, verified


def _value_valid(value: Any) -> bool:
    # Do not round binary floats or accept bool as a financial measurement.
    if type(value) not in (int, str):
        return False
    if isinstance(value, str) and (not value.strip() or len(value) > 64):
        return False
    try:
        number = Decimal(value)
        return number.is_finite() and number >= 0
    except (InvalidOperation, ValueError):
        return False


def _record_fingerprint(value: Any) -> str:
    # Hash *submitted* normalized JSON, not purported original provider bytes.
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=True, default=str,
                         separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_batch(envelope: Any, policy: Any) -> dict[str, Any]:
    """Evaluate a user-supplied batch with a separate, explicit local policy.

    Never accepts source text as commands, never performs I/O, never certifies
    the accuracy of the caller-supplied license/mapping evidence.
    """
    sources, identities = _clean_policy(policy)
    if not isinstance(envelope, dict) or set(envelope) != {"prediction_cutoff", "observations"}:
        raise ValidationInputError("Envelope requires only prediction_cutoff and observations")
    cutoff = _iso_time(envelope["prediction_cutoff"])
    if cutoff is None:
        raise ValidationInputError("prediction_cutoff must be timezone-aware ISO 8601")
    records = envelope["observations"]
    if not isinstance(records, list) or not records or len(records) > 10000:
        raise ValidationInputError("observations must contain 1 to 10,000 records")

    results: list[dict[str, Any]] = []
    seen_versions: set[tuple[str, str, str]] = set()
    selected: dict[tuple[str, str], tuple[datetime, int]] = {}
    all_synthetic = True

    for index, record in enumerate(records):
        reasons: set[str] = set()
        digest = _record_fingerprint(record)
        result = {"index": index, "submitted_sha256": digest,
                  "eligible": False, "selected_at_cutoff": False, "reasons": []}
        if not isinstance(record, dict):
            reasons.add("NOT_AN_OBJECT")
        else:
            missing = REQUIRED_FIELDS - set(record)
            unexpected = set(record) - REQUIRED_FIELDS
            if missing:
                reasons.add("MISSING_FIELDS")
            if unexpected:
                reasons.add("UNEXPECTED_FIELDS")  # e.g. injected operator instructions
            for field in REQUIRED_FIELDS - {"value", "synthetic"}:
                if field in record and not _required_text(record[field]):
                    reasons.add("INVALID_FIELD_TYPE")
            if "synthetic" in record:
                if type(record["synthetic"]) is not bool:
                    reasons.add("INVALID_FIELD_TYPE")
                elif not record["synthetic"]:
                    all_synthetic = False
            if "value" in record and not _value_valid(record["value"]):
                reasons.add("INVALID_VALUE")
            if "source_sha256" in record and (not isinstance(record["source_sha256"], str)
                or re.fullmatch(r"[0-9a-fA-F]{64}", record["source_sha256"]) is None):
                reasons.add("INVALID_SOURCE_HASH")
            if "issuer_cik" in record and (not isinstance(record["issuer_cik"], str)
                or re.fullmatch(r"[0-9]{10}", record["issuer_cik"]) is None):
                reasons.add("INVALID_CIK")
            if "units" in record and (not isinstance(record["units"], str)
                or record["units"] not in ALLOWED_UNITS):
                reasons.add("UNSUPPORTED_UNITS")
            if record.get("usage_rights") != "research_permitted":
                reasons.add("USAGE_RIGHTS_UNCONFIRMED")

            source = sources.get(record.get("source_root_id")) if isinstance(record.get("source_root_id"), str) else None
            if source is None:
                reasons.add("SOURCE_NOT_APPROVED")
            elif source["synthetic"] != record.get("synthetic"):
                reasons.add("SOURCE_CLASS_MISMATCH")
            if not all(isinstance(record.get(name), str) for name in (
                "issuer_cik", "importer_id", "mapping_proof")) or (
                record.get("issuer_cik"), record.get("importer_id"),
                record.get("mapping_proof")) not in identities:
                reasons.add("IDENTITY_NOT_APPROVED")

            times = {key: _iso_time(record.get(key)) for key in (
                "first_publication_time", "available_as_of", "revision_published_at", "retrieved_at"
            )}
            if any(t is None for t in times.values()):
                reasons.add("MISSING_OR_INVALID_TIMESTAMP")
            else:
                first = times["first_publication_time"]
                revision = times["revision_published_at"]
                available = times["available_as_of"]
                retrieved = times["retrieved_at"]
                if first > cutoff:
                    reasons.add("PUBLISHED_AFTER_CUTOFF")
                if revision > cutoff:
                    reasons.add("REVISION_AFTER_CUTOFF")
                if available > cutoff:
                    reasons.add("AVAILABLE_AFTER_CUTOFF")
                if revision < first:
                    reasons.add("REVISION_BEFORE_INITIAL_PUBLICATION")
                if available < max(first, revision):
                    reasons.add("AVAILABLE_BEFORE_PUBLICATION")
                if retrieved < max(first, revision):
                    reasons.add("RETRIEVED_BEFORE_PUBLICATION")
                try:
                    event = date.fromisoformat(record["event_date"])
                    if event > first.date():
                        reasons.add("EVENT_AFTER_PUBLICATION")
                except (TypeError, ValueError, KeyError):
                    reasons.add("INVALID_EVENT_DATE")

            id_fields = (record.get("source_root_id"), record.get("record_id"), record.get("revision_id"))
            if all(isinstance(v, str) and v for v in id_fields):
                if id_fields in seen_versions:
                    reasons.add("DUPLICATE_REVISION")
                seen_versions.add(id_fields)
            if not reasons:
                result["eligible"] = True
                key = (record["source_root_id"], record["record_id"])
                current = selected.get(key)
                if current is None or times["revision_published_at"] > current[0]:
                    selected[key] = (times["revision_published_at"], index)
        result["reasons"] = sorted(reasons)
        results.append(result)

    selected_indices = sorted(index for _, index in selected.values())
    for index in selected_indices:
        results[index]["selected_at_cutoff"] = True
    blocked = any(not r["eligible"] for r in results)
    return {
        "schema_version": SCHEMA_VERSION,
        "prediction_cutoff_utc": cutoff.isoformat(),
        "status": "BLOCKED" if blocked else "ELIGIBLE_FOR_HUMAN_REVIEW",
        "record_count": len(results),
        "blocked_count": sum(not r["eligible"] for r in results),
        "selected_indices": selected_indices,
        "all_synthetic": all_synthetic,
        "predictive_value": "UNKNOWN",
        "modeling_authorized": False,
        "trading_authorized": False,
        "rights_and_identity_independently_verified": False,
        "records": results,
    }


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ValidationInputError("Duplicate JSON key")
        obj[key] = value
    return obj


def _load_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_INPUT_BYTES:
        raise ValidationInputError("Input must be an ordinary file of at most 2 MB")
    raw = path.read_bytes()
    if len(raw) > MAX_INPUT_BYTES:
        raise ValidationInputError("Input exceeds 2 MB")
    return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_keys,
                      parse_constant=lambda _: (_ for _ in ()).throw(
                          ValidationInputError("Non-finite JSON number")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline financial point-in-time eligibility check")
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = validate_batch(_load_json(args.observations), _load_json(args.policy))
    except (ValidationInputError, OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"schema_version": SCHEMA_VERSION, "status": "BLOCKED",
                          "error": str(exc), "modeling_authorized": False,
                          "trading_authorized": False}, sort_keys=True))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "ELIGIBLE_FOR_HUMAN_REVIEW" else 2


if __name__ == "__main__":
    sys.exit(main())
