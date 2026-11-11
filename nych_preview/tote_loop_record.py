"""Provisional presence check for one TOTE loop record. Stated, not approved.

The NYCH repo defines TOTE as Test–Operate–Test–Exit. Its migration stores
actor, action, object, and tool on ``tote_loop_elements`` and the modality
operator on ``tote_steps.operator_id``. That schema is not changed here.

This check only asks whether a record carries the four fields named by the
2026-11-10 10:01 PM ET statement: actor, action, modality operator, and object.
It does not choose field types, modality-operator values, or a database
engine. A field is missing when its key is absent or its value is None.
Empty strings and other present values are not judged.

Open, and not decided here: whether Test and Exit conditions belong on the
record; whether the object is a gestalt id; whether an actor may be implied;
and whether a tool satisfies the object field. The existing migration view
treats object or tool as one invariant. This check does not adopt that
substitution.
"""
from __future__ import annotations

from collections.abc import Mapping

REQUIRED_FIELDS = ("actor", "action", "modality_operator", "object")


class ToteLoopRecordError(ValueError):
    """Raised when a provisional loop record lacks one of the four fields."""

    def __init__(self, missing: tuple[str, ...]):
        self.missing = missing
        super().__init__("missing required TOTE fields: " + ", ".join(missing))


def require_tote_loop_fields(record: Mapping) -> None:
    """Reject a record that does not carry all four required fields."""
    if not isinstance(record, Mapping):
        raise TypeError("record must be a mapping")
    missing = tuple(name for name in REQUIRED_FIELDS if name not in record or record[name] is None)
    if missing:
        raise ToteLoopRecordError(missing)
