# D-MFDOM — the `MAXFILES` argument domain

> ## ✅ LANDED 2026-07-31 — 53/53, falsified, **NET −6 B**
>
> The filed item was stale *and* the domain behind it held **two live defects**,
> one of them a silent accept. `ex_maxfiles` now takes its argument through
> `eval_byte_arg`: **page 1 free 63 → 69 B, low region unchanged at 23 B.**
>
> * 🔴 **`MAXFILES=65536` was accepted SILENTLY as `MAXFILES=0`** — every file
>   channel disabled, no error — where the reference raises ERR 6 `Overflow`.
>   `eval`'s `flt_to_int16` zeroes `DE` for out-of-int16 values, so the
>   hand-inlined high-byte test could never fire for the arguments it existed
>   to catch.
> * 🔴 **A second defect was invisible to the rows that found the first.**
>   `32768`/`-32769` *are* representable in 16 bits, so the old test fired —
>   with ERR 5 where the reference says ERR 6. Only the boundary rows, added to
>   pin the denominator of the **fix**, could see it.
> * ⚠️ **The probe would have scored the silent accept as `agree`.**
>   `ERR_CLASSES` had no `Overflow`, so an unclassified reference error and a
>   silently-accepting zerobas both read `None` and compared equal. Fixed
>   first — see [`chancost-cf3300-characterization.md`](chancost-cf3300-characterization.md) §0.2.
> * ⚠️ **Two of my own rows were weak and were corrected before they became
>   oracles**: `MAXFILES=1.5` read `mf1`, and 1 *is* the boot default; and a
>   fractional row read off `FRE(0)` is `COMPARE absfre`, i.e. informational —
>   it would have gated nothing on the machine under test.
> * ⚠️ **The knife corrected a prediction.** I expected `MAXFILES=32768` to be a
>   silent accept too. It read `IFC`. Measurement, not reasoning, is what named
>   the second defect.
>
> Results: [`chancost-cf3300-characterization.md`](chancost-cf3300-characterization.md) §11.
> Gate: `make chancost-characterize` — **53 cases, `KNOWN_DIVERGE` EMPTY**.

Owner of the filed item: **S-FCH-2** ([`spec-basic-filechan-alloc.md`](spec-basic-filechan-alloc.md) §7).
Characterization it updates: [`chancost-cf3300-characterization.md`](chancost-cf3300-characterization.md) §3, §7.2.
Gate: `make chancost-characterize`.

## 0. The filed item is STALE — measured, not read off the diff

