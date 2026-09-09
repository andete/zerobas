# D-FNALIAS — the aliasing divergence is REAL, and the cheap fix is refuted by a second measurement

**2026-08-27.** Takes the reference reading `TODO.md` asked for before the fix
could be priced ([`docs/deffn-impl-2026-08-22.md`](deffn-impl-2026-08-22.md) §8),
and prices it. **The fix is NOT the ~30 B the item guessed, and not for the
reason it guessed.** Refiled 🙋: it costs scarce page-3 RAM.

## 1. The premise was re-run, not inherited

The item was filed **2026-08-22 against a DRAFT**; DEF FN shipped **2026-08-23**
(D-DEFFNLAND). The draft's binding behaviour therefore had to be re-established
on the shipped code, not assumed. It survives: `sub/deffn.asm`'s `dfn_a_x` grows
`FN_FEND` over each slot **as it is opened**, so a slot is visible to the shadow
lookup while the *remaining* actuals are still being evaluated.

## 2. The reference reading — both references agree, so there IS an oracle

[`scratchpad/deffn_alias_probe.py`](../scratchpad/deffn_alias_probe.py), driven
through the shipped probe's own fixture so a fixture fault reddens a control
first.

| row | program | vg8020 | cf3300 | zb |
|---|---|---|---|---|
| `o.alias` | `DEF FNA(P,Q)=P*100+Q : P=3 : PRINT FNA(5,P)` | **503** | **503** | **505** |
| `o.alias.ctl` | …`PRINT FNA(5,7)` | 507 | 507 | 507 ✅ |
| `o.aliasnest` | `DEF FNA(X,Q)=X*100+Q : DEF FNB(X)=FNA(9,X) : PRINT FNB(3)` | **903** | **903** | **909** |
| `o.aliasnest.ctl` | …`DEF FNB(X)=FNA(9,7)` | 907 | 907 | 907 ✅ |

**The reference evaluates EVERY actual in the caller's scope.** zerobas lets the
first formal's binding shadow the caller before the second actual is read. Two
live divergences, both controls green.

⚠️ **Prediction scored.** I predicted zb = 505/909 from reading `dfn_a_x` — right.
I also guessed the reference would shadow the same way — **wrong**; it does not.

## 3. Two rows, two different causes

They are not one defect with one fix.

