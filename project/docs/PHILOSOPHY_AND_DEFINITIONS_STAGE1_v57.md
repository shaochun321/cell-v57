# PHILOSOPHY AND DEFINITIONS — STAGE 1

## Why this file exists
This file records the project's working definitions and philosophical boundaries in plain language.
It exists because the project has repeatedly lost context when conversations restarted.
These definitions are not decoration. They constrain what the project is allowed to optimize and what counts as progress.

## Matter-first / physical-computation-first stance
The project assumes:
- material organization comes first
- physical response comes first
- symbols come later
- symbolic labels are not privileged ground truth at the cell-sphere layer

The working belief is:
- the cell sphere, foam mesh, and interface bundles together form a physical information unit
- this unit is allowed to generate rich, continuous, scale-dependent, profile-dependent responses
- a later readout layer may compress those responses into center, direction, class, or symbol
- therefore symbol-level failure does not automatically imply physical-core failure

## What “physical computation” means in this project
Physical computation here does **not** mean “the simulator already contains a neural network in disguise.”
It means:
- a structured physical body is placed in a field / perturbation regime
- its material and geometric organization transform the perturbation into structured internal response
- those responses are sampled by interface bundles and later compressed by a readout
- the body is treated as a computation-bearing dynamical object, not as a passive conduit

Practical consequence:
- response structure matters more than early symbolic correctness
- local pattern generation, propagation, damping, and routing all count as part of the computation

## What “symbol” means in this project
A symbol is a later-stage semantic compression, not a primitive object.
Examples:
- `translation_x_pos`
- `translation_x_neg`
- `rotation_z_pos`
- `baseline`

Important boundary:
- the cell sphere itself does **not** inherently emit these symbols
- an external readout layer emits them
- therefore a symbolic label is only as trustworthy as the readout that produced it

## What the cell sphere is
The cell sphere is not just a container.
The current project treats it as:
- a structured physical computation body
- a relative spatial origin
- a time-and-space lever arm that changes sensitivity to field input as scale changes
- a carrier of shell structure, propagation structure, and response geometry

Implication:
- changing cell count changes more than “resolution”
- it changes response geometry, delay structure, shell ratios, and observability

## What the foam mesh is
The foam mesh is not merely a static support scaffold.
It is currently understood as:
- the structure that stabilizes the sphere
- the coupling fabric that constrains propagation
- part of the mechanism that shapes which responses survive, spread, or cancel

Current caution:
- we still have not proven bottom-layer robustness
- the foam mesh may be correct enough to sustain useful response structure, but not yet proven scale-robust

## What interface bundles are
Interface bundles are not simple wires.
In current project language they are:
- distributed measurement units
- localized coupling / receiving structures
- part of the separation and transmission process
- the source of the event-level observable streams consumed by the external readout

Strong rule:
- interface bundles may measure and transmit
- they should not be treated as final semantic judges

## What the external readout is
The external readout layer is the system that turns continuous response into symbolic categories.
Current role:
- gate translation vs nontranslation
- decide sign within translation
- refine nontranslation classes such as baseline vs rotation

Project reality learned so far:
- the external readout has been the dominant bottleneck through most of Stage 1
- many apparent “physical failures” were actually readout geometry failures

## Core top-level goal
The project does **not** want pointwise equality across scales.
The goal is not:
\[
A_{N_1}=A_{N_2}
\]

The real goal is a constrained semantic equivalence:
\[
A_{N_1}\sim_{\Phi}A_{N_2}
\]
meaning:
- raw states may differ across scales
- but after a controlled overview/readout mapping \(\Phi\), they should land in the same semantic class
- while different semantic classes must remain separable

This equivalence only has meaning if \(\Phi\) is:
1. low-complexity
2. non-probe-informed at the target scale
3. non-collapsing for different semantics

## Why drift is not automatically bad
The project explicitly accepts:
- drift can be useful
- conversion can be useful
- coarse-graining can be useful

But drift must be audited.
Useful drift:
- preserves semantic recoverability
- can be explained by scale, profile, or overview structure
- forms stable effective classes

Bad drift:
- forces arbitrary rescue thresholds
- causes random category crossing
- only works on specific seeds or probe-tuned panels
- collapses different semantics into one class

## Why the project is nontraditional
The project is nontraditional in **system composition**:
- cell sphere + foam mesh + interface bundles + external readout + drift auditing

It is **not** nontraditional in the mathematical tools it may borrow.
Mature imported tool families are allowed when useful:
- observability / delay embedding / effective dimension
- metric-aware gating
- multiscale time-series analysis
- Helmholtz-Hodge / Hodge-Morrey-Friedrichs style field decomposition
- spherical harmonic overview channels
- coarse global integral channels

## Theories and analogies that are allowed but not yet facts
Allowed as inspiration only:
- RG-like coarse-graining analogies
- metric-tensor flow analogies
- Ricci-flow-like drift handling analogies
- thermalization / entropy analogies

Not allowed as current project facts.
They remain hypotheses or metaphors until implemented and validated.

## Current discipline
Do not:
- treat analogies as mechanisms
- treat symbolic failure as direct proof of physical failure
- promote probe-informed emergency fixes to clean mainline solutions
- confuse clean but weak rules with strong and validated rules

Do:
- preserve the matter-first stance
- separate measurement, overview, and decision layers
- demand that the readout justify semantic equivalence across scales


## Governance corollary — success is two-layered
A successful farther-scale result now has two meanings that must stay separated:
- **physical meaning**: the body still produces structured response geometry
- **readout meaning**: a low-complexity separator can still recover semantics from that geometry

The project treats both as important.
But it does **not** allow the second statement to silently replace the first.


## Governance note — separator naming discipline (v29)
Farther-scale rules that intervene after overview-first readout must be named as **separator / safeguard / compensator** rules, not as proofs that the cell sphere directly emits clean symbolic categories. This naming discipline is part of the project’s matter-first boundary: separator success is useful evidence, but it does not erase the distinction between physical-response evidence and readout-compensator evidence.


## Constraint note on Φ
The project still uses the target relation
\[
A_{N_1}\sim_{\Phi}A_{N_2}
\]
but current engineering discipline should be read as follows:
- `\Phi` is always understood under **explicit observational and validation constraints**
- unrestricted all-scale semantic recoverability is **not** assumed to be already established
- current Stage 1 claims are about whether a low-complexity, non-probe-informed mapping can preserve recoverability on the audited panel family and scale regime
- if information appears to leave the current gate basis, that is not immediate proof of physical-core absence; it may instead indicate a projection mismatch or an underbuilt observable/overview layer

Practical reading:
- current negative results should be audited as failures of the **current measurement/overview/decision chain**, not automatically as proof that the physical body contains no recoverable information
- current positive results should be treated as evidence for **controlled recoverability**, not yet as proof of unrestricted universal recoverability


## Update — v36 observation vs basis-miss note
The project now records an additional discipline point for farther-scale residuals:
- observation failure under the current gate basis does **not** automatically imply information absence in the physical body
- a residual may reflect a current readout / projection mismatch rather than a proof that the underlying response no longer exists
- therefore farther-scale residual audits should distinguish `SNR loss` from `basis / projection miss` whenever possible

This note does **not** upgrade any particular basis-miss interpretation into a project fact. It simply preserves the discipline that measurement failure, overview failure, and physical-core failure are different claims and must be audited separately.

## v55 continuity note
Controlled-stack success and controlled-stack boundary are both readout-side findings first. The appearance of ATLAS-R7 and ATLAS-R8 at N288 phase 2 does not by itself justify a route change away from overview-first or toward physical-core rewrite.
