# GLOBAL OVERVIEW APPENDIX — STAGE 1

## Why this appendix exists
This appendix records the first concrete implementation of the long-discussed `O_N` overview layer:

\[
S_N(t) \rightarrow \mathcal{E}_N \rightarrow O_N \rightarrow \Phi(O_N)
\]

The project repeatedly suspected that local rescue logic was compensating for a missing intermediate system-level summary. This appendix records the first positive evidence that such a layer can be operational.

## What was actually built
This branch did **not** yet implement full HHD/HMF or a full spherical harmonic pipeline.
Instead, it implemented a cheaper prototype using data already exposed by the interface bundle traces:

1. **global integral-style channels**
   - translation dipole vectors
   - polarity dipole vectors
   - rotation/event/translation energy sums
2. **low-order angular moment channels**
   - translation quadrupole moments
   - polarity quadrupole moments
3. **simple overview-only readout**
   - gate from low-order overview coordinates
   - nontranslation split from a single event-energy overview key
   - translation sign from a single overview dipole-x key

## The fixed physically interpretable overview candidate
The current fixed candidate uses:

### Gate keys
- `overview_translation_dipole_norm_peak_abs`
- `overview_translation_energy_peak_abs`
- `overview_translation_quad_xx_mean`

### Nontranslation key
- `overview_event_energy_peak_abs`

### Sign key
- `overview_translation_dipole_x_mean`

These keys were chosen because they are easy to interpret physically:
- dipole magnitude = global directional asymmetry
- translation energy = coarse translation-mode mass
- quadrupole xx = low-order angular anisotropy aligned with x
- event energy = coarse global event load
- dipole x sign = signed x-direction overview

## Current results
### Prototype stress panel (N64/N96/N128 seen, N160 unseen)
- seen-scale overall: `1.000`
- seen-scale translation: `1.000`
- N160 overall: `1.000`
- N160 translation: `1.000`

### N160 richer nuisance panel
- overview candidate overall: `0.900`
- overview candidate translation: `0.833`

This is important because it clearly outperforms the recent local-rescue baseline on the same richer nuisance panel.

## Comparison against recent local-rescue line
On the N160 richer nuisance panel, recent local-rescue style results were approximately:
- clean hybrid: overall `0.667`, translation `0.444`
- probe-informed rescue candidate: overall `0.867`, translation `0.778`

So the current overview candidate is not merely interesting — it is already competitive and in this audit it is better.

## What this does and does not prove
### It does support
- the project really was missing an overview layer
- low-complexity global variables can stabilize semantic reading across scale better than many local rescue patches
- the target relation
  \[
  A_{N_1} \sim_{\Phi} A_{N_2}
  \]
  becomes more credible when `\Phi` contains a system-level overview summary

### It does not yet prove
- that local rescue logic is obsolete in every panel
- that HHD/HMF or spherical harmonic layers are unnecessary
- that the physical body is fully robust
- that the overview candidate is already the final promoted mainline

## Current interpretation
The overview result is strong enough to change project priority.
It does **not** mean the project is solved.
It means:

1. the earlier suspicion was likely correct
2. the next serious architecture branch should prioritize overview-first readout design
3. future work should compare overview-first branches against local-rescue branches instead of assuming local rescue is the unavoidable mainline

## Next build priorities
1. validate the overview candidate on richer nuisance with more seeds and/or more scales
2. test whether adding HHD/HMF-style decomposition improves the remaining N160 early-sharp failures
3. test whether low-order spherical channels add robustness without reintroducing complexity inflation
4. only keep local rescue logic if it still adds value after overview channels are present


## Update — temporal overview branch (v16)
A follow-up branch tested whether the first overview candidate was underpowered simply because it looked only at a compact end-of-trace summary.

### Added temporal descriptors
- peak time fractions for translation / rotation / event energies
- early/mid/late window means and peak magnitudes
- early-to-late and mid-to-late ratios
- signed x-dipole at the translation peak

