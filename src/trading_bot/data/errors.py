"""Fail-closed exceptions for the Phase 02 data kernel."""


class DataContractError(ValueError):
    """A record violates a declared data contract."""


class PointInTimeError(DataContractError):
    """A point-in-time query cannot be answered safely."""


class IdentityConflictError(DataContractError):
    """Instrument or alias history is ambiguous."""


class ImmutableStorageError(RuntimeError):
    """An immutable snapshot or manifest operation would overwrite data."""


class CalendarError(DataContractError):
    """Exchange-session data are missing, ambiguous, or inconsistent."""


class UniverseBuildError(DataContractError):
    """A monthly universe cannot be frozen safely."""


class LeakageError(DataContractError):
    """Future or untraceable information entered a historical decision."""
