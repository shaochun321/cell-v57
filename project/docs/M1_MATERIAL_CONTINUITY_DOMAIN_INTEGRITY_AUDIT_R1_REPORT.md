# M1 — material continuity / domain integrity audit

## Decision
- **Decision:** `go_m2_material_redesign`
- **Verdict:** `domain_integrity_compromised`
- **Why:** The current stack no longer looks blocked mainly by summary/readout issues. It now looks like a material/domain continuity problem: inner-shell amplitude source is still missing, restoration logic is outer-first in code, and the shell-to-atlas semantics are discontinuous in the second active window.

## What this audit checked
This audit did **not** try to repair another downstream residual. It checked whether the current `translation_x_pos` failure geometry is better explained by:

1. a still-fixable readout problem, or
2. a broken material/domain continuity problem.

The audit used the real **Round 54 repaired state** for `seed7` and `seed8`, plus the Round 49–54 repair chain and the current `mirror_channel_atlas.py` source.

## Core findings

### 1. Carrier count recovery is no longer the main blocker
By Round 54, `seed8` is no longer failing because it has *too few total carriers*.

- `seed7` active positive `x` translation carriers: `4`
  - shell distribution: `{0: 2, 1: 2}`
- `seed8` active positive `x` translation carriers: `6`
  - shell distribution: `{1: 2, 2: 2, 3: 2}`

So count recovery has already happened.

### 2. The real missing source is still `shell_0`
Even after Round 54:

- `seed7` strongest active shell = `0`
- `seed8` strongest active shell = `3`
- `seed8` still has **no positive translation carrier in `shell_0`**

That means the geometry is still outward-shifted.
The system has learned to populate `shell_1/2/3`, but it still has not restored the high-amplitude inner-core source that anchors `seed7`.

### 3. Amplitude remains far below the seed7 reference despite recovered counts
- `seed7` final active `x` mean polarity projection: `0.1793389098486903`
- `seed8` final active `x` mean polarity projection: `0.037125198401364745`

So the remaining gap is **not** a small counting issue.
It is a source-amplitude issue.

### 4. Inner-shell restoration is still coded as outer-first dependency
The current `mirror_channel_atlas.py` restores `shell_1` only when outer shells are already healthy.
Both:
- `_apply_inner_shell_translation_restoration`
- `_apply_inner_shell_amplitude_source_redesign`

require `shell_2` and `shell_3` to already be positive `translation_like` carriers.

That means inner-shell recovery is not arising as an intrinsic local material property.
It is being allowed only **after** the outer shells have already led.

This is exactly the kind of dependency inversion that makes a simulated material feel discontinuous.

### 5. The second active window still shows semantic discontinuity
In `seed8`, second active window, Round 54:

- `shell_1:x` = `translation_like`, positive
- `shell_2:x` = `translation_like`, positive
- `shell_3:x` = `translation_like`, positive

but the window-level atlas label is still:
- `static_like / z`

So the shell-level state and the atlas/window-level state are not living on the same continuous definition domain.
This is a strong indicator that the current mapping is structurally discontinuous, not just numerically noisy.

### 6. The Round 49 → 50 sequence also supports a continuity problem
- Round 49 repaired retention, but active summary got **shallower**
- Round 50 had to add a summary compatibility layer just to recover the retained-shell2 value

This is not a normal sign of a clean local fix.
It suggests the stack is working across layers that are not naturally aligned.

## Interpretation
The system is no longer mainly saying:
> “I cannot detect `x`.”

It is now saying:
> “I can assemble enough `x` carriers to look plausible, but the material/network does not naturally grow the same inner-shell amplitude source or preserve the same domain continuity that `seed7` has.”

That is why the work starts to feel like a bug loop.
It is not necessarily a coding bug loop anymore.
It is much closer to a **material continuity loop**.

## Formal judgment
This audit recommends:

- **Do not continue generic summary residual repair**
- **Do not reopen old sign / strongest-pair / shell2 retention branches**
- **Proceed to M2 material redesign**

## M2 redesign targets
1. Restore a true **`shell_0` high-amplitude positive `x` carrier source**
2. Remove the current **outer-first dependency** for inner-shell restoration
3. Rebuild shell-to-atlas mapping so window-level semantics do not collapse while shell-level `x` carriers remain present
4. Keep Round 50 + 52 summary/readout stack frozen as support infrastructure, not as the primary path for future gain

## Bottom line
The current project state is **not** best described as “one more summary bug to fix.”
It is better described as:

**the material/network prototype still does not define a fully continuous inner-to-outer `x` transmission domain.**

So the correct next move is to step out of repair-mode and into:

**M2 — material redesign**