### Outcome
A simple fixed temporal candidate improved the N160 richer-profile translation score to `1.000`, but introduced a new failure mode:
- both `baseline` cases crossed into the translation branch

### Reading of this result
This means:
- profile timing matters
- but profile timing by itself is not a sufficient overview basis
- the next better candidate should not be “more timing features”
- the next better candidate should try a more structural split between translation-like and circulation-like content


## HHD-lite proxy note
The project now includes a first field-decomposition-style overview proxy.
This is **not** a full discrete HHD/HMF solver on the foam mesh.
It is a low-complexity proxy built from current interface-bundle traces.

Its role is to test whether overview channels that explicitly separate divergence-like and curl-like response are more stable than raw local rescue logic.

Current evidence:
- the direction is promising on N160
- the first proxy is still too weak on seen-scale compatibility
Therefore the next engineering move is likely a hybrid overview branch rather than a pure HHD-lite replacement.


## v18 fixed-overview + HHD-lite hybrid update
A constrained seen-scale-only search across fixed overview and HHD-lite feature families found a non-probe-informed hybrid candidate that is stronger than both the temporal-only overview branch and the HHD-lite-only proxy on the current richer-profile panel. This supports the current architectural hypothesis that decomposition-style channels are most useful when they augment, rather than replace, the strongest low-order global overview channels.


## Update — v19 minimal timing supplement on overview-first
A single timing-aware gate supplement selected on seen scales only (`temporal_agg_rotation_mid_to_late_peak_ratio`) was sufficient to repair the last residual late-soft positive-translation miss in the fixed overview + HHD-lite hybrid candidate.

This does **not** invalidate the need for overview structure. The supplement works because the global overview already provides the right low-dimensional geometry; the timing ratio only repairs one remaining boundary condition.

Engineering meaning:
- overview-first is currently the strongest line
- HHD-lite is useful when paired with fixed overview channels
- small timing-aware supplements are acceptable when they remain low-complexity and non-probe-informed
- the next meaningful risk is not local late-soft repair anymore, but whether this candidate survives harder nuisance or larger unseen scale


## v20 note — overview-first now passes harder unseen nuisance
The fixed overview + HHD-lite + minimal late-soft timing supplement has now been tested on a harder OOD nuisance panel with unseen profile combinations (`early_soft`, `mid_sharp`, `late_balanced`). It remains at 1.000 / 1.000 on seen scales and N160.

Interpretation:
- the current global overview layer is beginning to behave like a stable low-complexity semantic basis rather than a panel-specific patch stack
- the next honest pressure test is no longer same-scale nuisance, but **farther unseen scale**


## N192 farther-scale note
The first farther-scale extension beyond N160 indicates that the current overview-first line does not generically collapse at N192. The residual error is specifically a mid-balanced rotation-to-translation leak, and it can be corrected with a single seen-scale-only veto on `hhd_curl_energy_peak_abs`. This is evidence that the overview layer is beginning to define a stable coarse semantic geometry across scale, but it is not yet proof of full cross-scale invariance because harder N192 nuisance remains untested.


## N192 harder nuisance note
A follow-up farther-scale audit evaluated the current N192 branch on a harder unseen nuisance panel with profile combinations `early_soft / mid_sharp / late_balanced`.

Results:
- seen-scale overall: `1.000`
- seen-scale translation: `1.000`
- N192 overall: `0.750`
- N192 translation: `1.000`

Reading of this result:
- translation remains stable
- the remaining farther-scale weakness is harder rotation nuisance leaking into `translation_x_neg`
- the existing mid-balanced veto does not solve this panel because it is profile-specific

Engineering meaning:
- the overview layer still appears useful and non-empty
- but the current farther-scale branch does not yet define a fully stable nuisance-robust coarse semantic geometry at N192
- the next honest move is not to reopen the physical core, but to search for a cleaner seen-scale-only generalized rotation separation rule


