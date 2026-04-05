# DECISION LOG AND ROUTE CHANGES — STAGE 1

## Why this file exists
The project changed direction multiple times. This file records those changes so future conversations do not repeat dead branches or confuse old baselines with the current target.

---

## Phase 0 — old signed-readout track
### Original working target
The early project behavior was evaluated mainly through direct signed readouts such as:
- `translation_x_pos`
- `translation_x_neg`
- `rotation_z_pos`
- `rotation_z_neg`

### Why this became unstable
The old track repeatedly encountered:
- sign ambiguity
- positive/negative direction reversal
- strong seed dependence
- repeated downstream repair loops

### What was learned
The old stack proved that some readout could be recovered, but it did **not** prove that the physical body itself cleanly emitted symbolic direction.

---

## Phase 1 — M2 material redesign line
### Why it happened
Audits concluded that the bottleneck was no longer “just another summary bug.”
The failure looked more like a material / domain continuity problem.

### What this phase tried
- inner-core source continuity redesign
- shell0/shell1 density redesign
- high-amplitude distribution shaping
- retaining summary support as frozen infrastructure

### Why this phase mattered
It established a critical historical result:
- **M2.4 is only a frozen historical baseline**
- it is not the current project objective
- it proved that upstream material redesign could recover old baseline-level behavior in a narrow sense

### Why this phase stopped being the mainline
It still evaluated progress using the old signed-readout worldview.
That was eventually judged too narrow and too easy to misread.

---

## Phase 2 — Stage 1 restart: response-first redefinition
### Route change
The project was redefined around a new Stage-1 goal:
- validate whether the integrated unit (cell sphere + foam mesh + interface bundles) can generate, preserve, and separate stable physical responses
- then test whether a simple external readout can recover direction/center semantics

### Why this was a real route change
This explicitly rejected the idea that the cell sphere itself should directly emit final symbolic classes.

### New hierarchy
1. physical body response
2. event / interface measurement
3. external overview / readout
4. semantic labels

---

## Phase 3 — external readout becomes the bottleneck
### What happened
Repeated audits showed that many apparent physical failures were actually failures of the readout geometry.

### Evidence
- N64 interface protocol showed separable response structure exists
- N96 failures were often recoverable with readout restructuring alone
- hierarchical branch-then-sign decoding outperformed flat decoding
- richer nuisance failures appeared first in gate geometry and sign handoff, not in total response collapse

### Route change
The project temporarily prioritized:
- gate structure
- sign basis
- veto logic
- stress/generalization audits
instead of physical-core redesign

---

## Phase 4 — medium / damping was tested and demoted
### Hypothesis
A medium-like or damping-like adjustment might stabilize larger-scale drift.

### What was tried
- effective-medium damping / drag style parameter variants
- stronger outer-shell damping variants

### Result
Medium-like changes could improve some within-scale metrics, but did not become the best cross-scale fix.

### Decision
- keep medium/damping as a valid control knob
- **do not** promote it to main solution

---

## Phase 5 — sign-anchor refactors and hierarchical stress line
### What happened
The project refined:
- cross-scale sign-stable feature subsets
- hierarchical translation vs nontranslation gate
- sign branches tuned for nuisance sensitivity

### Result
N64/N96/N128 became increasingly manageable.
This proved that the readout layer still had major untapped leverage.

### What it did **not** prove
It did not prove that the readout had become clean, scalable, or final.

---

## Phase 6 — N160 becomes the decisive stress point
### What happened
At N160, the old mainline no longer failed primarily in gate collapse.
The new front line became:
- translation sign drift under richer nuisance
- especially profile-sensitive early/late conditioned failures

### Why this mattered
This separated three previously entangled problems:
1. gate failure
2. sign observability failure
3. profile-routing / conditioning failure

### Resulting route change
The project then focused on:
- profile-aware sign candidates
- early-translation rescue candidates
- clean seen-scale rescue derivations
- comparison between clean and probe-informed rescue mechanisms

---

## Phase 7 — clean rescue vs probe-informed rescue
### What happened
Two different rescue families were separated:

#### A. Probe-informed rescue
- stronger at N160
- but selected with help from N160-specific overlap/probe evidence
- therefore useful but not promotable to mainline

