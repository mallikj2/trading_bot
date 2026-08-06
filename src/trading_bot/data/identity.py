"""Stable instrument identity and effective-dated symbol aliases."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from .contracts import Instrument, SymbolAlias
from .errors import IdentityConflictError
from .time_utils import interval_contains, require_aware


def _intervals_overlap(left: SymbolAlias, right: SymbolAlias) -> bool:
    left_end = left.valid_to
    right_end = right.valid_to
    return (right_end is None or left.valid_from < right_end) and (
        left_end is None or right.valid_from < left_end
    )


class InstrumentMaster:
    """In-memory reference implementation of identity invariants."""

    def __init__(self) -> None:
        self._instruments: dict[UUID, Instrument] = {}
        self._aliases: list[SymbolAlias] = []

    def add_instrument(self, instrument: Instrument) -> None:
        existing = self._instruments.get(instrument.instrument_id)
        if existing is not None and existing != instrument:
            raise IdentityConflictError(f"instrument_id already has different data: {instrument.instrument_id}")
        self._instruments[instrument.instrument_id] = instrument

    def add_alias(self, alias: SymbolAlias) -> None:
        if alias.instrument_id not in self._instruments:
            raise IdentityConflictError("alias references an unknown instrument")
        for existing in self._aliases:
            if not _intervals_overlap(existing, alias):
                continue
            same_market_symbol = (
                existing.exchange == alias.exchange and existing.symbol == alias.symbol
            )
            same_instrument = existing.instrument_id == alias.instrument_id
            if same_market_symbol and not same_instrument:
                raise IdentityConflictError(
                    f"ambiguous ticker ownership for {alias.exchange}:{alias.symbol}"
                )
            if same_instrument and existing.exchange == alias.exchange:
                raise IdentityConflictError(
                    f"overlapping aliases for instrument {alias.instrument_id} on {alias.exchange}"
                )
        self._aliases.append(alias)
        self._aliases.sort(key=lambda item: (item.exchange, item.symbol, item.valid_from))

    def resolve(
        self,
        *,
        symbol: str,
        exchange: str,
        at: datetime,
        decision_at: datetime | None = None,
    ) -> UUID:
        instant = require_aware(at, "at")
        decision = require_aware(decision_at or at, "decision_at")
        matches = [
            alias
            for alias in self._aliases
            if alias.symbol == symbol
            and alias.exchange == exchange
            and interval_contains(instant, alias.valid_from, alias.valid_to)
            and alias.available_at <= decision
        ]
        if len(matches) != 1:
            raise IdentityConflictError(
                f"expected one identity for {exchange}:{symbol} at {instant.isoformat()}, found {len(matches)}"
            )
        return matches[0].instrument_id

    def aliases_for(self, instrument_id: UUID) -> tuple[SymbolAlias, ...]:
        if instrument_id not in self._instruments:
            raise IdentityConflictError("unknown instrument")
        return tuple(alias for alias in self._aliases if alias.instrument_id == instrument_id)
