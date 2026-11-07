"""Shared helpers for recognizing optional event-log columns."""

from typing import Iterable, Optional


SOURCE_EVENT_ID_ALIASES = {
    "source_event_id",
    "event_id",
    "eventid",
}


def find_source_event_id_column(fieldnames: Iterable[str]) -> Optional[str]:
    """Return the unique source event ID column, rejecting ambiguous aliases."""
    matches = [
        field
        for field in fieldnames
        if field is not None and field.strip().casefold() in SOURCE_EVENT_ID_ALIASES
    ]
    if len(matches) > 1:
        raise ValueError(
            "CSV contains multiple source event ID columns. Keep only one of: "
            "source_event_id, event_id, or eventID."
        )
    return matches[0] if matches else None
