# RESIDUAL CONDITION ATLAS — STAGE 1 (v53)

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
- interpretation: the carried-forward negative translation-margin guard became too permissive on a farther-scale harder rotation family and had to be bounded by a curl ceiling restore rule
- status: recoverable controlled family via negative guard overreach restore

## v53 update
The broader `N288 harder` target-seed expansion through seeds `13-16` introduced **no new atlas family** under the fixed v52 stack.
Practical consequence:
- keep atlas discipline unchanged
- do not create a new family without a new residual
- the next honest pressure test is broader target seeds (`17-24`) rather than inventing a new mechanism in the absence of new failures
