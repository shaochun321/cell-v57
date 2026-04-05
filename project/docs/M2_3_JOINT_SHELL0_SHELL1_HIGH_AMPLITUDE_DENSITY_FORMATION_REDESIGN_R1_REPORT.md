# M2.3 — joint shell0/shell1 high-amplitude density formation redesign

## Decision
- **Decision:** `continue_inner_core_material_redesign`
- **Why:** This branch materially strengthens the joint `shell_0 / shell_1` positive-`x` inner-core density, improves both raw and final `seed8 translation_x_pos` active amplitude over M2.2, and preserves the `translation_x_neg` sign and `rotation_z` guardrails.

## What changed
- Added a targeted `mirror_channel_atlas` redesign path that only activates when the full positive `x` continuity chain (`shell_0..3`) is already present.
- In that regime, jointly raised the `shell_0` and `shell_1` positive `x` carrier polarity density instead of only reinforcing `shell_0` in isolation.
- Kept the redesign bounded to the inner-core source path; no new generic summary microblend was added.

## Key outcomes
- Round 52 frozen `seed8` final active `x` mean: `0.03719192219898326`
- Round 58 M2.2 `seed8` final active `x` mean: `0.028870438399823464`
- Round 59 M2.3 `seed8` final active `x` mean: `0.030372409939164347`
- Round 58 → Round 59 final mean delta: `0.0015019715393408822`
- Round 58 → Round 59 joint inner-core density delta: `0.0074790727746675625`
- Round 52 frozen baseline gap remaining after Round 59: `0.006819512259818916`
- Active translation carrier count (`seed8`): `8`
- Carrier-floor pair count (`seed8`): `6`

## Interpretation
This is a **real upstream material gain** over M2.2.

The redesign did not merely alter summary readout. The raw `seed8 translation_x_pos` signal increased, and the average positive-`x` density across `shell_0 / shell_1` increased materially. That means the inner-core source itself got denser.

At the same time, this branch still sits **below the frozen Round 52 final mean**. So the remaining problem is no longer “missing inner-core continuity” or “missing shell0 source” in the basic sense; it is that the joint `shell_0 / shell_1` high-amplitude source still does not match the already-working Round 52 summary-equivalent level.

## Bottom line
- M2.3 is a **real upstream material gain** over M2.2.
- It preserves the important guardrails.
- It still does **not** beat the frozen Round 52 final readout.

The correct next step is to continue **inner-core material redesign**, with the focus moved from joint `shell_0 / shell_1` density formation to **inner-core high-amplitude distribution shaping** rather than any new summary-layer tweak.