#### B. Clean seen-scale rescue
- derived only from N64/N96/N128-style evidence
- cleaner, but weaker
- currently not strong enough to replace the probe-informed rescue at N160

### Why this is important
This is one of the most important current truths:
- the project does **not yet** have a clean, cross-scale, promotable rescue mechanism for N160 richer nuisance

---

## Phase 8 — shift toward a global overview architecture
### Why this shift happened
By this point, the project had enough evidence that local statistics + conditional rescue alone were reaching diminishing returns.
The missing architectural layer appears to be a **global overview** layer between local distributed measurement and final gate decisions.

### New proposed structure
1. distributed measurement (interface bundles)
2. global overview layer
3. low-complexity semantic readout

### Candidate overview families
- global integral channels
- HHD / HMF style decomposition
- low-order spherical overview channels

### Current status
This is the next build direction.
It is proposed, not yet implemented in the mainline.

---

## Current project state in one sentence
The project has evolved from “fix direct signed readouts” into:

**build a physically meaningful, low-complexity overview/readout mapping \(\Phi\) that preserves semantic equivalence across scales without probe-informed leakage.**


## Phase 6 — overview-first branch refinement
### What changed
After the first fixed overview candidate outperformed the local-rescue mainline on N160 richer nuisance, a follow-up question emerged:
was overview underpowered because it lacked explicit profile timing information?

### What was tried
A temporal overview branch was built with:
- peak-time features
- early/mid/late summary windows
- profile-sensitive signed dipole readout

### What happened
- N160 translation errors disappeared
- but baseline leaked into translation

### What was learned
- overview-only is still the right direction
- but “more timing” is not enough
- the next better step is a field-decomposition style overview branch, not another local rescue stack


## v17 — HHD-lite overview proxy added and demoted
### Why
A stronger critique of the old local-statistics gate suggested introducing a more field-decomposition-style overview rather than continuing local rescue logic.

### What was done
A low-cost HHD-lite proxy was implemented from existing interface-bundle traces, producing divergence-like, curl-like, and harmonic-like overview channels.

### Result
- N160 richer-profile target performance improved strongly: overall 0.950, translation 1.000.
- But seen-scale compatibility remained weak: overall 0.717, translation 0.639.

### Consequence
The HHD-lite proxy is **promising but not promoted**.
It strengthens the overview-first argument but does not replace the stronger fixed overview candidate yet.


## v18 decision
Promote `fixed overview + HHD-lite hybrid` to the current strongest overview-first candidate. Keep `temporal-only overview` diagnostic only. Keep `HHD-lite-only` as promising-but-not-promoted. Immediate next task: study whether a very small timing-aware supplement can fix the remaining `translation_x_pos_late_soft -> baseline` miss without damaging the current seen-scale stability.


## v19 — fixed overview + HHD-lite + minimal late-soft supplement
- carried forward the v18 overview-first mainline
- performed a strict seen-scale-only search over single temporal supplements to repair the last residual `translation_x_pos_late_soft` miss
- selected `temporal_agg_rotation_mid_to_late_peak_ratio` as the only added gate key
- result: seen-scale overall 1.000 / translation 1.000, N160 overall 1.000 / translation 1.000 on the current richer-profile panel
- interpretation: overview-first is no longer merely promising; on the current panel it now fully dominates the old local-rescue route without target-scale rescue
- new risk: do not over-interpret current-panel success; the next task must be harsher nuisance or larger unseen scale validation


## v19 -> v20 decision
### What changed
- The fixed overview + HHD-lite + minimal late-soft timing supplement was frozen as the current overview-first mainline.
- A new harder nuisance validation was added with unseen profile combinations (`early_soft`, `mid_sharp`, `late_balanced`).

### What was learned
- The v19 mainline generalized cleanly to the harder nuisance panel without target-scale retuning.
- This strongly reduces the probability that the current mainline is merely memorizing the original richer-profile panel.

### Consequence
- Same-scale nuisance escalation is temporarily de-prioritized.
- The next mainline validation axis becomes **farther unseen scale**.


