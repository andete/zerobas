# D-NOTOPEN2 — `GET` / `PUT` / `FIELD` / `INPUT$(n,#f)` on a channel that is NOT OPEN must raise ERR 59

Status: **SIGNED OFF 2026-07-31 — implementing**
Filed: TODO.md ~2872, 2026-07-31, by D-NOTOPEN's denominator sweep.
Predecessor: [`docs/spec-basic-chan-notopen-err59.md`](spec-basic-chan-notopen-err59.md)
§2 row 4–7, §7.1 (the four sites it deliberately left).
Memory: `notopen-chan-err59-slice`, `appmiss-slice`,
`apparatus-is-part-of-the-measurement`, `gate-can-be-green-while-measuring-nothing`.

---

## 1. The defect (carried forward from the filed item, not re-derived)

Typed with channel 1 **never opened**, both machines, 0 mangled rows:

| typed | CF-3300 | zerobas |
|---|---|---|
| `GET #1,1` | **ERR 59** `File not OPEN` | `Syntax error` |
| `PUT #1,1` | **ERR 59** | `Syntax error` |
| `FIELD #1,10 AS A$` | **ERR 59** | `Syntax error` |
| `A$=INPUT$(3,#1)` | **ERR 59** | `Syntax error` |
| `CLOSE #1` | *(no error)* | *(no error)* ✅ already agrees |

⚠️ **NOT a missing error code and NOT a trappability defect.** ERR 59 exists and is
trappable (`lof_closed` / `trap_lof_closed` are 59/59 today), and — unlike
D-NOTOPEN's `load_error` — zerobas's wrong answer here *does* trap. §2b measures
that: the reference traps **59**, zerobas traps **2**. This is a wrong error CODE
at four sites, not a wrong control-flow class.

## 2. The NEIGHBOUR, MEASURED before designing — the whole point of this section

D-NOTOPEN left these four sites precisely because **`GET`/`PUT`'s site tests
`cp 4` and sends BOTH "not open" (mode 0) AND "open but not RANDOM" to the same
`gp_err`**, and what the reference answers for the second condition was **not
measured**. Splitting a check whose other arm is unmeasured is the trap this
project keeps hitting, so the neighbour was swept first.

Battery: the `diskbasic_probe_lof.py` apparatus wholesale (echo guard, /tmp disk
copy, `scrmod`-measured geometry), CASES swapped. 19 cases × 2 machines,
**0 mangled**, `ctl_syntax` SYNTAX on both.

**PRIMARY INSTRUMENT = the TRAPPED CODE.** `10 ON ERROR GOTO 100 … 100 PRINT ERR`
reads a NUMBER, so the class is named without any error-message table, and the
three outcomes stay distinct: a **number** = raised and trapped with that code, an
error **CLASS** = raised but *not* trapped, **`0`** = nothing raised at all
(⚠️ `appmiss-slice`: a sentinel that also means "no reading" is not a measurement).

### 2a. The COMPLETE grid — verb × every `FCH_MODES` value. MEASURED 2026-07-31

Two batteries. Battery 1 covered modes 0/1/2/4 (19 cases). ⚠️ Battery 2 was added
because modes **3 (APPEND), 5 (LPT) and 6 (CRT)** were still unmeasured, and a
slice that SWEEPS this column has to answer for every mode, not the three it
happened to sample (11 cases). Both: 0 mangled, `ctl_syntax` green on both sides.
Cell = trapped `ERR` code; **`0` = nothing was raised at all**.

| `FCH_MODES` | channel | `GET #1,1` | `PUT #1,1` | `FIELD #1,10 AS A$` | `A$=INPUT$(3,#1)` |
|---|---|---|---|---|---|
| **0** | **not open** | **59** / 2 | **59** / 2 | **59** / 2 | **59** / 2 |
| 1 | FOR INPUT | **61** / 2 | **61** / 2 | **61** / **0** 🔴 | ✅ 0 / 0 |
| 2 | FOR OUTPUT | **61** / 2 | **61** / 2 | **61** / **0** 🔴 | **55** / 2 |
| 3 | FOR APPEND | **61** / 2 | **61** / 2 | **61** / **0** 🔴 | **55** / 2 |
| 4 | RANDOM | ✅ 0 / 0 | ✅ (`rand_put`) | ✅ 0 / 0 | **61** / 2 |
| 5 | `LPT:` | **58** / 2 | **58** / 2 | **5** / **0** 🔴 | **55** / 2 |
| 6 | `CRT:` | — | — | **5** / **0** 🔴 | **55** / 2 |

*(cells are `reference / zerobas`; ✅ = both agree, the row works)*

**The reference's rules, read straight off the grid:**

* `GET`/`PUT`: mode 0 → **59**; a **disk** channel that is not RANDOM → **61**;
  a **device** channel → **58** `Sequential I/O only`.
* `FIELD`: mode 0 → **59**; a **disk** channel that is not RANDOM → **61**;
  a **device** channel → **5** `Illegal function call`.
* `INPUT$`: mode 0 → **59**; mode 1 works; **RANDOM → 61**; **every other open
  mode → 55** `Input past end`.

🔴 **That is FIVE distinct reference codes — 5, 55, 58, 59, 61 — not two.**
zerobas has exactly two of them (5 in `err_msgtab`, 59 in `rerr_sparse`).

Untrapped (message-text) readings, so the reference's wording is on record rather
than inferred from a code: `GET` on an INPUT channel → **`Bad file mode`** (61);
`INPUT$` on an OUTPUT channel → **`Input past end`** (55); `PUT` and `INPUT$` on a
not-open channel → **`File not OPEN`** (59).

⚠️ **APPARATUS, recorded because it read as a result.** Battery 2's first run
came back with the zb column **entirely `None`** — no capture on any row. Cause:
`rm -rf build && make basic-reloc` (the house rule for a clean wall measurement)
rebuilds neither `build/disk.rom` nor `build/zerobas-main-eu.rom`, and the
installed machine XML names both by absolute path, so the machine was dangling.
Caught only by `ctl_syntax`. **Order matters: clean wall measurement, THEN
`make repack-machine`, THEN any probe.**

