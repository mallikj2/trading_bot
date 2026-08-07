from pathlib import Path

import yaml

from trading_bot.data.gates import GateStatus, PhaseGateEvidence, audit_phase02_gates


def test_machine_readable_phase02_gate_snapshot_is_not_ready_for_phase03():
    root = Path(__file__).resolve().parents[3]
    payload = yaml.safe_load((root / "configs/data/phase02_data_gate_audit.yaml").read_text())
    gates = [
        PhaseGateEvidence(
            gate_id=row["id"],
            name=row["name"],
            status=GateStatus(row["status"]),
            mandatory_for_phase03=True,
            evidence=(row.get("evidence", row.get("reason", "documented")),),
            note=row.get("reason", ""),
        )
        for row in payload["mandatory_gates"]
    ]
    audit = audit_phase02_gates(gates)
    assert audit.ready_for_phase03 is False
    assert audit.mandatory_pass_count == payload["integration_result"]["pass"]
    assert len(audit.blocked_gate_ids) == payload["integration_result"]["blocked"]
    assert len(audit.conditional_gate_ids) == payload["integration_result"]["conditional"]
