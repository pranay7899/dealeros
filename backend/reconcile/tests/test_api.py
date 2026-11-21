from decimal import Decimal
import pytest
from rest_framework.test import APIClient
from reconcile.models import Location, SystemARecord, SystemBEntry


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def seed_test_data(db):
    loc_a = Location.objects.create(location_id="LOC-101", org_id="ORG-A", name="Branch 101")
    loc_b = Location.objects.create(location_id="LOC-201", org_id="ORG-B", name="Branch 201")

    # Record 1: Value mismatch in ORG-A
    SystemARecord.objects.create(
        record_id="REC-1",
        location=loc_a,
        event_date="2026-03-01",
        category_code="CAT-1",
        base_value=Decimal("100.00"),
        adjustment=Decimal("0.00"),
        total_value=Decimal("100.00"),
        state="CONFIRMED",
    )
    SystemBEntry.objects.create(
        entry_id="ENT/1",
        record_ref_raw="REC-1",
        record_ref="REC-1",
        location=loc_a,
        recorded_on="2026-03-01",
        value=Decimal("80.00"),
        value_raw="80.00",
    )

    # Record 2: Missing in B for ORG-A
    SystemARecord.objects.create(
        record_id="REC-2",
        location=loc_a,
        event_date="2026-03-02",
        category_code="CAT-1",
        base_value=Decimal("500.00"),
        adjustment=Decimal("0.00"),
        total_value=Decimal("500.00"),
        state="CONFIRMED",
    )

    # Record 3: Missing in B for ORG-B
    SystemARecord.objects.create(
        record_id="REC-3",
        location=loc_b,
        event_date="2026-03-03",
        category_code="CAT-2",
        base_value=Decimal("900.00"),
        adjustment=Decimal("0.00"),
        total_value=Decimal("900.00"),
        state="CONFIRMED",
    )


def test_api_missing_org_param(api_client, db):
    response = api_client.get("/api/disagreements/")
    assert response.status_code == 400
    assert "error" in response.json()


def test_api_unknown_org(api_client, db):
    response = api_client.get("/api/disagreements/?org=ORG-UNKNOWN")
    assert response.status_code == 404


def test_api_get_org_disagreements(api_client, seed_test_data):
    response = api_client.get("/api/disagreements/?org=ORG-A")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    reasons = {d["reason"] for d in data}
    assert "VALUE_MISMATCH" in reasons
    assert "MISSING_IN_B" in reasons


def test_api_filter_by_reason(api_client, seed_test_data):
    response = api_client.get("/api/disagreements/?org=ORG-A&reason=VALUE_MISMATCH")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["reason"] == "VALUE_MISMATCH"
    assert data[0]["record_id"] == "REC-1"


def test_api_sort_by_value(api_client, seed_test_data):
    response = api_client.get("/api/disagreements/?org=ORG-A&sort=-value")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # REC-2 has a_value 500, REC-1 has b_value 80
    assert data[0]["record_id"] == "REC-2"
    assert data[1]["record_id"] == "REC-1"


def test_api_orgs_and_reasons_endpoints(api_client, seed_test_data):
    res_orgs = api_client.get("/api/orgs/")
    assert res_orgs.status_code == 200
    assert "ORG-A" in res_orgs.json()
    assert "ORG-B" in res_orgs.json()

    res_reasons = api_client.get("/api/reasons/")
    assert res_reasons.status_code == 200
    assert any(r["code"] == "VALUE_MISMATCH" for r in res_reasons.json())
