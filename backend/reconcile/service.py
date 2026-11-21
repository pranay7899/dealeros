from decimal import Decimal
from typing import Any, Dict, List, Optional
from django.db.models import Q
from .compare import compare
from .models import Location, SystemARecord, SystemBEntry


def get_disagreements_for_org(
    org_id: str,
    reason_filter: Optional[str] = None,
    sort_by: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve disagreements strictly scoped to a tenant (org_id).
    Enforces tenant boundaries inside database queries.
    Prevents cross-tenant data leakage by masking foreign locations.
    """
    if not org_id:
        return []

    # 1. Source of truth for tenant ownership: locations.csv via Location model
    org_locations = set(
        Location.objects.filter(org_id=org_id).values_list("location_id", flat=True)
    )
    if not org_locations:
        return []

    # 2. System A records owned by this organization
    a_records = SystemARecord.objects.filter(location_id__in=org_locations)
    a_dict = {
        r.record_id: {
            "total": r.total_value,
            "location": r.location_id,
            "date": r.event_date.isoformat(),
            "state": r.state,
        }
        for r in a_records
    }
    tenant_a_ids = set(a_dict.keys())
    all_a_ids = set(SystemARecord.objects.values_list("record_id", flat=True))

    # 3. System B entries relevant to this organization:
    #    a) entries pointing to this tenant's System A records
    #    b) orphan entries recorded at this tenant's locations (non-existent across all of A)
    b_entries = SystemBEntry.objects.filter(
        Q(record_ref__in=tenant_a_ids)
        | (Q(location_id__in=org_locations) & ~Q(record_ref__in=all_a_ids))
    )

    b_list = []
    for e in b_entries:
        # Check if B's recorded location belongs to another tenant (trap row prevention)
        is_foreign = e.location_id not in org_locations
        safe_location = "[EXTERNAL_LOCATION]" if is_foreign else e.location_id

        b_list.append({
            "entry_id": e.entry_id,
            "ref": e.record_ref,
            "value": e.value,
            "location": safe_location,
            "raw_location": e.location_id,
            "date": e.recorded_on.isoformat(),
            "value_raw": e.value_raw,
        })

    # 4. Pure Python comparison engine
    disagreements = compare(a_dict, b_list)

    # 5. Sanitize and redact any potential foreign tenant leaks
    foreign_locations = set(
        Location.objects.exclude(org_id=org_id).values_list("location_id", flat=True)
    )

    sanitized = []
    for d in disagreements:
        loc = d.get("location")
        if loc not in org_locations:
            loc = "[EXTERNAL_LOCATION]"

        details = d.get("details", "")
        for fl in foreign_locations:
            if fl in details:
                details = details.replace(fl, "[EXTERNAL_LOCATION]")

        a_val = d.get("a_value")
        b_val = d.get("b_value")
        diff = d.get("difference")

        sanitized.append({
            "reason": d.get("reason"),
            "record_id": d.get("record_id"),
            "location": loc,
            "a_value": str(a_val) if a_val is not None else None,
            "b_value": str(b_val) if b_val is not None else None,
            "difference": str(diff) if diff is not None else None,
            "details": details,
            "entry_id": d.get("entry_id"),
            # raw numerical fields for sorting
            "_num_a": a_val,
            "_num_b": b_val,
            "_num_diff": diff,
        })

    # 6. Apply optional filtering by reason
    if reason_filter:
        reason_filter = reason_filter.strip().upper()
        sanitized = [d for d in sanitized if d["reason"] == reason_filter]

    # 7. Apply optional sorting
    if sort_by:
        sort_by = sort_by.strip()
        reverse = sort_by.startswith("-")
        sort_key = sort_by.lstrip("+-")

        def get_sort_val(item):
            if sort_key == "value":
                # Primary comparison value: b_value if available, otherwise a_value
                val = item["_num_b"] if item["_num_b"] is not None else item["_num_a"]
                return (0, val) if val is not None else (1, Decimal("-Infinity") if reverse else Decimal("Infinity"))
            elif sort_key == "difference":
                val = item["_num_diff"]
                return (0, val) if val is not None else (1, Decimal("-Infinity") if reverse else Decimal("Infinity"))
            elif sort_key == "record_id":
                return (0, item["record_id"] or "")
            elif sort_key == "reason":
                return (0, item["reason"] or "")
            elif sort_key == "location":
                return (0, item["location"] or "")
            return (0, "")

        sanitized.sort(key=get_sort_val, reverse=reverse)

    # Clean up internal sorting helper fields before output
    output = []
    for d in sanitized:
        row = {k: v for k, v in d.items() if not k.startswith("_")}
        output.append(row)

    return output
