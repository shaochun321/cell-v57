# BACKUP AND REJECTED PATHS — STAGE 1

## Why this file exists
This file records options that were considered, partially used, or explicitly rejected, so the project does not loop back into already-audited dead ends.

## Hard rule
A rejected path is not always false forever.
It may be:
- rejected as mainline
- retained as backup
- retained as diagnostic layer
- retained as future hypothesis only

---

## 1. Rejected as current mainline: direct downstream patch accumulation
### Description
Continue repairing signed readouts by adding local summary/gate/sign fixes without changing the architecture.

### Why rejected
- created bug-loop behavior
- increased dependence on special-case logic
- obscured whether progress was physical or readout-side
- old M2.4 baseline became historical support, not a future direction

### Retained as
Historical comparison only.

---

## 2. Rejected as current mainline: medium/damping as the main fix
### Description
Treat effective-medium damping / drag / dissipation tuning as the central route to fixing scale drift.

### Why rejected
- improved some within-scale metrics
- but did not become the best cross-scale solution
- risked confusing “more damping” with “better semantics”

### Retained as
A valid control knob for later experiments.

---

## 3. Rejected as current mainline: full physical-core rewrite
### Description
Assume late failures prove the physical core is wrong and restart from the bottom.

### Why rejected
- many failures were shown to be recoverable at the readout layer
- N64/N96/N128 evidence repeatedly showed the physical body still carries usable response structure
- rewriting the physical core now would destroy comparability

### Retained as
A later-stage option only if overview/readout refactoring fails decisively.

---

## 4. Rejected as current mainline: direct complexity expansion
### Description
Add richer world factors, heat/vibration/full environment complexity, or higher neural layers before the response channel is stable.

### Why rejected
- would destroy interpretability
- would make it impossible to separate scale drift from world-complexity drift
- would amplify ambiguity in readout failures

### Retained as
Future stage only after Stage 1 equivalence goals are met.

---

## 5. Rejected as current mainline: TDA-first replacement of the readout
### Description
Replace the current readout stack primarily with topological data analysis / persistent homology.

### Why rejected
- intellectually interesting
- useful as a diagnostic or auxiliary layer
- but currently too abstract and too weakly matched to profile/sign-specific decoding needs
- would risk solving the wrong problem first

### Retained as
Optional diagnostic / appendicial analysis layer.

---

## 6. Rejected as current mainline: “theory says drift is solved” narrative
### Description
Upgrade analogies such as renormalization, metric flow, Ricci-flow-like dynamics, entropy growth, or thermalization into current project facts.

### Why rejected
- analogies are useful
- but they are not current project mechanisms
- promoting them too early would create false confidence and architectural drift

### Retained as
Appendix hypotheses only.

---

## 7. Rejected as promotable mainline: probe-informed rescue branches
### Description
Use the unseen target scale itself to select rescue thresholds or feature keys.

### Why rejected
- can work very well as engineering emergency branches
- but contaminates the claim of clean cross-scale generalization
- risks mistaking target-specific fitting for reusable mechanism

### Retained as
Emergency candidate / comparison branch only.

---

## 8. Rejected as sufficient answer: “clean seen-scale rescue exists, so problem solved”
### Description
A rescue rule derived only from N64/N96/N128 is automatically good enough if it improves over baseline hybrid at N160.

### Why rejected
- the clean seen-scale rescue candidate improved N160 over the old hybrid
- but remained clearly weaker than the probe-informed branch
- therefore clean derivation exists, but not yet at promotable strength

### Retained as
The basis for the next mechanism search.

---

## 9. Backup plan A — continue external-readout-only refinement
### Use when
- overview layer prototypes are not yet ready
- the team wants a conservative path

### What it means
- keep physical core frozen
- keep probe-informed rescue as emergency comparator
- continue looking for clean seen-scale rescue / sign observables / routing rules

### Risk
May yield diminishing returns.

---

## 10. Backup plan B — add a global overview layer in parallel
### Use when
- local feature patching reaches obvious ceiling
- drift seems to be caused by missing system-level summarization

### What it means
- keep current readout stack as a comparator
- add overview channels in parallel
- test whether global summaries reduce rescue complexity

### Candidate overview families
- global integrals
- HHD/HMF decomposition
- low-order spherical channels

### Risk
Could add complexity without sufficient gain if overview variables are poorly defined.

---

## 11. Backup plan C — bottom-layer robustness audit
### Use when
- overview/readout work stalls
- repeated drift patterns suggest the physical body itself may not sustain scale-robust semantics

