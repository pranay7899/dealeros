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


def test_duplicate_in_b():
    """The same amount entered twice (or multiple entries not summing to total) is flagged as DUPLICATE_IN_B."""
    a = {"REC-1042": make_a_record("REC-1042", total="100.00", location="LOC-101")}
    b = [
        make_b_entry("ENT/1", ref="REC-1042", value="100.00", location="LOC-101"),
        make_b_entry("ENT/2", ref="REC-1042", value="100.00", location="LOC-101"),
    ]
    results = compare(a, b)
    assert len(results) == 1
    assert results[0]["reason"] == "DUPLICATE_IN_B"
    assert results[0]["record_id"] == "REC-1042"
    assert results[0]["a_value"] == Decimal("100.00")
    assert results[0]["b_value"] == Decimal("200.00")


def test_split_that_sums_is_not_an_error():
    """Two or more parts summing exactly to A's total are a valid split and not flagged as an error."""
    a = {"REC-1055": make_a_record("REC-1055", total="100.00", location="LOC-103")}
    b = [
        make_b_entry("ENT/1", ref="REC-1055", value="40.00", location="LOC-103"),
        make_b_entry("ENT/2", ref="REC-1055", value="60.00", location="LOC-103"),
    ]
    results = compare(a, b)
    assert results == []


def test_value_mismatch():
    """Different amounts between A and B are flagged as VALUE_MISMATCH."""
    a = {"REC-1003": make_a_record("REC-1003", total="121388.01")}
    b = [make_b_entry("ENT/1", ref="REC-1003", value="94834.38")]
    results = compare(a, b)
    assert len(results) == 1
    assert results[0]["reason"] == "VALUE_MISMATCH"
    assert results[0]["record_id"] == "REC-1003"
    assert results[0]["a_value"] == Decimal("121388.01")
    assert results[0]["b_value"] == Decimal("94834.38")
    assert results[0]["difference"] == Decimal("26553.63")


def test_blank_value_not_treated_as_zero():
    """A blank B value is flagged as VALUE_MISMATCH and is NOT treated as 0."""
    a = {"REC-1050": make_a_record("REC-1050", total="0.00")}
    b = [make_b_entry("ENT/1", ref="REC-1050", value=None)]
    results = compare(a, b)
    assert len(results) == 1
    assert results[0]["reason"] == "VALUE_MISMATCH"
    assert results[0]["record_id"] == "REC-1050"
    assert results[0]["b_value"] is None
    # Ensure it did not treat None as 0 and falsely match A's 0.00
    assert results[0]["difference"] is None


def test_clean_row():
    """A matching pair produces no disagreements."""
    a = {"REC-1001": make_a_record("REC-1001", total="500.00", location="LOC-101", date="2026-03-01")}
    b = [make_b_entry("ENT/1", ref="REC-1001", value="500.00", location="LOC-101", date="2026-03-01")]
    results = compare(a, b)
    assert results == []


def test_messy_references():
    """Normalized references match corresponding A records and are not falsely flagged as orphans or missing."""
    from reconcile.importer import normalize_ref

    raw_refs = ["rec1034", " REC - 1070 ", "1112"]
    a = {
        "REC-1034": make_a_record("REC-1034", total="100.00"),
        "REC-1070": make_a_record("REC-1070", total="200.00"),
        "REC-1112": make_a_record("REC-1112", total="300.00"),
    }
    b = [
        make_b_entry("ENT/1", ref=normalize_ref(raw_refs[0]), value="100.00"),
        make_b_entry("ENT/2", ref=normalize_ref(raw_refs[1]), value="200.00"),
        make_b_entry("ENT/3", ref=normalize_ref(raw_refs[2]), value="300.00"),
    ]
    results = compare(a, b)
    assert results == []
