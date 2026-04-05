# PROJECT HANDOFF — STAGE 1 (v57)

## Current authoritative status
- mainline architecture: **overview-first**
- fixed farther-scale stack: **v57 stack**
- `ATLAS-R7` is now a **recoverable controlled family** via `positive_guard_overreach_restore`
- `N288 harder` phase-2 target seeds `17-24` are **still not fully clean** under the fixed v57 stack
- the only remaining open phase-2 family is **ATLAS-R8 negative early-soft spill to baseline**

## What v57 actually did
v57 is a **raw validation** of the v56 `positive_guard_overreach_restore` candidate.
The restore is applied only when:
- the positive translation-margin guard would trigger
- `hhd_curl_energy_peak_abs > 3.8`

## What v57 established
- seen panel stays clean: `1.000 / 1.000`
- phase-2 target panel improves to overall `0.988`, translation `0.979`
- both repeated `ATLAS-R7` cases are restored cleanly to `rotation_z_pos`
- the only remaining phase-2 target error is `N288 / seed 21 / translation_x_neg_early_soft -> baseline`

## Current honest boundary
The phase-2 panel is **still not fully clean**.
The project should not narrate v57 as farther-scale closure.
It only shows that the repeated `R7` family is recoverable without contaminating seen scales.

## Authoritative next task
**Run N288 harder phase-2 negative early-soft spill candidate-definition audit.**
Do not retune separator or any carried-forward thresholds globally before that audit.
Keep the new work strictly focused on `ATLAS-R8`.
