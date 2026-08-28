# D-CONCATPEAK — the filed cause was wrong in three ways, and the real one predicts the threshold

**Status:** DIAGNOSED 2026-08-28. The gate hole is CLOSED; the fix is named,
priced in shape, and left as its own slice.

## 1. What was filed

`TODO.md`, from D-FNGCROOT / D-POOLCAP (2026-08-27), on the remaining half of
*"zerobas exhausts a `CLEAR 100` string pool where both references cope"*:

> `str_concat` snapshots **BOTH** operands
> (`basic/str-engine.asm:1435`), so `X$+X$` is 20+20 transient over the 40 B
> result.

🔴 **Three things wrong with that, and acting on it would have edited the wrong
verb:**

1. There is **no `str_concat` label** in the tree.
2. **Line 1435 is `ev_f_instr`** — INSTR. That routine *does* snapshot both
   operands (`efi_dup_a` / the `bT` snapshot), which is presumably how the claim
   arose. It is not concatenation.
3. Concatenation is **`str_concat_tail`**
   ([basic/str-engine.asm:426](../basic/str-engine.asm)), and it snapshots
   **operand 1 only** — operand 2 is passed straight through as `SH_SRC` and
   never copied.

[[a-justification-parenthesis-is-an-unrun-claim]], and
[[a-ranked-candidate-rots-like-a-wall]]: a line-number citation into a file that
keeps moving is a claim with a shelf life.

## 2. The real mechanism

`sh_append` ([sub/strheap.asm:1309](../sub/strheap.asm)) — op 2, the concat
accumulator step — **never appends in place.** For any non-empty total it:

```
        heap_alloc(lenR + lenTk)      ; a NEW body
        copy R's body   into it       ; sap_copy_clamped
        copy Tk's body  into it
        R.len/R.ptr := total/newbody  ; R's OLD body becomes garbage
```

`sap_empty` is the only branch that skips the allocation, and it handles total 0.
So while the new body is being allocated, **R's old body is still live**:

```
peak = held + R's old body + the new body
```

For `LEFT$(X$+X$,0)` with `X$` of length L and `A$` holding 4 B, held = L + 4,
R's body = L, and the new body = 2L:

```
peak = L + 4 + L + 2L  =  4L + 4
```

## 3. 🎯 That is a prediction, and it was tested where the filing never looked

The threshold must **move with L**. A "both operands are snapshotted" story
predicts a fixed 2L overhead and cannot produce this.
[`scratchpad/concatpeak_probe.py`](../scratchpad/concatpeak_probe.py):

| L | predicted `4L+4` | measured |
|---|---|---|
| 10 | 44 | fails at 30, 40 · passes at 50, 60 ✅ |
| 20 | 84 | fails at 70, 80 · passes at 90, 100 ✅ |
| 30 | 124 | fails at 110, 120 · passes at 130, 140 ✅ |

**12/12.** Only L=20 was ever measured before, and it is the case the model was
built on — L=10 and L=30 are the ones that could have refuted it.

## 4. ⚠️ The snapshot's own justification is false

`str_concat_tail` explains its unconditional snapshot as:

> *(unconditional: R must be a fresh temp we can **modify in place** — never a
> var slot; a function-result op1 just costs one extra harmless temp)*

`sh_append` does not modify the body in place; it allocates a new one every time.
What R must be is a **slot whose descriptor can be repointed** — that part is
real, and it is why a var slot will not do. But the **body copy** buys nothing,
and it is exactly the L bytes that make the peak `4L` instead of `3L`.

This is the inverse of [[a-fix-falsifies-the-justification-beside-it]]: not a
justification a later fix invalidated, but one that appears never to have
described `sh_append`'s actual contract.

## 5. The fix, and why it is its own slice

One allocation that copies **both sources** into a fresh body, instead of
copy-then-append: peak `3L + 4`, which makes `CLEAR 70` pass at L=20 and closes
the divergence. That needs a new sub-ROM op (`SH_SRC` + a second source, into a
fresh `SH_DEST` body) — sub-ROM bytes are plentiful, but concatenation is on
every string path in the language, so it earns its own slice and its own battery.

⚠️ **The obvious cheap shortcut does not work.** Making R an empty temp and
appending both operands leaves the peak unchanged at `4L + 4`: the first append
still leaves an L-byte body live while allocating 2L. Only a single combined
allocation reaches `3L`.

### What the slice starts from — the cell question, already surveyed

* **Op numbers 0–11 are taken** (`strheap_engine`'s dispatch), so the new op is
  12 or higher.
* **It needs THREE descriptors — srcA, srcB, dest — and only two cells exist**
  for that shape: `SH_SRC` and `SH_DEST`. A third is required.
* Reusing a cell across mutually-exclusive ops is this engine's established
  pattern (`SH_NUM` is HEX/OCT's, `SH_FILLBYTE` is FILL's, `SH_START`/`SH_COUNT`
  are SLICE's). 🔴 **But the obvious candidate, `SH_P`, is INSTR's — and
  concatenation can appear INSIDE an INSTR argument** (`INSTR(A$+B$,"x")`).
  `ev_f_instr` guards `p` on the STACK and writes `SH_P` only just before the
  search, so the orders probably do not collide — **"probably" is not a contract
  for a shared cell, and that is the first thing the slice must settle**, not the
  last. The alternative is a new cell, which means walking the RAM map
  (`scratchpad/rammap_sweep.py`) because [[deffn-ramhunt-slice]] — RAM has no
  gate, and a delta between two names is not free space.

## 6. The gate hole, closed

The recovered ground from D-POOLCAP (threshold 120 → 100) was **pinned by
nothing** — the fix could have regressed silently.
`probes/basic/basic_probe_clearpool.py` now carries:

* **gated** — `tslice-100`, `tslice-120`, and `tslice-var70`, the row that
  separates *slicing a temp* from *slicing a variable* (green at `CLEAR 70` on
  every side), so a future failure that took it too would be a different defect;
* **reported, never gated** — `topen-70` / `topen-80`, the still-divergent half.

They existed only in `scratchpad/leftkeep_probe.py`. The battery now shows the
open half on every run: **65/65 gated rows agree, 7 reported.**