## N192 generalized curl-veto note
The harder N192 nuisance failure showed that the earlier `mid_balanced` farther-scale veto was too profile-specific. A follow-up audit then selected a **profile-general seen-scale-only curl veto** on `hhd_curl_energy_peak_abs`, activated only when the mainline predicts `translation_x_neg`.

Selected harder-profile seen-scale separation:
- max seen `translation_x_neg`: `1.7549433118626119`
- min seen `rotation_z_pos`: `3.855299929665275`
- midpoint threshold: `2.8051216207639436`

Results:
- harder N192 nuisance: `1.000 / 1.000`
- standard richer-profile N192 replay: `1.000 / 1.000`

Reading of this result:
- the overview layer is beginning to define a broader coarse semantic geometry than the earlier profile-specific farther-scale veto suggested
- the remaining farther-scale mechanism may be expressible as a low-complexity curl-based nontranslation safeguard rather than a growing family of profile exceptions
- this is stronger evidence for overview-first semantics across scale, but still not final proof because seed expansion and another farther scale remain to be tested



## Standard N192 seed-expansion note
A first partial seed-expansion check has now been run on the standard richer-profile N192 panel using the fixed v23 generalized curl-veto candidate. On one additional unseen target seed (`seed 9`), the candidate remains at `1.000 / 1.000` without threshold reselection. This is useful support for farther-scale stability on the standard panel, but the harder-nuisance N192 seed expansion still remains the more important unresolved robustness audit.


## V25 note — harder N192 seed expansion
The fixed generalized curl-veto candidate was tested on a wider harder-nuisance N192 seed set (`7,8,9,10,11,12`) without threshold reselection. The result is mixed but informative: translation remains perfectly separated, while two seed-11 rotation cases now leak into `translation_x_pos`. This reinforces the view that the overview-first semantic basis is real, but that the current farther-scale rotation safeguard is still sign-asymmetric. The next architectural refinement should therefore stay overview-first and target a bidirectional rotation safeguard rather than reopening the physical core.



## V26 note — the farther-scale safeguard is really a sign-agnostic rotation separator
A replay-based refinement shows that the current farther-scale curl rule should not be interpreted as “special handling for `translation_x_neg` leaks.” The cleaner reading is stronger: high-curl translation predictions at N192 are simply rotation leaks, regardless of which translation sign the sign branch chose first. With the same fixed seen-scale-only threshold carried forward from v23, a direct sign-agnostic rotation veto clears all currently tested N192 farther-scale panels, including the harder seed expansion that previously left two `translation_x_pos` leaks. This strengthens the case that the overview layer is now carving out a stable coarse rotation-vs-translation geometry at farther scale, while still leaving broader seed expansion and beyond-N192 validation as the next honest tests.


## V28 note — farther-scale separator naming discipline
The project now explicitly treats farther-scale curl-based rules as **overview-side separators** rather than silent proof that the physical body directly emits clean symbolic classes.
This naming discipline is not cosmetic. It preserves interpretability by keeping overview geometry, separator geometry, and physical-body claims distinct.


## V28 note — first beyond-N192 harder nuisance probe
The fixed v26 farther-scale separator also clears the first harder unseen-nuisance N224 probe on seeds `7,8` without threshold changes. This strengthens the claim that the current overview geometry is still structured beyond N192, while still stopping short of any claim of unbounded farther-scale robustness.



## v29 note — N224 standard seed expansion
The fixed sign-agnostic direct rotation separator was carried forward unchanged into a broader `N224` standard richer-profile seed panel (`seeds 7,8,9,10,11,12`). The result stays high but no longer perfect: `overall = 0.983`, `translation = 0.972`, with a single residual `translation_x_neg_late_soft -> baseline` miss on `seed 9`.

Interpretation:
- the overview-first semantic geometry still extends beyond `N192`; there is no evidence of generic farther-scale collapse here
- however the farther-scale separator is not yet uniformly clean at `N224`
- the unresolved work has narrowed to a specific late-soft negative-translation boundary condition rather than a broad failure of the overview-first route



