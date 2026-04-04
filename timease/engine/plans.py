"""
Subscription plans and limits checker for TIMEASE.

Plans define the feature limits for each school.  In production, plans are
stored in the database and loaded at runtime — never hardcoded in application
logic.  The LimitsChecker reads only from Plan objects, so limits can be
changed from the admin panel without touching code.

Use -1 for any integer limit to mean "unlimited".
"""

from __future__ import annotations

from dataclasses import dataclass, field


# Mapping: entity_type string → (Plan attribute name, French display name)
_ENTITY_ATTR: dict[str, tuple[str, str]] = {
    "classes":     ("max_classes",     "classes"),
    "teachers":    ("max_teachers",    "enseignants"),
    "rooms":       ("max_rooms",       "salles"),
    "constraints": ("max_constraints", "contraintes"),
}


@dataclass
class Plan:
    """
    A subscription plan that defines feature limits for a school.

    All integer fields accept -1 to mean "unlimited".
    Price fields use -1.0 when the price has not yet been set.
    """

    name: str
    max_classes: int
    max_teachers: int
    max_rooms: int
    max_constraints: int
    max_generations_per_month: int
    max_ai_messages_per_month: int
    max_collab_links: int
    allowed_export_formats: list[str]
    price_monthly: float


def create_default_plans() -> list[Plan]:
    """
    Return the three standard subscription plans.

    In production, load plans from the database instead of calling this
    function, so admins can edit them at runtime from the admin panel.
    """
    return [
        Plan(
            name="Gratuit",
            max_classes=4,
            max_teachers=8,
            max_rooms=6,
            max_constraints=5,
            max_generations_per_month=3,
            max_ai_messages_per_month=20,
            max_collab_links=0,
            allowed_export_formats=["excel"],
            price_monthly=0.0,
        ),
        Plan(
            name="Standard",
            max_classes=15,
            max_teachers=30,
            max_rooms=20,
            max_constraints=15,
            max_generations_per_month=20,
            max_ai_messages_per_month=100,
            max_collab_links=10,
            allowed_export_formats=["excel", "pdf", "word", "markdown"],
            price_monthly=9.99,  # TODO: set actual price
        ),
        Plan(
            name="Premium",
            max_classes=50,
            max_teachers=80,
            max_rooms=50,
            max_constraints=-1,
            max_generations_per_month=-1,
            max_ai_messages_per_month=-1,
            max_collab_links=-1,
            allowed_export_formats=["excel", "pdf", "word", "markdown"],
            price_monthly=29.99,  # TODO: set actual price
        ),
    ]


@dataclass
class LimitsChecker:
    """
    Checks whether an action is permitted under a given Plan.

    Pass ``available_plans`` to enable upgrade suggestions in error messages.
    All limits are read from the Plan object — never from constants.
    """

    available_plans: list[Plan] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _next_plan(self, current: Plan) -> Plan | None:
        """Return the cheapest plan more expensive than ``current``, if known."""
        higher = [
            p for p in self.available_plans
            if p.price_monthly > current.price_monthly
        ]
        return min(higher, key=lambda p: p.price_monthly, default=None)

    def _upgrade_hint(self, current: Plan, attr: str, display: str) -> str:
        """Build a French upgrade suggestion, or '' if no higher plan is known."""
        nxt = self._next_plan(current)
        if nxt is None:
            return ""
        limit = getattr(nxt, attr)
        limit_str = "illimité" if limit == -1 else str(limit)
        return (
            f" Passez au plan {nxt.name} pour en avoir jusqu'à "
            f"{limit_str} {display}."
        )

    # ------------------------------------------------------------------
    # Public check methods
    # ------------------------------------------------------------------

    def check_can_add(
        self,
        school_plan: Plan,
        entity_type: str,
        current_count: int,
    ) -> tuple[bool, str | None]:
        """
        Check whether adding one more entity of ``entity_type`` is allowed.

        ``entity_type`` must be one of: 'classes', 'teachers', 'rooms',
        'constraints'.
        """
        if entity_type not in _ENTITY_ATTR:
            return True, None  # unknown type — don't block
        attr, display = _ENTITY_ATTR[entity_type]
        limit = getattr(school_plan, attr)
        if limit == -1:
            return True, None
        if current_count >= limit:
            hint = self._upgrade_hint(school_plan, attr, display)
            return False, (
                f"Votre plan {school_plan.name} est limité à {limit} "
                f"{display}.{hint}"
            )
        return True, None

    def check_can_generate(
        self,
        school_plan: Plan,
        generations_this_month: int,
    ) -> tuple[bool, str | None]:
        """Check whether a new timetable generation is allowed this month."""
        limit = school_plan.max_generations_per_month
        if limit == -1:
            return True, None
        if generations_this_month >= limit:
            hint = self._upgrade_hint(
                school_plan, "max_generations_per_month", "génération(s)"
            )
            return False, (
                f"Votre plan {school_plan.name} est limité à {limit} "
                f"génération(s) par mois.{hint}"
            )
        return True, None

    def check_can_export(
        self,
        school_plan: Plan,
        format: str,
    ) -> tuple[bool, str | None]:
        """Check whether exporting in ``format`` is allowed by the plan."""
        if format in school_plan.allowed_export_formats:
            return True, None
        allowed_str = ", ".join(school_plan.allowed_export_formats)
        return False, (
            f"Le format d'export '{format}' n'est pas disponible dans votre "
            f"plan {school_plan.name}. Formats disponibles : {allowed_str}."
        )

    def check_can_send_ai_message(
        self,
        school_plan: Plan,
        messages_this_month: int,
    ) -> tuple[bool, str | None]:
        """Check whether sending one more AI message is allowed this month."""
        limit = school_plan.max_ai_messages_per_month
        if limit == -1:
            return True, None
        if messages_this_month >= limit:
            hint = self._upgrade_hint(
                school_plan, "max_ai_messages_per_month", "message(s) IA"
            )
            return False, (
                f"Votre plan {school_plan.name} est limité à {limit} "
                f"message(s) IA par mois.{hint}"
            )
        return True, None

    def check_can_create_collab_link(
        self,
        school_plan: Plan,
        current_links: int,
    ) -> tuple[bool, str | None]:
        """Check whether creating one more collaboration link is allowed."""
        limit = school_plan.max_collab_links
        if limit == -1:
            return True, None
        if current_links >= limit:
            hint = self._upgrade_hint(
                school_plan, "max_collab_links", "lien(s) collaboratif(s)"
            )
            return False, (
                f"Votre plan {school_plan.name} est limité à {limit} "
                f"lien(s) collaboratif(s).{hint}"
            )
        return True, None
