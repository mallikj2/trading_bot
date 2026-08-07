"""Machine-readable Phase 02 data-gate integration audit."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence

from .errors import DataContractError


class GateStatus(str, Enum):
    PASS = "PASS"
    CONDITIONAL = "CONDITIONAL"
    BLOCKED = "BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True, slots=True)
class PhaseGateEvidence:
    gate_id: str
    name: str
    status: GateStatus
    mandatory_for_phase03: bool
    evidence: tuple[str, ...] = ()
    note: str = ""

    def __post_init__(self) -> None:
        if not self.gate_id.strip() or not self.name.strip():
            raise DataContractError("gate_id and name are required")
        if self.mandatory_for_phase03 and self.status == GateStatus.NOT_APPLICABLE:
            raise DataContractError("mandatory Phase 03 gate cannot be NOT_APPLICABLE")


@dataclass(frozen=True, slots=True)
class Phase02GateAudit:
    ready_for_phase03: bool
    mandatory_pass_count: int
    mandatory_total_count: int
    blocked_gate_ids: tuple[str, ...]
    conditional_gate_ids: tuple[str, ...]

    @property
    def result(self) -> str:
        return "PASS" if self.ready_for_phase03 else "NOT_READY"


def audit_phase02_gates(gates: Sequence[PhaseGateEvidence]) -> Phase02GateAudit:
    if not gates:
        raise DataContractError("Phase 02 gate audit requires evidence rows")
    ids = [gate.gate_id for gate in gates]
    if len(ids) != len(set(ids)):
        raise DataContractError("duplicate Phase 02 gate_id")

    mandatory = [gate for gate in gates if gate.mandatory_for_phase03]
    blocked = tuple(sorted(gate.gate_id for gate in mandatory if gate.status == GateStatus.BLOCKED))
    conditional = tuple(sorted(gate.gate_id for gate in mandatory if gate.status == GateStatus.CONDITIONAL))
    passed = sum(gate.status == GateStatus.PASS for gate in mandatory)
    ready = passed == len(mandatory) and not blocked and not conditional
    return Phase02GateAudit(
        ready_for_phase03=ready,
        mandatory_pass_count=passed,
        mandatory_total_count=len(mandatory),
        blocked_gate_ids=blocked,
        conditional_gate_ids=conditional,
    )


def assert_phase03_authorized(gates: Sequence[PhaseGateEvidence]) -> None:
    audit = audit_phase02_gates(gates)
    if not audit.ready_for_phase03:
        details = ", ".join(audit.blocked_gate_ids + audit.conditional_gate_ids)
        raise DataContractError(f"Phase 03 is not authorized; unresolved Phase 02 gates: {details}")
