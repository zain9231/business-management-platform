from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, TypedDict
from uuid import UUID, uuid5

RoleName = Literal["Administrator", "Manager", "Staff"]
ROLE_NAMES: tuple[RoleName, ...] = ("Administrator", "Manager", "Staff")

FACTORY_NAMESPACE = UUID("6b910a53-fc9f-53e9-a659-9a3fdf6bb592")
FACTORY_TIMESTAMP = datetime(2025, 1, 1, tzinfo=UTC)


class BusinessAttrs(TypedDict):
    id: UUID
    name: str
    business_type: str
    public_slug: str
    email: str
    phone: str
    address: str
    timezone: str
    currency: str
    logo_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RoleAttrs(TypedDict):
    id: UUID
    business_id: UUID
    name: RoleName


class UserAttrs(TypedDict):
    id: UUID
    business_id: UUID
    role_id: UUID
    name: str
    email: str
    password_hash: str
    is_active: bool
    last_login: datetime | None
    created_at: datetime
    updated_at: datetime


class TenantAttrs(TypedDict):
    business: BusinessAttrs
    roles: list[RoleAttrs]
    users: list[UserAttrs]


@dataclass(slots=True)
class FactorySequence:
    seed: str
    _counter: int = 0

    def next_uuid(self, kind: str) -> UUID:
        self._counter += 1
        return uuid5(FACTORY_NAMESPACE, f"{self.seed}:{kind}:{self._counter}")


def business_attrs(
    sequence: FactorySequence,
    *,
    name: str | None = None,
    timezone: str = "America/New_York",
    currency: str = "USD",
) -> BusinessAttrs:
    business_id = sequence.next_uuid("business")
    suffix = business_id.hex[:12]
    return {
        "id": business_id,
        "name": name or f"Business {suffix}",
        "business_type": "salon",
        "public_slug": f"business-{suffix}",
        "email": f"business-{suffix}@example.test",
        "phone": "+15550100000",
        "address": "100 Test Street",
        "timezone": timezone,
        "currency": currency,
        "logo_url": None,
        "is_active": True,
        "created_at": FACTORY_TIMESTAMP,
        "updated_at": FACTORY_TIMESTAMP,
    }


def role_attrs(
    sequence: FactorySequence,
    business_id: UUID,
    name: str,
) -> RoleAttrs:
    if name not in ROLE_NAMES:
        raise ValueError("role name must be Administrator, Manager, or Staff")
    role_name: RoleName = name
    return {
        "id": sequence.next_uuid(f"role:{role_name}"),
        "business_id": business_id,
        "name": role_name,
    }


def user_attrs(
    sequence: FactorySequence,
    business_id: UUID,
    role_id: UUID,
    *,
    email: str | None = None,
) -> UserAttrs:
    user_id = sequence.next_uuid("user")
    normalized_email = (
        email.strip().lower() if email is not None else f"user-{user_id.hex}@example.test"
    )
    return {
        "id": user_id,
        "business_id": business_id,
        "role_id": role_id,
        "name": f"User {user_id.hex[:12]}",
        "email": normalized_email,
        "password_hash": "$argon2id$v=19$m=65536,t=3,p=4$dGVzdA$dGVzdA",
        "is_active": True,
        "last_login": None,
        "created_at": FACTORY_TIMESTAMP,
        "updated_at": FACTORY_TIMESTAMP,
    }


def two_tenants(sequence: FactorySequence) -> tuple[TenantAttrs, TenantAttrs]:
    tenants: list[TenantAttrs] = []
    for _ in range(2):
        business = business_attrs(sequence)
        roles = [role_attrs(sequence, business["id"], name) for name in ROLE_NAMES]
        users = [user_attrs(sequence, business["id"], role["id"]) for role in roles]
        tenants.append({"business": business, "roles": roles, "users": users})
    return tenants[0], tenants[1]