## V21 — farther unseen scale N192 validation
- Continued from the v20 overview-first mainline rather than reopening local rescue or the physical core.
- Generated a clean cross-scale richer-profile raw panel including N192.
- Found that the v20 mainline fails only on `rotation_z_pos_mid_balanced` at N192, while all translation cases remain correct.
- Added a single seen-scale-only mid-balanced rotation veto based on `hhd_curl_energy_peak_abs > 2.7927037565600394` when the mainline predicts `translation_x_neg`.
- Outcome: seen-scale remains 1.000 / 1.000 and N192 reaches 1.000 / 1.000 on the standard richer-profile farther-scale panel.
- Status: promising farther-scale candidate, not yet elevated above the current mainline until harder N192 nuisance is tested.


## V22 — N192 harder unseen nuisance validation
- Continued from the v21 farther-scale N192 veto candidate without reopening local rescue or the physical core.
- Evaluated the current farther-scale branch on a harder OOD nuisance panel with unseen profile combinations `early_soft / mid_sharp / late_balanced`.
- Outcome: seen-scale remains `1.000 / 1.000`, but N192 falls to `0.750 / 1.000`.
- All N192 failures are `rotation_z_pos -> translation_x_neg` leaks under harder nuisance.
- The existing v21 mid-balanced veto does not activate on this panel because its profile condition is not present.
- Status change: v21 remains a clean standard-panel farther-scale candidate, but **harder farther-scale nuisance remains unsolved**.
- New authoritative next step: search for a clean seen-scale-only harder-profile rotation veto / generalized nontranslation separation rule at N192.


## V23 — generalized curl-veto farther-scale candidate
- Continued from the v22 harder N192 nuisance failure without reopening local rescue or the physical core.
- Observed that the remaining errors were all `rotation_z_pos -> translation_x_neg` leaks with high `hhd_curl_energy_peak_abs`.
- Selected a single **seen-scale-only generalized curl veto** by separating harder-profile seen-scale `translation_x_neg` from `rotation_z_pos` using `hhd_curl_energy_peak_abs`.
- Chosen threshold: midpoint between the seen-scale bands, `2.8051216207639436`.
- Applied the veto whenever the mainline predicts `translation_x_neg` and the curl feature exceeds that threshold.
- Outcome on harder N192 nuisance: `1.000 / 1.000`.
- Replay against the earlier standard richer-profile N192 candidate also remains `1.000 / 1.000`.
- Status: the profile-specific farther-scale veto has been upgraded into a cleaner generalized farther-scale separation rule.
- New authoritative next step: **N192 seed expansion** before stronger farther-scale claims.



## V24 — standard richer-profile N192 seed expansion (partial)
- kept the v23 generalized curl-veto candidate fixed
- evaluated one additional unseen N192 seed (`seed 9`) on the original standard richer-profile panel
- no threshold reselection and no target-seed tuning
- outcome: `1.000 / 1.000` on the added seed
- consequence: the candidate now has at least one successful unseen standard-panel seed beyond the original N192 pair
- caution: this is still only partial seed expansion; the more important unresolved task remains **harder-nuisance N192 seed expansion**


## V25 — harder N192 seed expansion
- Kept the v23 generalized curl-veto threshold fixed with no reselection.
- Rebuilt the harder nuisance panel needed for seed expansion using seen-reference scales `N64 / N96 / N128` with seeds `7,8` and target scale `N192` with seeds `7,8,9,10,11,12`.
- Outcome: seen-scale stays `1.000 / 1.000`; N192 harder seed expansion reaches overall `0.967`, translation `1.000`.
- New residual failures are narrower than the earlier v22 leak family: `rotation_z_pos_early_soft` and `rotation_z_pos_mid_sharp` on seed 11 now leak to `translation_x_pos`.
- Consequence: the current farther-scale safeguard is real but one-sided; the next step is a seen-scale-only **bidirectional** rotation safeguard, not a return to local rescue or physical-core changes.


## V26 — sign-agnostic direct rotation veto at farther scale
- Kept the v23 curl threshold fixed with no reselection.
- Reframed the farther-scale safeguard as a **bidirectional** rule: if the overview-first mainline predicts translation and `hhd_curl_energy_peak_abs` exceeds the seen-scale rotation separator, map directly to `rotation_z_pos` regardless of translation sign.
- Replayed that rule on all currently tested N192 farther-scale audits.
- Outcome: every replayed N192 panel now lands at `1.000 / 1.000`, including the harder seed expansion that previously exposed two seed-11 `rotation_z_pos -> translation_x_pos` leaks.
- Consequence: the farther-scale safeguard is now best understood as a **sign-agnostic rotation separator**, not as a negative-sign-only patch. The next task is broader standard N192 seed expansion and then another farther unseen scale, not a return to local rescue or physical-core redesign.