### 2b. What the neighbour measurement CHANGED about the design

1. 🔴 **The wrong-mode answer is ERR 61 `Bad file mode`, a code zerobas does not
   have at all.** `err_msgtab` is dense 1..25 and `rerr_sparse` knows exactly two
   codes past it (52, 59). Adding 61 costs a message string plus a third
   `rerr_sparse` arm. Costed at §2c, initially declined as unaffordable, and taken
   after §2d found the funding. Splitting `cp 4` into "not open → 59" and "not
   RANDOM → 61" is now IN scope — and `fch_mode_class` already returns CF =
   disk-vs-device, so the 61-vs-58 half of the split needs no new test at all.
2. 🔴 **`INPUT$`'s wrong-mode rule is not one rule.** RANDOM → **61**, but
   sequential-OUTPUT → **55 `Input past end`**. A design that swept "wrong mode →
   61" for `INPUT$` would have been wrong on row 12 — and row 12 is the only row
   that separates the two rules. This is exactly the
   `err21-no-resume-slice` shape (a characterization taken where two candidate
   rules coincide), caught here because the grid was swept rather than sampled.
3. 🔴 **`FIELD` on an open-but-not-RANDOM channel is SILENTLY ACCEPTED by
   zerobas** (rows 7 and 11 read `0` — *nothing raised*) where the reference
   raises 61. Nobody was looking for this; it is a silent-acceptance divergence,
   arguably worse than a wrong code, and it is the loudest thing the neighbour
   sweep found. FIXED here (§3.1) and gated by `wm_in_field` — it is also the one
   change in this slice that turns a working program into an erroring one, so it
   is called out separately at §4.3.
4. ✅ **Rows 8 and 13 agree at `0` on both machines**, so `INPUT$` on a correct
   INPUT channel and `GET` on a correct RANDOM channel both work today. They
   become permanent green controls (§5c) — without them, a fix that raised 59 (or
   61) for *everything* would pass every red-to-green row in §5a and §5d.

### 2c. COSTING THE FULL SWEEP — it does not fit, by ~33 B

Sign-off chose "also sweep wrong-mode → 61/55 now". Costed against the source
after battery 2 widened the answer from two codes to five:

**Infrastructure — three codes zerobas does not have (55, 58, 61).** ERR 5 already
exists (`err_msgtab[5]`), ERR 59 already exists (`rerr_sparse`).

| item | cost | where |
|---|---|---|
| `db "input past end",0` (55) — no phrase escape applies | 15 B | either |
| `db "sequential i/o only",0` (58) — no escape applies | 20 B | either |
| `db "bad ",MSGESC_FILE,"mode",0` (61) | 10 B | either |
| three `rerr_sparse` arms (`ld hl,msg`/`cp n`/`jr z,rsp_go`) | 21 B | **low region** |
| | **66 B** | |

*(A table-driven `rerr_sparse` was costed as the alternative: 5 entries × 3 B +
a 26 B search loop = 42 B, against 23 B existing + 21 B new = 44 B. It saves 2 B
and is not worth the rewrite.)*

**Per-site code**, net of the −13 B the `fch_mode_class` reuse gives back —
`fch_mode_class` already returns CF = disk-vs-device, which is exactly the
61-vs-58/5 split, so no new classifier is needed:

| site | net |
|---|---|
| `GET`/`PUT` (`jr nc` → 58, `cp 4`/`jr nz` → 61) | +3 B |
| `FIELD` (new `cp 4` arm; `jr nc` → 5) | +6 B |
| `INPUT$` (`cp 1` → ok, `cp 4` → 61, else 55) | +11 B |
| | **+20 B** |

**TOTAL ≈ 86 B.** Available at `f3e63c2`: low **23 B** + page 1 **30 B** = **53 B**.
🔴 **Short by ≈ 33 B.** The three message strings alone (45 B) are ~85 % of the
whole budget, and 21 B of the infrastructure is forced into the **low region** —
the harder of the two walls, with 23 B free.

Memory `rom-region-structure-review` costed the relief tiers and they are all
larger than one slice: the next carve is promoting `input.asm` (446 B), itself
blocked on room; de-eviction is REFUTED and closed. So the full sweep needs a
carve session BEFORE it, not alongside it.

**What DOES fit, measured the same way:**

| option | net | fits in 53 B? | wrong-mode cells reaching the reference's code |
|---|---|---|---|
| **A** — not-open column only (the filed item) | **−13 B** | yes, +66 B slack | 0 of 17 |
| **B** — not-open + ERR **61** only | **≈ +16 B** | yes, ~37 B slack | 10 of 17 (all the disk-mode cells) |
| **C** — the full grid (61 + 58 + 55) | **≈ +86 B** | **no, −33 B** | 17 of 17 |

**Sign-off took C: the full grid, funded by a carve first.** §2d is that carve.

### 2d. THE FUNDING CARVE — 63 B, all page 1, all in the same engine

⚠️ Not a sub-ROM eviction. `sub.rom` has room (page 0 **4078 B**, page 1 3339 B
of trailing `$FF`, measured — capacity was never the constraint), but an eviction
costs a resident stub and three tenant gates. Both carves below are pure
de-duplication inside `basic/files.asm`, found the same way this whole slice was:
**a fragment hand-inlined at N sites.** The second was found by the project's own
`tools/clone_scout.py`, not by eye.

**(a) `fch_modes_ptr` — the `&FCH_MODES[ch]` index, hand-inlined 10 times.**
`ld e,a / ld d,0 / ld hl,FCH_MODES / add hl,de` (7 B; also spelled with `BC`, and
once with `E` preset for 6 B) appears at `oo_storemode`, `oo_fail`, `oodv_ok`,
`oocas` (files.asm), the `CLOSE` arm, `fch_sync_mirror`, `fch_do_close_ch`,
`fdcc_clear`, `fch_close_all`, and inside `fch_mode_class` itself (expr.asm).

