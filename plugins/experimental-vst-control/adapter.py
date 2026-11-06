"""Experimental, host-neutral CV/MIDI-to-builder-parameter adapter.

This is an adapter scaffold, not a VST binary or a hardware driver. The host
provides normalized control frames and applies the returned proposal only when
the selected module parameter is live-writable and authorized.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import isfinite
from typing import Callable, Deque, Mapping, Optional


@dataclass(frozen=True)
class ControlFrame:
    timestamp_s: float
    source_values: Mapping[str, float]
    beat_phase: Optional[float] = None
    beat_event: Optional[str] = None  # e.g. "kick" or "snare"


@dataclass(frozen=True)
class ParameterBinding:
    module_id: str
    parameter_path: str
    source_id: str
    source_min: float
    source_max: float
    target_min: float
    target_max: float
    max_slew_per_second: float
    prediction_horizon_ms: float = 20.0
    max_history_frames: int = 8


@dataclass(frozen=True)
class ControlProposal:
    module_id: str
    parameter_path: str
    timestamp_s: float
    observed_value: float
    predicted_value: float
    confidence: float
    beat_phase: Optional[float]
    beat_event: Optional[str]
    source_id: str


Predictor = Callable[
    [tuple[ControlFrame, ...], float, float, Optional[float], Optional[str]],
    tuple[float, float],
]


def _clamp(value: float, low: float, high: float) -> float:
    return min(high, max(low, value))


class VSTControlAdapter:
    """Binds one source to one module parameter and emits bounded proposals."""

    def __init__(self, binding: ParameterBinding, predictor: Optional[Predictor] = None):
        if not binding.module_id or not binding.parameter_path or not binding.source_id:
            raise ValueError("module_id, parameter_path, and source_id are required")
        if binding.source_min >= binding.source_max or binding.target_min >= binding.target_max:
            raise ValueError("source and target ranges must be increasing")
        if binding.max_slew_per_second <= 0 or binding.prediction_horizon_ms < 0:
            raise ValueError("slew must be positive and prediction horizon nonnegative")
        if binding.max_history_frames < 2:
            raise ValueError("max_history_frames must be at least 2")
        self.binding = binding
        self.predictor = predictor
        self._history: Deque[ControlFrame] = deque(maxlen=binding.max_history_frames)
        self._last_output: Optional[float] = None
        self._last_timestamp: Optional[float] = None

    def update(self, frame: ControlFrame) -> ControlProposal:
        raw = frame.source_values.get(self.binding.source_id)
        if raw is None or not isfinite(raw) or not isfinite(frame.timestamp_s):
            raise ValueError("frame must contain a finite value and timestamp for the bound source")
        if self._last_timestamp is not None and frame.timestamp_s <= self._last_timestamp:
            raise ValueError("control frames must have strictly increasing timestamps")

        normalized = _clamp(
            (raw - self.binding.source_min) / (self.binding.source_max - self.binding.source_min),
            0.0,
            1.0,
        )
        observed = self.binding.target_min + normalized * (self.binding.target_max - self.binding.target_min)
        self._history.append(frame)

        predicted_normalized, confidence = normalized, 0.0
        if self.predictor is not None:
            predicted_normalized, confidence = self.predictor(
                tuple(self._history),
                normalized,
                self.binding.prediction_horizon_ms,
                frame.beat_phase,
                frame.beat_event,
            )
            if not isfinite(predicted_normalized) or not isfinite(confidence):
                raise ValueError("predictor must return finite prediction and confidence")
        predicted_normalized = _clamp(predicted_normalized, 0.0, 1.0)
        confidence = _clamp(confidence, 0.0, 1.0)
        predicted = self.binding.target_min + predicted_normalized * (
            self.binding.target_max - self.binding.target_min
        )

        # Keep forecasts provisional: blend only by confidence and apply the
        # same per-second slew bound used for measured control movement.
        candidate = observed + confidence * (predicted - observed)
        if self._last_output is not None and self._last_timestamp is not None:
            elapsed = frame.timestamp_s - self._last_timestamp
            max_delta = self.binding.max_slew_per_second * elapsed
            candidate = _clamp(candidate, self._last_output - max_delta, self._last_output + max_delta)
        candidate = _clamp(candidate, self.binding.target_min, self.binding.target_max)

        self._last_output = candidate
        self._last_timestamp = frame.timestamp_s
        return ControlProposal(
            module_id=self.binding.module_id,
            parameter_path=self.binding.parameter_path,
            timestamp_s=frame.timestamp_s,
            observed_value=observed,
            predicted_value=candidate,
            confidence=confidence,
            beat_phase=frame.beat_phase,
            beat_event=frame.beat_event,
            source_id=self.binding.source_id,
        )