## V28 — governance formalized and first beyond-N192 probe
### What changed
- the project formally added an anti-patch-illusion governance rule: farther-scale success must be reported as both physical-response evidence and readout-compensator evidence
- the fixed v26 sign-agnostic direct rotation separator was then carried forward unchanged to `N224` on the original standard richer-profile panel

### What was learned
- the first beyond-N192 standard probe remains clean at `1.000 / 1.000`
- therefore the route does not change yet
- the next real pressure test is **N224 harder unseen nuisance**, not immediate physical-core restart and not premature declaration of broad farther-scale victory


### V28 extension — N224 harder unseen-nuisance
- carried the fixed v26 sign-agnostic direct rotation separator unchanged to `N224` on the harder unseen-nuisance panel
- result: `1.000 / 1.000` on seeds `7,8`
- consequence: route remains overview-first; next task becomes N224 seed expansion rather than immediate route change



## v29 — N224 standard seed expansion
### What changed
- The fixed `v26/v28` sign-agnostic direct rotation separator was held constant.
- The `N224` standard richer-profile target seed set was widened to `7,8,9,10,11,12`.
- No threshold reselection and no target-seed tuning were allowed.

### What was learned
- The farther-scale rule remains broadly coherent at `N224`; there is no generic collapse under the widened seed set.
- But `N224` is not fully clean yet: one residual `translation_x_neg_late_soft -> baseline` error appears at `seed 9`.
- This narrows the unresolved farther-scale problem from “whether the rule survives at N224” to “why one late-soft negative-translation case crosses the translation/nontranslation boundary”.

### Consequence
- The route does **not** change at `v29`.
- The next task is a narrow residual audit with the mainline and farther-scale separator fixed, not a new rule family and not a physical-core rewrite.



## V30 — N224 late-soft negative-translation residual audit
- Performed a focused raw-feature audit on the only remaining v29 standard-seed-expansion error: `N224 seed 9 translation_x_neg_late_soft -> baseline`.
- Kept the overview-first mainline and the farther-scale separator fixed.
- Found that the error occurs **before** sign decoding: the sample crosses the stage-1 translation/nontranslation gate by a small margin.
- Confirmed that the farther-scale separator is **not** involved because the sample has low curl and is baseline-adjacent rather than rotation-like.
- Compared the matched `N192 seed 9 translation_x_neg_late_soft` case against `N224` and found the dominant changes are lower translation energy / quadrupole / event energy together with a higher mid-to-late timing ratio.
- Consequence: do not change the mainline yet; the next task is a seen-scale-only late-soft negative-translation boundary study at N224.


## V31 — boundary study says current gate family is underpowered for the residual
- Continued from the v30 residual audit rather than inventing another farther-scale veto.
- Checked whether the unique `N224 seed 9 translation_x_neg_late_soft` miss could be repaired cleanly inside the existing five-key gate family using seen-scale-only support.
- Found that the residual remains sign-coherent but exits seen `translation_x_neg_late_soft` support on all checked gate-support axes.
- Consequence: do **not** promote another threshold-style farther-scale patch as if it were clean boundary restoration.
- New next task: study a **sign-aware gate fallback** or a **richer temporal/trace gate basis** for this specific residual while keeping the overview-first mainline and current farther-scale separator fixed.


## v32 — sign-aware gate fallback candidate
### What changed
After v31 showed that no clean repair existed inside the current five-key gate family alone, the next question became whether the unique N224 late-soft negative residual could be recovered by a **controlled sign-aware fallback** without changing the overview-first mainline or the farther-scale bidirectional rotation separator.

