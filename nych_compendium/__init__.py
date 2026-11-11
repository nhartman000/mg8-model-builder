"""Streaming D2 typo-compendium builder.

Interpreted program name: ``python -m nych_compendium``. Counts can be built
without a smoothing method. Probabilities stay unset until the owner names one.
"""

from nych_compendium.build import SmoothingRefused, build_compendium
from nych_compendium.gate import automatic_correction_allowed, lower_bound

__all__ = [
    "SmoothingRefused",
    "automatic_correction_allowed",
    "build_compendium",
    "lower_bound",
]
