"""D12 inspector.

Interpreted program name: ``python -m nych_inspector``. No owner-specified
program name, report path, or diff format exists. This package reviews one
builder's evidence. It is not that builder, and it does not call
``gitson_boundary.validate_declaration``.
"""

from nych_inspector.review import review

__all__ = ["review"]