### What was done
- regenerated a minimal raw standard richer-profile panel for seen scales `N64 / N96 / N128` with seeds `7,8` and target `N224` with seeds `7,8,9,10,11,12`
- kept the farther-scale bidirectional rotation separator fixed
- derived fallback thresholds from seen `translation_x_neg_late_soft` and seen `baseline` support only
- allowed fallback only for stage1 nontranslation cases that would otherwise land in `baseline`, while still remaining strongly coherent with `translation_x_neg` sign geometry and low curl

### Result
- seen-scale overall: `1.000`
- seen-scale translation: `1.000`
- N224 overall: `1.000`
- N224 translation: `1.000`
- the only fallback activation on target scale is `N224 / seed 9 / translation_x_neg_late_soft`
- no fallback activations occur on seen scales

### Consequence
- this is the first evidence that the N224 late-soft negative residual can be recovered cleanly **outside** the five-key gate family but still inside a seen-scale-only, low-complexity fallback layer
- the project should still avoid over-promoting this until it is stress-tested on N224 harder nuisance
- next authoritative task: `N224 harder nuisance sign-aware fallback stress test`


## v33 — sign-aware fallback survives first N224 harder nuisance stress test
### What changed
The v32 sign-aware fallback candidate was carried forward **unchanged** into the first N224 harder unseen-nuisance panel (`early_soft / mid_sharp / late_balanced`).

### What was done
- regenerated a minimal harder unseen-nuisance raw panel for seen scales `N64 / N96 / N128` with seeds `7,8` and target `N224` with seeds `7,8`
- kept the overview-first mainline unchanged
- kept the farther-scale bidirectional rotation separator unchanged
- kept the v32 sign-aware fallback thresholds unchanged
- evaluated the fixed fallback without harder-panel reselection or target-scale tuning

### Result
- seen-scale overall: `1.000`
- seen-scale translation: `1.000`
- N224 overall: `1.000`
- N224 translation: `1.000`
- no sign-aware fallback activations on seen scales
- no sign-aware fallback activations on the current harder N224 panel

### Consequence
- the sign-aware fallback does not currently show evidence of spurious harder-nuisance activation
- this strengthens the interpretation that it behaves like a controlled low-energy negative-translation recovery layer rather than a standard-panel-only patch
- next authoritative task: broaden harder nuisance coverage with an N224 harder seed-expansion audit before broader farther-scale promotion



## v34 — N224 harder unseen-nuisance sign-aware fallback seed expansion
- carried the v32 negative sign-aware fallback forward unchanged into the broader N224 harder unseen-nuisance target seed set (`7,8,9,10,11,12`)
- kept the overview-first mainline and the farther-scale bidirectional rotation separator fixed; no target-scale reselection
- result: seen-scale remains `1.000 / 1.000`, but N224 harder seed expansion becomes `0.983 / 0.972`
- one negative case (`seed 9 translation_x_neg_early_soft`) is rescued by the fallback, but one positive case (`seed 9 translation_x_pos_late_balanced`) remains routed to `baseline`
- consequence: the project should not describe the sign-aware fallback as fully stress-tested or sign-complete; the next honest step is an N224 sign-asymmetry residual audit, not another generic farther-scale veto




## v35 — N224 sign-asymmetry residual audit
### What changed
- audited the remaining `translation_x_pos_late_balanced -> baseline` error against the rescued negative early-soft spill **without** changing the mainline, separator, or negative fallback
- compared seed sweeps for `translation_x_pos_late_balanced`, `translation_x_neg_early_soft`, and `translation_x_neg_late_balanced`
- checked the remaining positive residual against seen positive late-balanced support and against seen baseline states with positive sign preference

### What was learned
- the farther-scale residual picture is asymmetric but not mirror-symmetric
- the rescued negative spill fits a narrow bridge-eligible negative-sign recovery story
- the remaining positive late-balanced residual sits farther outside seen `translation_x_pos_late_balanced` gate support
- a mirrored positive fallback would not currently be justified by seen-scale evidence and would risk becoming target-informed

### Consequence
- keep the negative sign-aware fallback as a controlled fallback only
- do not promote a mirrored positive fallback family
- next honest branch: a white-box `translation_x_pos_late_balanced` residual audit or a richer temporal / trace gate-basis study


## v36 decision
### What changed
- The remaining `N224 / seed 9 / translation_x_pos_late_balanced -> baseline` error was audited under the fixed farther-scale stack instead of being patched immediately.

