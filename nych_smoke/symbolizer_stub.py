"""Test-only B6 boundary stub; it makes no LLM or network calls."""
from __future__ import annotations

from typing import Any, Mapping, Sequence


class LiteralSymbolizerStub:
    """Capture both channels in memory and return literal selections only.

    Tests may inspect ``calls`` to verify that GST and prompt remain separate.
    The stub has no serializer and must not be attached to QSON or reports.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[Mapping[str, Any], str]] = []

    def __call__(
        self,
        gst_context: Mapping[str, Any],
        natural_language_prompt: str,
        spans: Sequence[tuple[int, int]],
    ) -> list[dict[str, Any]]:
        if not isinstance(gst_context, Mapping):
            raise TypeError("GST context must be a mapping")
        if not isinstance(natural_language_prompt, str):
            raise TypeError("prompt must be text")
        prompt_bytes = natural_language_prompt.encode("utf-8")
        self.calls.append((gst_context, natural_language_prompt))
        output = []
        for start, end in spans:
            if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(prompt_bytes):
                raise ValueError("span must be a non-empty half-open UTF-8 byte range")
            output.append({"byte_start": start, "byte_end": end, "selection": "LITERAL", "reason": "TEST_STUB"})
        return output
