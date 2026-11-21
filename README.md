# DealerOS Reconciliation Ledger

A robust, tenant-isolated full-stack reconciliation application designed to detect, classify, and visualize accounting discrepancies between System A and System B ledgers.

---

## 1. How to Run (From a Clean Clone)

Prerequisites:
- **Python 3.11+**
- **Node.js 18+**

Execute the following commands in order:

### Backend Setup
```bash
# 1. Navigate to the repository root
cd dealeros

# 2. Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS / Linux:
source .venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Run database migrations
cd backend
python manage.py migrate

# 5. Import the raw CSV datasets (idempotent command)
python manage.py import_data

# 6. Run all backend and reconciliation tests
pytest

# 7. Start the backend development server (runs on http://127.0.0.1:8000)
python manage.py runserver 8000
```

### Frontend Setup (In a New Terminal)
```bash
# Navigate to the frontend directory
cd dealeros/frontend

# Install dependencies
npm install

# Start the frontend dev server (runs on http://localhost:5173)
npm run dev
```

Open your browser at `http://localhost:5173` to view the reconciliation interface.

---

## 2. What I Built

- **Robust CSV Ingestion Engine (`importer.py` & `management/commands/import_data.py`)**:
  - Reads `locations.csv`, `system_a.csv` (120 rows), and `system_b.csv` (121 rows).
  - Normalizes messy references (`rec1034`, ` REC - 1070 `, `1112` $\rightarrow$ `REC-xxxx`).
  - Correctly parses Indian comma-formatted numbers (`1,25,400.00` $\rightarrow$ `Decimal('125400.00')`).
  - Preserves blank fields as `null` / `None` without crashing or coercing to `0.00`.
  - Idempotent: safe to run repeatedly via `update_or_create`.
- **Pure Python Comparison Engine (`compare.py`)**:
  - Matches System A records with System B entries by cleaned reference.
  - Distinguishes legitimate split payments (sums matching `total_value`) from actual duplicates.
  - Detects `MISSING_IN_B`, `ORPHAN_IN_B`, `DUPLICATE_IN_B`, `VALUE_MISMATCH`, `LOCATION_MISMATCH`, and `DATE_MISMATCH`.
- **Strict Multi-Tenant API (`views.py` & `service.py`)**:
  - REST endpoint `GET /api/disagreements/?org=ORG-A&reason=...&sort=...`.
  - Filters tenant boundaries directly inside database queries using `locations.csv`.
  - Prevents cross-tenant information leakage by masking foreign locations on boundary-crossing transactions (e.g. `REC-1077`).
- **Interactive Table Screen (`frontend/src/App.jsx`)**:
  - Tenant dropdown (`ORG-A`, `ORG-B`).
  - Reason category filter dropdown.
  - Sortable value and difference headers.
  - Clean display of empty cells for missing values (never `0` or `null`).
- **Test Suite (`reconcile/tests/`)**:
  - 21 comprehensive pytest tests covering each comparison rule, messy data edge cases, API parameters, and tenant isolation guarantees.

---

## 3. What I Deliberately Did Not Build

To respect the assessment timebox and focus on correctness, dirty data handling, and tenant security, the following were intentionally omitted:
1. **User Authentication & Session Management**: No login screens, JWT tokens, or passwords; tenant context is driven cleanly via the `org` parameter and selector.
2. **Pagination / Infinite Scrolling**: With 120–121 records, rendering the full table provides immediate visibility without pagination complexity.
3. **Heavy UI Component Libraries / Complex CSS**: Used clean, plain CSS rather than Tailwind or Material-UI to ensure maximum readability and zero unnecessary dependencies.
4. **Docker / Container Orchestration**: Plain SQLite and Vite scripts run directly on any machine with standard Python and Node.js.
5. **Write APIs / Manual Reconciliation Overrides**: Did not build editable reconciliation status workflows since the task focuses on detection and ledger auditing.

---

## 4. How I Worked With the AI Agent

- **Agent Used**: Antigravity Assistant (powered by Google DeepMind Gemini model).
- **Workflow & Prompts**:
  - **Data Inspection First**: Wrote an audit script before modifying any schemas to inspect raw rows, unique keys, and edge cases in `locations.csv`, `system_a.csv`, and `system_b.csv`.
  - **Step-by-Step Architecture**: Kept business logic modular—pure Python comparison functions (`compare.py`), separated from Django ORM data access (`service.py`), separated from HTTP views (`views.py`).
  - **TDD & Incremental Commits**: Committed after every requirement step and verified each test suite before progressing.
- **Verification**:
  - Hand-calculated and checked row counts: 5 locations, 120 A records, 121 B entries.
  - Verified row `REC-1055` split arithmetic (`71,950.93 + 107,926.39 = 179,877.32`) to ensure valid splits were not falsely flagged.
  - Verified row `REC-1077` cross-tenant boundary masking (`LOC-102` vs `LOC-201`) to guarantee zero information leakage between tenants.

---

## 5. The Three Answers

### a. One thing the AI agent got wrong. How did you notice?
During early data exploration and comparison drafting, the agent's initial intuition was to flag **any** record with multiple System B entries as a `DUPLICATE_IN_B`. 

I noticed this when inspecting `REC-1055` in `system_b.csv`, which has two entries (`ENT/2026/4055` for \$71,950.93 and `ENT/2026/4903` for \$107,926.39 labeled `"Entry part 2 of 2"`). System A listed a total value of \$179,877.32. The AI's initial naive count check (`len(entries) > 1`) would have incorrectly flagged `REC-1055` as an error. By calculating the sum:
$$71,950.93 + 107,926.39 = 179,877.32$$
we proved that `REC-1055` is a legitimate split disbursement. We corrected the logic so that multiple B entries are only flagged as `DUPLICATE_IN_B` when their sum fails to equal System A's total.

### b. The part you are least confident about, and why
The part I am least confident about is the handling of **`REC-1077` (the cross-tenant trap row)** and **`REC-1019` (the VOIDED record)**:
- For `REC-1077`, System A places the event at `LOC-102` (`ORG-A`), but System B placed the entry at `LOC-201` (`ORG-B`). While our decision to attribute the record to System A (`ORG-A`) and mask B's location as `[EXTERNAL_LOCATION]` strictly prevents leaking `ORG-B`'s branch ID, in real banking/dealership operations `ORG-B`'s accountants might also notice a stray settlement on their books and wonder why it doesn't appear in their reconciliation view.
- For `REC-1019`, System A marks it `VOIDED` while System B has an active entry for the full amount (\$57,092.35). Because System B lacks a `state` column, the amounts match numerically. However, in strict accounting, an active B entry against a voided A record could represent an uncancelled disbursement. On a follow-up call, I would ask the finance team whether voided records require an explicit `RECORD_VOIDED` discrepancy reason.

### c. If you had a second day, what would you fix first?
If I had a second day, I would first implement **audit resolution and dispute tracking**:
- Create a `DiscrepancyResolution` model allowing accountants to click on any disagreement row and mark it as *Under Investigation*, *Approved Split*, *Void Reversal Pending*, or *Resolved*, complete with notes and timestamped user attribution.
- This would convert the current read-only auditing tool into a complete daily reconciliation workflow system for dealership accounting teams.
