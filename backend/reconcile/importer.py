import csv
import logging
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.conf import settings
from .models import Location, SystemARecord, SystemBEntry

logger = logging.getLogger(__name__)


def normalize_ref(raw: str) -> str | None:
    """
    Extract digits from raw reference string and format as REC-XXXX.
    Handles 'rec1034', ' REC - 1070 ', '1112' -> 'REC-1034', 'REC-1070', 'REC-1112'.
    Returns None if no digits are found.
    """
    if not raw:
        return None
    m = re.search(r"\d+", str(raw))
    return f"REC-{m.group()}" if m else None


def parse_amount(raw: str) -> Decimal | None:
    """
    Parse monetary amounts handling Indian-style grouping e.g. '1,25,400.00'.
    Blank or invalid text returns None (unknown/missing), NEVER Decimal('0.00').
    """
    s = (raw or "").strip().replace(",", "")
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        logger.warning("Unparseable decimal amount: '%s'", raw)
        return None


def parse_date(raw: str):
    """Parse date string YYYY-MM-DD."""
    s = (raw or "").strip()
    if not s:
        return None
    return datetime.strptime(s, "%Y-%m-%d").date()


def import_locations(file_path: str) -> dict:
    read_count = 0
    saved_count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            read_count += 1
            loc_id = row["location_id"].strip()
            org_id = row["org_id"].strip()
            name = (row.get("location_name") or row.get("name") or loc_id).strip()
            Location.objects.update_or_create(
                location_id=loc_id,
                defaults={
                    "org_id": org_id,
                    "name": name,
                },
            )
            saved_count += 1
    return {"read": read_count, "saved": saved_count}


def import_system_a(file_path: str) -> dict:
    read_count = 0
    saved_count = 0
    empty_actors = 0
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            read_count += 1
            rec_id = row["record_id"].strip()
            loc_id = row["location_id"].strip()
            location = Location.objects.get(location_id=loc_id)
            actor = row.get("actor_id", "").strip() or None
            if actor is None:
                empty_actors += 1
            event_date = parse_date(row["event_date"])
            cat_code = row.get("category_code", "").strip()
            base_val = parse_amount(row["base_value"])
            adj_val = parse_amount(row.get("adjustment", "0")) or Decimal("0.00")
            total_val = parse_amount(row["total_value"])
            state = row.get("state", "CONFIRMED").strip()

            SystemARecord.objects.update_or_create(
                record_id=rec_id,
                defaults={
                    "location": location,
                    "event_date": event_date,
                    "category_code": cat_code,
                    "actor_id": actor,
                    "base_value": base_val,
                    "adjustment": adj_val,
                    "total_value": total_val,
                    "state": state,
                },
            )
            saved_count += 1
    return {
        "read": read_count,
        "saved": saved_count,
        "empty_actors": empty_actors,
    }


def import_system_b(file_path: str) -> dict:
    read_count = 0
    saved_count = 0
    cleaned_refs_count = 0
    empty_values_count = 0
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            read_count += 1
            entry_id = row["entry_id"].strip()
            raw_ref = row.get("record_ref", "").strip()
            cleaned_ref = normalize_ref(raw_ref)
            if cleaned_ref and cleaned_ref != raw_ref:
                cleaned_refs_count += 1

            loc_id = row["location_id"].strip()
            location = Location.objects.get(location_id=loc_id)
            recorded_on = parse_date(row["recorded_on"])
            raw_val = row.get("value", "").strip()
            val = parse_amount(raw_val)
            if val is None:
                empty_values_count += 1
            label = row.get("label", "").strip()

            SystemBEntry.objects.update_or_create(
                entry_id=entry_id,
                defaults={
                    "record_ref_raw": raw_ref,
                    "record_ref": cleaned_ref,
                    "location": location,
                    "recorded_on": recorded_on,
                    "value_raw": raw_val,
                    "value": val,
                    "label": label,
                },
            )
            saved_count += 1
    return {
        "read": read_count,
        "saved": saved_count,
        "cleaned_refs": cleaned_refs_count,
        "empty_values": empty_values_count,
    }


def import_all(data_dir: str | None = None) -> dict:
    if not data_dir:
        data_dir = os.path.join(settings.BASE_DIR, "data")
    loc_file = os.path.join(data_dir, "locations.csv")
    sys_a_file = os.path.join(data_dir, "system_a.csv")
    sys_b_file = os.path.join(data_dir, "system_b.csv")

    loc_stats = import_locations(loc_file)
    a_stats = import_system_a(sys_a_file)
    b_stats = import_system_b(sys_b_file)

    return {
        "locations": loc_stats,
        "system_a": a_stats,
        "system_b": b_stats,
    }
