"""Streaming D2 typo-compendium builder.

Interpreted program name: ``python -m nych_compendium``. Probabilities use
interpolated Modified Kneser-Ney, ``chen-goodman-mkn-interpolated-v1``.
"""

from nych_compendium.build import build_compendium
from nych_compendium.gate import automatic_correction_allowed, lower_bound
from nych_compendium.smoothing import SMOOTHING_ID, SmoothingUnavailable, probability

__all__ = [
    "SMOOTHING_ID",
    "SmoothingUnavailable",
    "automatic_correction_allowed",
    "build_compendium",
    "lower_bound",
    "probability",
]
