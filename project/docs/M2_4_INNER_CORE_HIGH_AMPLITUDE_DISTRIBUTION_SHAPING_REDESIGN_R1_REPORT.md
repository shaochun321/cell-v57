# M2.4 — inner-core high-amplitude distribution shaping redesign

## What changed
This round stops chasing downstream summary patches and instead reshapes the **inner-core high-amplitude distribution** inside the atlas/source layer.

The redesign only activates when `shell_0/1/2/3` already form a positive `translation_like` `x` continuity chain. Under that condition it enforces a stronger radial amplitude shape for `shell_0`, `shell_1`, and `shell_2`:

- `shell_0` target polarity floor: `0.046`
- `shell_1` target polarity floor: `0.031`
- `shell_2` target polarity floor: `0.034`

No new learning layer, no new high-level interpretation layer, and no gate rewrite were added.

## Outcome
For `seed8 translation_x_pos`:

- final active mean: `0.030372409939164347 -> 0.037187900819361734`
- raw active mean: `0.030372409939164347 -> 0.037187900819361734`
- gap to frozen Round52 baseline: `0.006819512259818916 -> 0.0000040213796215285424`
- inner-core density (`shell_0/1/2` average active polarity): `0.028912678826403485 -> 0.038`

This effectively **matches the frozen Round52 baseline within tolerance** while keeping the material-source redesign path.

## Guardrails
Still preserved:

- `translation_x_pos` active dominant mode/axis = `translation_like / x`
- `translation_x_neg` active direction sign remains negative
- `rotation_z_pos` active dominant mode/axis = `rotation_like / z`
- `rotation_z_neg` active dominant mode/axis = `rotation_like / z`

## Decision
Freeze **M2.4** as the new material baseline.

The project is no longer in a pure summary-patch loop on this branch. The remaining open question is not whether the inner-core source exists, but how far source-first material redesign can outperform the old Round52 summary-equivalent stack.
