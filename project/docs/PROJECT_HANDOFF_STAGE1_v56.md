# PROJECT HANDOFF — STAGE 1 (v56)

## Current authoritative status
- mainline architecture: **overview-first**
- fixed farther-scale stack: **v55 stack**
- `N288 harder` phase-2 target seeds `17-24`: **not clean** under the fixed v53/v55 stack
- repeated open family: **ATLAS-R7 positive guard overreach into true rotation**
- isolated family still atlas-only: **ATLAS-R8 negative early-soft spill to baseline**

## What v56 actually did
v56 is a **candidate-definition audit**, not a repaired-panel claim.
It defines a single seen-scale-only restore candidate for `ATLAS-R7`:
- `positive_guard_overreach_restore`
- applies when the positive translation-margin guard would trigger and `hhd_curl_energy_peak_abs > 3.8`

## Why that candidate is admissible
Seen-scale support shows an open curl gap between:
- seen `translation_x_pos_mid_sharp` max curl = `1.754943`
- seen `rotation_z_pos_mid_sharp` min curl = `3.863997`

The proposed restore floor `3.8` lies inside that gap, so it targets a high-curl regime that is outside seen positive-translation support.

## What v56 actually established
- the candidate is **silent** on the earlier broader-panel positive true-translation guard activations (`seeds 7-16`)
- the candidate **would activate** on both repeated `R7` phase-2 cases (`seed 19`, `seed 23`)
- v56 does **not** claim that the panel is already repaired, because a fresh raw end-to-end validation was not completed in this session

## Current honest boundary
The project still does not have a verified repaired result for `N288 harder phase-2`.
What it has now is a narrow, seen-scale-only candidate for the repeated family `R7`.
That is enough to justify raw validation, but not enough to narrate success.

## Authoritative next task
**Run N288 harder phase-2 positive guard overreach raw validation.**
Do not retune separator or any carried-forward thresholds globally before that validation.
Keep `ATLAS-R8` atlas-only until it repeats or survives a dedicated gate/basis audit.
