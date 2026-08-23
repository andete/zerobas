# SPEC — D-DEFFNKNIFE: the knives DEF FN shipped without, and the switches nothing ever flipped

Status: **LANDED.** 2026-08-23, on top of D-DEFFNLAND (`0f18221`).
**No ROM byte changed**: `build/basic-reloc.rom` `7942cc20`,
`build/sub.rom` `34bb8554`, `build/zerobas-main-eu.rom` `031184d9`, before and
after, from clean.

Two jobs, and each found something the other could not have.

---

## 1. The problem, stated exactly

`make deffn-acceptance` had **69 subject rows agreeing with two reference
machines, and not one of them had been shown capable of disagreeing** about the
shipping implementation. `make deffn-selftest` mutation-tests the *classifier*
against planted face tables (18/18) — a claim about the instrument's
arithmetic, not about whether the ROW SET would catch a defect in
`basic/deffn.asm` or `sub/deffn.asm`. Exactly one knife existed: **K-DE1**
(`scratchpad/deffn_de_knife.py`), 0 → 31 of 69 rows.

That is this project's own most-repeated lesson
([[apparatus-is-part-of-the-measurement]]) pointed at its newest verb.

**`scratchpad/deffn_knives.py`** is the answer: eight knives, every prediction
written before the run, misses scored. Run 1:
[`scratchpad/deffn_knives.out`](../scratchpad/deffn_knives.out). The two
corrected knives: [`scratchpad/deffn_knives2.out`](../scratchpad/deffn_knives2.out).

---

## 2. 📏 The scoreboard — **6 of 8 EXACT on the first run**, and the two misses were the findings

| knife | cut | predicted | measured | |
|---|---|---|---|---|
| **K-DF1** | `sub` ceiling → the falsified `cp low FN_PAREA_END` | **{}** | **{}** | EXACT |
| **K-CE1** | `cp FN_AREA` → `cp FN_AREA-FN_SLOTSZ` | `{o.p9}` | `{o.p9}` | EXACT |
| **K-CE2** | `cp FN_AREA` → `cp FN_AREA+FN_SLOTSZ` | `{o.p10}` | `{o.p10}` | EXACT |
| **K-DE2** | `fn_leave`: `ld d,b/ld e,c` → `ld d,h/ld e,l` | 6 INT-result rows | the same 6 | EXACT |
| **K-PR1** | PRINT's FN arm: `jp z,exp_strvar` → `jp z,exp_num` | `{b.str, o.defstr, o.quotedcolon}` | the same 3 | EXACT |
| **K-RT1** | `dfn_bodydone`: `ld a,(FN_RTYPE)` → `ld a,4` | `{o.defint, o.fnpct}` | the same 2 | EXACT |
| **K-FE1** | `raise_error`: `ld (FN_FEND),a` → `ld (FN_TYP),a` | `{o.errrestore}` | **{}** | 🔴 MISS |
| **K-SF1** | `fn_enter`: `cp high FN_STK_FLOOR` → `cp 0` | **{}**, `b.recurse` BLANK | `{b.recurse}` | 🔴 MISS |

After the two findings below were acted on, K-FE1 and K-SF1 were re-cut against
corrected predictions and both are **EXACT**. Every knife's baseline was a clean
build scoring 0 DIFF / 0 control FAIL / 0 blank / 0 claim FAIL, every knife
asserted the RIGHT image moved (a `sub/*.asm` cut moves `sub.rom` only; a
`basic/*.asm` cut moves `basic-reloc.rom` + the merged image and NOT `sub.rom`),
and the restore put all four sources back byte-identical.

---

## 3. 🔴 K-DF1: the handoff's own knife reddens nothing, and that is a claim about a LAYOUT

D-DEFFNLAND §3.1's headline defect was the ceiling test

    ld  a,(FN_SLOTP)
    cp  low FN_PAREA_END
    jp  nc,fn_toomany

reading as `cp 0` — **44 of 69 rows**, ERR 5 on the first formal — because
`FN_CELLS` had grown 3 → 11 and slid `FN_PAREA_END` to `$EB00` exactly. The
handoff for this slice said, reasonably: *"A knife restoring that old compare
reddens `o.p3`."*

**It reddens nothing, and the prediction that it would not was written from the
sym before the run.** `make basic-reloc` emits

    FN_PAREA        EQU 0EA9CH
    FN_PAREA_END    EQU 0EAFFH

because the SAME slice that fixed the compare also deleted the `FN_REQ` cell
(§4.1, `FN_CELLS` 11 → 10), sliding the area back down. `low FN_PAREA_END` is
`$FF` again, `FN_SLOTP` only ever takes the values `$9C + 11k` for `k = 0..9`,
and `cp $FF` is NC on exactly one of them — the tenth. The old form and the
shipping form agree on **every reachable input**.

