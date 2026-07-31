# D-NOTOPEN — `PRINT#` / `INPUT#` / `LINE INPUT#` on a channel that is NOT OPEN must raise ERR 59

Status: ✅ **LANDED 2026-07-31**
Filed: TODO.md, 2026-07-31, by D-APPMISS's `append_new_wr` row (not aimed at).
Owner spec of the defect it was found under:
[`docs/spec-basic-append-missing-refuse.md`](spec-basic-append-missing-refuse.md) §5(a).
Memory: `appmiss-slice`, `apparatus-is-part-of-the-measurement`.

---

## 1. The defect (carried forward, not re-derived)

`PRINT #1,"X"` on a channel that was never opened:

* CF-3300 → **`File not OPEN`** (ERR 59)
* zerobas → **`load error`**

Gated today by [`probes/disk/diskbasic_probe_lof.py`](../probes/disk/diskbasic_probe_lof.py)
rows `append_new_wr` and `ctl_prwr_closed` (the attribution control: the same
`PRINT #` with **no `OPEN` typed at all**, which diverges identically), both
allowlisted in `KNOWN_DIVERGE` naming this item.

⚠️ **NOT a missing error code.** S-FCH-2 landed ERR 59 as an ordinary trappable
code raised and printed by the resident ROM, and `lof_closed` shows `LOF` on the
very same closed channel AGREEING with the reference at ERR 59. It is
`PRINT#`/`INPUT#`'s own disposition that derails.

## 2. The DENOMINATOR — MEASURED, all of it, before designing

Every channel-touching verb, typed with **channel 1 never opened**, both machines,
one line per case, `ctl_syntax` green and **0 mangled rows**
(scratch battery derived from `diskbasic_probe_lof.py`; the permanent rows §5 adds
are the subset that must not rot).

| # | typed | reference | zerobas | site | this slice |
|---|-------|-----------|---------|------|------------|
| 1 | `PRINT #1,"X"` | **ERR 59** | `load error` | [`print.asm:66`](../basic/print.asm:66) `cp 2 / jp nz,load_error` | ✅ **FIX** |
| 2 | `INPUT #1,A$` | **ERR 59** | `load error` | [`files.asm:791`](../basic/files.asm:791) `cp 1 / jp nz,load_error` | ✅ **FIX** |
| 3 | `LINE INPUT #1,A$` | **ERR 59** | `load error` | same site (shares `input_common`) | ✅ **FIX (free)** |
| 4 | `A$=INPUT$(3,#1)` | **ERR 59** | `Syntax error` | [`strvar.asm:182`](../basic/strvar.asm:182) `str_inputd_err` → `str_eval_no` | ❌ leave — §7 |
| 5 | `GET #1,1` | **ERR 59** | `Syntax error` | [`field.asm:527`](../basic/field.asm:527) `cp 4 / jr nz,gp_err` → `stmt_error` | ❌ leave — §7 |
| 6 | `PUT #1,1` | **ERR 59** | `Syntax error` | same site | ❌ leave — §7 |
| 7 | `FIELD #1,10 AS A$` | **ERR 59** | `Syntax error` | [`field.asm:165`](../basic/field.asm:165) `or a / jp z,stmt_error` | ❌ leave — §7 |
| 8 | `CLOSE #1` | *(no error)* | *(no error)* | [`files.asm:906`](../basic/files.asm:906) `dc_done` | ✅ already agrees |
| 9 | `PRINT EOF(1)` | **ERR 59** | **ERR 59** | `fch_mode_class` | ✅ already agrees |
| 10 | `PRINT LOF(1)` | **ERR 59** | **ERR 59** | `fch_mode_class` | ✅ already agrees |

Case 8 is not a null reading: the row types `CLOSE #1` **then `PRINT 7`**, so
"no error" is the value `7`, distinguishable from "nothing was read"
(⚠️ `appmiss-slice`: a sentinel that also means "no reading" is not a measurement).

### 2b. ERR 52 is a DIFFERENT class, and it is also wrong — measured, not swept

| typed | reference | zerobas |
|-------|-----------|---------|
| `PRINT #2,"X"` (2 > MAXFILES=1) | **ERR 52 `bad file number`** | `load error` |
| `INPUT #2,A$` | **ERR 52 `bad file number`** | `load error` |
| `PRINT #0,"X"` | **ERR 59 `file not open`** | `load error` |