### What it means
- revisit foam-mesh robustness
- revisit interface bundle coverage
- revisit whether the physical body truly contains stable observables across scale

### Risk
This is expensive and should not be triggered casually.

---

## 12. Current official status of major alternatives
- probe-informed rescue: **allowed candidate, not promotable**
- clean seen-scale rescue: **promising but insufficient**
- medium/damping: **control knob only**
- TDA-first: **diagnostic only**
- full physical-core rewrite: **not justified yet**
- global overview layer: **next main architectural experiment**


## 8. Rejected as current mainline: temporal-overview-only replacement
### Description
Replace the fixed overview candidate with a purely temporal overview branch using peak-time and early/late ratio descriptors.

### Why rejected
- fixed N160 early-sharp translation failures
- but leaked baseline into translation
- timing descriptors alone do not provide a sufficient global semantic basis

### Retained as
Diagnostic branch only.
Evidence that profile timing matters, but not enough to become the main overview mechanism.


## HHD-lite overview proxy (status)
This path is **not rejected**, but it is **not promoted**.
It currently sits between core backup and mainline candidate:
- better than local rescue in target-scale interpretability
- worse than the fixed overview candidate in seen-scale compatibility
Current status: keep as a branch for combination and comparison, not as a direct replacement.


## V21 caution
The N192 mid-balanced veto candidate must not be over-promoted. It is clean (seen-scale-only selected) and strong on the standard farther-scale panel, but it has not yet been stress-tested on harder N192 nuisance. Do not declare farther-scale generalization solved until that harder panel is run.


## V22 caution
The v21 N192 mid-balanced veto candidate is now confirmed to be **insufficient for harder farther-scale nuisance**.
It remains valid on the standard richer-profile farther-scale panel, but harder N192 nuisance shows that the farther-scale rotation-to-translation leak is not fully captured by a `mid_balanced`-only veto.

Practical consequence:
- do not treat the v21 veto rule as a general farther-scale solution
- do not overfit a new N192-specific patch using target labels
- the next acceptable move is a **seen-scale-only** harder-profile rotation separation study


## V23 caution
The generalized curl-veto candidate is stronger than the old `mid_balanced`-specific farther-scale veto because it clears both the standard richer-profile N192 panel and the harder N192 nuisance panel with one seen-scale-only rule.

But it still must not be over-promoted.
Practical consequence:
- do not claim full farther-scale invariance from two seeds alone
- prefer N192 seed expansion next, then another farther unseen scale
- keep the generalized curl veto low-complexity; do not silently regrow a large local rescue stack around it



## V24 caution
The new standard-panel N192 seed-9 success is useful positive evidence, but it must not be over-read. The candidate still needs **harder-nuisance N192 seed expansion** before stronger farther-scale robustness claims are made.


## V25 caution
The current generalized curl-veto candidate should not be over-promoted to “farther-scale solved.” It is now clear that the rule is strongest against the `translation_x_neg` leak family, but harder N192 seed expansion reveals two remaining seed-11 rotation-to-`translation_x_pos` leaks. The correct next move is a seen-scale-only bidirectional rotation safeguard, not reopening the physical core.



## V26 caution
The bidirectional farther-scale rotation-veto candidate is the strongest farther-scale rule so far because it clears every N192 panel currently tested with one fixed seen-scale-only threshold. But it still must not be over-promoted to “all farther scales solved.” Practical consequence:
- keep the rule fixed and low-complexity
- broaden standard N192 seed expansion next
- then move beyond N192 before making broader invariance claims


## V28 governance caution — patch-illusion overreach
The project must not confuse farther-scale separator success with proof that compensation has disappeared.

### Why this caution was added
- farther-scale results can look cleaner than they really are if the report only shows final accuracy
- score-only reporting can hide whether the result came from structured overview geometry or from silent separator accumulation

### Current rule
- every farther-scale report must describe both the physical-response side and the separator side
- a fixed seen-scale-only separator is allowed as evidence of structure
- but it must not be promoted into “physical core solved” language by default



## V29 caution
The `N224` standard seed-expansion result must not be misreported as either a full farther-scale victory or a farther-scale collapse. The current state is narrower:
- the fixed farther-scale separator survives the broadened `N224` seed set in general,
- but one late-soft negative-translation residual remains.
Therefore the next move is targeted residual diagnosis with the separator fixed, not immediate invention of another rule family and not premature route change.



## V30 caution
Do not misread the v29 residual as proof of generic farther-scale collapse. The focused audit shows it is a narrow late-soft negative-translation gate-boundary residual at `N224`, not a sign-readout failure and not a rotation-separator failure. The next response should be a constrained seen-scale-only boundary study, not a broad return to local rescue or a premature physical-core rewrite.


