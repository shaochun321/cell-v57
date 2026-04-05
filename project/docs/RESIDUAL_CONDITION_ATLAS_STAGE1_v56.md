# RESIDUAL CONDITION ATLAS — STAGE 1 (v56)

## Current named farther-scale residual families

### ATLAS-R1 — N224 negative late-soft gate-boundary residual
- canonical case: `N224 / seed 9 / translation_x_neg_late_soft -> baseline`
- status: recoverable controlled family

### ATLAS-R2 — N224 positive late-balanced basis miss
- canonical case: `N224 / seed 9 / translation_x_pos_late_balanced -> baseline`
- status: recoverable controlled family

### ATLAS-R3 — N288 separator overreach into true translation
- canonical case: `N288 / seed 7 / translation_x_neg_early_sharp -> rotation_z_pos`
- status: recoverable controlled family via negative translation-margin guard

### ATLAS-R4 — N288 baseline-edge leak into translation
- canonical case: `N288 / seed 8 / baseline -> translation_x_pos`
- status: recoverable controlled family via baseline-support guard

### ATLAS-R5 — N288 positive separator overreach into true translation
- canonical case: `N288 / seed 7 / translation_x_pos_mid_sharp -> rotation_z_pos`
- status: recoverable controlled family via positive translation-margin guard

### ATLAS-R6 — N288 harder negative guard overreach into true rotation
- status: recoverable controlled family via negative guard overreach restore

### ATLAS-R7 — N288 phase2 positive guard overreach into true rotation
- canonical cases:
  - `N288 / seed 19 / rotation_z_pos_mid_sharp -> translation_x_pos`
  - `N288 / seed 23 / rotation_z_pos_mid_sharp -> translation_x_pos`
- morphology: **positive mid-sharp guard overreach into true rotation**
- separator status: suppressed by positive translation-margin guard
- current best interpretation: the carried-forward positive translation-margin guard is too permissive for a farther-scale high-curl mid-sharp rotation subset
- current support status: **seen-scale-only restore candidate defined; raw validation pending**
- v56 candidate: `positive_guard_overreach_restore` with `hhd_curl_energy_peak_abs > 3.8`
- project lesson: repeated carried-forward overreach families should first receive a narrow restore candidate, then a raw validation, not an immediate global retune

### ATLAS-R8 — N288 phase2 negative early-soft spill to baseline
- canonical case: `N288 / seed 21 / translation_x_neg_early_soft -> baseline`
- morphology: **negative early-soft gate miss into baseline**
- separator status: quiet
- current best interpretation: gate/basis spill into baseline before sign-aware or separator logic can help
- current support status: **atlas only**

## v56 update
`R7` now has a narrow candidate definition, but it is **not yet a verified recoverable family**.
Practical consequence:
- the next authoritative task is **R7 raw validation**
- `R8` remains recorded but not yet promotable to controlled recovery work
