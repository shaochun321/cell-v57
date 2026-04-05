# M2 — inner-core source continuity redesign

## Decision
- **Decision:** `continue_material_redesign_not_summary_loop`
- **Why:** The redesign restored a real `shell_0` positive `x` carrier source in both active windows and removed the second active-window `static_like / z` semantic collapse. This is evidence of a source/domain fix rather than another summary patch.

## What changed
- Restored `shell_0:x` as a positive `translation_like` carrier in both active windows.
- Removed the requirement that inner-core restoration must wait for upstream process-level `translation_like / x` in the current window.
- Allowed active-window continuity to override a stale `static_like / z` atlas label when contiguous positive `x` carriers are already present.

## Key outcomes
- Baseline active positive `x` carriers: `6`
- Repaired active positive `x` carriers: `8`
- Baseline raw active `x` mean: `0.020663211884178058`
- Repaired raw active `x` mean: `0.025882873551830568`
- Baseline final active `x` mean: `0.037125198401364745`
- Repaired final active `x` mean: `0.027901552286239736`

## Interpretation
This branch **did** fix a real material/domain continuity defect:
- `shell_0` now participates as an inner-core `x` source.
- the second active window no longer collapses to `static_like / z` while `x` carriers are present.

At the same time, the final summary amplitude is still below the frozen Round 54 baseline. That means the remaining problem is no longer “no source” or “semantic collapse”. It is now a **true upstream amplitude-density problem** rather than a readout bug.

## Bottom line
This was **not** another bug-loop patch. It was a real source/continuity redesign. But it does **not** eliminate the amplitude gap to seed7.

The correct next step is to continue **material redesign**, not go back to generic summary microblends.
