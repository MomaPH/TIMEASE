"""
Tests for timease/engine/plans.py.

Covers:
- Plan dataclass and default plan values
- LimitsChecker: each check method at under / at / over limit
- LimitsChecker: -1 means unlimited
- LimitsChecker: upgrade hint when available_plans is populated

Run with:  uv run pytest
"""

from __future__ import annotations

import pytest

from timease.engine.plans import LimitsChecker, Plan, create_default_plans


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def default_plans() -> list[Plan]:
    return create_default_plans()


@pytest.fixture(scope="module")
def gratuit(default_plans: list[Plan]) -> Plan:
    return next(p for p in default_plans if p.name == "Gratuit")


@pytest.fixture(scope="module")
def standard(default_plans: list[Plan]) -> Plan:
    return next(p for p in default_plans if p.name == "Standard")


@pytest.fixture(scope="module")
def premium(default_plans: list[Plan]) -> Plan:
    return next(p for p in default_plans if p.name == "Premium")


@pytest.fixture(scope="module")
def checker_with_plans(default_plans: list[Plan]) -> LimitsChecker:
    return LimitsChecker(available_plans=default_plans)


@pytest.fixture(scope="module")
def checker_no_plans() -> LimitsChecker:
    return LimitsChecker()


# ---------------------------------------------------------------------------
# 1. Default plan values
# ---------------------------------------------------------------------------

class TestDefaultPlans:
    def test_three_plans_created(self, default_plans: list[Plan]) -> None:
        assert len(default_plans) == 3

    def test_plan_names(self, default_plans: list[Plan]) -> None:
        names = {p.name for p in default_plans}
        assert names == {"Gratuit", "Standard", "Premium"}

    # Gratuit
    def test_gratuit_max_classes(self, gratuit: Plan) -> None:
        assert gratuit.max_classes == 4

    def test_gratuit_max_teachers(self, gratuit: Plan) -> None:
        assert gratuit.max_teachers == 8

    def test_gratuit_max_rooms(self, gratuit: Plan) -> None:
        assert gratuit.max_rooms == 6

    def test_gratuit_max_constraints(self, gratuit: Plan) -> None:
        assert gratuit.max_constraints == 5

    def test_gratuit_max_generations(self, gratuit: Plan) -> None:
        assert gratuit.max_generations_per_month == 3

    def test_gratuit_max_ai_messages(self, gratuit: Plan) -> None:
        assert gratuit.max_ai_messages_per_month == 20

    def test_gratuit_max_collab_links(self, gratuit: Plan) -> None:
        assert gratuit.max_collab_links == 0

    def test_gratuit_export_formats(self, gratuit: Plan) -> None:
        assert gratuit.allowed_export_formats == ["excel"]

    def test_gratuit_price(self, gratuit: Plan) -> None:
        assert gratuit.price_monthly == 0.0

    # Standard
    def test_standard_max_classes(self, standard: Plan) -> None:
        assert standard.max_classes == 15

    def test_standard_max_teachers(self, standard: Plan) -> None:
        assert standard.max_teachers == 30

    def test_standard_max_rooms(self, standard: Plan) -> None:
        assert standard.max_rooms == 20

    def test_standard_all_export_formats(self, standard: Plan) -> None:
        assert set(standard.allowed_export_formats) == {
            "excel", "pdf", "word", "markdown"
        }

    # Premium
    def test_premium_unlimited_constraints(self, premium: Plan) -> None:
        assert premium.max_constraints == -1

    def test_premium_unlimited_generations(self, premium: Plan) -> None:
        assert premium.max_generations_per_month == -1

    def test_premium_unlimited_ai_messages(self, premium: Plan) -> None:
        assert premium.max_ai_messages_per_month == -1

    def test_premium_unlimited_collab_links(self, premium: Plan) -> None:
        assert premium.max_collab_links == -1

    def test_premium_max_classes(self, premium: Plan) -> None:
        assert premium.max_classes == 50

    def test_premium_max_teachers(self, premium: Plan) -> None:
        assert premium.max_teachers == 80

    def test_premium_max_rooms(self, premium: Plan) -> None:
        assert premium.max_rooms == 50


# ---------------------------------------------------------------------------
# 2. check_can_add
# ---------------------------------------------------------------------------

class TestCheckCanAdd:
    def test_under_limit_allowed(self, gratuit: Plan, checker_no_plans: LimitsChecker) -> None:
        ok, msg = checker_no_plans.check_can_add(gratuit, "classes", 3)
        assert ok is True
        assert msg is None

    def test_at_limit_blocked(self, gratuit: Plan, checker_no_plans: LimitsChecker) -> None:
        ok, msg = checker_no_plans.check_can_add(gratuit, "classes", 4)
        assert ok is False
        assert msg is not None
        assert "4" in msg
        assert "Gratuit" in msg

    def test_over_limit_blocked(self, gratuit: Plan, checker_no_plans: LimitsChecker) -> None:
        ok, msg = checker_no_plans.check_can_add(gratuit, "classes", 10)
        assert ok is False

    def test_unlimited_always_allowed(self, premium: Plan, checker_no_plans: LimitsChecker) -> None:
        # Premium has max_constraints = -1
        ok, msg = checker_no_plans.check_can_add(premium, "constraints", 9999)
        assert ok is True
        assert msg is None

    def test_unknown_entity_type_allowed(self, gratuit: Plan, checker_no_plans: LimitsChecker) -> None:
        ok, msg = checker_no_plans.check_can_add(gratuit, "unknown_entity", 100)
        assert ok is True
        assert msg is None

    def test_upgrade_hint_included(
        self, gratuit: Plan, checker_with_plans: LimitsChecker
    ) -> None:
        ok, msg = checker_with_plans.check_can_add(gratuit, "classes", 4)
        assert ok is False
        assert "Standard" in msg   # upgrade suggestion

    def test_no_upgrade_hint_without_plans(
        self, gratuit: Plan, checker_no_plans: LimitsChecker
    ) -> None:
        ok, msg = checker_no_plans.check_can_add(gratuit, "classes", 4)
        assert ok is False
        assert "Standard" not in msg

    @pytest.mark.parametrize("entity_type", ["teachers", "rooms", "constraints"])
    def test_all_entity_types_work(
        self, entity_type: str, gratuit: Plan, checker_no_plans: LimitsChecker
    ) -> None:
        ok, _ = checker_no_plans.check_can_add(gratuit, entity_type, 0)
        assert ok is True


