"""Funding-route rules for French vocational training enquiries.

Scope and honesty statement
---------------------------
These rules encode the *routing* logic a training provider uses on a first
inbound call: which funding body is worth contacting, and what information is
still missing before anyone's time is wasted.

They deliberately do NOT decide entitlement. Entitlement depends on the
caller's CPF balance, their employer's OPCO agreement, and France Travail
caseworker approval - none of which are knowable during a 90-second call.
The engine's job is to route and to flag, never to promise.

Reference points (public, stable):
  - CPF applies to a personal training account and covers courses registered
    with France Competences (RNCP or RS). A non-registered course is not
    CPF-fundable.
  - OPCO funding runs through the employer, so it is only relevant to
    employees of private-sector companies.
  - France Travail (formerly Pole emploi) handles jobseeker training aid.
  - Self-employed workers go through their own FAF (FIFPL, AGEFICE, etc.).
  - Apprenticeship contracts are funded through the OPCO via the CFA.
"""

from __future__ import annotations

from .models import Decision, Enquiry, Funding, Status

# An employer below this headcount is handled by a different OPCO budget line
# and, in practice, needs a human to walk the employer through the paperwork.
SMALL_EMPLOYER_THRESHOLD = 50

CONTACT_FIELDS = ("full_name", "phone")


def _missing_fields(enquiry: Enquiry) -> list[str]:
    missing = [f for f in CONTACT_FIELDS if not getattr(enquiry, f)]
    if enquiry.status is Status.UNKNOWN:
        missing.append("status")
    if enquiry.certified_training is None:
        missing.append("certified_training")
    if enquiry.status is Status.PRIVATE_EMPLOYEE and enquiry.employer_size is None:
        missing.append("employer_size")
    return missing


def _routes_for(enquiry: Enquiry) -> tuple[list[Funding], str]:
    certified = bool(enquiry.certified_training)

    if enquiry.status is Status.APPRENTICE:
        return [Funding.OPCO], "Apprenticeship contract: funded by the employer's OPCO via the CFA."

    if enquiry.status is Status.PRIVATE_EMPLOYEE:
        routes = [Funding.OPCO]
        if certified:
            routes.append(Funding.CPF)
        reason = "Private-sector employee: employer's OPCO is the primary route"
        if certified:
            reason += "; the course is registered, so CPF is a fallback."
        else:
            reason += "; the course is not registered, so CPF does not apply."
        return routes, reason

    if enquiry.status is Status.PUBLIC_EMPLOYEE:
        if certified:
            return [Funding.CPF], "Public-sector employee: CPF applies; no OPCO route exists."
        return [Funding.SELF_FUNDED], "Public-sector employee and the course is not registered: no public route."

    if enquiry.status is Status.JOBSEEKER:
        routes = [Funding.FRANCE_TRAVAIL]
        if certified:
            routes.append(Funding.CPF)
        return routes, "Jobseeker: France Travail is the primary route, subject to caseworker approval."

    if enquiry.status is Status.SELF_EMPLOYED:
        routes = [Funding.FAF]
        if certified:
            routes.append(Funding.CPF)
        return routes, "Self-employed: their own FAF (FIFPL, AGEFICE...) is the primary route."

    return [], "Status not established during the call."


def evaluate(enquiry: Enquiry) -> Decision:
    """Route an enquiry and decide whether a human should take over.

    Handoff is triggered by ambiguity, not by value: a small employer or a
    missing field costs more in a bad automated answer than in a callback.
    """
    missing = _missing_fields(enquiry)
    routes, reason = _routes_for(enquiry)

    handoff = bool(missing) or not routes
    if (
        enquiry.status is Status.PRIVATE_EMPLOYEE
        and enquiry.employer_size is not None
        and enquiry.employer_size < SMALL_EMPLOYER_THRESHOLD
    ):
        handoff = True
        reason += f" Employer under {SMALL_EMPLOYER_THRESHOLD} staff: routed to a human for the OPCO paperwork."

    score = 0
    if routes and Funding.SELF_FUNDED not in routes:
        score += 40
    if enquiry.certified_training:
        score += 25
    if enquiry.email:
        score += 15
    if enquiry.course:
        score += 10
    if not missing:
        score += 10

    return Decision(routes=routes, missing=missing, handoff=handoff, reason=reason.strip(), score=score)
