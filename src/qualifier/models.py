"""Domain models for the inbound training-enquiry qualifier."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class Status(str, Enum):
    """Employment status of the caller, as declared during the call."""

    PRIVATE_EMPLOYEE = "private_employee"
    PUBLIC_EMPLOYEE = "public_employee"
    JOBSEEKER = "jobseeker"
    SELF_EMPLOYED = "self_employed"
    APPRENTICE = "apprentice"
    UNKNOWN = "unknown"


class Funding(str, Enum):
    """Funding route the caller may be directed to."""

    CPF = "CPF"
    OPCO = "OPCO"
    FRANCE_TRAVAIL = "FRANCE_TRAVAIL"
    FAF = "FAF"
    SELF_FUNDED = "SELF_FUNDED"


@dataclass
class Enquiry:
    """What the voice agent collects before any routing decision is made."""

    status: Status = Status.UNKNOWN
    certified_training: bool | None = None  # RNCP / RS registered course
    employer_size: int | None = None
    company_name: str | None = None
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    course: str | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "Enquiry":
        """Build an Enquiry from a raw agent tool-call payload.

        Unknown or malformed values degrade to UNKNOWN / None rather than
        raising: a voice transcript is never guaranteed to be well formed.
        """
        raw_status = str(payload.get("status", "")).strip().lower()
        try:
            status = Status(raw_status)
        except ValueError:
            status = Status.UNKNOWN

        size = payload.get("employer_size")
        try:
            employer_size = int(size) if size is not None else None
        except (TypeError, ValueError):
            employer_size = None

        certified = payload.get("certified_training")
        if isinstance(certified, str):
            certified = certified.strip().lower() in {"true", "yes", "oui", "1"}

        return cls(
            status=status,
            certified_training=certified,
            employer_size=employer_size,
            company_name=payload.get("company_name"),
            full_name=payload.get("full_name"),
            email=payload.get("email"),
            phone=payload.get("phone"),
            course=payload.get("course"),
        )


@dataclass
class Decision:
    """Outcome of the rules engine. Never a promise of funding."""

    routes: list[Funding] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    handoff: bool = False
    reason: str = ""
    score: int = 0

    @property
    def complete(self) -> bool:
        return not self.missing

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["routes"] = [r.value for r in self.routes]
        data["complete"] = self.complete
        return data
