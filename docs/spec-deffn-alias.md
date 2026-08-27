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
