# Architecture & Reconciliation Decisions

## Decision: compare B's value with A's total_value
- Rejected: compare with base_value
- Why: B's values equal A's total_value (base_value + adjustment) across matched rows; base_value excludes adjustments already recognized in System B.

## Decision: clean references using regex digits extraction
- Rejected: strict prefix stripping or raw string matching
- Why: System B records contain variants like 'rec1034', ' REC - 1070 ', and '1112' that refer to the same records in System A.

## Decision: store blank amounts as null, never zero
- Rejected: defaulting empty string amounts to Decimal('0.00')
- Why: In accounting reconciliation, a blank value represents missing/unknown information; zero is an explicit numerical claim that distorts audits.

## Decision: use DecimalField instead of float for monetary values
- Rejected: standard Python float or SQLite REAL
- Why: Binary floating-point representation causes precision loss (e.g. 0.1 + 0.2 != 0.3), whereas Decimal guarantees exact arithmetic for financial reconciliation.

## Decision: treat multiple B entries that sum to A's total as valid splits
- Rejected: flagging all 1-to-many relationships as duplicate errors
- Why: Row REC-1055 has two entries (labeled 'part 2 of 2') whose values sum exactly to A's total value, representing a legitimate split disbursement rather than an accounting error.

## Decision: isolate tenant queries in the database and mask foreign location in cross-tenant conflicts
- Rejected: filtering rows client-side in React or displaying foreign tenant location IDs
- Why: Client-side filtering leaks data in the network payload, and showing an ORG-B location (e.g., LOC-201 on REC-1077) to ORG-A breaches tenant isolation boundaries.

## Decision: treat VOIDED record with identical B value as matching ledger history
- Rejected: automatically overriding A's total to 0.00 or silently deleting voided records
- Why: System B has no state/cancellation field and records historical ledger entries as they occurred; since the numerical amounts match, the record reflects historical agreement, while void workflow rules should be handled via operational audit policy.

## Decision: track date and location differences as auxiliary disagreements
- Rejected: ignoring all non-monetary metadata differences
- Why: An entry recorded at a mismatched branch or different date represents an audit risk that helps operators identify data synchronization faults.
