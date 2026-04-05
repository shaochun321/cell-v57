# M2.2 — inner-core amplitude density redesign

## Decision
- **Decision:** `continue_inner_core_material_redesign`
- **Why:** This branch materially strengthens the restored `shell_0` positive `x` source and improves both raw and final `seed8 translation_x_pos` active amplitude while preserving the `translation_x_neg` sign and `rotation_z` guardrails.

## What changed
- Increased inner-core continuity restoration targets in `mirror_shell_interface` for `shell_0` active `x` sectors.
- Allowed `mirror_channel_atlas` to reinforce an already-restored but under-amplitude `shell_0` positive `x` carrier instead of only restoring from `static_like`.
- Kept the redesign bounded to the inner-core source path; no new generic summary microblend was added.

## Key outcomes
- Round 52 frozen `seed8` final active `x` mean: `0.03719192219898326`
- Round 57 M2 continuity `seed8` final active `x` mean: `0.027903613781007728`
- Round 58 M2.2 density `seed8` final active `x` mean: `0.028870438399823464`
- Round 57 → Round 58 final mean delta: `0.0009668246188157363`
- Round 57 → Round 58 raw mean delta: `0.0007500000000000007`
- Round 52 frozen baseline gap remaining after Round 58: `0.008321483799159798`
- Active translation carrier count (`seed8`): `8`
- Carrier-floor pair count (`seed8`): `6`

## Interpretation
This is **not** another summary-loop patch. The raw `seed8 translation_x_pos` signal increased, which means the inner-core source itself got stronger.

At the same time, the redesigned branch still sits **below the frozen Round 52 final mean**. So the remaining problem is not “no source” anymore; it is that the joint `shell_0 / shell_1` inner-core amplitude density is still too weak relative to the already-working Round 52 summary stack.

## Bottom line
- M2.2 is a **real upstream material gain** over M2 continuity.
- It preserves the important guardrails.
- It still does **not** beat the frozen Round 52 final readout.

The correct next step is to continue **inner-core material redesign**, with the focus moved from `shell_0` continuity to **joint `shell_0 / shell_1` high-amplitude density formation**.
