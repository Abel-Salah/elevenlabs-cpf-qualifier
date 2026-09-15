from qualifier.models import Enquiry, Funding, Status
from qualifier.rules import evaluate

BASE = dict(full_name="Marie Durand", phone="+33600000000", certified_training=True)


def make(**kwargs) -> Enquiry:
    return Enquiry.from_payload({**BASE, **kwargs})


def test_private_employee_large_company_routes_to_opco_and_cpf():
    decision = evaluate(make(status="private_employee", employer_size=250))
    assert decision.routes == [Funding.OPCO, Funding.CPF]
    assert decision.handoff is False


def test_small_employer_is_handed_to_a_human():
    decision = evaluate(make(status="private_employee", employer_size=12))
    assert decision.handoff is True
    assert "under 50" in decision.reason


def test_non_certified_course_removes_the_cpf_route():
    decision = evaluate(make(status="private_employee", employer_size=250, certified_training=False))
    assert Funding.CPF not in decision.routes


def test_public_employee_without_certified_course_has_no_public_route():
    decision = evaluate(make(status="public_employee", certified_training=False))
    assert decision.routes == [Funding.SELF_FUNDED]


def test_jobseeker_routes_to_france_travail_first():
    decision = evaluate(make(status="jobseeker"))
    assert decision.routes[0] is Funding.FRANCE_TRAVAIL


def test_self_employed_routes_to_their_faf():
    decision = evaluate(make(status="self_employed"))
    assert decision.routes[0] is Funding.FAF


def test_apprentice_routes_to_opco_only():
    decision = evaluate(make(status="apprentice"))
    assert decision.routes == [Funding.OPCO]


def test_missing_phone_is_reported_and_forces_handoff():
    decision = evaluate(Enquiry.from_payload({"full_name": "X", "status": "jobseeker", "certified_training": True}))
    assert "phone" in decision.missing
    assert decision.handoff is True


def test_unknown_status_yields_no_route():
    decision = evaluate(make(status="not_a_status"))
    assert decision.routes == []
    assert decision.handoff is True


def test_garbled_employer_size_does_not_crash():
    decision = evaluate(make(status="private_employee", employer_size="a lot"))
    assert "employer_size" in decision.missing


def test_score_rewards_a_complete_fundable_enquiry():
    poor = evaluate(make(status="public_employee", certified_training=False))
    rich = evaluate(make(status="private_employee", employer_size=250, email="m@d.fr", course="Anglais pro"))
    assert rich.score > poor.score
