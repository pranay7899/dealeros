import json
from decimal import Decimal
import pytest
from rest_framework.test import APIClient
from reconcile.importer import import_all
from reconcile.models import Location, SystemARecord, SystemBEntry


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def populated_db(db):
    """Ensure database has the full real dataset loaded for end-to-end tenant checks."""
    if Location.objects.count() == 0:
        import_all()
    return db


def test_tenant_a_isolation(client, populated_db):
    """
    Assert that calling API as ORG-A returns ONLY ORG-A records.
    Strictly asserts that no ORG-B locations (LOC-201, LOC-202) appear anywhere
    in the JSON response (neither in location fields nor in details text).
    """
    response = client.get("/api/disagreements/?org=ORG-A")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) > 0

    org_b_locations = {"LOC-201", "LOC-202"}
    raw_payload_str = json.dumps(rows)

    # Prove no ORG-B location leaks in the entire payload
    for loc in org_b_locations:
        assert loc not in raw_payload_str, f"Leaked ORG-B location '{loc}' in ORG-A payload!"

    # Prove each returned row is legitimately an ORG-A record
    org_a_valid_locations = {"LOC-101", "LOC-102", "LOC-103", "[EXTERNAL_LOCATION]"}
    for row in rows:
        assert row["location"] in org_a_valid_locations


def test_tenant_b_isolation(client, populated_db):
    """
    Assert that calling API as ORG-B returns ONLY ORG-B records.
    Strictly asserts that no ORG-A locations (LOC-101, LOC-102, LOC-103) appear anywhere
    in the JSON response.
    """
    response = client.get("/api/disagreements/?org=ORG-B")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) > 0

    org_a_locations = {"LOC-101", "LOC-102", "LOC-103"}
    raw_payload_str = json.dumps(rows)

    # Prove no ORG-A location leaks in the entire payload
    for loc in org_a_locations:
        assert loc not in raw_payload_str, f"Leaked ORG-A location '{loc}' in ORG-B payload!"

    # Prove each returned row is legitimately an ORG-B record
    org_b_valid_locations = {"LOC-201", "LOC-202", "[EXTERNAL_LOCATION]"}
    for row in rows:
        assert row["location"] in org_b_valid_locations


def test_trap_row_cross_org_leak_prevention(client, populated_db):
    """
    Test the trap row REC-1077:
    System A: LOC-102 (ORG-A)
    System B: LOC-201 (ORG-B)
    ORG-A must see the LOCATION_MISMATCH, but System B's location must be masked.
    ORG-B must NOT see REC-1077 because it does not own the System A record.
    """
    res_a = client.get("/api/disagreements/?org=ORG-A")
    rows_a = res_a.json()
    trap_matches_a = [r for r in rows_a if r["record_id"] == "REC-1077"]

    assert len(trap_matches_a) == 1
    trap_row = trap_matches_a[0]
    assert trap_row["reason"] == "LOCATION_MISMATCH"
    assert trap_row["location"] == "LOC-102"
    # Verify LOC-201 is masked and never exposed to ORG-A
    assert "LOC-201" not in trap_row["details"]
    assert "[EXTERNAL_LOCATION]" in trap_row["details"]

    # Verify ORG-B cannot see REC-1077
    res_b = client.get("/api/disagreements/?org=ORG-B")
    rows_b = res_b.json()
    trap_matches_b = [r for r in rows_b if r["record_id"] == "REC-1077"]
    assert len(trap_matches_b) == 0, "ORG-B should not see REC-1077 owned by ORG-A!"


def test_orphan_attribution_by_b_location(client, populated_db):
    """
    Orphan B entry ENT/2026/4901 has reference REC-1999 (not in System A)
    and location LOC-102 (belongs to ORG-A).
    It must be visible to ORG-A as an orphan, and completely hidden from ORG-B.
    """
    res_a = client.get("/api/disagreements/?org=ORG-A")
    rows_a = res_a.json()
    orphans_a = [r for r in rows_a if r["record_id"] == "REC-1999"]
    assert len(orphans_a) == 1
    assert orphans_a[0]["reason"] == "ORPHAN_IN_B"
    assert orphans_a[0]["location"] == "LOC-102"

    res_b = client.get("/api/disagreements/?org=ORG-B")
    rows_b = res_b.json()
    orphans_b = [r for r in rows_b if r["record_id"] == "REC-1999"]
    assert len(orphans_b) == 0


def test_missing_in_b_tenant_isolation(client, populated_db):
    """
    REC-1015 is missing in B and belongs to ORG-A (LOC-103).
    REC-1061 is missing in B and belongs to ORG-B (LOC-202).
    Each must appear only in their respective tenant query.
    """
    res_a = client.get("/api/disagreements/?org=ORG-A")
    rows_a = res_a.json()
    rec_ids_a = {r["record_id"] for r in rows_a}
    assert "REC-1015" in rec_ids_a
    assert "REC-1061" not in rec_ids_a

    res_b = client.get("/api/disagreements/?org=ORG-B")
    rows_b = res_b.json()
    rec_ids_b = {r["record_id"] for r in rows_b}
    assert "REC-1061" in rec_ids_b
    assert "REC-1015" not in rec_ids_b