## V30 note — farther-scale residual reading discipline
The N224 late-soft negative-translation audit reinforces the governance rule that farther-scale residuals must be described by **which layer failed**. In this case the relevant layer is the stage-1 translation/nontranslation gate, not the sign branch and not the high-curl rotation separator. This is exactly why farther-scale reports should continue to separate physical-response evidence, gate evidence, sign evidence, and separator evidence rather than collapsing them into one headline metric.


## V31 note — current gate family boundary reached at N224 residual
A focused boundary study on the unique `N224 seed 9 translation_x_neg_late_soft -> baseline` residual found that the sample remains sign-coherent but exits seen `translation_x_neg_late_soft` support on all checked gate-support axes inside the current five-key gate family. This is important because it marks a limit of the *current gate basis*, not evidence that the overview-first route has failed in general. The next honest branch is therefore to study a sign-aware gate fallback or a richer temporal/trace gate basis rather than adding another farther-scale veto and narrating it as a solved boundary.


## v32 note — sign-aware fallback outside the five-key gate family
The N224 late-soft negative residual showed that the current five-key gate family alone did not contain a clean seen-scale-only boundary repair. A follow-up study then tested whether a **sign-aware fallback** could recover the residual without changing the overview-first mainline or the farther-scale bidirectional rotation separator.

Current result:
- on the N224 standard seed-expansion panel, a seen-scale-only sign-aware fallback restores the unique `translation_x_neg_late_soft` residual and returns the panel to `1.000 / 1.000`
- this fallback is not itself a new farther-scale separator; it is a controlled post-gate recovery layer that leverages persistent sign geometry when gate spill remains small and curl remains low

Engineering meaning:
- the farther-scale residual does not currently force a route change away from overview-first
- but it does suggest that some farther-scale late-soft cases may leave the current gate basis while still remaining semantically coherent in sign space
- this strengthens the interpretation that current failures may sometimes reflect **projection mismatch**, not simply information disappearance


## v33 note — sign-aware fallback survives first N224 harder nuisance stress test
The v32 sign-aware fallback candidate was then carried forward unchanged into the first N224 harder unseen-nuisance panel. It stays at `1.000 / 1.000` with **zero fallback activations** on both seen scales and the current harder N224 target set.

Interpretation:
- this is stronger evidence that the fallback is behaving like a controlled low-energy negative-translation recovery layer, not like a broadly misfiring panel-specific patch
- the overview-first route still does not require a route change at N224
- the next honest pressure test is broader harder seed expansion, not yet farther promotion language



## v34 note — N224 harder seed expansion exposes sign asymmetry
The carried-forward v32 sign-aware fallback does not generically blow up under N224 harder seed expansion, but it also does not stay fully closed: it rescues one negative-translation harder case while leaving one positive-translation harder residual (`translation_x_pos_late_balanced -> baseline`).

Interpretation:
- this is not evidence that the overview-first line has collapsed
- it is evidence that the current farther-scale fallback geometry is becoming **sign-asymmetric** under the harder expanded N224 panel
- therefore the next clean move is an explicit sign-asymmetry residual audit rather than immediate promotion or immediate threshold multiplication




## v35 sign-asymmetry note
The N224 harder-seed audit indicates that the current farther-scale residual picture is asymmetric but not mirror-symmetric: the rescued negative early-soft spill remains bridge-eligible under the fixed negative fallback, while the remaining positive late-balanced residual exits seen positive late-balanced gate support more substantially. This argues against a naive mirrored positive fallback and suggests that the remaining issue is better framed as a localized gate-basis miss or a missing trace-aware positive-late-balanced overview coordinate.


