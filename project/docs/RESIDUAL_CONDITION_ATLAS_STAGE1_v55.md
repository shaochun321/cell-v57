# RESIDUAL CONDITION ATLAS — STAGE 1 (v55)

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
- canonical cases:
  - `N288 / seed 10 / rotation_z_pos_early_soft -> translation_x_neg`
  - `N288 / seed 10 / rotation_z_pos_mid_sharp -> translation_x_neg`
  - `N288 / seed 12 / rotation_z_pos_early_soft -> translation_x_neg`
  - `N288 / seed 12 / rotation_z_pos_mid_sharp -> translation_x_neg`
- status: recoverable controlled family via negative guard overreach restore

### ATLAS-R7 — N288 phase2 positive guard overreach into true rotation
- canonical cases:
  - `N288 / seed 19 / rotation_z_pos_mid_sharp -> translation_x_pos`
  - `N288 / seed 23 / rotation_z_pos_mid_sharp -> translation_x_pos`
- morphology: **positive mid-sharp guard overreach into true rotation**
- separator status: suppressed by positive translation-margin guard
- current best interpretation: the carried-forward positive translation-margin guard is too permissive for a farther-scale mid-sharp rotation subset with very high curl
- current support status: **unresolved repeated family**
- project lesson: repeated families created by carried-forward guards should be studied before any isolated spill is patched

### ATLAS-R8 — N288 phase2 negative early-soft spill to baseline
- canonical case:
  - `N288 / seed 21 / translation_x_neg_early_soft -> baseline`
- morphology: **negative early-soft gate miss into baseline**
- separator status: quiet
- current best interpretation: the sample exits translation support before sign-aware or separator logic can help; this is a gate/basis spill, not a separator problem
- current support status: **atlas only for now**
- project lesson: do not answer isolated negative spills with a mirrored quick patch before they repeat or survive a dedicated gate/basis audit

## v55 update
`N288 harder` phase-2 target seeds `17-24` are **not clean** under the fixed v53 stack.
Practical consequence:
- the next authoritative task is **ATLAS-R7 controlled study**
- `ATLAS-R8` remains recorded but not yet promotable to controlled recovery work
