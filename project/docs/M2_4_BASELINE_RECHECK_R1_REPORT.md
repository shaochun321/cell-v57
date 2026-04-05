# M2.4 baseline recheck

## What this round does
This round does **not** add another redesign. It rechecks whether **M2.4** is strong enough to freeze as the new project baseline.

The recheck compares three concrete states from the same branch:

- **Round52 frozen reference**
- **Round59 (M2.3 joint shell0/shell1 density)**
- **Round60 (M2.4 inner-core high-amplitude distribution shaping)**

It only answers one decision question:

> Is M2.4 good enough to freeze as the new material baseline without reopening summary/gate patching?

## Outcome
Decision: **freeze_m2_4_as_project_baseline**

Headline:

> m2.4 reaches the frozen round52 x_pos baseline within tolerance while preserving source-first continuity and guardrails

### Core evidence
For `seed8 translation_x_pos`:

- Round52 frozen final active mean: `0.03719192219898326`
- Round59 final active mean: `0.030372409939164347`
- Round60 / M2.4 final active mean: `0.037187900819361734`

Key deltas:

- M2.4 minus M2.3 final mean: `0.006815490880197388`
- Round52 minus M2.4 gap: `4.0213796215285424e-06`
- Raw gain vs frozen Round52: `0.019855608995475477`

Source-side strength also improved:

- translation support: `0.4330941582110475 -> 0.5259714592893056`
- carrier floor pair count: `4 -> 6`
- translation carrier pair count: `5 -> 8`

## Guardrails
All required guardrails remain preserved:

- `translation_x_pos` stays `translation_like / x`
- `translation_x_neg` keeps negative sign
- `rotation_z_pos` stays `rotation_like / z`
- `rotation_z_neg` stays `rotation_like / z`

## Decision
Freeze **M2.4** as the new project baseline.

Recommended next step:

> freeze M2.4 as the new project baseline and only open M2.5 if it can outperform this baseline without reopening summary/gate patches

## Residual issue
m2.4 essentially closes the frozen round52 gap, but seed7-level superiority is still not reclaimed; future work must beat this baseline from the source side rather than re-opening summary patches