* **`o.alias` (top level).** `FN_FEND` starts at `low FN_PAREA` ("no call in
  progress"). `dfn_a_x`'s *grow, never shrink* makes slot 0 live immediately, so
  `Q`'s actual `P` finds the binding. **Removing that block alone fixes this row
  and frees 8 B.**
* **`o.aliasnest` (nested).** `fn_enter` resets `FN_SLOTP` to slot 0 on *every*
  call, so the callee's binding **physically overwrites** the caller's slot 0.
  `FN_FEND` already covers slot 0 from the caller's own frame, so the grow is not
  even involved. **Removing the block does nothing here.** The caller's copy is
  saved on the Z80 stack by `fn_enter`, but `fn_shadow_find` reads the live area.

🔴 **This is why D-DEFFNKNIFE's K-GS1 reddened ZERO rows.** That knife cut exactly
this *grow, never shrink* block on 2026-08-26 and nothing went red; I recorded
then that it was "not a licence to delete it". The cause was the ROW SET: nothing
separated the two behaviours. `o.alias` is that row, and with it K-GS1 becomes an
observable knife.

## 4. The cheap fix, and the measurement that refutes it

The obvious repair is to start a call's slots **above** the caller's live frame
(`FN_SLOTP := FN_FEND` at entry), drop the grow, and relocate down at
`dfn_body` — roughly **+17 B**, all in `sub/`, which has **2464 B free on page 0**
against the item's assumed "a region that has none". So the item's *price* premise
was wrong.

Its *conclusion* survives anyway, for a reason the item did not name. Both frames
must coexist during binding, and the shadow area holds **nine slots, full stop**:

```
FN_AREA equ ((LINEBUF - FN_PAREA)/FN_SLOTSZ)*FN_SLOTSZ    ; basic/sysvars.inc:3325
FN_MAXP equ FN_AREA/FN_SLOTSZ                             ; the ceiling IS this division (9)
```

So the design only works if a nested call may have fewer than nine formals. It
may not — [`scratchpad/deffn_nestcap_probe.py`](../scratchpad/deffn_nestcap_probe.py):

| row | vg8020 | cf3300 | zb |
|---|---|---|---|
| `o.p9nest` — nine formals called from inside `FNB(X)` | **9** | **9** | **9** ✅ |
| `o.p9nest.ctl` — the same nine at top level | 9 | 9 | 9 ✅ |

🎯 **zerobas matches the reference here PRECISELY BECAUSE it clobbers.** The cheap
fix would trade a measured divergence for a *different* measured divergence
(`o.p9nest` → ERR 5), which is not a fix. Supporting caller + callee needs ~18
slots ≈ **198 B** where 99 exist, and `FN_AREA` is bounded by `LINEBUF` — D-DEFFNEV
already slid the area up against it.

### 4.1 🔴 AND 18 IS THE WRONG NUMBER — THE REFERENCE HAS NO CEILING HERE (2026-09-09)

The 198 B was derived from **one row at depth 2**. Joost authorised
*"we need to match the reference"*, so the first thing to do with that
authorisation was ask what the reference's ceiling actually is, rather than build
to a number taken from a single measurement
([`scratchpad/deffn_nestdepth_probe.py`](../scratchpad/deffn_nestdepth_probe.py),
[`.out`](../scratchpad/deffn_nestdepth.out)). Nine formals at the innermost
level, at nesting depths 1 to 4:

| row | vg8020 | cf3300 | zb | what it asks |
|---|---|---|---|---|
| `d.n1` | 9 | 9 | 9 | nine formals at top level |
| `d.n2` | 9 | 9 | 9 | …called from inside ONE outer FN |
| `d.n3` | 9 | 9 | 9 | …from inside TWO |
| `d.n4` | 9 | 9 | **ERR 7** 🔴 | …from inside THREE |

**Both references answer 9 at every depth probed.** A fixed 18-slot area would
close `o.alias` and `o.aliasnest` and then introduce a NEW ceiling of its own at
some depth — which is *"a bigger number is a different wrong answer, not a fix"*,
the exact reasoning `docs/spec-basic-trapsvc.md` §6 used, and §10 then had to
**invert** when the references turned out to have no fixed array either.
Building one here would be making that mistake a second time in the same tree.

🟢 **AND `d.n4` IS A NEW DIVERGENCE WITH A ROW AT LAST.** zerobas's `ERR 7` at
depth 4 is NOT the shadow area — it answers 9 at depth 3 *because it clobbers*,
so nine slots always suffice however deep it goes. It is the `DEF FN` nesting cap
of **three** that §19 (D-FNSTK) measured and called *"not a constant, it is the
Z80 stack's address"*. That item had no differential row; this is one.

### 4.2 ➡️ SO THE SHAPE IS A POOL FRAME, AND IT COSTS NO NEW RAM

`ctl_alloc` (`basic/str-engine.asm`) already is a HIMEM-bounded allocator —
`HL` = size in, frame base out, `CF=1` when it collides with `CTLLIM` — and
D-CTLPOOL landed it precisely because the references allocate control frames from
one pool rather than from fixed arrays. A `DEF FN` call's shadow frame is the
same kind of object.

* Each call allocates `formals × FN_SLOTSZ` from the pool, so the caller's frame
  is never in the callee's way and **both alias rows close**.
* Depth becomes HIMEM- and `CLEAR`-bounded like the references, which is also
  the shape `d.n4` asks for.
* It **frees** the 99 B `FN_PAREA` array instead of spending 99 more. Joost's
  RAM authorisation is not needed.
* `FN_FEND`'s two meanings — the visibility window *and* the "a call is in
  progress" gate — separate naturally: the frame pointer is the window, and
  "no frame allocated" is the gate. That is the exact overloading the −8 B
  attempt proved cannot be skipped.

⚠️ **THE COST IS ADDRESSING, AND IT IS NOT SMALL.** Slots are reached today by
LOW BYTE against a fixed page (`ld h,high FN_PAREA`, `FN_SLOTP` is one byte); a
pool frame is at an arbitrary 16-bit address, so the slot walk becomes 16-bit
through `sub/deffn.asm`, the formal lookup in `sub/arrays.asm`, the GC root walk
`sg_walk_fnframe` in `sub/strheap.asm`, and `basic/usr.asm`'s in-progress test.
That is a slice, not an edit — and it is why this went back to Joost rather than
being built under the authorisation he had already given for a different shape.

## 5. Why this is 🙋 and not 🤖

Every remaining route spends **scarce page-3 RAM** or accepts one of two measured
divergences:

1. Grow the shadow area (~+99 B of page-3 RAM) — needs something evicted below
   `LINEBUF`.
2. Evaluate actuals into RAM temps before binding — the temps cannot live on the
   Z80 stack (a `CALSLT` is not resumable, which is why the parse state is in RAM
   at all: `basic/sysvars.inc:3293`), so this is the same RAM question in a
   different shape.
3. Fix `o.alias` only (**−8 B**, delete the grow) and leave `o.aliasnest`
   diverging — a real improvement, but it ships a knowingly-partial rule.

Which of those is worth what it costs is a page-3 eviction call, not a reference
question. The reference has said everything it can say.

## 6. What is deliberately NOT in the tree yet

The four `o.alias*` rows are **not** added to
[`probes/basic/basic_probe_deffn.py`](../probes/basic/basic_probe_deffn.py).
`make deffn-strict` requires every gate row to match and the probe has no XFAIL
class; adding a knowingly-divergent row would redden a green battery, and
inventing an XFAIL mechanism to hold one finding is how a battery learns to lie.
They are recorded here with their measured reference values and reproduce on
demand from the tracked scout. **Adding them to `CASES`/`WANT` is step 1 of
whichever fix is chosen** — the rows exist, the oracle is banked.
