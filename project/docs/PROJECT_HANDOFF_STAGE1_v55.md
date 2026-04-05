# PROJECT HANDOFF — STAGE 1 (v55)

## Current authoritative status
- mainline architecture: **overview-first**
- fixed farther-scale separator: **bidirectional rotation separator**
- carried-forward controlled layers:
  1. negative sign-aware fallback candidate
  2. positive trace-basis bridge candidate
  3. negative translation-margin guard candidate
  4. baseline-support guard candidate
  5. positive translation-margin guard candidate
  6. negative guard overreach restore candidate
- current harder-scale target panel status at `N288`:
  - seeds `7-16`: clean under the fixed v53 stack
  - seeds `17-24`: **not clean** under the fixed v53 stack (`v54` phase-2 expansion)

## What v54 actually tested
v54 did **not** add a new rule.
It carried the full fixed v53 stack forward unchanged and evaluated it on `N288 harder unseen-nuisance` target seeds `17-24`.

Results:
- seen overall: `1.000`
- seen translation: `1.000`
- N288 overall: `0.9625`
- N288 translation: `0.9792`
- target misclassifications: `3`

Remaining target errors split into two residual families:
- two cases of `rotation_z_pos_mid_sharp -> translation_x_pos`
- one case of `translation_x_neg_early_soft -> baseline`

## What v55 actually did
v55 is a **structured audit**, not a new compensator.
It localized the v54 residuals into two separate atlas families:

- **ATLAS-R7 — N288 phase2 positive guard overreach into true rotation**
  - repeated family
  - canonical cases:
    - `N288 / seed 19 / rotation_z_pos_mid_sharp -> translation_x_pos`
    - `N288 / seed 23 / rotation_z_pos_mid_sharp -> translation_x_pos`
  - reading: the fixed positive translation-margin guard is too permissive for a farther-scale mid-sharp rotation subset with very high curl

- **ATLAS-R8 — N288 phase2 negative early-soft spill to baseline**
  - isolated family for now
  - canonical case:
    - `N288 / seed 21 / translation_x_neg_early_soft -> baseline`
  - reading: this is a gate/basis spill into baseline, not a separator event

## What v55 means
- the fixed v53 stack did **not** survive a second harder target-seed expansion cleanly
- the first repeated new family is **R7**, not R8
- the next honest move is to study **R7 first**, because it repeats and is clearly a carried-forward stack boundary
- do **not** answer R8 with a mirrored quick patch yet

## Current honest boundary
The project now has evidence that the current controlled stack remains useful but not closed under broader `N288 harder` seed expansion. The current boundary is not general physical-core collapse. It is a carried-forward readout-side stack boundary with one repeated positive overreach family and one isolated negative spill family.

## Authoritative next task
**Run N288 harder phase-2 positive guard overreach controlled study**.
Study `ATLAS-R7` first.
Do not retune separator, fallback, bridge, or any existing thresholds globally before that study.
