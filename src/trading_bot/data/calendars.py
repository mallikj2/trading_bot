"""Versioned exchange-session calendar primitives."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .contracts import ExchangeSession
from .errors import CalendarError


NEW_YORK = ZoneInfo("America/New_York")


class ExchangeCalendar:
    def __init__(self, sessions: list[ExchangeSession]) -> None:
        if not sessions:
            raise CalendarError("calendar requires at least one session")
        ordered = sorted(sessions, key=lambda item: item.session_date)
        keys = {(item.calendar_id, item.calendar_version) for item in ordered}
        if len(keys) != 1:
            raise CalendarError("calendar cannot mix identity or version")
        dates = [item.session_date for item in ordered]
        if len(dates) != len(set(dates)):
            raise CalendarError("duplicate session dates")
        self._sessions = ordered
        self._by_date = {item.session_date: item for item in ordered}
        self.calendar_id, self.calendar_version = next(iter(keys))

    def session(self, session_date: date) -> ExchangeSession:
        try:
            return self._by_date[session_date]
        except KeyError as exc:
            raise CalendarError(f"unknown exchange session: {session_date}") from exc

    def decision_at(self, session_date: date, delay_minutes: int = 30) -> datetime:
        if delay_minutes < 0:
            raise CalendarError("decision delay cannot be negative")
        return self.session(session_date).close_at + timedelta(minutes=delay_minutes)

    def next_session(self, session_date: date) -> ExchangeSession:
        for session in self._sessions:
            if session.session_date > session_date:
                return session
        raise CalendarError(f"no next session after {session_date}")

    def previous_session(self, session_date: date) -> ExchangeSession:
        candidates = [session for session in self._sessions if session.session_date < session_date]
        if not candidates:
            raise CalendarError(f"no previous session before {session_date}")
        return candidates[-1]

    def final_session_of_month(self, year: int, month: int) -> ExchangeSession:
        candidates = [
            session
            for session in self._sessions
            if session.session_date.year == year and session.session_date.month == month
        ]
        if not candidates:
            raise CalendarError(f"no sessions for {year:04d}-{month:02d}")
        return candidates[-1]

    def universe_freeze_at(self, effective_month: date, delay_minutes: int = 30) -> datetime:
        if effective_month.day != 1:
            raise CalendarError("effective_month must be the first day of a month")
        prior_day = effective_month - timedelta(days=1)
        prior_final = self.final_session_of_month(prior_day.year, prior_day.month)
        return prior_final.close_at + timedelta(minutes=delay_minutes)