🎯 **THE LESSON IS NOT "THE OLD CODE WAS FINE".** It is that the defect was never
a property of those instructions: it was a property of the instructions
**times the layout**, and the layout moved back. A knife aimed at the *source
form* of a defect can therefore be a no-op while the defect class is wide open —
which is why the ceiling needed the two knives below and not this one.
Same family as [[a-derived-constant-falsified-from-another-file]], read from the
other end.

### 3.1 The two that DO cut, and why one would not have been enough

* **K-CE1**, one slot too LOW (`cp FN_AREA-FN_SLOTSZ`) → **`{o.p9}` alone.**
  `o.p8` stays green on one side, `o.p10..o.p16` (already ERR 5) on the other.
* **K-CE2**, one slot too HIGH (`cp FN_AREA+FN_SLOTSZ`) → **`{o.p10}` alone.**

The measured nine-formal ceiling is pinned from **both** directions by **one row
each**, and the two rows are different rows. A suite carrying only one of them
would certify a test that is half blind — and the too-HIGH direction is the one
the falsified compare also got wrong (a wrapped `FN_SLOTP` read as legal), so it
is precisely the half that had no witness.

---

## 4. 🔴 K-FE1: the row the SOURCE named as its evidence is blind to it

`basic/interp.asm`'s `raise_error` resets `FN_FEND`, and said so:

> *"a stale FN_FEND would leave every later reference to a formal's NAME reading
> a dead slot. That is a silent wrong answer, and **o.errrestore** … is the row
> that says so."*

`sub/arrays.asm` carried the same sentence. **Both were wrong.** K-FE1 disabled
the reset and `deffn-strict` stayed **0 of 69 divergent**.

**Why**, and it is written in this tree's own header three files away —
`fp_runtime_error`: the float ops *"have no mid-expression unwind, only SET
FPERR and yield a defined value (0)"*, and the abort is *"realized at the
statement boundary"*. So in `o.errrestore` (`DEF FNA(X)=X/0`, called as
`Y=FNA(2)`) the division does **not** raise: the FN call **returns normally**,
`fn_leave` restores the frame in the ordinary way, and only then does `ex_let`'s
FPERR check funnel into `raise_error` — with nothing stale to reset. The row
scores `5 11` with the guard and `5 11` without it.

🎯 **A DEFERRED ERROR IS NOT AN ERROR AT THE PLACE IT IS WRITTEN.** Every row in
the 69 that faults inside an FN body faults this way or faults *before* a slot is
opened. The guard had **no witness at all**.

### 4.1 The rows that do score it — measured, not predicted

The shape needed is a fault that reaches `jp raise_error` **while the frame is
live**, where the trap path resets SP outright and `fn_leave` never runs. The
tenant's own dispositions are exactly that. Both were read off **both**
references ([`scratchpad/deffn_fend_probe.out`](../scratchpad/deffn_fend_probe.out)):

| row | program | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|---|
| `o.errfend18` | `X=5:DEF FNA(X)=FNZ(0)` … `Y=FNA(2)` | `5 18` | `5 18` | **`5 18`** |
| `o.errfend13` | `X=5:DEF FNA(X)=A$` … `Y=FNA(2)` | `5 13` | `5 13` | **`5 13`** |
| `o.errrestore` (the separating control) | `X=5:DEF FNA(X)=X/0` … | `5 11` | `5 11` | **`5 11`** |

Under K-FE1 the two new rows read **`2 18`** and **`2 13`** — `X` is the dead
formal — while `o.errrestore` stays green. The three programs differ **only in
which error the body raises**, so the deferral is what separates them and
nothing else.

`deffn-strict` is now **0 of 71 divergent, 0 of 8 controls failed, 3 of 3
address claims PASS**, and both source comments have been corrected to name the
rows that actually carry the claim ([[a-fix-falsifies-the-justification-beside-it]],
here in the form *the justification was already false and only a knife could
tell*).

---

## 5. 🔴 K-SF1: the blank that wasn't — a runaway ANSWERS

The second miss went the other way. Removing `fn_enter`'s `FN_STK_FLOOR` test
(`cp high FN_STK_FLOOR` → `cp 0`, which never sets CF) lets `DEF FNA(X)=FNA(X)`
recurse without bound. The prediction was that the probe would read
`<NO OUTPUT>` — scored `....` NOT MEASURED, **not** a divergence — and that the
floor would therefore turn out to be pinned by no scored row at all.

