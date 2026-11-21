from decimal import Decimal
from typing import Any, Dict, List, Optional


def create_disagreement(
    reason: str,
    record_id: str,
    location: str,
    a_value: Optional[Decimal] = None,
    b_value: Optional[Decimal] = None,
    details: Optional[str] = None,
    entry_id: Optional[str] = None,
) -> Dict[str, Any]:
    difference = None
    if a_value is not None and b_value is not None:
        difference = abs(a_value - b_value)

    return {
        "reason": reason,
        "record_id": record_id,
        "location": location,
        "a_value": a_value,
        "b_value": b_value,
        "difference": difference,
        "details": details or "",
        "entry_id": entry_id,
    }


def compare(
    a_rows: Dict[str, Dict[str, Any]],
    b_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Compare records from System A with entries from System B.

    a_rows: dict mapping record_id -> {
        'total': Decimal,
        'location': str,
        'date': str or date,
        'state': str (optional),
    }
    b_rows: list of dicts with keys: {
        'entry_id': str,
        'ref': str (already normalized),
        'value': Decimal or None,
        'location': str,
        'date': str or date,
    }
    """
    disagreements = []
    by_ref: Dict[str, List[Dict[str, Any]]] = {}

    for e in b_rows:
        ref = e.get("ref")
        by_ref.setdefault(ref, []).append(e)

    # 1. ORPHAN_IN_B: A B entry points at a record that is not in A
    for ref, entries in by_ref.items():
        if not ref or ref not in a_rows:
            for e in entries:
                disagreements.append(
                    create_disagreement(
                        reason="ORPHAN_IN_B",
                        record_id=ref or e.get("entry_id", ""),
                        location=e.get("location", ""),
                        a_value=None,
                        b_value=e.get("value"),
                        entry_id=e.get("entry_id"),
                        details=f"Entry {e.get('entry_id')} in System B references unknown record '{ref}'.",
                    )
                )

    # 2. MISSING_IN_B & Multi-entry checks
    for rid, a in a_rows.items():
        entries = by_ref.get(rid, [])
        if not entries:
            disagreements.append(
                create_disagreement(
                    reason="MISSING_IN_B",
                    record_id=rid,
                    location=a.get("location", ""),
                    a_value=a.get("total"),
                    b_value=None,
                    details=f"Record {rid} present in System A but absent from System B.",
                )
            )
            continue

        vals = [e.get("value") for e in entries]

        # Multi-entry in B (Splits vs Duplicates)
        if len(entries) > 1:
            if any(v is None for v in vals):
                disagreements.append(
                    create_disagreement(
                        reason="VALUE_MISMATCH",
                        record_id=rid,
                        location=a.get("location", ""),
                        a_value=a.get("total"),
                        b_value=None,
                        details=f"Record {rid} has multiple B entries with missing/unparseable values.",
                    )
                )
                continue

            sum_b = sum(vals)
            if sum_b != a.get("total"):
                disagreements.append(
                    create_disagreement(
                        reason="DUPLICATE_IN_B",
                        record_id=rid,
                        location=a.get("location", ""),
                        a_value=a.get("total"),
                        b_value=sum_b,
                        details=f"Record {rid} has {len(entries)} entries in System B summing to {sum_b}, which differs from System A total {a.get('total')}.",
                    )
                )
                continue
            # If sum_b == a['total'], it is a valid split disbursement and NOT flagged as an error.
            continue

        # Single entry in B
        e = entries[0]
        b_val = e.get("value")
        a_total = a.get("total")

        if b_val is None:
            disagreements.append(
                create_disagreement(
                    reason="VALUE_MISMATCH",
                    record_id=rid,
                    location=a.get("location", ""),
                    a_value=a_total,
                    b_value=None,
                    entry_id=e.get("entry_id"),
                    details=f"Record {rid} has a blank/missing value in System B (raw: '{e.get('value_raw', '')}').",
                )
            )
        elif b_val != a_total:
            disagreements.append(
                create_disagreement(
                    reason="VALUE_MISMATCH",
                    record_id=rid,
                    location=a.get("location", ""),
                    a_value=a_total,
                    b_value=b_val,
                    entry_id=e.get("entry_id"),
                    details=f"Value mismatch for record {rid}: System A has {a_total}, System B has {b_val}.",
                )
            )

        # Auxiliary checks: Location and Date mismatches
        a_loc = (a.get("location") or "").strip()
        b_loc = (e.get("location") or "").strip()
        if a_loc and b_loc and a_loc != b_loc:
            disagreements.append(
                create_disagreement(
                    reason="LOCATION_MISMATCH",
                    record_id=rid,
                    location=a_loc,
                    a_value=a_total,
                    b_value=b_val,
                    entry_id=e.get("entry_id"),
                    details=f"Location mismatch for record {rid}: System A has {a_loc}, System B has {b_loc}.",
                )
            )

        a_date = str(a.get("date") or "").strip()
        b_date = str(e.get("date") or "").strip()
        if a_date and b_date and a_date != b_date:
            disagreements.append(
                create_disagreement(
                    reason="DATE_MISMATCH",
                    record_id=rid,
                    location=a_loc,
                    a_value=a_total,
                    b_value=b_val,
                    entry_id=e.get("entry_id"),
                    details=f"Date mismatch for record {rid}: System A recorded {a_date}, System B recorded {b_date}.",
                )
            )

    return disagreements