### What was learned
- The residual keeps positive sign preference and low curl.
- Its miss is profile-specific to positive `late_balanced`.
- The strongest farther-scale deviation is a timing-ratio inflation paired with a loss of positive late-balanced quadrupole support.
- This makes the residual look like a **gate-basis miss** rather than a mirrored-positive fallback candidate.

### Consequence
- Do **not** mirror the negative sign-aware fallback into a positive fallback yet.
- The next branch should test a **richer temporal / trace gate basis** instead of multiplying fallback rules.


## v37 — richer temporal / trace positive-basis study
### What changed
- Instead of inventing a mirrored positive sign-aware fallback, the project searched a restricted richer temporal / trace diagnostic family already emitted by the current stack.
- The search was constrained to seen-scale-only support checks around the remaining `translation_x_pos_late_balanced` farther-scale residual.

### What was learned
- The remaining positive late-balanced residual is recoverable without a mirrored sign patch.
- Multiple richer temporal / trace features already separate seen `translation_x_pos_late_balanced` from baseline while still supporting all N224 target seeds.
- The simplest retained probe is the discrete-track active dynamic-phasic family centroid-shell index.

### Consequence
- The positive residual is better read as a **projection / basis miss** than as a sign-asymmetric collapse.
- A positive trace-basis bridge is now a promising farther-scale candidate, but it is **not yet promoted** until it survives additional panels.


## v38 — residual discussion moved into a dedicated continuity axis
### What changed
The project now formally separates:
1. recovery branches (separator / fallback / richer basis candidates)
2. residual classification and relation hypotheses

### Why
Farther-scale work now produces residuals whose research value is not exhausted by the question “can they be patched right now?”
Some residuals carry relation evidence about scale, timing, sign geometry, and projection choice.

### Consequence
Two dedicated continuity documents are now part of the standard read order:
- `RESIDUAL_TAXONOMY_AND_RELATION_HYPOTHESES_STAGE1.md`
- `GEOMETRIC_CANONICALIZATION_AND_RESIDUAL_RELATION_HYPOTHESES_STAGE1.md`

These remain appendix / diagnostics oriented.
They do not change the mainline architecture by themselves.

## v39 — positive trace-basis bridge passes N224 standard contamination probe
- kept the overview-first mainline, the bidirectional rotation separator, the negative sign-aware fallback, and the positive trace-basis bridge all fixed
- generated a standard richer-profile raw panel for `N64 / N96 / N128` seen seeds `7,8` and `N224` target seeds `7,8,9,10,11,12`
- evaluated the positive trace-basis bridge as a **probe** rather than a new candidate search
- outcome: seen-scale remained `1.000 / 1.000`, N224 remained `1.000 / 1.000`, and the positive bridge triggered **zero** times on both seen and target rows
- consequence: the bridge no longer looks like a harder-only patch risk; it currently behaves like a controlled farther-scale support that stays silent when not needed
- new next task: test the fixed rule stack on a farther unseen scale beyond N224 before any promotion decision



## V40 — beyond-N224 standard full-stack probe
- Carried the current full farther-scale stack beyond N224 without changing thresholds.
- Used the standard richer-profile panel at N256 (`early_sharp / mid_balanced / late_soft`, seeds `7,8`).
- Kept the overview-first mainline, the bidirectional rotation separator, the negative sign-aware fallback, and the positive trace-basis bridge all fixed.
- Outcome: seen remains 1.000 / 1.000 and N256 reaches 1.000 / 1.000.
- Neither support layer triggers on the current N256 standard panel.
- Consequence: do not change the mainline route yet; the next authoritative task is N256 harder unseen nuisance.



## v41 — beyond-N224 harder unseen-nuisance full-stack probe
- carried forward the fixed v40 full rule stack into the first N256 harder unseen-nuisance panel
- kept the overview-first mainline, the bidirectional rotation separator, the negative sign-aware fallback, and the positive trace-basis bridge all unchanged
- result: seen-scale 1.000 / 1.000, N256 1.000 / 1.000
- support-layer trigger counts remained at zero on both seen and target panels
- consequence: route still does not change; next authoritative task is N256 harder seed expansion before broader promotion