**Measured: `b.recurse` reads `ERR 8 AT 60` against a wanted `ERR 7 AT 60`.** The
row diverges, the floor IS pinned, and the failure mode is not a silence but
*Undefined line number* — a wrong answer of entirely the wrong kind, produced by
a stack walking down through the program text. 🎯 One more instance of the
pattern this arc keeps meeting: **every wrong answer here is a plausible
something, never visible damage** (K-DE1's `22529`, the draft's `-3392`, and now
an ERR 8 from a stack floor).

---

## 6. What the other four knives pinned

* **K-DE2** — `fn_leave`'s `DE`, the third instance of
  [[a-scratch-register-that-was-the-callers-value]]. Predicted and measured
  `{o.defint, o.dynaddr, o.fnpct, o.realcell, o.suffn, o.varptr}` — **the six
  rows whose FUNCTION resolves INT**, which is the draft's original footprint
  ("six rows, six bodies, one identical `-3392`") recovered exactly.
  🎯 **A DIFFERENT SET FROM K-DE1's 31**: K-DE1 destroys the ACTUAL's value (an
  integer *literal* is FACTYP=2 too), this destroys the RESULT's. Same class,
  disjoint evidence, and the two together are what make the class covered rather
  than sampled.
* **K-PR1** — PRINT's item classification, exactly the three rows
  `basic/print.asm`'s own comment names. ⚠️ **`o.numstr` stays green and is NOT
  evidence**: it wants ERR 13 and the knife produces ERR 13 by a different
  route, [[a-case-that-agrees-can-agree-for-the-wrong-reason]] in miniature.
* **K-RT1** — *"the FN's own type IS its result type"*, cut from the type side:
  `{o.defint, o.fnpct}`, with `o.fnbang`/`o.defintbang` green as the single-typed
  twins. That is the `o.fnpct` 2 / `o.fnbang` 2.5 pair, certified.
* **K-DF1** — §3.

**Two of the handoff's four named sites turned out to be ONE.** `fn_slot`'s type
byte in `E` was a *draft* defect in main-side code that no longer exists: the
slot open moved into the tenant (`dfn_a_open`), which runs under CALSLT with its
own `DE`. The only thing protecting the servicer's live `DE` across that boundary
is the `push de`/`pop de` in `fn_lp` — **which is K-DE1's site**. No second knife
was cut for it, and that is a finding, not an omission.

---

## 7. 💰 Second job: the build-switch class, closed by a gate — `make switch-build-check`

D-DEFFNLAND §3.3 found `G8_RESIDENT equ 0` unbuildable and fixed the instance;
`scratchpad/alias_gate_sweep.py` said it was 1 of 107 label aliases. **The class
was open, and the sweep was a scratch script, not a gate.**

`tools/check_switch_builds.py` assembles the main image with each of
`G6_RESIDENT` / `G7_RESIDENT` / `G8_RESIDENT` / `I1_RESIDENT` / `TRAPS_T3` /
`TRAPS_T4` set to 0 in turn and asks **only that it BUILDS** — not that it fits,
not that it is correct; a disabled feature's stub moves the walls, and gating a
wall here would fail for reasons that are not the switch. Scope is asserted, not
assumed: `scope_holds()` refuses to report a PASS if any switch is ever read from
a file outside `basic/`.

### 7.1 🔴 It was RED on TWO switches, and fixing one revealed a THIRD

| round | reading |
|---|---|
| 1 | `FAIL G7_RESIDENT` — `Symbol 'gfx_syntax' is undefined  on line 1522 of file basic/interp.asm` |
| 1 | `FAIL G8_RESIDENT` — `Symbol 'g8_open_paren' is undefined  on line 1063 of file basic/graphics.asm` |
| 2 | `FAIL G7_RESIDENT` — `Symbol 'spr_tenant' is undefined  on line 1350 of file basic/graphics.asm` |
| 3 | **6 of 6 assemble** |

**Every one is the same shape and none is an alias.** The class D-DEFFNLAND filed
as *"an `equ` alias to a conditionally-assembled symbol"* is really
*"**any** symbol defined inside one feature's `IF` and used from another's"*, and
the sprite/VDP pair is riddled with it because the two features share grammar:

* `gfx_syntax` (the trappable ERR 2) is defined in G7's block and used by G8's
  `LET VDP(0)=` / `LET BASE(0)=` refusal, over in `interp.asm`;
* `g8_open_paren` / `g8_num_operand` are defined in G8's block and called by G7's
  `spr_parse_index`, because `SPRITE$(n)` and `VDP(n)` are the same grammar;
* `spr_tenant` is defined in G7's block and called by G8's `g8_run`, because
  `VDP(n)=v` runs through the same page-0 tenant.

⚠️ **AND EVERY DIAGNOSTIC NAMES A DIFFERENT FILE AND A DIFFERENT FEATURE FROM ITS
CAUSE.** Turn off SPRITE and the assembler complains about VDP code; turn off VDP
and it complains about sprite code. That is precisely why this must be a standing
gate and not a thing you re-derive mid-slice.

