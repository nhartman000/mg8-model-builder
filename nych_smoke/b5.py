"""Read-only bridge to the NYCH repository's B5 GST implementation."""
from __future__ import annotations

from pathlib import Path
import sqlite3
from urllib.parse import quote
from typing import Any, Mapping, Sequence

from nych_smoke.upstream import gst_context_module


def lookup_gst(
    database_path: str | Path,
    *,
    domain_id: str,
    action_key: str,
    narrative: Mapping[str, Any] | None = None,
    provenance: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Call upstream B5 with explicit B4 outputs; never infer or write rows."""
    path = Path(database_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError("the configured TOTE database is unavailable")
    uri = "file:" + quote(path.as_posix(), safe="/") + "?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    try:
        result = gst_context_module().lookup_loop(
            connection,
            domain_id=domain_id,
            action_key=action_key,
            narrative=narrative,
            provenance=provenance,
        )
        return result.as_dict()
    finally:
        connection.close()
