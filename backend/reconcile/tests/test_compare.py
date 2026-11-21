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


def test_orphan_in_b():
    """A B entry with an unknown reference is flagged as ORPHAN_IN_B."""
    a = {"REC-101": make_a_record("REC-101", total="100.00", location="LOC-101")}
    b = [
        make_b_entry("ENT/1", ref="REC-101", value="100.00", location="LOC-101"),
        make_b_entry("ENT/999", ref="REC-999", value="450.00", location="LOC-102"),
    ]
    results = compare(a, b)
    assert len(results) == 1
    assert results[0]["reason"] == "ORPHAN_IN_B"
    assert results[0]["record_id"] == "REC-999"
    assert results[0]["entry_id"] == "ENT/999"
    assert results[0]["location"] == "LOC-102"
    assert results[0]["a_value"] is None
    assert results[0]["b_value"] == Decimal("450.00")
