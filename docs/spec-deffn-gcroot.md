# D-FNGCROOT — a string formal's shadow slot IS a GC root, and two rounds of green proved nothing

**2026-08-27.** Closes the measured half of the item D-DEFFN filed on 2026-08-22
([`docs/deffn-impl-2026-08-22.md`](deffn-impl-2026-08-22.md) §8), which ended
*"the ROW that would catch it does not exist yet."* It exists now, it went red,
and the fix is **30 B of sub page 0**. One residual is refiled 🙋.

## 1. The premise, re-run on the shipped code

Filed against the **draft**; DEF FN shipped 2026-08-23. Both halves still hold:

* `sg_walk` ([`sub/strheap.asm:750`](../sub/strheap.asm:750)) called
  `sg_walk_scalars`, `sg_walk_arrays`, `sg_walk_temps` — **and nothing else**.
* A string formal's slot really is a `[len][ptr]` descriptor at `entry+3`,
  because `str_set_key` ([`basic/vars.asm:979`](../basic/vars.asm:979)) snapshots
  the actual into a temp, stores **that copy's** descriptor into the destination,
  and then restores `TEMPTOP` — releasing the temp. While an FN call is live the
  destination is a shadow slot, since `scv_find` consults `fn_shadow_find` first
  ([`sub/arrays.asm`](../sub/arrays.asm)).

⚠️ One thing in the neighbouring prose is **not** true of the tree:
`basic/deffn.asm:48` describes *"four `call fn_shadow` preludes in
basic/vars.asm"*. There is no `fn_shadow` symbol anywhere — that paragraph
records a **rejected** design (~64 B of main ROM) whose job the sub-side
`scv_find` does instead. Read as current, it sends you looking for the redirect
in the wrong ROM.

## 2. Two rounds of green that proved nothing

🔴 **THE FIRST ROW AGREED, AND ITS "DOES IT MOVE" ARM WAS BLIND.**
Round 1 put `FRE("")` (which compacts first) at the head of the body and read the
formal after it. All three sides said `ABCD`. Its check that the heap really
moved used `VARPTR(A$)` — which is the address of the **descriptor**, in the
variable table, and does not move during a collection at all. It reported the
same number everywhere and separated nothing.

Round 2 replaced it with the descriptor's **ptr field**, read either side of the
collection in one run — [`scratchpad/deffn_gcmove_probe.py`](../scratchpad/deffn_gcmove_probe.py):

| row | vg8020 | cf3300 | zb |
|---|---|---|---|
| `m.move` (ptr before → after) | 61787 → 61797 | 56402 → 56412 | **47851 → 47868** |
| `m.move2` (bigger hole) | 61777 → 61797 | 56392 → 56412 | **47836 → 47868** |
| `m.varptr` — the blind arm, kept as a negative control | 32596 → same | same | same |

🎯 **The body moves, and it moves UPWARD** — which is exactly why round 1 could
never have caught the hazard. The dead copy is the **lowest** allocation, so a
collection moves every live body *away* from it and leaves its bytes intact. A
green row here was luck of direction, not correctness.

## 3. The row that catches it

The frontier has to march back **down** over the copy, so the body must
**allocate after the collection** and only then read the formal — all inside one
expression, evaluated left to right:

```basic
DEF FNA$(S$)=LEFT$(STR$(FRE(""))+X$+X$,0)+S$
                   \____ GC ____/  \ alloc /   then read the stale slot
```

| row | what it isolates | vg8020 | cf3300 | zb (before) |
|---|---|---|---|---|
| `o.gcroot` | formal + collect + allocate | ABCD | ABCD | **`376A`** |
| `o.gcroot.ctlv` | same expression, ordinary variable | ABCD | ABCD | ABCD ✅ |
| `o.gcroot.ctln` | formal, no collection, no allocation | ABCD | ABCD | ABCD ✅ |
| `o.gcroot.ctla` | formal, allocation but no collection | ABCD | ABCD | ABCD ✅ |

Each control removes exactly **one** of the three ingredients, so the subject is
the only row that can be red for this reason. `376A` is not a wrong answer — it is
raw heap bytes.

🔴 **THE CONTROL CAUGHT A CONFOUND BEFORE THE SUBJECT DID.** At `CLEAR 100` the
*variable* control `o.gcroot.ctlv` — which has no FN in it at all — failed with
`Out of string space` on zerobas while both references returned `ABCD`. That is a
pool-capacity divergence, not a GC-root one, and it would have been read as the
subject failing. The rows moved to `CLEAR 400`, where every control is green on
every side; the capacity finding is filed separately (green from `CLEAR 150`).

## 4. The fix

`sg_walk_fnframe` in [`sub/strheap.asm`](../sub/strheap.asm) — walk
`[FN_PAREA, FN_FEND)`, stride `FN_SLOTSZ`, visit `entry+3` where `entry+2 == 1`.
Same shape as `sg_walk_scalars`; the end test is byte-wise against `FN_FEND`,
mirroring `fn_shadow_find`'s own loop. `FN_FEND == low FN_PAREA` means "no FN
call in progress", so a program with no live call pays one compare.

**Price: 30 B of sub page 0** (2464 → 2434 free). The main ROM does not move:
low region **39 B** and page 1 **89 B**, identical before and after.

`o.gcroot` **`376A` → `ABCD`**, all controls unchanged. The four rows are now in
[`probes/basic/basic_probe_deffn.py`](../probes/basic/basic_probe_deffn.py) and
gate under `make deffn-strict` (4 printed, 4 scored, 0 divergent, 0 of 11
controls failed).

## 5. What it does NOT fix — measured, not implied

`sg_walk_fnframe` walks the **live** frame. `fn_enter` saves the caller's live
prefix to the **Z80 stack**, which no walk can address, so during a nested call an
outer string formal has the same hazard. Claimed in the code comment and then
measured — [`scratchpad/deffn_gcnest_probe.py`](../scratchpad/deffn_gcnest_probe.py):

```basic
DEF FNI$(T$)=LEFT$(STR$(FRE(""))+X$+X$,0)+T$    inner: collect, then allocate
DEF FNO$(S$)=FNI$("q")+S$                       outer: call inner, THEN read S$
```

| row | vg8020 | cf3300 | zb |
|---|---|---|---|
| `n.outer` | qABCD | qABCD | **`q75AB`** |
| `n.outer.ctl` — same nesting, no collection | qABCD | qABCD | qABCD ✅ |

🎯 **This is the SAME root cause as D-FNALIAS** ([`spec-deffn-alias.md`](spec-deffn-alias.md)):
`fn_enter` resets `FN_SLOTP` to slot 0 and parks the caller's frame on the Z80
stack, so only one frame is ever addressable. Aliasing and the outer-frame GC hole
are two symptoms of that one decision, and both fixes want the same thing — frames
that coexist in the shadow area — which needs page-3 RAM below `LINEBUF`. Refiled
🙋 there, with this row as its second piece of evidence.

The `n.outer` row is deliberately **not** added to the probe: `deffn-strict`
requires every gate row to match and has no XFAIL class.
