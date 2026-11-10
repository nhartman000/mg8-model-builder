"""Offline validator for one per-boundary GitSON declaration.

This package does not split or reassemble canon bundles. That transport
remains nhartman000/gitson- and mg8-engine src/mg8_engine/gitson.py.
"""
from .validator import (
    MAX_BYTES_EXCLUSIVE,
    SCHEMA_DIGEST,
    SCHEMA_ID,
    SCHEMA_PATH,
    validate_declaration,
)

__all__ = [
    "MAX_BYTES_EXCLUSIVE",
    "SCHEMA_DIGEST",
    "SCHEMA_ID",
    "SCHEMA_PATH",
    "validate_declaration",
]
