# APPENDIX — Drift, observability, and scale-growth hypotheses

## Why this appendix exists
This appendix records ideas that are useful for steering the project, but are **not** yet established project results.

## Mature theory that can be imported safely
1. **Observability / delay embedding / effective dimension**
   - Use this family to reason about how many gate units and event channels are needed as sphere scale grows.
   - Safe status: mature theory family, relevant to Stage 1.

2. **Metric-aware gating**
   - The current stage-1 gate compares distances in a low-dimensional feature space under an implicit Euclidean metric.
   - A next practical extension is to replace the identity metric with a scale-aware or learned metric tensor.
   - Safe status: mature method family, directly actionable.

3. **Multiscale time-series methods**
   - Wavelet / shapelet / multiscale decomposition ideas are relevant when local fragments look similar while global periods differ.
   - Safe status: mature method family, directly actionable.

## Hypotheses that are interesting but not yet project facts
1. **RG-like coarse-graining**
   - The project drift sometimes looks like different microscopic states landing in the same coarse-grained effective class.
   - This is a useful analogy for thinking.
   - Current status: analogy only, not a completed renormalization formalism.

2. **Metric-tensor flow / Ricci-flow-like drift handling**
   - It may be fruitful to think of the gate metric as something that evolves to reduce harmful distortion across scales.
   - Current status: speculative analogy only.
   - Do **not** treat this as an established mechanism already present in the project.

## Current discipline
- Do not upgrade analogies into facts.
- Keep physical-core changes secondary.
- First attack scale drift in the external readout and gate geometry.
- Keep a record that bottom-layer robustness is still unproven and must be audited later.


## New note: hybrid drift handling

The current project state supports a practical three-part drift treatment at the external readout layer:

1. **Tuned base gate** to preserve the already-recovered N64/N96 regime.
2. **Panel-adaptive veto** to intercept new translation-branch leakage when a target panel shows a strong low-tail split on `discrete_channel_track_transfer_std`.
3. **Scale-adaptive sign handoff** only beyond the calibration regime, rather than forcing a new sign basis onto scales that are already stable.

Interpretation boundary:
- this is a successful engineering treatment of the current stressed-panel drift,
- not yet a proof that drift has been “explained” in a full renormalization, metric-flow, or Ricci-flow-like sense.


## New caution from the N160 sign-drift audit
The latest evidence strengthens a practical warning:
- not all drift is bad,
- but not all drift is useful either.

At N160, the dominant new failure is a **late-sharp translation sign drift** that survives after gate stability is restored.
This suggests that some larger-scale drift will look like a problem of **profile-specific sign observables**, not just coarse gate collapse.

Working rule:
- treat drift first as an audit object,
- only later decide whether it is an effective coarse-graining phenomenon or a destructive semantic collapse.


## Probe-informed candidate boundary
A drift-handling branch that is selected with the help of an unseen probe is allowed as an engineering candidate, but it must not be promoted to the mainline decoder until it survives a farther unseen scale or richer nuisance panel. This applies to the current N160 profile-aware sparse sign candidate.


## Relationship to the new master handoff
This appendix is subordinate to:
- `PROJECT_HANDOFF_STAGE1.md`
- `PHILOSOPHY_AND_DEFINITIONS_STAGE1.md`
- `DECISION_LOG_AND_ROUTE_CHANGES_STAGE1.md`
- `BACKUP_AND_REJECTED_PATHS_STAGE1.md`

If an analogy conflicts with the master handoff, the master handoff wins.


## GLOBAL OVERVIEW NOTE
Recent evidence shows that some drift previously attributed to missing local rescue logic can instead be absorbed by a low-complexity global overview layer. This does not prove all drift is overview-fixable, but it weakens the assumption that local rescue is the only viable response to scale/profile drift.