Both come from `fch_valid`'s `jp nc,load_error`, which sits **before** the mode
check this slice touches, so **this slice does not move them** and must not.
🔴 Note the third row: on the reference, channel **0 is a legal channel number
that is merely not open** (ERR 59), not a bad file number — so an ERR 52 slice
cannot simply route all of `fch_valid`'s rejects to 52. Filed, §7.

### 2c. TRAPPABILITY — the semantics half, measured separately

`10 ON ERROR GOTO 100 / 20 <stmt> / 100 PRINT ERR / RUN`. The handler prints the
code; **`0` means no error was raised at all**, so "trapped", "not trapped" and
"nothing happened" are three distinct readings.

| subject | reference | zerobas today |
|---------|-----------|---------------|
| `PRINT #1,"X"` | **59** (handler ran) | `load error` (handler did NOT run) |
| `INPUT #1,A$` | **59** (handler ran) | `load error` (handler did NOT run) |
| `A=LOF(1)` — **GREEN CONTROL** | **59** | **59** ✅ |

`load_error` ([`bload.asm:162`](../basic/bload.asm:162)) is a `ret`-based print
path: it prints and the program CONTINUES. `err_notopen_raise` → `raise_error`
takes the shared trap decision. **So trappability is IN SCOPE** — it is what makes
this a semantics fix rather than a wording fix — and it comes for free with the
change in §3, because the raiser is the one `LOF` already uses. The `A=LOF(1)`
row is the control that proves the harness can read trappability at all.

## 3. The change — REUSE the raiser `LOF` already reaches

`fch_mode_class` ([`expr.asm:1036`](../basic/expr.asm:1036) — named
`ev_chan_hasfile` before this slice, see §7.3) already is exactly
"read `FCH_MODES[E]` into A, raise ERR 59 if it is 0, and report disk-vs-device in
CF". `EOF`/`LOF` are its only callers today. **`PRINT#` and `INPUT#` hand-inline
its first half and omit the `or a` — that omission is the whole defect.**

Both sites become a call to it. **Two hunks, no new routine, no new code path.**

[`basic/print.asm`](../basic/print.asm) (`ex_print`, the `PRINT #n` arm):

```
                push    hl                  ; save the text cursor
-               ld      d,0                 ; DE = channel (e preserved by fch_valid)
-               ld      hl,FCH_MODES
-               add     hl,de
-               ld      a,(hl)              ; A = FCH_MODES[ch]
+               call    fch_mode_class      ; A = FCH_MODES[ch]; ERR 59 if it is 0
                pop     hl                  ; restore the text cursor
                cp      LPT_MODE
```

[`basic/files.asm`](../basic/files.asm) (`input_common`, the `#n` arm — serves
`INPUT#` **and** `LINE INPUT#`):

```
                push    hl                  ; guard text cursor
-               ld      d,0
-               ld      hl,FCH_MODES
-               add     hl,de
-               ld      a,(hl)
+               call    fch_mode_class      ; A = FCH_MODES[ch]; ERR 59 if it is 0
                pop     hl
                cp      CAS_IN_MODE
```

Plus the rename and comment update on the routine itself (§7.3): its note said
"they are the ONLY two callers", which stops being true.

### Contract checks (each verified against the source, not assumed)

* **Preserves `E`** — both sites do `ld a,e / call fch_select` afterwards. ✅
* **Clobbers `A`/`HL`** — `HL` is already guarded by the surrounding `push`/`pop`
  at both sites; `A` is the value we want. ✅
* **`D` is no longer zeroed** — the helper indexes off `E` alone with an 8-bit
  add + `adc` into H. Neither site reads `D` afterwards (`PRINT#` does
  `ld a,e / call fch_select`; `INPUT#` overwrites with `ld de,fat_io_getbyte`). ✅
* **Raising with `HL` still pushed is safe.** `raise_error` resets `SP` on BOTH
  arms — `ld sp,(SAVSTK)` on the trap arm ([`interp.asm:829`](../basic/interp.asm:829)),
  and `fre_abort_low` resets from `SAVSTK` as its own first act on the abort arm.
  This is the same depth-independence `LOF`'s existing use relies on (it raises
  from deep inside the evaluator). ✅
* **`cp LPT_MODE` is repeated deliberately.** The helper's tail is
  `cp LPT_MODE / ret`, so its `Z` flag survives and `PRINT#` could drop its own
  compare for 2 more bytes. **Declined:** that would make `PRINT#`'s device
  dispatch depend on a flag set by the last instruction of a routine in another
  file. Not worth 2 B.