## v36 note — positive late-balanced residual is a basis-miss candidate
The remaining `N224` harder-seed positive late-balanced residual does not currently look like a failure of sign space or a rotation-leak event. It stays positively oriented in sign space and low in curl, but it exits seen positive late-balanced gate support through a combination of timing-ratio inflation and reduced quadrupole support. This makes it a candidate for a richer temporal / trace basis study rather than a simple mirrored fallback rule.


## V37 note — richer temporal / trace positive basis
A constrained search over richer temporal / trace diagnostics already emitted by the current stack shows that the remaining `translation_x_pos_late_balanced` farther-scale residual does not require a mirrored sign patch to become recoverable. In particular, active family centroid-shell metrics from the discrete channel track provide a clean seen-scale-only support family for the current residual. This strengthens the interpretation that the positive late-balanced miss is a projection / basis miss rather than a sign-asymmetric collapse.

## v39 note — positive trace-basis bridge remains silent on N224 standard seed-expansion
The positive trace-basis bridge discovered on the N224 harder panel was probed on the N224 standard richer-profile seed-expansion panel without any threshold reselection. It fired zero times on both seen and target rows while preserving `1.000 / 1.000`.

Interpretation:
- this is evidence against reading the bridge as a broad target-scale contamination layer
- the bridge currently behaves like a sparse farther-scale support for a particular positive residual family
- the next honest question is not whether to mirror it further on N224, but whether the whole fixed rule stack survives **beyond N224**



## N256 farther-scale note
The first beyond-N224 standard richer-profile probe indicates that the current overview-first stack does not immediately collapse when extended to N256. Importantly, the pass occurs with the full current stack held fixed and with both support layers staying silent on the current N256 standard panel. This strengthens the reading that the present farther-scale structure is still controlled, but it is not yet evidence of broad farther-scale closure because N256 harder unseen nuisance remains untested.



## N256 harder unseen-nuisance note
The current full stack (overview-first mainline + bidirectional rotation separator + negative sign-aware fallback + positive trace-basis bridge) now also passes the first N256 harder unseen-nuisance panel with 1.000 / 1.000 while both support layers remain silent. This strengthens the interpretation that the current farther-scale stack is staying controlled rather than broadening into an indiscriminate patch regime. It is still not final promotion evidence because N256 harder seed expansion remains untested.


## N256 harder unseen-nuisance seed-expansion note
The broader N256 harder unseen-nuisance seed expansion also passes cleanly under the current fixed full stack with 1.000 / 1.000 while both support layers remain silent across the expanded target set. This modestly strengthens the reading that the current farther-scale stack is remaining controlled rather than broadening into an indiscriminate patch regime, while still leaving standard seed expansion or another farther unseen scale as the next honest promotion tests.
## N256 standard seed-expansion note
The broader N256 standard richer-profile seed expansion also passes cleanly under the current fixed full stack with `1.000 / 1.000` while both support layers remain silent across the expanded target set. This slightly strengthens the interpretation that the present farther-scale overview geometry remains controlled at N256 under both the standard and harder seed-expansion checks, while still not licensing any claim that drift is fully solved in general.

## N288 farther-scale note
The first beyond-N256 standard probe at N288 is the first farther-scale point where the current fixed full stack is not perfectly clean. Importantly, the support layers stay silent. This means the new failures should be read as structured farther-scale residuals of the current overview/readout geometry rather than as evidence that the support stack is broadly overfitting by firing everywhere.


## N288 separator-overreach note
A controlled farther-scale study now indicates that the first N288 `translation_x_neg_early_sharp -> rotation_z_pos` failure is not a generic breakdown of the overview basis. It is recoverable with a single seen-scale-only translation-margin guard layered on top of the fixed bidirectional separator. This supports the view that some farther-scale residuals still belong to the same overview geometry, but become misclassified when a support boundary crosses into true-translation territory.

## v55 note
The fixed overview-first stack remains the current mainline, but the phase-2 harder target-seed expansion shows that carried-forward support layers still define the practical farther-scale boundary. Overview-first remains justified; mainline closure does not.
