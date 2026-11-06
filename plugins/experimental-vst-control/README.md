# Experimental VST Control Plugin for the Model Builder

Status: **EXPERIMENTAL / adapter scaffold**

This is a separate, optional plugin package for the model builder. It explores a VST-style live-control path: a CV, MIDI, beat-clock, or other continuous controller can steer one exposed parameter on one selected builder module. The binding is à la carte and can be changed without editing the target module.

The first control concept is beat-conditioned predictive feedback. The plugin keeps a very short history of normalized control states, estimates a near-future value from movement, and can pass beat phase or kick/snare events to an HDRP predictor hook. The prediction is provisional; the latest measured control value remains authoritative. A small bounded state history supports correction without delaying the control stream with a long playback buffer.

## Adapter path

`hardware or host input → normalized control frame → optional HDRP prediction → selected module/parameter proposal → trusted builder host`

The adapter does not access raw hardware voltages. A CV-capable interface or host must first condition and measure the signal, then provide calibrated numeric control frames. The builder host must expose a parameter catalog and decide whether to apply each proposal. The scaffold returns proposals; it does not execute an LLM call, modify model weights, or bypass MG8/G8SON gates.

## Binding model

A binding selects exactly one target pair:

```json
{
  "module_id": "builder-2-tokenizer",
  "parameter_path": "config.merge_threshold",
  "source_id": "cv-1",
  "source_range": [-5.0, 5.0],
  "target_range": [0.0, 1.0],
  "max_slew_per_second": 2.0,
  "prediction_horizon_ms": 20,
  "max_history_frames": 8
}
```

The module and parameter are examples only. A host should populate selectable targets from its live module catalog. Parameters that are not declared live-writable must be rejected. The adapter clamps values to the declared range and limits change rate; it never silently changes another parameter.

## Possibilities to explore

- **Live inference controls:** steer exposed generation, retrieval, or decoding parameters while output streams.
- **Builder-worker controls:** adjust a worker's declared experiment parameter or search range while it operates, with accepted changes recorded in its run trace.
- **Training and tuning:** sweep or nudge declared hyperparameters in a controlled experiment. The host should schedule updates at safe step or batch boundaries and record the exact state transition.
- **Evaluation and simulation:** change a simulation variable or visualization parameter in real time while the evaluator reports resulting state changes.
- **Rhythmic or cyclic control:** use beat phase/events as timing context for gestures; the same predictor hook can use another periodic clock for non-musical applications.
- **Multiple live targets:** instantiate separate bindings for separate module/parameter pairs. Each stays individually selectable and bounded.

Mutable policy, safety limits, gate outcomes, and authorization rules should not be exposed as ordinary live performance parameters. The plugin can propose experiment values; trusted builder logic decides which values are mutable and when they can take effect.

## Predictive control semantics

- The observed control frame and beat timing form the current state.
- An optional predictor (for example, an HDRP-backed callback) may propose a short-horizon future value using recent control deltas and rhythmic phase/events.
- Predictions are bounded and reversible. New measured input immediately supersedes a forecast; a stop or reversal should not leave a stale predicted value latched.
- A small recent-state window is retained for prediction and correction. It is not an accumulating audio/video feedback buffer.
- The host can return observed output features as feedback, but should return a compact state/error summary with timestamps rather than recursively replaying the entire generated media stream.
- Every proposal carries binding identity, observed/predicted values, timestamp, and confidence/provenance so the host can record a QSON event and accept, reject, or constrain it.

## Scope and safety boundary

This scaffold demonstrates the adapter seam and binding shape. It is not yet a VST2/VST3 binary, a CV driver, a full feedback controller, an HDRP implementation, or an integrated MG8PK runtime unit. Direct CV requires appropriate DC-coupled hardware and voltage conditioning; audio-rate FM must be sampled/decoded by a compatible host before it becomes a model-builder control frame. The builder's trusted host remains responsible for authorization, timing, gate checks, and application of parameter updates.
