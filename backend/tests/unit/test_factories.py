from datetime import UTC
from uuid import UUID

import pytest

from tests.factories import (
    FactorySequence,
    business_attrs,
    role_attrs,
    two_tenants,
    user_attrs,
)


def test_factory_sequence_is_deterministic_and_collision_free() -> None:
    first = FactorySequence("repeatable-test")
    second = FactorySequence("repeatable-test")

    first_values = [first.next_uuid("business") for _ in range(3)]
    second_values = [second.next_uuid("business") for _ in range(3)]

    assert first_values == second_values
    assert len(set(first_values)) == 3
    assert all(isinstance(value, UUID) for value in first_values)


def test_business_attrs_match_referenced_dbml_fields() -> None:
    business = business_attrs(FactorySequence("business-fields"))

    assert set(business) == {
        "id",
        "name",
        "business_type",
        "public_slug",
        "email",
        "phone",
        "address",
        "timezone",
        "currency",
        "logo_url",
        "is_active",
        "created_at",
        "updated_at",
    }
    assert business["timezone"] == "America/New_York"
    assert business["currency"] == "USD"
    assert len(business["currency"]) == 3
    assert business["created_at"].tzinfo is UTC
    assert business["updated_at"].tzinfo is UTC


@pytest.mark.parametrize("invalid_name", ["Owner", "Admin", "", "staff"])
def test_role_attrs_reject_unknown_role_names(invalid_name: str) -> None:
    sequence = FactorySequence("invalid-role")

    with pytest.raises(ValueError, match="Administrator, Manager, or Staff"):
        role_attrs(sequence, sequence.next_uuid("business"), invalid_name)


def test_user_attrs_normalize_globally_unique_email() -> None:
    sequence = FactorySequence("user-emails")
    business_id = sequence.next_uuid("business")
    role_id = sequence.next_uuid("role")

    first = user_attrs(sequence, business_id, role_id, email="  USER@Example.COM ")
    second = user_attrs(sequence, business_id, role_id)

    assert first["email"] == "user@example.com"
    assert second["email"] == second["email"].lower()
    assert first["email"] != second["email"]


def test_two_tenants_supplies_two_businesses_all_roles_and_users() -> None:
    tenants = two_tenants(FactorySequence("tenant-pair"))

    assert len(tenants) == 2
    assert tenants[0]["business"]["id"] != tenants[1]["business"]["id"]
    assert {role["name"] for tenant in tenants for role in tenant["roles"]} == {
        "Administrator",
        "Manager",
        "Staff",
    }
    assert all(len(tenant["roles"]) == 3 for tenant in tenants)
    assert all(len(tenant["users"]) == 3 for tenant in tenants)
    assert len({user["email"] for tenant in tenants for user in tenant["users"]}) == 6
    for tenant in tenants:
        business_id = tenant["business"]["id"]
        roles_by_id = {role["id"]: role for role in tenant["roles"]}
        assert all(role["business_id"] == business_id for role in tenant["roles"])
        assert all(user["business_id"] == business_id for user in tenant["users"])
        assert all(user["role_id"] in roles_by_id for user in tenant["users"])