TODO ([`../TODO.md:12023 (T-F37B1B)`](../TODO.md:12023)) says `MAXFILES=16` raises **ERR 2
`syntax error`** on zerobas where the reference raises **ERR 5 `Illegal function
call`**. That was fixed by `61e3a48` ("S-FCH-2: measure it, and land the half
that costs nothing"), which turned `ex_maxfiles`'s two `jp cc,stmt_error` rejects
into `jp cc,gb_illegal`, and `19e8bfd` (S3) later dropped the lean-cart `ELSE`
arm that still had `stmt_error`.

**Verified by RUNNING the gate at `32fb7ba`, not by reading the commit** — a
clean `make chancost-characterize`, 39 cases, exit 0:

| row | reference | zerobas | verdict |
|---|---|---|---|
| `mf16` (`MAXFILES=16`) | `IFC` | `IFC` | agree |
| `mf255` (`MAXFILES=255`) | `IFC` | `IFC` | agree |
| `err_over` (`ON ERROR` + `MAXFILES=16`, `PRINT ERR`) | **5** | **5** | agree |

`err_over` is the load-bearing one: it reads the trapped **code**, so the
agreement is on the CLASS and not on the wording (which is deliberately
different — PROVENANCE §851). `KNOWN_DIVERGE` is EMPTY and 0 rows diverge.

So the item is **closeable**. This slice does not close it on that alone.

## 1. Why this is a slice and not a checkbox

The filed claim is a statement about a **domain** — "over-ceiling `MAXFILES`".
The gate pins that domain at exactly **two** points, and both are on the same
side of the same test. `ex_maxfiles` ([`basic/files.asm:1382`](../basic/files.asm:1382))
has **two** reject arms:

```
                ld      a,d
                or      a
                jp      nz,gb_illegal       ; arm A: high byte set
                ld      a,e
                cp      FCH_CEIL+1
                jp      nc,gb_illegal       ; arm B: > FCH_CEIL (15)
```

`16` and `255` both have **`d = 0`**. Every typed reject row in the corpus lands
on **arm B**; nothing in 39 cases reaches **arm A**, on either machine. The
recurring lesson applies literally: *sampling 3 of 7 rows gave a different answer
than all 7* ([[gpfi-wrongmode-grid-slice]]) and *measure the DENOMINATOR*.

⚠️ And `ex_maxfiles` reaches its argument through **`eval`**, not through
`get_byte_arg`. That matters and is the reason to expect an answer rather than a
formality:

* `get_byte_arg` ([`basic/interp.asm:1730`](../basic/interp.asm:1730)) is the
  reference-faithful byte-argument path — `get_int16_checked` first (**ERR 6
  `Overflow`** outside int16), *then* the 0..255 test (ERR 5). `WIDTH`, `ON n`,
  `STRING$`, `SPACE$` and `CHR$` all go through it.
* `eval` ([`basic/expr.asm:35`](../basic/expr.asm:35)) is documented as
  *"unsigned 16-bit, low-word on overflow"* and has **no int16 stage at all**.

If that documented wrap is what happens, then `MAXFILES=65536` **wraps to 0 and
is SILENTLY ACCEPTED** where the reference raises. That is the worst class this
project files — a wrong answer with no error — and it is one typed line away
from the rows already in the corpus. It is also *unmeasured*: the wrap is a claim
in `expr.asm`'s header, and how a >32767 literal is even tokenised has not been
checked.

## 2. What this slice measures

Nine rows added to [`probes/disk/diskbasic_probe_chancost.py`](../probes/disk/diskbasic_probe_chancost.py),
which already owns the apparatus this needs: SCREEN-1 geometry, boot-per-case
both sides, the echo guard, and `ERR_CLASSES` comparison-by-class.

| label | typed | arm it aims at |
|---|---|---|
| `mfd_300` | `MAXFILES=300` | **arm A**, first row ever to reach it |
| `mfd_65536` | `MAXFILES=65536` | the wrap — accept-vs-raise |
| `mfd_70000` | `MAXFILES=70000` | beyond int16, non-power-of-two |
| `mfd_neg` | `MAXFILES=-1` | negative |
| `mfd_neg16` | `MAXFILES=-16` | negative, in-range magnitude |
| `mfd_frac` | `MAXFILES=1.5` | fractional, accept side |
| `mfd_frac15` | `MAXFILES=15.9` | fractional AT the accept boundary |
| `mfd_expr` | `MAXFILES=8+8` | over-ceiling reached by an EXPRESSION, not a literal |
| `mfd_noeq` | `MAXFILES 2` | the SYNTAX arm — must stay `SYNTAX` on both |

Each fractional row is `MAXFILES=n : PRINT FRE(0)` so an **accepted** value is
read off the ladder rather than merely "no error": `1.5` truncating to 1 and
`1.5` rounding to 2 are different `FRE(0)` numbers (14849 vs 14799 on zerobas,
23430 vs 23163 on the reference), so the row distinguishes the two rules instead
of agreeing for either reason. Same for `15.9` → 15 vs 16-and-reject.

### 2.1 Controls — paired, per house rule

* **Green control, accept side:** `mf15` and `mf2` already stand, and every new
  accept row is read against the SAME ladder in the same run.
* **Green control, syntax side:** `ctl_syntax` (existing) — a real `Syntax
  error`, so `mfd_noeq` reading `SYNTAX` is not evidence the machine is broken.
* **Green control, expression side:** `mfd_expr` is paired with the existing
  `mf16` — if `8+8` reads differently from `16`, the divergence is in the
  evaluator's hand-off, not in the domain test.
* **The apparatus control** is the echo guard, which already runs before any
  value is read and is fatal.

⚠️ **Every new row is ORACLE-LOCKED in `REF_EXPECT` before it counts.** These are
exploratory rows and the standing lesson is that an exploratory row without a
`want=` cannot be wrong ([[vacuous-gate-row-steers-not-just-misses]]). Method is
therefore two-step and stated in advance:

1. **Characterize.** Run the nine rows with `--side ref` and record what the
   CF-3300 answers. That reading is the oracle; it is written into `REF_EXPECT`
   and into the characterization doc as a measured table.
2. **Gate.** Run both sides. Any zerobas row that differs from the reference is a
   divergence and must be either FIXED or allowlisted with the item that owns it.

Step 1's readings are committed **before** step 2's verdict is known, so the
oracle cannot be back-fitted to whatever zerobas happens to do.

## 3. What lands, by outcome

* **All nine agree** → the slice is **probe + docs only, 0 ROM bytes**. The
  filed TODO item closes on a nine-point domain instead of a two-point one, and
  the stale docs in §4 are repaired.
* **A row diverges** → it is specced and fixed here if it fits the walls, or
  filed with a measured cost if it does not. ⚠️ **Cost a carve before reporting a
  shortfall as a blocker** ([[carve-scout-before-proposing]]) — `clone_scout`
  still reports groups, and page-1 → low moves are always legal
  ([[rom-region-structure-review]]). Walls at `32fb7ba`: **low 23 B, page 1
  63 B**, to be re-measured from clean before any claim.

The likeliest fix shape, if `mfd_65536`/`mfd_70000` diverge, is to route
`ex_maxfiles` through `get_byte_arg` instead of `eval` + hand-rolled `ld a,d /
or a` — which would *replace* code rather than add it, and could be byte-neutral
or negative. ⚠️ But a byte-neutral knife has no symbol witness
([[gpfi-wrongmode-grid-slice]]), so the witness must be a probe row, not a size
delta. **This is a prediction, not a decision** — nothing is edited in `basic/`
until §2's measurement says what is wrong.

## 4. Doc debt this repairs — it CONTRADICTS the code today

1. [`basic/files.asm:1366`](../basic/files.asm:1366) — the `ex_maxfiles` header
   still reads *"A larger value is still a `syntax error` where the reference
   raises ERR 5 Illegal function call — the CLASS is wrong"*. Thirty lines below
   it, the code raises ERR 5. A header that contradicts its own body is worse
   than no header.
2. [`chancost-cf3300-characterization.md`](chancost-cf3300-characterization.md)
   §7.2 — filed as an open incidental finding; it is fixed.
3. [`spec-basic-filechan-alloc.md`](spec-basic-filechan-alloc.md) §7 — the
   S-FCH-2 bullet lists ERR 5 as landed already (§5c does say so), but §7's
   summary line still reads as though the class work is open.
4. [`../TODO.md:12023 (T-F37B1B)`](../TODO.md:12023) — the item itself.

## 5. Gates

Probe-only change → `make chancost-characterize` (39 + 9 = **48 cases**, 0
mangled, 0 oracle drift, 0 unfiled divergence, `KNOWN_DIVERGE` EMPTY).

If `basic/` is touched: clean `rm -rf build && make basic-reloc` (dead-code
**0/0 both builds**) → `make repack-machine` → the full corpus listed in the
session brief. ⚠️ Clean measure **before** `repack-machine`, or the probe reads
the zb column as `None`.

## 6. Sign-off questions

* **Q1 — is nine rows the right denominator, or is this scope creep?** The
  argument for nine: arm A has never been executed by any test on either
  machine, and the `eval`-vs-`get_byte_arg` gap is a documented wrap sitting
  directly under an unmeasured input. The argument against: the filed item said
  "over-ceiling", and 16/255 are over-ceiling. **Recommended: nine.** Closing a
  domain item on two same-side samples is the exact shape this project has been
  burned by repeatedly.
* **Q2 — `MAXFILES 2` (`mfd_noeq`) is a syntax question, not a domain one.**
  Keep it? **Recommended: yes**, as the green control for the `SYNTAX` class —
  it costs one row and it proves the domain rows' `IFC` readings are not the
  machine erroring at everything.
* **Q3 — if a row diverges, fix in this slice or file it?** **Recommended: fix
  it here if it is a silent-accept** (that class is why the rows exist), **file
  it with a measured cost if it is a class-only mismatch on an already-rejecting
  input** — the latter is S-FCH-2's remaining shape and not new.