# ---------------------------------------------------------------------------
# 3. check_can_generate
# ---------------------------------------------------------------------------

class TestCheckCanGenerate:
    def test_under_limit_allowed(self, gratuit: Plan, checker_no_plans: LimitsChecker) -> None:
        ok, msg = checker_no_plans.check_can_generate(gratuit, 2)
        assert ok is True

    def test_at_limit_blocked(self, gratuit: Plan, checker_no_plans: LimitsChecker) -> None:
        ok, msg = checker_no_plans.check_can_generate(gratuit, 3)
        assert ok is False
        assert "3" in msg

    def test_unlimited_always_allowed(self, premium: Plan, checker_no_plans: LimitsChecker) -> None:
        ok, msg = checker_no_plans.check_can_generate(premium, 99999)
        assert ok is True
        assert msg is None

    def test_upgrade_hint_included(
        self, gratuit: Plan, checker_with_plans: LimitsChecker
    ) -> None:
        ok, msg = checker_with_plans.check_can_generate(gratuit, 3)
        assert ok is False
        assert "Standard" in msg


# ---------------------------------------------------------------------------
# 4. check_can_export
# ---------------------------------------------------------------------------

class TestCheckCanExport:
    def test_allowed_format_accepted(self, gratuit: Plan, checker_no_plans: LimitsChecker) -> None:
        ok, msg = checker_no_plans.check_can_export(gratuit, "excel")
        assert ok is True
        assert msg is None

    def test_disallowed_format_rejected(self, gratuit: Plan, checker_no_plans: LimitsChecker) -> None:
        ok, msg = checker_no_plans.check_can_export(gratuit, "pdf")
        assert ok is False
        assert "pdf" in msg
        assert "Gratuit" in msg

    def test_all_formats_allowed_on_premium(
        self, premium: Plan, checker_no_plans: LimitsChecker
    ) -> None:
        for fmt in ("excel", "pdf", "word", "markdown"):
            ok, _ = checker_no_plans.check_can_export(premium, fmt)
            assert ok is True, f"format '{fmt}' unexpectedly blocked on Premium"


# ---------------------------------------------------------------------------
# 5. check_can_send_ai_message
# ---------------------------------------------------------------------------

class TestCheckCanSendAiMessage:
    def test_under_limit_allowed(self, gratuit: Plan, checker_no_plans: LimitsChecker) -> None:
        ok, _ = checker_no_plans.check_can_send_ai_message(gratuit, 19)
        assert ok is True

    def test_at_limit_blocked(self, gratuit: Plan, checker_no_plans: LimitsChecker) -> None:
        ok, msg = checker_no_plans.check_can_send_ai_message(gratuit, 20)
        assert ok is False
        assert "20" in msg

    def test_unlimited_always_allowed(self, premium: Plan, checker_no_plans: LimitsChecker) -> None:
        ok, _ = checker_no_plans.check_can_send_ai_message(premium, 99999)
        assert ok is True

    def test_upgrade_hint_included(
        self, gratuit: Plan, checker_with_plans: LimitsChecker
    ) -> None:
        ok, msg = checker_with_plans.check_can_send_ai_message(gratuit, 20)
        assert ok is False
        assert "Standard" in msg


# ---------------------------------------------------------------------------
# 6. check_can_create_collab_link
# ---------------------------------------------------------------------------

class TestCheckCanCreateCollabLink:
    def test_gratuit_blocks_first_link(
        self, gratuit: Plan, checker_no_plans: LimitsChecker
    ) -> None:
        # Gratuit has max_collab_links = 0, so even 0 current links → blocked
        ok, msg = checker_no_plans.check_can_create_collab_link(gratuit, 0)
        assert ok is False
        assert "0" in msg

    def test_standard_under_limit_allowed(
        self, standard: Plan, checker_no_plans: LimitsChecker
    ) -> None:
        ok, _ = checker_no_plans.check_can_create_collab_link(standard, 9)
        assert ok is True

    def test_standard_at_limit_blocked(
        self, standard: Plan, checker_no_plans: LimitsChecker
    ) -> None:
        ok, msg = checker_no_plans.check_can_create_collab_link(standard, 10)
        assert ok is False

    def test_premium_unlimited(
        self, premium: Plan, checker_no_plans: LimitsChecker
    ) -> None:
        ok, _ = checker_no_plans.check_can_create_collab_link(premium, 99999)
        assert ok is True

    def test_upgrade_hint_mentions_next_plan(
        self, gratuit: Plan, checker_with_plans: LimitsChecker
    ) -> None:
        ok, msg = checker_with_plans.check_can_create_collab_link(gratuit, 0)
        assert ok is False
        assert "Standard" in msg
