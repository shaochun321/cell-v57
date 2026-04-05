# RESIDUAL TAXONOMY AND RELATION HYPOTHESES — STAGE 1

## Why this file exists
The project now has enough farther-scale evidence that residuals should no longer be discussed only inside one-off report conclusions.
This file is the dedicated place for:
- naming residual families
- separating recoverable residuals from unresolved residuals
- recording hypotheses about how residuals relate to scale, profile, sign, overview basis, and physical observability

This document is **not** the mainline readout spec.
It is the project's structured notebook for residual classification and relation-tracing.

---

## Core rule
A residual is **not** automatically:
- proof of physical-core failure
- proof that information disappeared
- proof that the current panel is impossible
- proof that the current separator/fallback stack is wrong in general

A residual is first a **localized relation signal**.
The first job is to classify it.
Only after localization should the project decide whether it implies:
- a gate miss
- a sign miss
- a separator miss
- a basis / projection miss
- or a deeper physical observability limit

---

## Project-level interpretation rule
Residual discussion lives here because the project now needs a persistent place to separate two questions:

1. **Recoverability question**
   - can the residual be brought back into semantic recoverability under a low-complexity, seen-scale-only, non-probe-informed mapping?
2. **Relation question**
   - even if the residual is not currently recoverable, what does it reveal about the relation between:
     - scale
     - profile timing
     - sign geometry
     - interface observability
     - overview basis choice
     - drift structure

The second question is not a fallback topic. It is part of the research program.

---

## Residual family taxonomy (current Stage-1)
### A. Gate-boundary residual
Definition:
- the sample loses at stage-1 translation-vs-nontranslation separation by a narrow margin
- sign space and separator geometry may still remain coherent

Typical interpretation:
- current overview gate basis may be too weak or misprojected for that profile/scale region

### B. Sign-coherent spill
Definition:
- the sample first lands in the wrong coarse branch or baseline-like region
- but sign geometry remains strongly coherent toward the correct translation sign
- a controlled fallback may bridge it without seen-scale pollution

Typical interpretation:
- the information was not lost; the current gate projection was insufficient

### C. Separator residual
Definition:
- the sample is first classified as translation but has high curl / nontranslation geometry suggesting a rotation leak
- overview-side separator geometry, not translation sign logic, is the front line

Typical interpretation:
- coarse rotation-vs-translation geometry is present, but the mainline gate did not carve it out cleanly enough

### D. Basis / projection residual
Definition:
- the sample preserves semantic coherence in some auxiliary trace/timing/shape coordinates
- but exits the support of the current compact gate basis

Typical interpretation:
- the information may still be present in the response traces, but the current low-dimensional projection fails to expose it

### E. Physical observability residual
Definition:
- after repeated audits, the sample no longer retains clean support in current overview, sign, separator, or richer trace coordinates
- evidence begins to suggest that the interface/readout stack no longer receives enough recoverable structure

Typical interpretation:
- this is the point where deeper physical observability or bottom-layer robustness concerns become more credible

---

## Current named residuals
### 1. N224 `translation_x_neg_late_soft` residual
Observed case:
- `N224 / seed 9 / translation_x_neg_late_soft -> baseline`

Current classification history:
- first identified as a **narrow gate-boundary residual**
- then shown to remain **sign-coherent** toward `translation_x_neg`
- finally recovered by a **controlled negative sign-aware fallback** without seen-scale pollution on the tested panels

Current status:
- treat as a **recoverable sign-coherent spill**, not as evidence of global farther-scale collapse

### 2. N224 `translation_x_pos_late_balanced` residual
Observed case:
- `N224 / seed 9 / translation_x_pos_late_balanced -> baseline`

Current classification history:
- not a sign collapse
- not a rotation leak
- exits the compact positive late-balanced gate support
- recovered by a **richer temporal / trace positive bridge** on the tested harder-seed panel

Current status:
- treat as a **basis / projection residual** until more panels are checked
- do **not** mirror the negative fallback mechanically

---

## Current relation hypotheses
These are hypotheses, not established project facts.

### Hypothesis R1 — profile-sensitive late/soft regimes are the first place where compact gate bases lose support at farther scales
Reading:
- low-energy or late-arriving translation regimes may remain semantically present while dropping out of the current coarse gate support