## v42 — beyond-N224 harder unseen-nuisance seed expansion
- carried forward the fixed v41 full rule stack into a broader N256 harder unseen-nuisance target seed set (`7,8,9,10,11,12`)
- result: seen-scale remains `1.000 / 1.000`, N256 harder seed expansion also remains `1.000 / 1.000`
- both support layers stay fully silent across the expanded target set
- consequence: route still does not change; the next authoritative task is now N256 standard seed expansion before broader farther-scale promotion
## v43 — beyond-N224 standard seed expansion at N256
- carried forward the fixed v42 full rule stack into a broader N256 standard richer-profile target seed set (`7,8,9,10,11,12`)
- kept the overview-first mainline, the bidirectional rotation separator, the negative sign-aware fallback, and the positive trace-basis bridge all unchanged
- result: seen-scale remains `1.000 / 1.000`, N256 standard seed expansion also remains `1.000 / 1.000`
- both support layers stay fully silent across the expanded target set
- consequence: route still does not change; the next authoritative task becomes a farther unseen scale beyond N256 rather than more local patch growth

## V44 — first beyond-N256 standard failure pair
- Carried the fixed full rule stack to a first beyond-N256 standard richer-profile probe at N288.
- Found that the full stack no longer remains perfectly clean at this farther scale.
- Residual pair:
  - `translation_x_neg_early_sharp -> rotation_z_pos` (seed 7)
  - `baseline -> translation_x_pos` (seed 8)
- Both support layers stayed completely silent.
- Consequence: do **not** run N288 harder unseen nuisance yet. First perform a structured white-box audit of the N288 standard residual pair.


## v45 — N288 residual pair structured audit
### What changed
- The first beyond-N256 standard probe at `N288` produced two target errors.
- Rather than escalating immediately to N288 harder nuisance or inventing a new support rule, the pair was audited in white-box form.

### What was learned
- `translation_x_neg_early_sharp -> rotation_z_pos` is best read as **separator overreach into true translation**:
  - pre-veto prediction is already `translation_x_neg`
  - negative sign remains coherent
  - failure occurs only because the fixed bidirectional curl separator triggers at N288
- `baseline -> translation_x_pos` is best read as a **baseline-edge leak into translation**:
  - curl stays low
  - the stage-1 crossing is small
  - once inside the translation branch, sign readout prefers the positive side

### Consequence
- N288 should now be treated as a **structured-audit frontier**.
- The route does not change yet, but harder unseen-nuisance escalation is demoted until the two N288 residual families are studied as separate controlled problems.


## v46 — residual condition atlas formalized
### What changed
A new parallel workstream was added: **Residual Condition Atlas**. Instead of allowing new farther-scale residuals to immediately trigger a rescue-rule search, the project now requires each residual to be recorded as an atlas family with a canonical case and a current best condition bundle.

### Why
Recent N224 and N288 work showed that residual handling can become black-box-like if the project only asks how to recover an error, but not under which condition cluster it appears.

### Consequence
- support studies remain allowed
- but the atlas must now precede them
- the next authoritative task is a pair-specific controlled study of the two N288 residual families, using the atlas as the descriptive layer


## v47 — N288 separator-overreach controlled study
- isolated the first N288 residual family where the fixed bidirectional separator crosses into a true `translation_x_neg_early_sharp` sample
- tested a single seen-scale-only guard:
  - pre-veto prediction must already be `translation_x_neg`
  - separator must trigger
  - `gate_margin_translation_minus_nontranslation <= -2.5`
- control panels at N224 standard, N256 standard, and N256 harder remained unchanged at `1.000 / 1.000`
- on N288 standard the guard triggered exactly once and restored `translation_x_neg_early_sharp`
- outcome: N288 standard improved from `0.900 / 0.917` to `0.950 / 1.000`
- consequence: the separator-overreach family is now treated as **recoverable with a controlled guard candidate**, while the separate baseline-edge leak remains the next frontier

## v54-v55 update — phase-2 harder target-seed expansion and residual split
- v54 carried the fixed v53 stack unchanged into N288 harder target seeds `17-24` and did not remain clean.
- v55 localized the resulting errors into two families rather than treating them as generic farther-scale collapse.
- Priority is now the repeated positive family (ATLAS-R7), not the isolated negative spill (ATLAS-R8).