* **Mode 0 is unambiguously "not open"**: `FCH_MODES` values are 1 INPUT, 2 OUTPUT,
  3 APPEND, 4 RANDOM, 5 LPT, 6 CRT, 7 CAS-out, 8 CAS-in
  ([`sysvars.inc:1147`](../basic/sysvars.inc:1147)). ✅
* **Order is unchanged**: `fch_valid` still rejects 0 / >MAXF to `load_error`
  first, so §2b does not move.

### Byte cost

Per site: `ld d,0`(2) + `ld hl,nn`(3) + `add hl,de`(1) + `ld a,(hl)`(1) = **7 B**
replaced by `call nn` = **3 B** → **−4 B**. Two sites → **−8 B, all page 1**
(`ex_print` @ `$53C8`, `input_common` @ `$6EE8`, `ev_chan_hasfile` @ `$4EAF`,
`err_notopen_raise` @ `$7FCF` — all in page 1; the low region is untouched).

Clean baseline at `25b0b1e`: low **23 B**, page 1 **22 B**.
**Predicted: low 23 B (unchanged), page 1 30 B. MEASURED, clean build: low 23 B,
page 1 30 B — the prediction landed exactly.**

## 4. Behaviour that CHANGES, stated plainly

1. `PRINT #n` / `INPUT #n` / `LINE INPUT #n` on a not-open (but in-ceiling)
   channel print **`file not open`** instead of `load error`.
2. **They now HALT the program instead of continuing.** `load_error` prints and
   returns; ERR 59 aborts (or traps). This is the reference's behaviour and is the
   point of the slice, but it IS a control-flow change and every probe was checked
   for a mid-program closed-channel `PRINT#`/`INPUT#` (§6) — there are none.
3. They now **fire an armed `ON ERROR GOTO`**, with `ERR = 59`.

## 5. The gate

All in [`probes/disk/diskbasic_probe_lof.py`](../probes/disk/diskbasic_probe_lof.py),
beside the rows that filed this. **18 → 26 cases.**

**(a) The two filed entries are DELETED, not updated.** `KNOWN_DIVERGE["append_new_wr"]`
and `KNOWN_DIVERGE["ctl_prwr_closed"]` go away entirely; both rows must read
`FNO` on both machines. (Memory `deadcode-gate`: an allowlist that only
suppresses is rot.)

**(b) New rows for the verbs the item names but nothing gated.** `ctl_prwr_closed`
covers `PRINT#`; `INPUT#` and `LINE INPUT#` had **no row at all**:

| new case | typed | expect |
|---|---|---|
| `closed_input` | `INPUT #1,A$` | `FNO` both |
| `closed_lineinp` | `LINE INPUT #1,A$` | `FNO` both |

**(c) TRAPPABILITY rows, with their own GREEN control.** Value = the code the
handler printed; `0` = no error raised:

| new case | subject | expect |
|---|---|---|
| `trap_print_closed` | `PRINT #1,"X"` under `ON ERROR GOTO` | `59` both |
| `trap_input_closed` | `INPUT #1,A$` under `ON ERROR GOTO` | `59` both |
| `trap_lof_closed` | `A=LOF(1)` — **CONTROL, green TODAY** | `59` both |

Without `trap_lof_closed`, a `trap_*` row that stayed red would not distinguish
"the fix does not trap" from "this probe cannot read a trap".

**(d) The sites deliberately LEFT get rows too, on the allowlist.** This is what
keeps `KNOWN_DIVERGE` a **control that must keep matching** rather than an empty
box, and it makes an accidental sweep of §7's sites trip the gate:

| new case | typed | `KNOWN_DIVERGE` |
|---|---|---|
| `closed_get` | `GET #1,1` | `("FNO", "SYNTAX")` — item §7.1 |
| `closed_field` | `FIELD #1,10 AS A$` | `("FNO", "SYNTAX")` — item §7.1 |
| `closed_ch2` | `PRINT #2,"X"` | `("BFN", "LOADERR")` — item §7.2 |

`REF_EXPECT` / `DIR_EXPECT` entries are the values MEASURED above, recorded as
oracle locks; every new row is oracle-locked before it is scored
(memory `vacuous-gate-row-steers-not-just-misses`).

## 6. Two-sided controls that must NOT move

* `lof_closed` — `LOF` on a closed channel, ERR 59, agrees today. **The proof that
  ERR 59 works**; if it moves, the slice broke the thing it is reusing.