### Hypothesis R2 — some farther-scale misses are projection failures rather than semantic destruction
Reading:
- the sample remains coherent in sign or trace geometry even after exiting the compact gate basis
- therefore the information may still exist in the measured response, but not in the current low-dimensional coordinates

### Hypothesis R3 — residual families are relation evidence, not merely cleanup targets
Reading:
- residuals may reveal structured links between scale growth, profile timing, shell-level propagation, and interface observability
- therefore residual classification is itself a valid research product, even before a clean recovery rule is promoted

---

## How this file should be used
### Use this file when:
- a new farther-scale miss appears
- a residual is recovered by a controlled fallback or richer basis probe
- the project needs to decide whether a miss belongs to gate / sign / separator / basis / physical-observability categories
- the team wants to record relation evidence without falsely promoting it to mainline mechanism

### Do not use this file to:
- silently promote emergency fixes to mainline rules
- claim a hypothesis is now a proved mechanism
- narrate every residual as either total failure or total victory

---

## Reporting discipline
Whenever a new residual is found, record:
1. the exact sample identity (`scale / seed / case / profile`)
2. the first failure layer (gate / sign / separator / basis)
3. whether sign geometry remains coherent
4. whether separator geometry remains coherent
5. whether a richer trace basis can recover it
6. whether the proposed recovery is seen-scale-only and non-polluting
7. whether the residual appears isolated or family-like across seeds/scales

This reporting rule is meant to prevent the project from collapsing all farther-scale misses into a single narrative.

## v39 residual-taxonomy note
The `translation_x_pos_late_balanced` residual family currently has a more refined status:
- on the N224 harder panel it can be made semantically recoverable by a sparse positive trace-basis bridge
- on the N224 standard seed-expansion panel the same bridge stays silent, implying the standard panel does not contain an active member of that residual family under the current rule stack
- this supports classifying the bridge as a **family-specific farther-scale support** rather than a global positive translation repair layer



## V40 residual note
The first beyond-N224 standard richer-profile probe at N256 introduces no new residuals on the current panel. This is itself a useful residual-classification fact: the next relation question shifts from “what family appeared?” to “does harder unseen nuisance at the same farther scale reintroduce a known family or create a new one?”



## V41 residual status note
The first N256 harder unseen-nuisance full-stack probe introduces no new residuals on seeds 7 and 8. Residual taxonomy therefore does not change class structure at v41; the main update is that the existing N224 residual families do not automatically recur under the first N256 harder probe.


## V42 residual note
The N256 harder unseen-nuisance seed expansion introduces no new residual families on target seeds `7,8,9,10,11,12`. Residual taxonomy therefore remains unchanged at v42; the update is a negative result in the useful sense that the existing N224 residual families do not automatically recur at the broader N256 harder seed set.
## V43 residual note
The N256 standard richer-profile seed expansion introduces no new residual families on target seeds `7,8,9,10,11,12`. Residual taxonomy therefore remains unchanged at v43; the useful update is again a negative one: the previously observed N224 residual families do not recur on the broader N256 standard seed set under the current fixed full stack.

## V44 residual pair
The first beyond-N256 standard probe adds a new residual pair at N288:
- a negative early-sharp translation sample crossing into rotation
- a baseline sample crossing into positive translation
These two residuals should not be treated as one family. Their coexistence, while all support layers stay silent, is evidence that the next step should be family-wise white-box audit rather than symmetric support invention.


## V45 update — N288 residual pair families
Two new residual families now appear at N288 standard richer-profile:
1. **separator overreach into true translation**
   - current exemplar: `translation_x_neg_early_sharp -> rotation_z_pos`
2. **baseline-edge leak into translation**
   - current exemplar: `baseline -> translation_x_pos`

These should be tracked separately in future audits and must not be merged into one coarse “farther-scale failure” bucket.


## v46 note — taxonomy vs atlas
This document defines residual classes. `RESIDUAL_CONDITION_ATLAS_STAGE1.md` is where concrete canonical cases and condition bundles are recorded.


## Update — N288 separator-overreach family
The N288 `translation_x_neg_early_sharp -> rotation_z_pos` family should now be classified as:
- residual class: **support-boundary overreach**
- subtype: **separator overreach into true translation**
- current recoverability status: **recoverable with a controlled seen-scale-only guard candidate**
- symmetry note: this family is not the same as baseline-edge leak and should not be bundled with it