## V31 caution
Do not force a “seen-scale-only boundary fix” claim for the `N224 translation_x_neg_late_soft` residual if the proposed repair requires extrapolating beyond seen `translation_x_neg_late_soft` support on multiple gate axes. In that situation, the honest move is to treat the current gate family as underpowered for that residual and study a sign-aware or richer temporal/trace gate basis instead of narrating another narrow threshold tweak as clean generalization.


## V32 caution
The new sign-aware fallback candidate must not be confused with a new farther-scale mainline rule. It currently has clean evidence only on the N224 standard seed-expansion panel. Do not promote it beyond controlled fallback status until it is stress-tested on N224 harder unseen nuisance.


## V33 caution
The sign-aware fallback now survives both the N224 standard seed-expansion panel and the first N224 harder unseen-nuisance panel without spurious activation. This is stronger evidence than v32, but it still must not be over-promoted into a new farther-scale mainline rule. The remaining honest next step is broader harder-nuisance seed expansion, not victory language and not immediate route change.



## V34 caution
Do not over-promote the negative sign-aware fallback after the first N224 harder panel. Under harder seed expansion it remains controlled, but it is no longer fully closed: one positive-translation residual remains. Do not describe the current fallback as a sign-complete farther-scale solution until the sign asymmetry is explicitly audited.




## V35 caution
Do **not** mirror a negative farther-scale fallback into a positive fallback family merely because a single positive residual remains. If the positive residual exits seen positive-support geometry more substantially than the rescued negative spill, a mirrored fallback should be treated as target-informed unless clean seen-scale evidence is produced first.


## V36 caution
The project now has evidence that the remaining `translation_x_pos_late_balanced` farther-scale residual is not a clean mirror of the rescued negative spill. Therefore a mirrored positive fallback should be treated as **not yet justified**. If a future positive fallback is proposed, it must first show seen-scale support or stronger white-box evidence than the current isolated `seed 9` residual.


## V37 caution
The richer temporal / trace positive probe is **promising but not yet promoted**. It rescues the current N224 harder-seed positive late-balanced residual cleanly, but it has not yet been validated on N224 standard seed expansion or beyond-N224 farther unseen scale. Do not rewrite the main farther-scale stack around it until those checks are complete.

## V39 caution
The positive trace-basis bridge has now passed a clean N224 standard contamination probe, but that is still not equivalent to promotion. Do not collapse the distinction between:
- controlled farther-scale support that stays silent when not needed
- fully promoted mainline rule proven beyond the current farther-scale frontier
The next required test remains farther unseen scale validation beyond N224.




## V41 caution
The clean N256 harder first probe should not be over-read as proof that farther-scale support logic is fully settled. The next honest pressure test is seed expansion at N256 harder unseen nuisance; do not promote the positive trace-basis bridge beyond controlled-support status before that seed-expansion check.


## V42 caution
The clean N256 harder seed-expansion pass should not be over-read as proof that farther-scale support logic is fully settled or globally unnecessary. The next honest pressure test is N256 standard seed expansion (or another farther unseen scale) under the same fixed stack, not immediate victory language.

## V44 caution
The first N288 standard richer-profile probe is not clean under the fixed full stack. Do not treat N256 success as evidence that the same stack has already generalized to all farther unseen scales. The next honest move is residual audit, not automatic escalation to N288 harder nuisance or immediate support expansion.


## V45 caution
The first beyond-N256 failures at N288 are heterogeneous. Do **not** compress them into one generic farther-scale story. Specifically:
- do not treat separator overreach into true translation as the same phenomenon as a baseline-edge leak into translation
- do not jump straight to N288 harder nuisance before the pair-specific controlled studies are done
- do not invent a new combined support rule that tries to absorb both N288 residual families at once


## V46 governance note
A new failure mode has been recognized: **black-box residual chasing**.
This is not yet listed as a rejected architecture, but it is now considered a governance risk. The mitigation is to require atlas entry and family classification before new farther-scale support rules are proposed.


## v47 caution
The N288 translation-margin guard candidate must not be over-promoted. It is clean on the currently audited control panels and resolves the separator-overreach family, but the N288 standard frontier still contains the separate baseline-edge leak. Do not treat the pair as solved until that second family is audited.

## v55 caution
Do not respond to the new phase-2 residual split by inventing two simultaneous new rules. Study the repeated ATLAS-R7 family first; keep ATLAS-R8 atlased until it repeats or proves basis-auditable.
