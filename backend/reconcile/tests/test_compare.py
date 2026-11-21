from decimal import Decimal
import pytest
from reconcile.compare import compare


def make_a_record(record_id="REC-1", total="100.00", location="LOC-101", date="2026-03-01", state="CONFIRMED"):
    return {
        "total": Decimal(total),
        "location": location,
        "date": date,
        "state": state,
    }


def make_b_entry(entry_id="ENT/1", ref="REC-1", value="100.00", location="LOC-101", date="2026-03-01", label="Entry"):
    return {
        "entry_id": entry_id,
        "ref": ref,
        "value": Decimal(value) if value is not None else None,
        "location": location,
        "date": date,
        "label": label,
    }


def test_missing_in_b():
    """An A record with no B entry is flagged as MISSING_IN_B."""
    a = {"REC-101": make_a_record("REC-101", total="250.00", location="LOC-101")}
    b = []
    results = compare(a, b)
    assert len(results) == 1
    assert results[0]["reason"] == "MISSING_IN_B"
    assert results[0]["record_id"] == "REC-101"
    assert results[0]["a_value"] == Decimal("250.00")
    assert results[0]["b_value"] is None
