"""Load the authoritative NYCH module implementations from their own repo.

The builder repo must not copy or reimplement B1/B5.  The build runner sets
``NYCH_MODEL_SRC`` to the sibling checkout's ``src`` directory; a conventional
sibling checkout is also supported for local development.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
from types import ModuleType


def nych_model_src() -> Path:
    configured = os.environ.get("NYCH_MODEL_SRC")
    candidates = [Path(configured)] if configured else []
    candidates.append(Path(__file__).resolve().parents[2] / "nych-language-model" / "src")
    for candidate in candidates:
        root = candidate.expanduser().resolve()
        if (root / "nych_language_model" / "pipeline" / "ingest.py").is_file():
            return root
    raise FileNotFoundError(
        "NYCH model source is unavailable; set NYCH_MODEL_SRC to the "
        "nych-language-model/src directory"
    )


def load_nych_module(relative_path: str, module_name: str) -> ModuleType:
    """Load one source module by path without copying it into this repository."""
    path = nych_model_src() / "nych_language_model" / "pipeline" / relative_path
    existing = sys.modules.get(module_name)
    if existing is not None:
        return existing
    if not path.is_file():
        raise FileNotFoundError(f"NYCH module is missing: {path.name}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load NYCH module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(module_name, None)
        raise
    return module


def ingest_bytes(*args, **kwargs):
    """Call B1's source-of-truth implementation from the NYCH repo."""
    module = load_nych_module("ingest.py", "_nych_upstream_ingest")
    return module.ingest_bytes(*args, **kwargs)


def gst_context_module() -> ModuleType:
    """Return B5's source-of-truth module from the NYCH repo."""
    return load_nych_module("gst_context.py", "_nych_upstream_gst_context")
