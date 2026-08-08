from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from trading_bot.platform.event_journal import SQLiteEventJournal
from trading_bot.platform.leads import LeadLifecycleState
from trading_bot.platform.replay import ReplayEngine, TradeLeadProjector, trade_lead_snapshot_event
from trading_bot.platform.research_console import build_fixture_console


def test_pf01_leads_survive_persistent_journal_restart_and_replay(tmp_path: Path) -> None:
    console = build_fixture_console()
    source_leads = console._snapshot.leads
    path = tmp_path / "platform-events.sqlite3"

    journal = SQLiteEventJournal(path)
    offset = 0
    for lead in source_leads:
        event = trade_lead_snapshot_event(lead)
        journal.append(event, recorded_at=event.occurred_at + timedelta(seconds=1 + offset))
        offset += 1
    first = ReplayEngine(TradeLeadProjector()).replay_journal(journal)
    first_head = journal.head_hash
    journal.close()

    reopened = SQLiteEventJournal(path)
    second = ReplayEngine(TradeLeadProjector()).replay_journal(reopened)
    assert reopened.verify_integrity() == first_head
    assert first.state_hash == second.state_hash
    assert first.snapshot == second.snapshot
    assert [lead.content_hash for lead in second.state.book.all()] == [
        lead.content_hash for lead in sorted(source_leads, key=lambda item: item.lead_id)
    ]


def test_replaying_lead_lifecycle_after_restart_preserves_monotonic_history(tmp_path: Path) -> None:
    console = build_fixture_console()
    qualified = next(lead for lead in console._snapshot.leads if lead.state == LeadLifecycleState.QUALIFIED)
    planned = qualified.with_allocation(proposed_weight="0.16", proposed_shares=2).transition(
        to_state=LeadLifecycleState.PLANNED,
        changed_at=qualified.decision_at + timedelta(minutes=5),
    )
    path = tmp_path / "lead.sqlite3"

    first_event = trade_lead_snapshot_event(qualified)
    journal = SQLiteEventJournal(path)
    journal.append(first_event, recorded_at=first_event.occurred_at + timedelta(seconds=1))
    journal.close()

    reopened = SQLiteEventJournal(path)
    second_event = trade_lead_snapshot_event(planned, causation_id=first_event.event_id)
    reopened.append(second_event, recorded_at=second_event.occurred_at + timedelta(seconds=1))
    result = ReplayEngine(TradeLeadProjector()).replay_journal(reopened)
    latest = result.state.book.get(qualified.lead_id)
    assert latest is not None
    assert latest.state == LeadLifecycleState.PLANNED
    assert len(latest.transition_history) == len(planned.transition_history)