* `append_exist` 26/26, `roundtrip` 8/8, `lof_input` 26, `lof_bin` 2048,
  `ctl_syntax` SYNTAX.
* `fat-error-acceptance` **8/8 + the directory check** — all eight are
  MISSING-FILE cases (`load error`), a different situation from channel-not-open.
  Checked by reading its `CASES`: every case is a single `LOAD`/`RUN`/`KILL`/
  `BLOAD`/`OPEN`/`NAME`/`MERGE` line, **none types a `PRINT#`/`INPUT#`**, so none
  can reach the changed code.
* `chancost-characterize` 39 / **allowlist EMPTY** — its `err_notopen`, `fno_eof`,
  `bfn_trap`, `bfn_zero` rows already exercise ERR 52/59 trappability via
  `LOF`/`EOF`/`OPEN`. None of its 39 rows types a closed-channel `PRINT#`/`INPUT#`.
  ⚠️ It still has **no echo guard** (its own filed item) — a caveat on its rows,
  not on this slice's.
* `disk_probe_append.py`'s byte-identical Ctrl-Z round trip.
* The `diskbasic_probe_lof.py` echo guard is **not touched**; `MANGLED` stays fatal
  with or without `--gate`.

## 7. Deliberately NOT in this slice — with the measurement for each

Both get a `TODO.md` item carrying §2's table, and both are pinned by §5(d) rows
so they cannot drift silently.

**7.1 `INPUT$(n,#f)` / `GET` / `PUT` / `FIELD` answer `Syntax error` where the
reference answers ERR 59.** A **different disposition at different sites**
(`stmt_error` / `str_eval_no`, not `load_error`), in `field.asm` and `strvar.asm`.
`FIELD`'s would be a 0-byte change (`jp z,stmt_error` → `jp z,err_notopen_raise`)
and `GET`/`PUT`'s about 4 B — but `GET`'s site conflates "not open" with "open but
not RANDOM", and **what the reference answers for `GET` on a channel open FOR
INPUT is not measured**. Sweeping an unmeasured neighbour is the trap; one item
per session, and this one arrives with its own measurement.

**7.2 `fch_valid`'s rejects are the wrong class (ERR 52).** `PRINT #2` / `INPUT #2`
→ ref ERR 52, zerobas `load error`; and `PRINT #0` → ref **ERR 59**, so the fix is
not "route `fch_valid` failures to 52" (§2b). Six OPEN sites already raise 52
correctly via `oo_fail_bfn`, so again this is a per-verb disposition item.

**7.3 ✅ RENAMED (sign-off Q4).** `ev_chan_hasfile` → **`fch_mode_class`**: with
four callers across three files the `ev_` (evaluator) prefix was a misnomer. 0
bytes, 4 references. It stays SITED in `expr.asm` beside `EOF`/`LOF` — the move to
`files.asm` was not taken, and the routine's own comment now names all four callers
and states which half of it each one wants.

## 8. Gates to RUN (not assume)

`make repack-machine`, then clean `rm -rf build && make basic-reloc` (HARD
dead-code gate, **0 dead in BOTH builds**), then:

`make unit-test` 55/55 · `make lof-acceptance` **25 cases / 3 filed
(`closed_get`, `closed_field`, `closed_ch2`) and `KNOWN_DIVERGE` holding exactly
those three** · `make chancost-characterize` 39 / **allowlist EMPTY** ·
`make diskbasic-acceptance` 34/34 · `make bdos-acceptance` 12/12 ·
`make fat-error-acceptance` 8/8 + dir check · `make error-trap-acceptance` ·
`make abort-acceptance` 49/49 · `make stop-trap-acceptance` ·
`make linemax-acceptance` 60/60 · `make arrdim-acceptance` 73/73 ·
`make clearpool-acceptance` 52/52 · `make array-acceptance` 149/151 (the two
standing rows confirmed **BY NAME**: `ifc.instr.zero`, `ifc.instr.neg`).

`error-trap-acceptance` and `abort-acceptance` are the load-bearing ones, because
§4.2/§4.3 change control flow.

### RESULT — every gate RUN 2026-07-31, none assumed