```
fch_modes_ptr:                      ; A = channel -> HL = &FCH_MODES[A]
                add     a,FCH_MODES & $FF   ; page-local: the array is well within
                ld      l,a                 ; one page of its base (the same
                ld      a,FCH_MODES >> 8    ; assumption fch_mode_class already
                adc     a,0                 ; makes)
                ld      h,a
                ret
```

9 B — the 8-bit page-local form, which clobbers **only A and HL** and so preserves
`BC` *and* `DE`. It costs 1 byte more than the obvious `ld e,a / ld d,0 /
ld hl,FCH_MODES / add hl,de`.

🔴 **I JUSTIFIED THAT BYTE WITH A CLAIM THE FALSIFICATION REFUTED (K0′, §9).** The
claim was that the DE-clobbering form *breaks* the two callers that read `E` after
the index (`fch_do_close_ch`'s `fdcc_disk`, and the `CLOSE` arm), citing
`refactor-inherits-clobber-contracts`. Built and gated, the naive form is
**GREEN** — `diskbasic-acceptance` 34/34 and the full 41-case lof battery — and one
byte smaller. Why: every call site passes the channel in **A**, so the naive
helper's own `ld e,a` puts the same channel straight back into `E`. The hazard I
designed against cannot arise *given how I wrote the call sites*.
⚠️ **A plausible clobber-contract argument, in a codebase that has genuinely been
bitten by clobber contracts, is still just an argument.** It reads as diligence and
it was not measured until the knife measured it.
The form is **kept**, on the smaller and now-honest reason: with the naive helper
those two callers are correct only *by luck* — they depend on `A == E` holding at
every present and future call site, which nothing enforces (`cont-depth-slice`: one
exit was clean by luck and the next slice paid for it). One byte for a contract
that does not rest on a coincidence.
Sites: 3 × −3 B, 2 × −2 B, 3 × −4 B, 1 × −3 B, `fch_mode_class` −5 B, helper +9 B
= **−23 B**.

**(b) `oo_parse_as_chan` — the `AS #n` clause, duplicated VERBATIM.**
`oo_setmode` (files.asm:251, the disk `OPEN`) and `oocas_setmode` (files.asm:539,
the cassette `OPEN`) contain a byte-identical 47-byte run: `skip_spaces`, match
`A`, match `S`, optional `#`, `eval`, `ld a,d / or a / jp nz,oo_fail_bfn`,
`ld a,e / call fch_valid / jp nc,oo_fail_bfn`. Same raisers, same registers, same
exit contract (HL past the clause, DE = channel). Factored into one routine
(48 B) called from both (3 B each): 2 × 47 − 48 − 6 = **−40 B**.
The two mode stores that differ (`ld (FCH_MODE),a` vs `ld (OO_DEVTYPE),a`) stay at
the call sites.

**Carve total: −63 B, all page 1.** Running budget:

| | low | page 1 | total |
|---|---|---|---|
| baseline `f3e63c2` | 23 | 30 | 53 |
| after the carve (−63) | 23 | 93 | 116 |
| after the not-open column (−13) | 23 | 106 | 129 |
| wrong-mode sweep (infra 63–66 + sites +33) | | | **≈ −99** |
| **predicted final** | | | **≈ 30 B** |

⚠️ Every number in this table is **arithmetic, not a measurement**
(`linemax-slice`: a size from arithmetic is not a measurement). The clean
`rm -rf build && make basic-reloc` after each stage is what settles it, and the
stages are ordered so the carve lands — and is gated — **before** anything spends
it.

## 3. The change — the SAME reuse D-NOTOPEN made, at the three remaining sites

🔴 **All three sites are further hand-inlined copies of `fch_mode_class`**
([`basic/expr.asm:1118`](../basic/expr.asm:1118)). D-NOTOPEN found two copies that
had dropped the `or a`; these three kept the test but raise the wrong code (or, in
`FIELD`'s case, index the array by hand and then raise ERR 2). The fix is again
**delete the copy, call the original** — no new routine, no new code path, no new
message, and the raiser (`err_notopen_raise`) is the one `LOF` already reaches.

### 3.1 `FIELD` — [`basic/field.asm:270`](../basic/field.asm:270) (`ex_field`)

```
                ld      (FLD_CHAN),a
                ; the channel must be open (FCH_MODES[ch] != 0).
                push    hl                  ; guard cursor across the array read
-               ld      d,0
-               ld      e,a
-               ld      hl,FCH_MODES
-               add     hl,de
-               ld      a,(hl)
-               pop     hl
-               or      a
-               jp      z,stmt_error        ; channel not open
+               call    fch_mode_class      ; ERR 59 if FCH_MODES[E] is 0
+               pop     hl
```

`E` is still the channel here (`fch_valid` clobbers only A and B —
[`files.asm:1096`](../basic/files.asm:1096)), so the local `ld e,a` goes with the
rest. ⚠️ The filed item predicted a **0-byte** change for `FIELD`; the not-open
half alone is −9, because the item costed the `jp` swap and not the inlined array
read sitting above it.

Then the wrong-mode arms, which `FIELD` has **none** of today — this is the
silent acceptance (§2b.3). `fch_mode_class` returns **CF = disk-vs-device**, which
is exactly the 61-vs-5 split, so no new classifier is needed:

```
+               jr      nc,exf_dev          ; device channel -> ERR 5
+               cp      4                   ; a disk channel must be RANDOM
+               jr      nz,exf_bfm          ; INPUT/OUTPUT/APPEND -> ERR 61
                ; re-FIELD replaces: drop prior fields on this channel, offset = 0.
…
+exf_dev:       ld      a,5                 ; illegal function call (already in
+               jr      exf_raise           ; err_msgtab -- no new message)
+exf_bfm:       ld      a,61                ; bad file mode
+exf_raise:     jp      raise_error         ; SP is reset on both arms -- no `pop hl`
```

**14 B → 5 B for the not-open half, +15 B for the two wrong-mode arms = +6 B.**

### 3.2 `GET` / `PUT` — [`basic/field.asm:517`](../basic/field.asm:517) (`gp_common`)

```
                push    hl                  ; guard cursor across select + disk op
                ; the channel must be open RANDOM (FCH_MODES[ch] == 4).
                ld      a,(GP_CHAN)
                ld      e,a
-               ld      d,0
-               ld      hl,FCH_MODES
-               add     hl,de
-               ld      a,(hl)
+               call    fch_mode_class      ; ERR 59 if not open at all; CF = disk
+               jr      nc,gp_dev           ; device channel -> ERR 58
                cp      4
-               jr      nz,gp_err
+               jr      nz,gp_bfm           ; disk but not RANDOM -> ERR 61
…
-gp_err:        pop     hl
-               jp      stmt_error
+gp_dev:        ld      a,58                ; sequential i/o only
+               jr      gp_raise
+gp_bfm:        ld      a,61                ; bad file mode
+gp_raise:      jp      raise_error
```

**16 B → 12 B for the not-open half, +7 B for the two wrong-mode arms = +3 B.**
`gp_err` disappears; the disk-error `jp c,load_error` at `gp_fin` keeps its own
`pop hl` and is untouched.

### 3.3 `INPUT$` — [`basic/strvar.asm:220`](../basic/strvar.asm:220) (`str_inputd`)

⚠️ The filed item warned that `INPUT$` "fails via `str_eval_no`, i.e. the error is
raised by the CALLER". Measured: that caller's answer is ERR **2**, and the fix
does not go through it at all — the mode test simply moves **before** `fch_select`
and reads the array directly:

```
                push    hl                  ; guard the eval cursor
-               ld      a,e
-               call    fch_select          ; make channel f live; FCH_MODE = its mode
-               ld      a,(FCH_MODE)
-               cp      1                   ; must be open FOR INPUT
-               jr      nz,str_inputd_err
+               call    fch_mode_class      ; A = FCH_MODES[E]; ERR 59 if not open
+               cp      1                   ; open FOR INPUT -> proceed
+               jr      z,sid_ok
+               cp      4                   ; RANDOM -> ERR 61, everything else -> 55
+               ld      a,55                ; (input past end -- measured for modes
+               jr      nz,sid_raise        ;  2, 3, 5 and 6 alike)
+               ld      a,61                ; bad file mode
+sid_raise:     jp      raise_error
+sid_ok:        ld      a,e
+               call    fch_select          ; make channel f live
                call    str_inputd_read
```

`str_inputd_err` disappears with its `jp str_eval_no` — measured, that path's
answer was ERR 2, and no open mode reaches it any more.
**12 B → 12 B for the not-open half, +11 B for the wrong-mode arms = +11 B**, and
it fixes a second thing for free: today `INPUT$`
calls `fch_select` on the channel **before** checking its mode, so a not-open (or
device/cassette) slot gets selected — the exact hazard `fch_mode_class`'s own
header warns about ("never `fch_select` them"). After the change no wrong-mode or
not-open channel is ever selected.

Raising with the `INPUT$` operand half-parsed is safe: by this point
`INPUT` `$` `(` *expr* `,` `#` *expr* `)` has all been consumed, so the operand is
unambiguously `INPUT$` and there is no alternative parse for `str_eval_no` to fall
back to.

### 3.4 Contract checks — verified against the source, not assumed

* **`fch_mode_class` preserves `E` and `IX`, clobbers `A`/`HL`.** `HL` is inside a
  `push`/`pop` at all three sites; `A` is the value each site wants. ✅
* **`D` is no longer zeroed** at the two `field.asm` sites. The helper indexes off
  `E` alone (8-bit add + `adc` into H). Neither site reads `D` afterwards
  (`FIELD` → `ld a,(FLD_CHAN)`; `GET`/`PUT` → `ld a,(GP_CHAN)` then
  `ld de,…`/`fch_select`). ✅
* **Raising with `HL` pushed is safe** — `raise_error` resets `SP` on BOTH arms
  (`ld sp,(SAVSTK)` on the trap arm, `fre_abort_low`'s own first act on the abort
  arm). Same depth-independence `LOF` and D-NOTOPEN already rely on. ✅
* **Dropping `stmt_error`'s two side effects is safe.** `stmt_error` does
  `xor a / ld (PRDEST),a` and `ld a,$DD / ld (ERRMARK),a`; `err_notopen_raise`
  does neither. `exec_stmt` ([`interp.asm:160`](../basic/interp.asm:160)) zeroes
  `PRDEST` at the head of **every** statement, so it is already 0 on these paths —
  the clear is redundant here (it exists for errors raised *inside* `PRINT#`'s item
  loop). `ERRMARK`'s only reader is [`missing.asm:537`](../basic/missing.asm:537),
  which **clears it itself** at line 517 before the call it inspects, so an unset
  landmark from these paths is inert. ✅
* **Order is unchanged**: `fch_valid` still rejects 0 / >MAXF *before* the mode
  test at all three sites, so the ERR 52 item (§7.2) does not move. ✅
* **Mode 0 is unambiguously "not open"** — `FCH_MODES` is 1 INPUT, 2 OUTPUT,
  3 APPEND, 4 RANDOM, 5 LPT, 6 CRT, 7 CAS-out, 8 CAS-in. ✅

### 3.4b The three new error codes — 55, 58, 61

ERR **5** needs nothing (`err_msgtab[5]` already). ERR **59** needs nothing
(`rerr_sparse` already). The other three are new to zerobas:

```
                db      "input past end",0              ; 55 -- 15 B, no escape fits
                db      "sequential i/o only",0         ; 58 -- 20 B, no escape fits
                db      "bad ",MSGESC_FILE,"mode",0     ; 61 -- 10 B (MSGESC_FILE)
```

and three arms in `rerr_sparse` ([`main.asm:347`](../basic/main.asm:347)), which is
already the "sparse disk-range codes past the dense `err_msgtab`" path and already
routes through `raise_error_hl`, so **trappability comes for free and the untrapped
wording comes from the same table as 52 and 59**. 7 B per arm, 21 B.

⚠️ A table-driven `rerr_sparse` was costed as the alternative (5 entries × 3 B + a
25 B search loop = 41 B, against 23 B existing + 21 B new = 44 B). It saves 3 B and
is **declined**: 3 B does not buy rewriting the one routine every disk-range error
in the ROM passes through, and the linear chain reads as the codes it names (its
own comment makes that argument for the 52/59 pair already).

### 3.5 Byte cost and the walls

| stage | hunk | delta |
|---|---|---|
| **carve** | `fch_modes_ptr` (§2d a) | **−23 B** |
| **carve** | `oo_parse_as_chan` (§2d b) | **−40 B** |
| sweep | `FIELD` (`field.asm`): −9 not-open, +15 wrong-mode | **+6 B** |
| sweep | `GET`/`PUT` (`field.asm`): −4 not-open, +7 wrong-mode | **+3 B** |
| sweep | `INPUT$` (`strvar.asm`): 0 not-open, +11 wrong-mode | **+11 B** |
| sweep | three messages (45 B) + three `rerr_sparse` arms (21 B) | **+66 B** |
| | | **≈ −23 B net** |

`field.asm`, `strvar.asm`, `files.asm` and `expr.asm` are all page-1
(`main.asm:158`, `main.asm:261`); the messages and the `rerr_sparse` arms are
**low region** (beside `err_bad_filenum`/`err_file_notopen`), and the low region has
23 B — so **66 B of the new material must be placed deliberately**: the three
strings go to the page-1 tail (a string is position-independent within the slot, and
`ld hl,msg` costs the same from anywhere), the 21 B of arms stay low. That is the
`promotion-funds-low-region` move in reverse and it is the reason the carve targets
page 1.

Clean baseline MEASURED at `f3e63c2` (`rm -rf build && make basic-reloc`):
low **23 B**, page 1 **30 B**, `__MEAS_PAGE1_END` @ **$7FE2**, dead-code 0/0 both builds.

**Predicted final: low ≈ 2 B, page 1 ≈ 74 B.** ⚠️ Arithmetic, not a measurement.
The build order is carve → measure → not-open → measure → wrong-mode → measure, so
a wrong number is caught at the stage that caused it rather than at the end.

## 4. Behaviour that CHANGES, stated plainly

1. `GET #n`, `PUT #n`, `FIELD #n`, `INPUT$(k,#n)` on a **not-open but in-ceiling**
   channel print **`file not open`** instead of `syntax error`, and set `ERR = 59`
   instead of `ERR = 2` in an armed handler.
2. **`GET`/`PUT` on an open channel that is not RANDOM** → `bad file mode` (61) for
   a disk channel, `sequential i/o only` (58) for `LPT:`/`CRT:`. Was ERR 2 for both.
3. **`FIELD` on an open channel that is not RANDOM** → 61 for a disk channel, 5 for
   a device channel. 🔴 **Was accepted SILENTLY** — this is the one change that
   turns a non-error into an error, so it is the one most able to break a working
   program. §6 checks every probe for a `FIELD` on a sequential channel; there are
   none, and `rand_put` is the control that proves the RANDOM path still works.
4. **`INPUT$` on an open channel that is not INPUT** → 61 for RANDOM, 55 for every
   other open mode. Was ERR 2.
5. **Trappability does NOT change** at any of these sites — `stmt_error` already
   routed through `raise_error`, and `rerr_sparse` routes through `raise_error_hl`.
   Only the codes move. Still GATED (§5b), not assumed.
6. `INPUT$` no longer calls `fch_select` on a channel it is about to reject.
7. Three new error messages exist, so `ERROR 55` / `ERROR 58` / `ERROR 61` typed
   directly now print real text instead of `unprintable error`.

## 5. The gate — [`probes/disk/diskbasic_probe_lof.py`](../probes/disk/diskbasic_probe_lof.py), **26 → 41 cases**

⚠️ Cost: 41 cases × 2 machines = 82 emulator boots; `make lof-acceptance` gets
~58 % longer. §5d explains why it is 7 wrong-mode rows and not 17.

**(a) The two filed entries are DELETED, not updated** (memory `deadcode-gate`).
`KNOWN_DIVERGE["closed_get"]` and `KNOWN_DIVERGE["closed_field"]` go away
entirely; both rows must read `FNO` on both machines. Two more rows join them —
the item names four verbs and only two had any row at all, which is the exact
mistake D-NOTOPEN had to correct for `INPUT#`/`LINE INPUT#`:

| case | typed | expect |
|---|---|---|
| `closed_get` (exists) | `GET #1,1` | `FNO` both |
| `closed_field` (exists) | `FIELD #1,10 AS A$` | `FNO` both |
| `closed_put` **NEW** | `PUT #1,1` | `FNO` both |
| `closed_inpd` **NEW** | `A$=INPUT$(3,#1)` | `FNO` both |

**(b) TRAPPABILITY rows — the code, not the message.** Handler prints `ERR`;
`0` = nothing raised, an error CLASS = raised but not trapped.

| case | subject | expect |
|---|---|---|
| `trap_get_closed` **NEW** | `GET #1,1` under `ON ERROR GOTO` | `59` both |
| `trap_put_closed` **NEW** | `PUT #1,1` | `59` both |
| `trap_field_closed` **NEW** | `FIELD #1,10 AS A$` | `59` both |
| `trap_inpd_closed` **NEW** | `A$=INPUT$(3,#1)` | `59` both |
| `trap_lof_closed` (exists) | `A=LOF(1)` — **CONTROL, green today** | `59` both |

**(c) GREEN CONTROLS that must NOT move — the rows that stop "raise 59 for
everything" from passing.** §2a rows 8 and 13, measured `0`/`0` today:

| case | subject | expect |
|---|---|---|
| `ok_in_inpd` **NEW** | `OPEN "HI.TXT" FOR INPUT AS #1` : `A$=INPUT$(3,#1)` | `0` both |
| `ok_rnd_get` **NEW** | `OPEN "HI.TXT" AS #1` : `FIELD…:GET #1,1` | `0` both |

`ok_in_inpd` is load-bearing for §3.3 specifically: it is the only row that would
notice `INPUT$` breaking when its mode test moved ahead of `fch_select`. The
existing `rand_put` (LOF 256) is the corresponding control for `FIELD` + `PUT` on a
real RANDOM channel.

**(d) The WRONG-MODE column — now FIXED rows, not allowlisted ones.** Sign-off took
the full grid, so every one of these must AGREE after the slice. Seven rows, chosen
to cover **each distinct rule once and each rule's boundary once** rather than all
17 cells (17 cells × 2 machines would add 34 boots for 10 cells that re-measure a
rule already covered):

| case | subject | expect | which rule it pins |
|---|---|---|---|
| `wm_in_get` **NEW** | INPUT channel, `GET #1,1` | `61` both | GET/PUT, disk non-RANDOM |
| `wm_app_put` **NEW** | APPEND channel, `PUT #1,1` | `61` both | …and the mode-3 end of it, on the other verb |
| `wm_lpt_get` **NEW** | `LPT:` channel, `GET #1,1` | `58` both | GET/PUT, device — the CF arm |
| `wm_in_field` **NEW** | INPUT channel, `FIELD #1,10 AS A$` | `61` both | 🔴 the silent acceptance |
| `wm_lpt_fld` **NEW** | `LPT:` channel, `FIELD #1,10 AS A$` | `5` both | FIELD, device → a DIFFERENT code from GET's 58 |
| `wm_rnd_inpd` **NEW** | RANDOM channel, `A$=INPUT$(3,#1)` | `61` both | INPUT$, the RANDOM exception |
| `wm_out_inpd` **NEW** | OUTPUT channel, `A$=INPUT$(3,#1)` | `55` both | INPUT$, everything else — **the row that separates the two INPUT$ rules** |

`wm_lpt_fld` and `wm_lpt_get` are the pair that stops "device → one code" from
passing: the reference answers **5** for `FIELD` and **58** for `GET` on the *same*
`LPT:` channel, so a fix that collapsed them would go red on exactly one of the two.

**(e) `KNOWN_DIVERGE` after this slice holds exactly ONE entry**, `closed_ch2`
(`("BFN","LOADERR")`, the §7.2 ERR 52 item). It is still a control that must keep
matching, not an empty box. Both entries this item put there are **DELETED, not
updated**.

`REF_EXPECT` entries are the values measured in §2a, recorded as oracle locks
before anything is scored (memory `vacuous-gate-row-steers-not-just-misses`).
`ERR_CLASSES` gains `BFM` (`bad file mode`), `IPE` (`input past end`) and `SIO`
(`sequential i/o only`) so neither machine's message can classify as `None`.

**Total: 26 → 41 cases** (4 + 4 + 2 + 7 new), 82 emulator boots.

## 6. Two-sided controls that must NOT move

* `lof_closed`, `trap_lof_closed` (59/59) — the proof ERR 59 works at all.
* `closed_input`, `closed_lineinp`, `ctl_prwr_closed`, `trap_print_closed`,
  `trap_input_closed` — D-NOTOPEN's rows, 59/`FNO` on both.
* `append_exist` 26/26, `roundtrip` 8/8, `lof_input` 26, `lof_bin` 2048,
  `rand_put` (LOF 256, dir 0/256 filed), `ctl_syntax` SYNTAX.
* `closed_ch2` must KEEP diverging `BFN`/`LOADERR` — the separate ERR 52 item.
* `fat-error-acceptance` 8/8 + the directory check: all eight are MISSING-FILE
  cases; none types a `GET`/`PUT`/`FIELD`/`INPUT$`, so none can reach the changed
  code.
* `chancost-characterize` 39 / **allowlist EMPTY** — none of its 39 rows types
  `GET`/`PUT`/`FIELD`/`INPUT$` on a closed channel.
* The `diskbasic_probe_lof.py` echo guard is **not touched**; `MANGLED` stays fatal
  with or without `--gate`.

## 7. Deliberately NOT in this slice — each with its measurement

**7.1 ✅ TAKEN — the wrong-mode column is IN this slice** (sign-off, §2c). It is
recorded here rather than deleted because the reasoning that nearly left it out is
the point: it was costed at ~86 B against 53 B free and declined, then the funding
carve (§2d) was found in the same engine and it became affordable. ⚠️ **"It does
not fit" is a statement about today's budget, not about the change** — the honest
next question is what would fund it, and `clone_scout` answered that in one run.

**7.1b NOT taken: the CAS: channel modes (7, 8).** `FCH_MODES` also has
`CAS_OUT_MODE`/`CAS_IN_MODE`, and the grid does **not** cover them — no row was
typed against a cassette channel. §3's dispositions send them down the *device*
arm (CF clear, since 7 and 8 are >= `LPT_MODE`), i.e. `GET`/`PUT` → 58, `FIELD` → 5,
`INPUT$` → 55, by analogy with LPT/CRT. 🔴 **That is an INFERENCE, not a
measurement**, and it is exactly the shape this spec spent §2 avoiding. It is
called out rather than quietly shipped: filed as its own TODO item, to be measured
against a real cassette channel (the probe harness mounts disks, not tapes, so it
needs `disk_probe`-side work the lof battery cannot do today).

**7.2 `fch_valid`'s rejects are the wrong class (ERR 52).** Unchanged and untouched
by this slice: `fch_valid` still rejects before the mode test at all three sites.
⚠️ Worth recording for that item: `FIELD`/`GET`/`PUT` route their bad-file-number
reject to `stmt_error` (ERR 2) where `PRINT#`/`INPUT#` route theirs to
`load_error` — two wrong dispositions for one class, so the ERR 52 item's
denominator is larger than the three rows D-NOTOPEN §2b measured. Not measured
here (out of scope); flagged, not claimed.

## 8. Gates to RUN (not assume)

`make repack-machine`, then clean `rm -rf build && make basic-reloc` (HARD
dead-code gate, **0 dead in BOTH builds**), then:

`make unit-test` 55/55 · `make lof-acceptance` **41 cases / 1 filed
(`closed_ch2` alone) and `KNOWN_DIVERGE` holding exactly that one** · `make chancost-characterize` 39 /
**allowlist EMPTY** · `make diskbasic-acceptance` 34/34 · `make bdos-acceptance`
12/12 · `make fat-error-acceptance` 8/8 + dir check · `make error-trap-acceptance` ·
`make abort-acceptance` 49/49 · `make stop-trap-acceptance` ·
`make linemax-acceptance` 60/60 · `make arrdim-acceptance` 73/73 ·
`make clearpool-acceptance` 52/52 · `make array-acceptance` 149/151 (the two
standing rows confirmed **BY NAME**: `ifc.instr.zero`, `ifc.instr.neg`).

`error-trap-acceptance` and `abort-acceptance` are load-bearing: §4.1 changes which
code an armed handler sees, and `stmt_error` is the raiser being bypassed at three
sites.

### RESULT — every gate RUN 2026-07-31, none assumed

| gate | result |
|---|---|
| clean `rm -rf build && make basic-reloc` | ✅ low **23 B unchanged**, page 1 **30 → 49 B** (net **+19 B** over the f3e63c2 baseline); dead-code **0 dead in BOTH builds** |
| `make lof-acceptance` | ✅ **41 cases, 0 unfiled, 0 oracle drift, 0 mangled**; `KNOWN_DIVERGE` = `closed_ch2` alone |
| `make unit-test` | ✅ 55/55 |
| `make chancost-characterize` | ✅ 39 cases, **0 filed — allowlist still EMPTY** |
| `make diskbasic-acceptance` | ✅ 34/34 (incl. `CLOSE(list)`, `OPEN(LPT/CRT)` — the carve's two riskiest paths) |
| `make bdos-acceptance` | ✅ 12/12 |
| `make fat-error-acceptance` | ✅ **8/8 + directory check** |
| `make error-trap-acceptance` | ✅ ALL PASS |
| `make abort-acceptance` | ✅ 49/49 |
| `make stop-trap-acceptance` | ✅ ALL PASS |
| `make linemax-acceptance` | ✅ 60/60 |
| `make arrdim-acceptance` | ✅ 73/73 |
| `make clearpool-acceptance` | ✅ 52/52 |
| `make array-acceptance` | ✅ 149/151 — the two failures confirmed **BY NAME**: `ifc.instr.zero`, `ifc.instr.neg` (capitalisation-only, standing) |

Wall arithmetic vs measurement: the carve was predicted −107 B and measured
**−107 B**; the sweep was predicted +92 B and measured **+88 B**. The 4 B is not
chased — it is recorded, because §3.5 said the table was arithmetic and this is
what checking it looks like.

## 9. Falsification — FOUR knives (K0, K0′, K1, K2), staged with the build

⚠️ **A CUT WITNESS MUST BE DOWNSTREAM OF THE EDIT** (D-NOTOPEN §11 named `ex_print`
and `input_common`, both of which sit *before* the edited bytes and are invariant
either way — two of its three "cut verified" checks would have passed on a knife
that never applied). Witnesses here are chosen accordingly, and **no knife is
scored until its witness has been read**.

**K0 — the CARVE (§2d).** Revert `fch_modes_ptr` and `oo_parse_as_chan`.
This one is not expected to move ANY probe row: the carve is a pure
de-duplication, so **its whole predicted result is "nothing changes but the
addresses"**. That makes it the one knife whose green is meaningless and whose
witness is everything:

| witness | predicted under K0 |
|---|---|
| `__MEAS_PAGE1_END` | **+63 B back**, i.e. page-1 free returns to its pre-carve number |
| `fch_close_all`, `fch_do_close_ch` (downstream of the last `fch_modes_ptr` site) | shift |
| `md5(build/basic-reloc.bin)` | differs |
| every `lof-acceptance` row, `diskbasic-acceptance` 34/34, `bdos-acceptance` 12/12 | **unchanged** |

🔴 K0's real job is the opposite of a normal knife: if a probe row *does* move under
it, the carve changed behaviour and is wrong. `CLOSE` on a device channel and
`OPEN "CAS:…"` are the two paths most at risk (they are the `E`-preserving and the
`oo_parse_as_chan` sites), and `diskbasic-acceptance` + `bdos-acceptance` are what
cover them.

**K0 was NOT run as a revert, and that is a judgement, not an omission.** A revert
of a pure de-duplication predicts "no row moves" — the same result as success — so
it carries no information. Its cut is already witnessed by the wall: page-1 free
30 → 137 B, **exactly the −107 B predicted**, which is a downstream measurement that
could have disagreed and did not.

**K0′ — the knife that WAS worth running, aimed at my own reasoning.** Replace
`fch_modes_ptr` with the naive DE-clobbering form that §2d(a) claims breaks `CLOSE`
on a device channel, and see whether any gate notices.
🔴 **RESULT: NOTHING NOTICED.** `diskbasic-acceptance` 34/34 (including its
`CLOSE(list)` and `OPEN(LPT/CRT)` rows) and the 41-case lof battery both GREEN, at
8 bytes instead of 9. The justification was wrong; §2d(a) is corrected in place
rather than quietly reworded. ⚠️ **This is the knife that mattered most in the
slice, because it was the only one aimed at a claim rather than at code** — and it
is the only one that came back with an answer I did not predict.

**K1 — the NOT-OPEN column.** Revert the three `call fch_mode_class` hunks.

| witness | predicted under K1 |
|---|---|
| `fld_add` (`field.asm`) — downstream of 3.1, upstream of 3.2 | shifts |
| `gp_err`/`gp_raise` (`field.asm`) — downstream of both `field.asm` hunks | shifts |
| `__MEAS_PAGE1_END` | shifts |
| `str_inputd_read` (`strvar.asm`) — downstream of 3.3 | **unchanged** (3.3's not-open half is byte-neutral) |
| `md5(build/basic-reloc.bin)` | differs |

RED: `closed_get`, `closed_field`, `closed_put`, `closed_inpd` (`FNO` vs `SYNTAX`),
`trap_get_closed`, `trap_put_closed`, `trap_field_closed`, `trap_inpd_closed`
(`59` vs `2`).
GREEN, the paired controls without which those reds prove nothing:
`trap_lof_closed` 59/59, `lof_closed`, `ok_in_inpd` 0/0, `ok_rnd_get` 0/0,
`ctl_syntax`, `append_exist` 26/26, `roundtrip` 8/8, `rand_put`, `closed_ch2` still
diverging its filed way. **0 mangled.**

**K2 — the WRONG-MODE arms only.** Revert the three wrong-mode dispositions
(`gp_dev`/`gp_bfm`, `exf_dev`/`exf_bfm`, `sid_raise`) and the three `rerr_sparse`
arms, keeping the not-open column.

RED: all seven `wm_*` rows.
GREEN: all four `closed_*` rows and all four `trap_*_closed` rows — i.e. K2 is what
**attributes each row to the right half of the slice**. Without it, a single
all-or-nothing knife could not tell a not-open regression from a wrong-mode one,
and the two halves land in the same three routines.

⚠️ A green falsification is a claim about the PATCH first
(`err21-no-resume-slice`), and a RED row reads as success — which is why every
knife above names its GREEN control set, not just its reds.

## 10. Sign-off — answered 2026-07-31

**Q1. Scope — OVERRIDDEN to the FULL GRID.** I proposed the not-open column only
(option A) and then, after battery 2, option B; sign-off took **C — the full grid,
carve first**. Recorded because the override was right on the merits: the funding
existed (§2d) and my "does not fit" was a claim about today's budget that I had not
tried to move. ⚠️ It also cost a second measurement round — the grid I costed C
against was the 4-mode one, and modes 3/5/6 turned two codes into five.

**Q2. Gate size — ALL TWELVE, plus three.** 26 → **41** cases. The wrong-mode rows
became FIXED rows rather than allowlisted ones when scope went to C, and three more
were added (`wm_app_put`, `wm_lpt_get`, `wm_lpt_fld`) to cover the device arm and
the 58-vs-5 split that only a device row can separate.

**Q3. `FIELD`'s silent acceptance — ITS OWN ITEM, then absorbed.** It is fixed here
as part of C. The item it would have been is instead **7.1b** (the unmeasured
`CAS:` modes), which is the genuinely separate unknown.

**Q4. Knives — BOTH, and a third.** K0 (the carve), K1 (not-open), K2 (wrong-mode).
K0 is the one whose green means nothing, so its witness list is the whole test.

## 11. Build order — each stage measured before the next spends it

1. **Carve** (§2d) → clean `rm -rf build && make basic-reloc`, `make repack-machine`,
   `diskbasic-acceptance` + `bdos-acceptance` + `lof-acceptance` unchanged. **K0.**
2. **Not-open column** (§3.1–3.3 first halves) → measure → new `closed_*`/`trap_*`
   rows go green. **K1.**
3. **Wrong-mode arms + the three codes** (§3.1–3.4b) → measure → `wm_*` rows go
   green. **K2.**
4. Full gate set (§8), then commit.

⚠️ `make repack-machine` after EVERY ROM change and before EVERY probe — §2a's
apparatus note. And never rebuild while a differential is running.


## 12. Falsification RESULTS — all four knives RUN 2026-07-31

**K0 — not run as a revert** (reasoning in §9); its cut is witnessed by the wall
moving exactly the predicted −107 B.

**K0′ — the naive `fch_modes_ptr`.** 🔴 **REFUTED MY OWN JUSTIFICATION.**
`diskbasic-acceptance` 34/34 and the 41-case lof battery both GREEN at 8 bytes.
§2d(a) corrected in place.

**K1 — the ERR 59 raise deleted at the three sites.** Cut verified BEFORE scoring:
page-1 free **49 → 40 B**, `__MEAS_PAGE1_END` **$7FCF → $7FD8**.
* **RED, all eight:** `closed_get`, `closed_field`, `closed_put` (`BFM` vs `FNO`),
  `closed_inpd` (`IPE` vs `FNO`), `trap_get_closed`, `trap_put_closed`,
  `trap_field_closed` (**61** vs 59), `trap_inpd_closed` (**55** vs 59).
* **GREEN, every paired control:** `trap_lof_closed` 59/59, `lof_closed`,
  `closed_input`, `ctl_prwr_closed`, `ok_in_inpd` 0/0, `ok_rnd_get` 0/0,
  `ctl_syntax`, `append_exist` 26/26, `roundtrip` 8/8 — **and all seven `wm_*`
  rows still GREEN**, which is what makes the eight reds attributable to the
  not-open half specifically. **0 mangled.**

**K2 — the wrong-mode arms sent back to ERR 2.** ⚠️ **BYTE-NEUTRAL**
(`jp raise_error` → `jp stmt_error`, 3 B → 3 B), so page-1 free stayed at 49 B and
`__MEAS_PAGE1_END` did not move — **no symbol could witness this cut**, exactly the
case §9 was written for. Witness taken from the EMITTED BYTES instead: all three
sites read `C3 4A 42` = `jp $424A` = `stmt_error`, against `raise_error` at `$42C3`.
* **RED, all seven `wm_*` rows** (`2` vs 61/61/58/61/5/61/55).
* **GREEN, all eight not-open rows** and every control.

K1 and K2 partition the slice's fifteen new rows exactly — eight to the not-open
half, seven to the wrong-mode half, none to both and none to neither.