### 7.2 The fixes cost the shipping build ZERO, and that is measured

`gfx_syntax` is an `equ` and was **hoisted** above `IF G7_RESIDENT` (an `equ`
emits no bytes). The other two were **bracketed** — `ENDIF` before, `IF …` after
— so that in the shipping build, where every condition is true, the same
instructions are emitted **in the same order**. Neither routine is entered by
fallthrough (`spr_parse_index` ends in `ret`; `g8_int_result` ends in `jp`), so
the bracket is safe.

> **The proof is the hash.** Clean `rm -rf build && make repack-machine` after all
> three fixes: `7942cc20` / `34bb8554` / `031184d9` — the same three the arc
> shipped. Not one byte moved.

### 7.3 🔴 And the gate's FIRST green run broke the next gate

`latch-check` went **rc=2** in the very battery that first ran
`switch-build-check` green:

    APPARATUS FAILURE -- openMSX preflight: NOTHING WAS MEASURED
      STALE       build/zerobas-main-eu.rom

The tool rewrites `basic/sysvars.inc` and restores it **byte-identical** — but
the write bumps the **mtime**, so `make -q` reports the shipping ROM out of date
and `probes/lib/latch_check.py`'s preflight refuses. Every emulator gate after it
would have refused until someone rebuilt.

🎯 **THE FIX INVERTS THIS TREE'S OWN KNIFE RULE, DELIBERATELY.** A knife must
*never* preserve mtime (make then rebuilds nothing and the next gate scores the
previous knife's ROM). This is not a knife: the content is provably identical, so
there is nothing to rebuild, and the tool now restores the mtime with
`os.utime()` immediately after the byte-identity assert. Verified: `make -q
build/zerobas-main-eu.rom` is rc=0 before **and** after the gate, and
`latch-check` is 16/16 immediately after it.
[[apparatus-is-part-of-the-measurement]] — the instrument I added to measure the
switches was itself a fault in the apparatus, on its first green run.

---

## 8. What was run

**Static, all rc=0:** `basic-reloc` (all four walls, dead-code both builds,
audit-citations, tenant closure, resident ABI), `unit-test` **59/59 files**,
`deffn-selftest` **18/18**, **`switch-build-check` 6/6**, `wall-assertion-check`,
`redundant-load-check`, `rowshape-check`, `injector-check`, `preflight-check`,
`latch-check` **16/16**, `diskdep-check`, `diskdep-selftest`.

**The verb:** `deffn-strict` — **0 of 71 DEF FN rows divergent, 0 of 8 controls
failed, 3 of 3 address claims PASS** (87 printed, 82 scored).

**`kwsweep`:** `DIVERGENT=1  NO-ORACLE=5  SUPPORTED=30  WEAK=1` — unchanged, no
`MISSING=` line.

**Knives:** 8 of 8 cut in their final configuration; 6 of 8 EXACT against
first-run predictions, both misses diagnosed and re-cut EXACT.

⚠️ **The eleven emulator batteries are covered by BYTE-IDENTITY, not by
re-running all of them.** Every source change here is a comment, an `IF`/`ENDIF`
bracket, a probe row, or a new tool; the three shipping artefacts hash the same
as at `0f18221`, so the machine under test is literally the same machine.
`graphics-acceptance` and `lineerr-acceptance` were re-run anyway, because
`basic/graphics.asm` is where the structural edits landed and a control that
costs four minutes is worth more than an argument.

---

## 9. What is NOT claimed

* **The row set is not proven complete.** Eight knives is a candidate roster, not
  a verdict [[a-hand-listed-denominator-is-a-scope-claim]]. Unknifed and named:
  the phase discriminator (`dfn_is_result`'s `inc a`), `fn_enter`'s
  "only the live part" copy length, the `$FFFF` result-slot re-key itself (K-RT1
  cuts the TYPE it writes, not the KEY), `dfn_delim`'s two-cursor swap, and
  `FN_FEND`'s grow-never-shrink rule in `dfn_a_x`.
* **`o.errfend18`/`o.errfend13` close ONE guard.** The wider question — how many
  other rules in this tree are witnessed only by a DEFERRED error, and therefore
  witnessed by nothing — is filed, not swept.
* **`switch-build-check` assembles ONE image and asks ONE question.** It does not
  link, boot, or run a switched-off build, and it does not test switch
  COMBINATIONS (2⁶, and the failure it exists to catch is per-switch).
* **Nothing about** formal aliasing, the string formal's shadow slot as a GC
  root, or `RESUME`/`CONT`/`TRON`/array actuals — the impl slice's filed list,
  unchanged.
