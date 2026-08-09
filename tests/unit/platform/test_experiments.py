from datetime import date, datetime, timezone
from decimal import Decimal
import sqlite3

import pytest

from trading_bot.platform.experiments import (
    EvidenceClass,
    ExperimentContractError,
    ExperimentDefinition,
    ExperimentRegistryError,
    ExperimentRun,
    PerformanceAttribution,
    SQLiteExperimentRegistry,
    build_pf08_fixture_report,
    compare_runs,
)

UTC = timezone.utc


def definition(scenario: str = "BASE") -> ExperimentDefinition:
    return ExperimentDefinition.create(
        name=f"fixture-{scenario}", strategy_id="CSMOM-LS", strategy_version="0.2", scenario=scenario,
        purpose="test", code_commit="abc123", dataset_manifest_hash="a"*64,
        universe_manifest_hash="b"*64, parameter_manifest_hash="c"*64,
        cost_model_version="v1", acceptance_start=date(2024,1,2), acceptance_end=date(2024,3,28), random_seed=7,
    )


def attribution(cost: str = "-20") -> PerformanceAttribution:
    return PerformanceAttribution(Decimal("30"), Decimal("10"), {"spread": Decimal(cost)})


def run(d: ExperimentDefinition, *, cost: str = "-20", minute: int = 0) -> ExperimentRun:
    a = attribution(cost)
    return ExperimentRun.create(
        definition_id=d.definition_id, evidence_class=EvidenceClass.SYNTHETIC_FIXTURE,
        started_at=datetime(2026,8,8,20,minute,tzinfo=UTC), completed_at=datetime(2026,8,8,20,minute,30,tzinfo=UTC),
        source_runtime_hash="d"*64, artifact_hashes={"report":"e"*64},
        metrics={"net_return_bps": a.net_return_bps, "benchmark_return_bps":"5", "max_drawdown_bps":"-40", "sharpe":"0.2", "turnover_bps":"100"},
        attribution=a,
    )


def test_definition_id_is_deterministic():
    assert definition().definition_id == definition().definition_id


def test_definition_changes_when_scenario_changes():
    assert definition("BASE").definition_id != definition("COST_2X").definition_id


def test_definition_rejects_invalid_manifest_hash():
    with pytest.raises(ExperimentContractError):
        ExperimentDefinition.create(name="x",strategy_id="s",strategy_version="1",scenario="x",purpose="x",code_commit="x",dataset_manifest_hash="bad",universe_manifest_hash="b"*64,parameter_manifest_hash="c"*64,cost_model_version="x",acceptance_start=date(2024,1,1),acceptance_end=date(2024,1,2),random_seed=0)


def test_attribution_rejects_positive_cost_component():
    with pytest.raises(ExperimentContractError):
        PerformanceAttribution(Decimal("1"), Decimal("1"), {"spread": Decimal("1")})


def test_attribution_identity():
    a = attribution("-20")
    assert a.gross_return_bps == Decimal("40")
    assert a.total_cost_bps == Decimal("-20")
    assert a.net_return_bps == Decimal("20")


def test_run_rejects_metric_attribution_mismatch():
    d = definition()
    a = attribution()
    with pytest.raises(ExperimentContractError):
        ExperimentRun.create(definition_id=d.definition_id,evidence_class=EvidenceClass.SYNTHETIC_FIXTURE,started_at=datetime(2026,8,8,20,tzinfo=UTC),completed_at=datetime(2026,8,8,20,1,tzinfo=UTC),source_runtime_hash="d"*64,artifact_hashes={"x":"e"*64},metrics={"net_return_bps":"999","benchmark_return_bps":"0","max_drawdown_bps":"-1","sharpe":"0","turnover_bps":"1"},attribution=a)


def test_pf08_rejects_phase03_acceptance_evidence():
    d = definition()
    a = attribution()
    with pytest.raises(ExperimentContractError):
        ExperimentRun.create(definition_id=d.definition_id,evidence_class=EvidenceClass.PHASE03_ACCEPTANCE,started_at=datetime(2026,8,8,20,tzinfo=UTC),completed_at=datetime(2026,8,8,20,1,tzinfo=UTC),source_runtime_hash="d"*64,artifact_hashes={"x":"e"*64},metrics={"net_return_bps":a.net_return_bps,"benchmark_return_bps":"0","max_drawdown_bps":"-1","sharpe":"0","turnover_bps":"1"},attribution=a)


def test_run_round_trip_and_hashes():
    original = run(definition())
    restored = ExperimentRun.from_dict(original.to_dict())
    assert restored == original
    assert restored.result_hash == original.result_hash


def test_compare_runs_is_deterministic_and_delta_based():
    d1, d2 = definition("BASE"), definition("STRESS")
    r1, r2 = run(d1,cost="-20",minute=0), run(d2,cost="-30",minute=2)
    c1 = compare_runs([r2,r1], baseline_run_id=r1.run_id)
    c2 = compare_runs([r1,r2], baseline_run_id=r1.run_id)
    assert c1.comparison_hash == c2.comparison_hash
    row = next(row for row in c1.rows if row["run_id"] == r2.run_id)
    assert row["delta_net_return_bps"] == "-10"


def test_registry_is_append_only_idempotent_and_verifiable(tmp_path):
    d = definition(); r = run(d)
    with SQLiteExperimentRegistry(tmp_path/"experiments.sqlite") as registry:
        assert registry.register_definition(d) is True
        assert registry.register_definition(d) is False
        assert registry.register_run(r) is True
        assert registry.register_run(r) is False
        assert registry.verify() == {"status":"PASS","definitions":1,"runs":1}
        with pytest.raises(sqlite3.DatabaseError):
            registry._connection.execute("UPDATE experiment_runs SET result_hash='x'")


def test_registry_requires_definition_before_run(tmp_path):
    d=definition(); r=run(d)
    with SQLiteExperimentRegistry(tmp_path/"x.sqlite") as registry:
        with pytest.raises(ExperimentRegistryError):
            registry.register_run(r)


def test_registry_detects_tampering_if_trigger_is_removed(tmp_path):
    d=definition(); r=run(d)
    path=tmp_path/"x.sqlite"
    with SQLiteExperimentRegistry(path) as registry:
        registry.register_definition(d); registry.register_run(r)
        registry._connection.execute("DROP TRIGGER experiment_runs_no_update")
        registry._connection.execute("UPDATE experiment_runs SET result_hash=?", ("0"*64,))
        registry._connection.commit()
        with pytest.raises(ExperimentRegistryError):
            registry.verify()


def test_fixture_report_is_explicitly_not_strategy_evidence():
    report=build_pf08_fixture_report(as_of=datetime(2026,8,8,20,30,tzinfo=UTC))
    assert report["status"] == "PASS"
    assert report["strategy_profitability_validated"] is False
    assert report["phase03_acceptance_backtest"] is False
    assert all(row["label"] == "NOT_STRATEGY_EVIDENCE" for row in report["experiments"])
    assert len(report["experiments"]) == 3
