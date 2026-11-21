# Data Inspection & Audit Notes

Detailed inspection of `locations.csv`, `system_a.csv`, and `system_b.csv` conducted prior to writing import and reconciliation logic.

---

## 1. File Summaries

| File | Row Count | Key Columns | Description |
|---|---|---|---|
| `locations.csv` | 5 | `location_id`, `org_id`, `location_name` | Source of truth for tenant mapping (`LOC-101..103` -> `ORG-A`, `LOC-201..202` -> `ORG-B`). |
| `system_a.csv` | 120 | `record_id`, `location_id`, `event_date`, `category_code`, `actor_id`, `base_value`, `adjustment`, `total_value`, `state` | System A transaction ledger. 120 unique record IDs. |
| `system_b.csv` | 121 | `entry_id`, `record_ref`, `location_id`, `recorded_on`, `value`, `label` | System B entry ledger. 121 unique entry IDs. |

---

## 2. Anomalies and Irregularities Discovered

### A. Non-Standard Reference Formats in System B
System B contains three non-standard reference variations pointing to System A records:
1. `ENT/2026/4034`: `rec1034` (lowercase without hyphen) $\rightarrow$ normalizes to `REC-1034`.
2. `ENT/2026/4070`: ` REC - 1070 ` (whitespace padding around hyphen) $\rightarrow$ normalizes to `REC-1070`.
3. `ENT/2026/4112`: `1112` (numeric only, missing `REC-` prefix) $\rightarrow$ normalizes to `REC-1112`.

**Normalization Rule**: Extract digit sequence with `r'\d+'` and format as `f"REC-{digits}"`.

---

### B. Bad & Formatted Values
1. `ENT/2026/4050`: `value` is an empty string (`""`). Must be preserved as `null`, **never** coerced to `0` or `0.00`.
2. `ENT/2026/4064`: `value` is `'1,25,400.00'` (Indian numbering comma format). Must strip commas and parse as `Decimal('125400.00')`.

---

### C. Missing Fields in System A
1. `REC-1050`: `actor_id` is an empty string (`""`). Must be stored as `null` in the database without failing validation or dropping the record.

---

### D. Orphan Entry in System B
1. `ENT/2026/4901`: Points to `REC-1999` with value `41250.00` at location `LOC-102`. `REC-1999` does not exist in System A.
   - Flag as: `ORPHAN_IN_B`.
   - Tenant attribution: Belongs to `ORG-A` derived from `LOC-102`.

---

### E. Missing Entries in System B (Present in A, absent in B)
1. `REC-1015`: Present in System A (`LOC-103`, `ORG-A`, total `41095.33`, state `CONFIRMED`). No corresponding entry in System B.
   - Flag as: `MISSING_IN_B`.
2. `REC-1061`: Present in System A (`LOC-202`, `ORG-B`, total `87615.49`, state `CONFIRMED`). No corresponding entry in System B.
   - Flag as: `MISSING_IN_B`.

---

### F. Multi-Entry Records in System B (Splits vs. Duplicates)
1. `REC-1042`:
   - System A total: `112837.06`.
   - System B entries: `ENT/2026/4042` (`112837.06`) and `ENT/2026/4902` (`112837.06`).
   - Sum in B: `225674.12` $\neq$ `112837.06`. Both share label `"Entry for CAT-02"`.
   - **Diagnosis**: Duplicate entry. Flag as `DUPLICATE_IN_B`.
2. `REC-1055`:
   - System A total: `179877.32`.
   - System B entries: `ENT/2026/4055` (`71950.93`, label `"Entry for CAT-08"`) and `ENT/2026/4903` (`107926.39`, label `"Entry part 2 of 2"`).
   - Sum in B: `71950.93 + 107926.39 = 179877.32` == `179877.32`.
   - **Diagnosis**: Legitimate split entry. **NOT an error / NOT flagged**.

---

### G. Value Mismatches (Single entries with differing amounts)
1. `REC-1003`: A total = `121388.01`, B value = `94834.38`. Flag as `VALUE_MISMATCH`.
2. `REC-1027`: A total = `79259.03`, B value = `61921.12`. Flag as `VALUE_MISMATCH`.
3. `REC-1050`: A total = `160405.85`, B value is blank (`None`). Flag as `VALUE_MISMATCH`.
4. `REC-1064`: A total = `183244.16`, B value = `125400.00` (parsed from `1,25,400.00`). Flag as `VALUE_MISMATCH`.
5. `REC-1088`: A total = `138948.30`, B value = `108553.36`. Flag as `VALUE_MISMATCH`.

---

### H. Date Mismatch
1. `REC-1009`: System A `event_date` is `2026-03-31`, System B `recorded_on` is `2026-04-02`. Flag as `DATE_MISMATCH`.

---

### I. Location Mismatch & Cross-Tenant Boundary Trap
1. `REC-1077`:
   - System A: Location `LOC-102` (`ORG-A`).
   - System B: Location `LOC-201` (`ORG-B`).
   - Values match (`40875.00`).
   - **Cross-tenant risk**: Revealing System B's location `LOC-201` to `ORG-A` leaks `ORG-B`'s operational location. System A is the primary record owner (`ORG-A`), so `ORG-A` sees the disagreement, but foreign tenant details (`LOC-201`) must be masked / redacted so no cross-org leak occurs.

---

### J. VOIDED Record in System A
1. `REC-1019`:
   - System A: State is `VOIDED`, total = `57092.35`.
   - System B: Entry `ENT/2026/4019` recorded `57092.35`.
   - B does not track voiding states. Both record the historical value `57092.35`. Handled according to explicit policy documented in `DECISIONS.md`.