| gate | result |
|---|---|
| clean `rm -rf build && make basic-reloc` | ✅ low **23 B**, page 1 **22 → 30 B**; dead-code **0 dead in BOTH builds** |
| `make lof-acceptance` | ✅ **26 cases, 0 unfiled, 0 oracle drift, 0 mangled** |
| `make unit-test` | ✅ 55/55 |
| `make chancost-characterize` | ✅ 39 cases, **0 filed — allowlist still EMPTY** |
| `make diskbasic-acceptance` | ✅ 34/34 |
| `make bdos-acceptance` | ✅ 12/12 |
| `make fat-error-acceptance` | ✅ **8/8 + directory check** |
| `make error-trap-acceptance` | ✅ ALL PASS |
| `make abort-acceptance` | ✅ 49/49 |
| `make stop-trap-acceptance` | ✅ ALL PASS |
| `make linemax-acceptance` | ✅ 60/60 |
| `make arrdim-acceptance` | ✅ 73/73 |
| `make clearpool-acceptance` | ✅ 52/52 |
| `make array-acceptance` | ✅ 149/151 — the two failures confirmed **BY NAME**: `ifc.instr.zero`, `ifc.instr.neg` (capitalisation-only, standing) |

## 9. Falsification — RUN

Knife: revert **both** `call fch_mode_class` hunks to the inlined read and
rebuild + reinstall the machine.

**✅ THE KNIFE WAS VERIFIED TO CUT BEFORE ANYTHING WAS SCORED.** Clean rebuild +
machine reinstall: page-1 free **30 → 22 B** and `__MEAS_PAGE1_END` **$7FE2 →
$7FEA**. ⚠️ Correction to this section as planned: it said `ex_print` and
`input_common` must move too. They do **not** — both labels sit *before* the edited
bytes, so their addresses are invariant under this knife and would have "passed"
either way. The page-1 end symbol is the one that actually carries the cut, and
naming the wrong witness in advance is exactly how a knife gets scored without
having cut.

* **Went RED, all six**: `append_new_wr`, `ctl_prwr_closed`, `closed_input`,
  `closed_lineinp` (all `FNO` vs `LOADERR`), `trap_print_closed`,
  `trap_input_closed` (both `59` vs `LOADERR` — the handler did not run).
* **Stayed GREEN, every paired control**: `trap_lof_closed` **59/59** (so the six
  reds are the subject, not a probe that cannot read a trap), `lof_closed`,
  `ctl_syntax`, `append_exist` 26/26, `roundtrip` 8/8, `lof_input`, `lof_bin`, and
  `closed_get` / `closed_field` / `closed_ch2` still diverging their filed way.
  **0 mangled rows.**

⚠️ A GREEN falsification is a claim about the APPARATUS first (`appmiss-slice`).
This probe mounts a /tmp copy of `test720.dsk` per case and echo-guards every row,
so the "no fixture" failure mode that made D-APPMISS's class gate vacuous does not
apply — but the knife is what establishes that, not this paragraph.

## 10. Sign-off — answered 2026-07-31

**Q1. Scope — AGREED.** PRINT# / INPUT# / LINE INPUT# only; §7.1 and §7.2 filed
with their measurements, each pinned by a `KNOWN_DIVERGE` row so it cannot drift.

**Q2. Trappability IN scope — AGREED.** Landed and measured: `trap_print_closed`
and `trap_input_closed` both read **59 on both machines**.

**Q3. Keep the rows in the lof battery — AGREED.** 18 → 26 cases, one gate.

**Q4. RENAME — TAKEN.** `ev_chan_hasfile` → `fch_mode_class`, 0 bytes; sited where
it was (§7.3).

## 11. What this slice got wrong, for the next one

🔴 **THE PLANNED KNIFE NAMED TWO WITNESSES THAT COULD NOT MOVE.** §9 specified that
`ex_print` and `input_common` must shift under the knife. Both labels precede the
edited bytes, so they are invariant either way — had the knife silently failed to
apply, two of the three "cut verified" checks would still have read as expected.
Only `__MEAS_PAGE1_END` (and the page-1 free number) actually carried the cut.
⚠️ **A cut witness must be downstream of the edit.** Generalises past this slice:
the same reasoning that picks a gate row picks a knife witness, and "the addresses
moved" is only evidence when the addresses *could* have moved.

⚠️ The case count in §5 was written as 25 and is 26 (18 + 8, not 18 + 7) — the
arithmetic was wrong, not the design. Recorded rather than quietly corrected,
because §3's byte arithmetic in the same draft *was* load-bearing and did land
exactly (−8 B); a spec that gets one count wrong earns a re-check of the others.
