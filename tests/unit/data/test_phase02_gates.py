import pytest

from trading_bot.data.errors import DataContractError
from trading_bot.data.gates import (
    GateStatus,
    PhaseGateEvidence,
    assert_phase03_authorized,
    audit_phase02_gates,
)


def gate(gate_id, status, mandatory=True):
    return PhaseGateEvidence(gate_id, gate_id, status, mandatory, evidence=("test",))


def test_all_mandatory_pass_authorizes_phase03():
    rows = [gate("A", GateStatus.PASS), gate("B", GateStatus.PASS), gate("C", GateStatus.CONDITIONAL, False)]
    audit = audit_phase02_gates(rows)
    assert audit.ready_for_phase03
    assert audit.result == "PASS"
    assert_phase03_authorized(rows)


def test_blocked_or_conditional_mandatory_gate_prevents_phase03():
    rows = [gate("A", GateStatus.PASS), gate("B", GateStatus.BLOCKED), gate("C", GateStatus.CONDITIONAL)]
    audit = audit_phase02_gates(rows)
    assert not audit.ready_for_phase03
    assert audit.blocked_gate_ids == ("B",)
    assert audit.conditional_gate_ids == ("C",)
    with pytest.raises(DataContractError, match="Phase 03 is not authorized"):
        assert_phase03_authorized(rows)


def test_duplicate_gate_id_is_rejected():
    with pytest.raises(DataContractError, match="duplicate"):
        audit_phase02_gates([gate("A", GateStatus.PASS), gate("A", GateStatus.PASS)])


def test_mandatory_gate_cannot_be_not_applicable():
    with pytest.raises(DataContractError):
        gate("A", GateStatus.NOT_APPLICABLE)
