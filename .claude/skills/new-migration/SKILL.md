---
name: new-migration
description: Create an Alembic migration that provably matches the authoritative DBML, with upgrade, downgrade, and clean-replay verification.
argument-hint: "<rev-id> <slug> e.g. 002 create_customers_staff_services_availability"
disable-model-invocation: true
---

# New migration — $ARGUMENTS

## 1. Read the DBML first

Open `docs/architecture/erd/source/business-management-platform-erd-v1.2.dbml` and read every table
block this migration touches — **including the Note blocks**, which carry behavioral rules that do
not appear in the PDF. Never open the ERD PDF.

List, before writing anything: tables, columns with type and precision, nullability, defaults, check
constraints, unique constraints, composite tenant keys, foreign keys with their ON DELETE rules,
named indexes, and enum members in order.

## 2. Generate with an explicit revision id

```bash
cd backend && alembic revision --rev-id <rev-id> -m "<slug>"
```

Never generate and then rename. `alembic.ini` sets `file_template = %%(rev)s_%%(slug)s`.

If you use `--autogenerate`, treat the result as a draft: diff it line by line against the list from
step 1. Autogenerate routinely drops check constraints, index names, ON DELETE rules, and server
defaults.

## 3. Write a real downgrade

Reverse every operation in reverse order. "Not supported" is acceptable only where the DBML makes it
genuinely unsafe, and then it must be stated in the migration docstring with the reason.

## 4. Verify — all three, with output

```bash
cd backend && alembic upgrade head
cd backend && alembic downgrade base
cd backend && alembic upgrade head
```

## 5. Prove parity

Run the `schema-parity-checker` subagent. Add or extend introspection tests covering every attribute
from step 1. Check these explicitly, every time:

- `staff_availability.end_time` round-trips `24:00:00` and rejects `24:00:01`
- `roles` rows are tenant-owned with the three-name check constraint; no global role rows
- customer email, staff email, and service name remain non-unique within a tenant
- user email is globally unique and lowercased
- bookings/payments composite foreign key exists
- no hard-delete path for bookings

## 6. Report

Table: `DBML attribute | migration line | parity test`. Any row you cannot fill is unfinished work —
say so rather than closing the task.
