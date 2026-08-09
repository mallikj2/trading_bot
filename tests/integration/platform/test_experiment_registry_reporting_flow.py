from datetime import datetime, timezone

from trading_bot.platform.experiments import ExperimentDefinition, ExperimentRun, SQLiteExperimentRegistry, build_pf08_fixture_report

UTC=timezone.utc


def test_fixture_report_can_be_persisted_reopened_and_verified(tmp_path):
    report=build_pf08_fixture_report(as_of=datetime(2026,8,8,20,30,tzinfo=UTC))
    path=tmp_path/"registry.sqlite"
    expected_run_ids=[]
    expected_result_hashes=[]
    with SQLiteExperimentRegistry(path) as registry:
        for row in report["experiments"]:
            d=ExperimentDefinition.from_dict(row["definition"])
            r=ExperimentRun.from_dict(row["run"])
            registry.register_definition(d)
            registry.register_run(r)
            expected_run_ids.append(r.run_id)
            expected_result_hashes.append(r.result_hash)
        first=registry.verify()
    with SQLiteExperimentRegistry(path) as registry:
        second=registry.verify()
        reopened=registry.runs()
        assert first == second == {"status":"PASS","definitions":3,"runs":3}
        assert {run.run_id for run in reopened} == set(expected_run_ids)
        assert {run.result_hash for run in reopened} == set(expected_result_hashes)
