---
paths:
  - "backend/alembic/**/*.py"
  - "backend/alembic.ini"
  - "backend/app/models/**/*.py"
---

# Migration and model rules

`docs/architecture/erd/source/business-management-platform-erd-v1.2.dbml` is the authority. Read the
relevant table block in it before writing or editing a migration or an ORM model. The ERD PDF is a
viewing export and must never be used as a source.

## Writing a migration

- Create revisions with **explicit revision ids** (`alembic revision --rev-id 001 ...`). Never
  generate then hand-rename. `alembic.ini` sets `file_template = %%(rev)s_%%(slug)s`.
- Autogenerate is a starting draft, not an answer. Diff it against the DBML by hand: column types,
  defaults, nullability, check constraints, unique constraints, composite tenant keys, foreign keys,
  **delete rules**, and every named index.
- Write a real `downgrade()`. "Not supported" is only acceptable where the DBML makes it genuinely
  unsafe, and then it must be stated in the migration docstring.
- Migrations do not contain business logic and do not import the application's service layer.

## Verifying a migration

Before calling migration work done, run all three and show the output:

```bash
cd backend && alembic upgrade head
cd backend && alembic downgrade base
cd backend && alembic upgrade head        # clean replay from empty
```

Schema-parity tests introspect the live database and must cover every table, enum, column, default,
nullability rule, check, unique constraint, foreign key, delete rule, and required index — including
all tenant composite relationships and the bookings/payments composite relationship.

## Things that are easy to get wrong here

- Role rows are **tenant-owned**. Every `roles` row carries a `business_id`. There are no global role
  rows. The three fixed role names are enforced by a database check constraint.
- Customer emails, staff emails, and service names are **non-unique** within a tenant. Do not add a
  unique constraint the DBML does not have.
- User email is globally unique, lowercased.
- `staff_availability.end_time` must store and round-trip `24:00:00`. Choose a PostgreSQL-compatible
  representation that preserves it; do not silently coerce.
- A single stored availability row never crosses midnight.
- Payments tables exist from migration 003 but stay unused until the Phase 9 stretch gate.
- Bookings have no hard-delete path at the database or application level.

If an ORM representation cannot express something the DBML states, record the exception explicitly in
the model and tell me — do not change what the DBML means.
