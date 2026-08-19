<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-MSGSUB — the 14 unimplemented error messages, hosted in the sub-ROM

**Status: implemented and measured 2026-08-02 — see §10.**

Denominator: [`docs/msgexact-msx1-characterization.md`](msgexact-msx1-characterization.md)
§1/§2 — the verbatim text for all 41 ERR codes on **both** references, measured
2026-08-02. **Nothing in this slice transcribes a message from a published
reference.** Filed by [`docs/spec-basic-msgexact.md`](spec-basic-msgexact.md) §4.2.

## 1. The subject

Fourteen codes print `Unprintable error` on zerobas where the references print
real text:

| ERR | reference text | ERR | reference text |
|----:|---|----:|---|
| 12 | `Illegal direct` | 54 | `File already open` |
| 15 | `String too long` | 56 | `Bad file name` |
| 18 | `Undefined user function` | 57 | `Direct statement in file` |
| 19 | `Device I/O error` | 60 | `Bad FAT` |
| 50 | `FIELD overflow` | 62 | `Bad drive name` |
| 51 | `Internal error` | 63 | `Bad sector number` |
| 53 | `File not found` | 64 | `File still open` |

1..59 are two-reference values; 60..64 are CF-3300-only (the VG-8020 has no disk
ROM and answers `Unprintable error` there). zerobas is a disk machine, so the
CF-3300 is its oracle for that span — the characterization doc's own rule.

**They are reachable ONLY via `ERROR n`.** Verified by enumeration rather than
asserted: every `ld a,<n>` feeding `raise_error` across `basic/` and `sub/`
yields `{1,2,3,4,5,7,8,13,24,52,59,61}`, plus `fperr_to_err`'s
`{2,5,6,7,9,10,11,13,14,16}`, plus `raise_error_forced`'s 22. **No zerobas site
raises any of the fourteen.** That enumeration is also what bounds §7's blast
radius.

## 2. Why the sub-ROM, and why the prior objection is void

Main-resident the fourteen strings cost ≈**227 B** against **39 B** of page 1.
Not fundable.

[`spec-basic-msgenc-carve.md:286`](spec-basic-msgenc-carve.md:286) Q4 resolved
"does the encoding belong in the sub-ROM?" with **no** — the decoder runs on the
abort path, *"which must work when the sub-ROM is absent"*. That argument is
about **one** message (`err_subrom_absent`, whose alias target
`err_illegal_fn_arr` is low-region and stays there) and about the **decoder**.

🎯 **This slice does not rely on that argument at all**, and that is a
deliberate strengthening of D-MSGEXACT §4.2's position. §4.2 argued the absent
case is *unreachable* (`tokenise` is itself a sub-ROM page-0 tenant, so with no
sub-ROM you cannot type `ERROR 12`). That argument has a hole — a **tokenised**
program can arrive from tape or disk without `tokenise` ever running, so
`ERROR 12` is reachable on a sub-ROM-less machine in principle. Rather than
patch the argument, the design below makes the absent case **degrade to exactly
what zerobas prints today** (`Unprintable error`), for **one byte**, and §6's K1
measures that instead of reasoning about it.

**The constraint that does bite**: `print_string` (`$4673`) and `print_msg`
(`$7717`) are main **page 1**, switched out while a page-1 tenant runs;
`check_tenant_closure --page1` enforces it. The sub-ROM cannot call main's
printer. It emits through BIOS **`CHPUT` `$00A2`**, which is page 0 and stays
mapped — the same edge `title_tenant` (index 17) already uses, and the reason
that tenant is page-1 rather than page-0.

## 3. Design

### 3.1 One new escape byte, and the table entries do the rest

`MSGESC_SUB equ 6` — **above** `MSGESC_HI` (which stays `MSGESC_FILE` = 5), so
the phrase table's length and the decoder's phrase bound stay one fact in one
place. `print_msg_stopcr` gains an explicit test **ahead of** the phrase bound:

```
pm_lp:          ld      a,(hl)
                inc     hl
                or      a
                ret     z
                cp      MSGESC_SUB          ; +2   NEW
                jr      z,pm_sub            ; +2   NEW
                cp      MSGESC_HI + 1       ;      unchanged
                jr      nc,pm_lit
```

⚠️ It **must** precede the bound test: `MSGESC_SUB` > `MSGESC_HI`, so the
existing `jr nc,pm_lit` would otherwise `pchar` a raw `$06`. And it must **not**
be folded into the phrase range: `tests/test_msgenc.py:115` reads exactly
`MSGESC_HI - MSGESC_LO + 1` phrases out of `msg_phrase_tab`, so bumping
`MSGESC_HI` would make that test read one entry PAST the table and compare
against whatever follows — a readout that fails by producing plausible garbage.
§7 adds the standing guard for that (`MSGESC_SUB > MSGESC_HI`).

The marker string is **one byte**, deliberately sited so that `err_unprintable`
immediately follows it:

```
err_subhosted:  db      MSGESC_SUB          ; +1
err_unprintable:                            ; the ABSENT-sub-ROM fall-through
                db      "Unprintable",MSGESC_ERROR,0
```

🎯 **That adjacency IS the degradation path**, not a coincidence of layout: on
`CF=1` (sub-ROM absent) the decoder resumes at the next byte, which is the `U`
of `Unprintable`. §7 pins the adjacency with a unit-test control, exactly as
D-MSGEXACT's K5 control pins the `err_overflow` split.

```
pm_sub:         push    hl                  ; +1  CALSLT clobbers everything
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_ERRMSG  ; +4
                call    subrom_call         ; +3
                pop     hl                  ; +1  (POP does not touch flags)
                ret     nc                  ; +1  tenant printed it -> done
                jr      pm_lp               ; +2  ABSENT -> "Unprintable error"
```

⚠️ **`A` cannot carry a status and neither can `CF` from the tenant.** A is not
preserved across CALSLT ([`basic/float-arith.asm:1799`](../basic/float-arith.asm:1799),
the SQR/ATN/EXP/LOG lesson) and `subrom_call`'s own `CF` means "absent", never
"found" ([`basic/field.asm:638`](../basic/field.asm:638)). So the tenant cannot
say *"not my code"* — it must print **something** for every input, and it
carries its own `Unprintable error` for codes outside its table. The only signal
main reads back is `subrom_call`'s absent-CF.

### 3.2 Routing: four dense entries and one pointer, all zero bytes

| site | change | B |
|---|---|---:|
| `err_msgtab` 12 / 15 / 18 / 19 | `dw err_unprintable` → `dw err_subhosted` | 0 |
| `rerr_unprintable` ([`interp.asm:992`](../basic/interp.asm:992)) | `ld hl,err_unprintable` → `ld hl,err_subhosted` | 0 |

`rerr_unprintable` is the fall-through of `rerr_sparse` → `rerr_sparse2`
(52/59, then 55/58/61), i.e. **every out-of-dense-table code**. Repointing it
routes the ten sparse holes *and* codes 26..49 / 65..255 sub-side in one edit,
with no membership test main-side. The tenant answers those with its own
`Unprintable error`, so the text is unchanged for them.

🎯 **That makes code 26 a live control that rides the new mechanism.** It is
already in the gate, already green, already asserted as `Unprintable error` —
and after this change it is produced by the tenant instead of by main. If the
tenant or the CALSLT is *broken*, **26 reddens** (K2 measured that it does).
Code 23 keeps its own dense entry pointing at main's `err_unprintable`, so it is
the paired control on the *unchanged* path.

⚠️ **BUT 26 CANNOT TELL "ROUTED SUB-SIDE" FROM "NOT ROUTED AT ALL", AND K5
MEASURED THAT.** Reverting `rerr_unprintable` to `err_unprintable` leaves 26
**green** — because main's string and the tenant's fallback are the same text,
which is the very property that makes the routing free. So 26 is a control for
the mechanism being *sound*, not for it being *present*; the ten sparse holes are
what pin the routing's presence. Stating that rather than letting one green row
stand for two different claims ([[one-row-cannot-separate-two-rules]]).

### 3.3 The tenant — page 1, index 22, no marshalling

`sub/errmsg.asm`, entry `errmsg_tenant`, `SUBROM_IDX_ERRMSG equ 22` (the next
free page-1 index; the page-0 table is full to the `$0038` vector). Its only
input is `ERRFLG` `$F414`, already in RAM and already set by `raise_error`
before any message resolves — **so nothing marshals at all**, the
`title_tenant` shape.

```
errmsg_tenant:  ld      a,(ERRFLG)
                ld      hl,em_table
                ld      b,EM_ROWS
em_scan:        cp      (hl)                ; row code
                inc     hl                  ; (INC rr / LD r,(HL) do not touch Z)
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                inc     hl
                jr      z,em_print
                djnz    em_scan
                ld      de,em_unprintable   ; not one of ours
em_print:       ex      de,hl
em_lp:          ld      a,(hl)
                inc     hl
                or      a
                ret     z
                push    hl
                call    CHPUT
                pop     hl
                jr      em_lp
```

🎯 **The sub-side strings are PLAIN, not phrase-encoded, and that is a decision
rather than an omission.** D-MSGENC measured a decoder at 44 B and a phrase
table at 40 B; duplicating both sub-side would buy roughly 20 B of literal text
back out of a 3 KB budget, and would create a second copy of the phrase table
that can silently drift from main's. Plain text costs ~14 B of emitter and
cannot drift. The "print code duplication" the sign-off approved therefore comes
to **a nine-instruction CHPUT loop**.

`ERRFLG` is RAM and `CHPUT` is `< $4000`, so `check_tenant_closure --page1`
passes by construction; the tenant is a seed for the dead-code gate.

### 3.4 Byte accounting — PREDICTIONS from the symbol table

⚠️ Predictions. The figures that count come from `rm -rf build && make
basic-reloc` and nothing else ([[measure-the-wall-from-clean]]).

**Main page 1**

| item | B |
|---|---:|
| `cp MSGESC_SUB` + `jr z,pm_sub` | +4 |
| `pm_sub` body | +12 |
| `err_subhosted` marker | +1 |
| `err_msgtab` 12/15/18/19 + `rerr_unprintable` repoints | 0 |
| **total** | **+17** |

Main low region: **0**. `MSGESC_SUB`, `SUBROM_IDX_ERRMSG` are equates.

Predicted: page 1 **39 B → 22 B free**; low **23 B → 23 B**.

**Sub page 1** (measured free space: **3067 B**, content ends `$7405`; the
"3084 B / last symbol `$73F4`" figure in the TODO is the last *symbol*, not the
last byte)

| item | B |
|---|---:|
| 14 strings + the `Unprintable error` fallback, plain + NUL | 249 |
| `em_table` 14 rows × 3 | 42 |
| tenant code + `sub_p1_table` row | ~31 |
| **total** | **≈322** |

Predicted: sub page 1 **3067 B → ≈2745 B free**.

### 3.5 Explicitly NOT in this slice

* **Raising any of the fourteen.** "Should zerobas raise ERR 12 for a direct-mode
  `INPUT`?" is a different question per code, with its own oracle work. This
  slice makes the *message* right for `ERROR n`; it adds no raiser.
* **Migrating existing messages** (§8). Sized there, not done here.

## 4. What is being claimed, so the knives have something to cut

1. A page-1 tenant emitting through `CHPUT` is **indistinguishable from
   `print_msg`** on the abort path, because `fre_abort_low` zeroes `PRDEST`
   first and `pchar` with `PRDEST=0` *is* `call CHPUT`. — K3.
   🔴 **Half-refuted, and §5.2/§6 record how.** The zero *is* load-bearing
   (K3 measured both directions on `mid-ifc`), but the rows this spec originally
   offered as the measurement could not see it, and the sub-hosted path can never
   meet `PRDEST != 0` at all — so for *that* path the claim is **bounded away,
   not measured**.
2. The absent-sub-ROM case **degrades to `Unprintable error`**, not to silence
   and not to a crash. — K1.
3. Code 26 is a **live** control of the new mechanism. — K2.
4. The four dense repoints and the one sparse repoint are **two independent
   mechanisms**, and one row cannot separate them. — K4, K5.

## 5. Gate

[`probes/basic/basic_probe_msgexact.py`](../probes/basic/basic_probe_msgexact.py)
already owns the denominator, the lock and `--relock`. Changes:

* `HOLES` → **empty**. Every one of the 45 rows then asserts the reference text.
  The set is kept as a named empty frozenset with its history, not deleted: the
  HOLE-SURPRISE reporting is the mechanism that told us a hole had been filled,
  and an empty set is the honest statement that there are none left.
* A new **SUBX** battery (already added, measured pre-sign-off as spec input —
  §5.2) covering the abort-path shapes the direct-mode code walk is structurally
  blind to.

### 5.1 Predicted RED and GREEN — locked BEFORE the build

⚠️ **Derived from the EDIT LIST, not from the scope list.** D-MSGEXACT predicted
25 red and got 40 because a scope call leaked into the forecast
([[predicted-red-set-must-not-inherit-scope]]). The edit list here is §3.1–§3.3;
what it can move is: the four dense-hole entries, the sparse fall-through, and
anything that rides `print_msg_stopcr`.

**PREDICT_RED (the pre-edit run of the NEW gate) — exactly 14 rows:**

`12 15 18 19 50 51 53 54 56 57 60 62 63 64`

plus SUBX's `hole-run` and `prd-hole` (§5.2), i.e. **16 red rows of 49**:
`msgexact --gate` reads **33/49 before → 49/49 after**. Nothing else can
move: the decoder change is additive (a byte value no existing message
contains), and the two repoints touch only pointers whose current target text is
identical to the tenant's fallback.

**PREDICT_GREEN — 31 rows, of which five are load-bearing:**

* **26** — rides the new sparse routing; if the tenant/dispatch is wrong it
  reddens (K2 checks it can).
* **23** — the *unchanged* main-resident `Unprintable error`; separates "the
  tenant is broken" from "the string is broken".
* **52 / 59** — matched by `rerr_sparse` *before* the fall-through. If the new
  routing swallowed them they would redden.
* **55 / 58 / 61** — same, in `rerr_sparse2`. (`61` is the one immediately
  before the fall-through.)

Plus D-MSGEXACT's own `5 9 10 16 25` and the four EXTRA rows, all untouched.

**SUBX predicted** (post-edit): `hole-run` gains the run-mode suffix,
`ifc-run` unchanged, `prd-hole` == `prd-ifc` in disposition. Values locked from
§5.2's reference measurement.

### 5.2 SUBX — measured on both references BEFORE the design was fixed

| row | what it separates |
|---|---|
| `hole-run` / `ifc-run` | RUN mode: does a sub-emitted body get main's `" in <line>"` suffix, the same as a resident one? Every row in the code walk is DIRECT mode, so this arm of `fre_abort_low` was **never** covered for any message. |
| `prd-hole` / `prd-ifc` | An error raised mid-`PRINT#` **to a disk file**. `pchar` honours PRDEST; `CHPUT` cannot. This is claim 4.1, measured. CF-3300 + zb only (needs a disk); the VG-8020 row reads `<skipped:no-disk>`, a **third** sentinel so it can never be read as `<none>`. |

**Measured 2026-08-02, before the design was fixed** — full table in
[`docs/msgexact-msx1-characterization.md`](msgexact-msx1-characterization.md) §6:

| row | both refs (`prd-*`: CF-3300) | zb @ `3ffd390` | post-edit target |
|---|---|---|---|
| `hole-run` | `Illegal direct in 10` | `Unprintable error in 10` | `Illegal direct in 10` |
| `ifc-run` | `Illegal function call in 10` | `Illegal function call in 10` ✅ | unchanged |
| `prd-hole` | `Illegal direct in 30` | `Unprintable error in 30` | `Illegal direct in 30` |
| `prd-ifc` | `Illegal function call in 30` | `Illegal function call in 30` ✅ | unchanged |

🔴 **`prd-ifc` PASSING WAS READ AS "CLAIM §4.1 IS MEASURED". IT IS NOT, AND
KNIFE K3 IS WHAT SAID SO** — see §6 and the characterization doc §6 for the full
correction. `PRINT#1,"[";` restores `PRDEST` at statement end, so the `ERROR n`
on the *next* line never meets it set: deleting `fre_abort_low`'s
`ld (PRDEST),a` moved **neither** `prd-` row. A green row that cannot go red was
being cited as the load-bearing measurement of this whole slice.

🎯 **`mid-ifc` (added after K3) is the row that can.** The error is raised
*inside* the `PRINT#` argument list, so `PRDEST` really is set — and K3 measured
both directions: with the zero, `Illegal function call in 20`; without it, an
**empty screen** and the message in the file. It is green before and after this
slice, and it now holds down the mechanism the sub-ROM path depends on. Nothing
in the corpus held it before.

⚠️ **And there is deliberately no `mid-hole`.** `ERROR n` is a statement and
cannot appear inside a `PRINT#` argument list, so a sub-hosted message can never
be raised with `PRDEST` set. For that path §4.1 is **bounded away, not
measured** — weaker than the original claim, and true.

So the SUBX battery adds **2 predicted-RED rows** (`hole-run`, `prd-hole`) and
**3 predicted-GREEN controls** (`ifc-run`, `prd-ifc`, `mid-ifc`). ⚠️ `mid-ifc`
did not exist at baseline time, so it is **not** counted in the "before" figure:
**33/49 before → 50/50 after**.

### 5.3 Knives — aimed at the JUSTIFICATION

| # | cuts | target claim | predicted |
|---|---|---|---|
| K1 | `10 POKE &HF107,0 : ERROR 12` + `RUN` (`SUBSLOT_OK`), **no rebuild** | "the absent case degrades to `Unprintable error`" (§4.2) | **`Unprintable error in 10`** — and the control, the same line without the POKE, reads `Illegal direct in 10` |
| K2 | corrupt the tenant's `em_unprintable` leading byte | "26 is a live control of the new mechanism" (§4.3) | **RED on 26**, GREEN on 23 |
| K3 | delete `ld (PRDEST),a` from `fre_abort_low` | "CHPUT-vs-pchar equivalence is *given by* the PRDEST zero, not by luck" (§4.1) | **`prd-ifc` RED** (resident message diverted into the file) while **`prd-hole` stays GREEN** (CHPUT cannot be diverted) — the asymmetry is the reading |
| K4 | revert `err_msgtab[15]` to `dw err_unprintable` | "each dense hole is wired independently" | **RED on 15 only**; 12/18/19 GREEN |
| K5 | revert `rerr_unprintable` to `ld hl,err_unprintable` | "the sparse fall-through is a SECOND mechanism" | **RED on all ten sparse holes**, GREEN on 12/15/18/19 **and on 26** |

🎯 **K1 is the one that can embarrass this spec.** If the fall-through does not
fire — a mis-sited `err_subhosted`, a `jr` that lands wrong — the absent machine
prints nothing and §2's whole "we don't need the unreachability argument" claim
collapses. It is also the cheapest knife in the tree: a `POKE`, no rebuild.

⚠️ **K3 is predicted RED on the CONTROL and GREEN on the subject** — the
inverse of the usual shape. A knife whose predicted-green row is the *new* code
is the only kind that can show the new path is not accidentally riding a
protection it does not have ([[knife-that-refutes-its-own-control]]).

## 6. Corpus after the change

The full standing list (README/TODO). The ones this slice can plausibly move:

* `msgexact --gate` — **45/45**, zero holes.
* `msgexact --relock` — untouched (references, not zerobas).
* `error-trap-acceptance` MSGTAB_BOUND — `ERROR 23..26` text. **26 is now
  sub-hosted**; a second, independent probe holding the same control. No edit.
* `unit-test` — two new files (§7).
* `deadcode` both builds, all four closure checks.

## 7. Blast radius — and why it is small, stated with its reason

D-MSGEXACT broke 30 comparisons across 9 files because it changed the text of
messages **the corpus actually prints**. This slice changes only text that
**nothing prints today except `ERROR n` with a hole code** — which §1's
enumeration establishes, and which is the reason the assertion-vs-needle hazard
is *not* live here. Checked, not assumed: no probe or test drives `ERROR` with
any of the fourteen (`grep -rn "ERROR [0-9]" probes/ tests/` → codes
5/7/9/10/11/21/23/24/25/26 only).

Needle vocabularies that *could* newly match — `kwsweep.ERROR_WORDS`
(`illegal direct`, `file not found`, `device i/o error`, `bad file`),
`chancost`/`lof`.`ERR_CLASSES` (`file not found`) — are **not** reachable,
because a needle only fires on text a case prints, and no case prints these.
They stay lowercase regardless; no edit.

Edits outside `basic/`/`sub/`:

1. `probes/basic/basic_probe_msgexact.py` — `HOLES` empty, `SUBX` gate rows,
   D-MSGSUB's predicted sets recorded beside D-MSGEXACT's (never overwriting
   them).
2. `tests/test_msgenc.py` — two new **controls**:
   * `MSGESC_SUB > MSGESC_HI`, so a future "tidy-up" that folds the new escape
     into the phrase range cannot silently make `read_phrases` overrun.
   * `err_unprintable == err_subhosted + 1`, the absent-sub-ROM fall-through
     adjacency (§3.1) — the same shape as the existing `err_overflow` gap check.
3. `tests/test_msgsub.py` — **new**. Decodes `em_table` out of `build/sub.rom`
   and asserts each of the fourteen codes maps to the reference text, typed
   independently of the `db` lines that produce it (`test_msgenc`'s own rule);
   asserts the table's code set is **exactly** the fourteen (the denominator, so
   a fifteenth row or a missing one is a failure, not a silent pass); asserts
   `EM_ROWS` equals the row count.
4. `docs/msgexact-msx1-characterization.md` — the zerobas column for the
   fourteen, plus §6 (the SUBX readings).
5. `Makefile` — 🔴 **`SUB_PARTS` += `sub/errmsg.asm`. NOT optional and NOT
   cosmetic**: without it `make` never rebuilds `sub.rom` when the tenant
   changes. Clean builds hid it completely; knife K2 is what found it, by
   predicting RED and getting green ([[makefile-subparts-stale-tenant]]).
   **Any new `sub/*.asm` needs this line, every time.**
6. `basic/PROVENANCE.md` — the error-text row said *"own wording (plain English;
   not copied)"*. That was true of the pre-D-MSGEXACT tree and is now a **false
   attestation**: zerobas reproduces the reference's text verbatim. Replaced with
   the actual provenance — every string is a **black-box reading of a running
   machine's screen**, not a ROM read and not a transcription from a published
   reference (which is measurably wrong about ERR 17). `sub/PROVENANCE.md` gets
   the matching entry, since `sub/errmsg.asm` is nothing but such strings.
7. `TODO.md` — close the item; file §8 as **D-MSGMIGRATE**.

## 8. The prize, sized — a follow-on, NOT this slice

Main page 1 currently holds **252 B of message strings** plus the 40 B phrase
table (measured from `build/basic-reloc.sym` + the ROM image, not estimated):

`err_type_mismatch` 14 · `err_fp_divzero` 17 · `err_resume_noerr` 9 ·
`err_unprintable` 13 · `err_line` 22 · `err_verify` 8 · `brk_msg` 6 ·
`err_cont` 15 · `err_noret` 14 · `err_nofor` 10 · `err_data` 7 ·
`err_missing_operand` 16 · `err_input_pastend` 15 · `err_seq_only` 20 ·
`err_bad_filemode` 10 · `err_linebuf_overflow` 21 · `err_overflow` 9 ·
`err_bad_filenum` 12 · `err_file_notopen` 14

🎯 **The mechanism migrates a table-reached message for ZERO main-side bytes** —
the `err_msgtab` entry just becomes `dw err_subhosted` and the string is deleted.
That is the structural relief page 1 has needed since the wall closed.

⚠️ **But not all 252 B are migratable, and the difference is the follow-on's
real work.** The tenant is keyed on `ERRFLG`, so a message can move only if
**every** path that prints it goes through the table. These do **not**:
`err_verify` (cload's own `jp print_msg`), `err_mem`/`err_prog_mem` (cload's
`ctp_oom`), `brk_msg`, `err_input_pastend`/`err_seq_only`/`err_bad_filemode`
(reached via `rerr_sparse2`'s own `ld hl`, which is a *different* key), and
`err_bad_filenum`/`err_file_notopen` (`rerr_sparse`, same). A second selector —
`db MSGESC_SUB, <index>, 0`, 2 B per message instead of 0 — covers those, and
whether that pays is a measurement, not a claim made here.

Un-encoding a migrated message sub-side also shrinks main's phrase table if it
was the last user of a phrase (`MSGESC_FILE` has exactly two users).

## 9. Sign-off — answered 2026-08-02

| # | question | answer |
|---|---|---|
| 1 | route ALL out-of-dense codes sub-side (§3.2) | **yes** — one mechanism, 0 B, and 26 becomes a live control |
| 2 | plain strings sub-side, no duplicated phrase decoder (§3.3) | **yes** — the duplication is a nine-instruction CHPUT loop |
| 3 | 60/62/63/64 take the CF-3300's text (§1) | **yes** — zerobas is a disk machine, the CF-3300 is its oracle |
| 4 | `pm_sub` sited in page 1 at +17 B (§3.4) | **page 1** — leave the low region's 23 B alone |

Confirmed 2026-08-02; implemented below.

## 10. The measurement

### 10.1 Walls — clean `rm -rf build && make basic-reloc`

| wall | before (`3ffd390`) | after | predicted |
|---|---|---|---|
| main page 1 `$4000-$7FFF` | 39 B free | **22 B free** | +17 B ✅ **exact** |
| main low `$2812-$3FFF` | 23 B free | **23 B free** | unchanged ✅ |
| sub page 1 (content end) | 3067 B free (`$7405`) | **2740 B free** (`$754C`) | ≈322 B, actual **327** |

Dead code 0/0 both builds. All four closure checks pass; `errmsg_tenant` joins
the page-1 closure (22 → 23 tenants) with no main-page-1 escape.

### 10.2 Gate — the prediction was EXACT

`basic_probe_msgexact.py --gate`: **33/49 before → 50/50 after.**

🎯 **The 16 predicted-RED rows were exactly the 16 measured**, with no
unpredicted red and no predicted-red-but-green — the probe diffs the run against
`MSGSUB_PREDICT_RED` and printed `exact match`. That is the thing D-MSGEXACT did
not manage (25 predicted, 40 measured), and the difference is §5.1's rule:
derive the forecast from the EDIT LIST.

(49 → 50 because `mid-ifc` was added mid-slice, after K3; §5.2 records why it is
not counted in the "before".)

### 10.3 Knives — five aimed, two of them landed on ME

| # | claim | predicted | measured |
|---|---|---|---|
| K1 | the absent case degrades to `Unprintable error` | `Unprintable error in 10` | ✅ **3/3**, incl. a control proving the POKE did not just wreck the abort path |
| K2 | 26 is a live control of the new mechanism | RED on 26, GREEN on 23/12 | ✅ 3/3 — **but only after it found a defect in my own change** |
| K3 | the PRDEST zero is what makes CHPUT ≡ pchar | `prd-ifc` RED, `prd-hole` GREEN | 🔴 **REFUTED — neither moved.** Re-aimed as K3b: ✅ both directions |
| K4 | each dense hole is wired independently | RED on 15 only | ✅ 4/4 |
| K5 | the sparse fall-through is a SECOND mechanism | RED on the sparse holes, GREEN on the dense four | ✅ 5/5 — **and 26 stayed green**, which corrects §3.2 |

🔴 **K2 FOUND A REAL DEFECT IN THIS SLICE, AND THE WAY IT SURFACED IS THE
LESSON.** Its first run reddened nothing. Before recording that as a finding
about code 26, the cut itself was checked — and `build/sub.rom` was **byte-
identical to the baseline**. `sub/errmsg.asm` was missing from the Makefile's
`SUB_PARTS`, so `make` never rebuilt the sub-ROM. The clean-build results were
all valid (`rm -rf build` forces a full rebuild), so nothing shipped wrong — but
the *next* incremental edit to the tenant would have silently shipped a stale
`sub.rom` with no gate able to see it. That is exactly
[[makefile-subparts-stale-tenant]], met again by adding a new sub-ROM file, and
it was caught only because a knife predicted RED and got green
([[knife-that-reddens-nothing-is-the-finding]], [[knife-found-defect-in-own-fix]]).

🔴 **K3 REFUTED THE SPEC'S OWN HEADLINE MEASUREMENT.** §4.1/§5.2 and the
characterization doc all said the `prd-*` pair proved CHPUT-vs-pchar equivalence
because it raised its error with `PRDEST` set. Deleting `ld (PRDEST),a` from
`fre_abort_low` moved **neither row** — `PRINT#` restores `PRDEST` at statement
end, so the `ERROR n` on the next line never sees it. Two rows had been written
into a spec and a denominator as the load-bearing reading of the slice, and they
could not go red. Re-aimed at `mid-ifc` (the error raised *inside* the `PRINT#`
argument list) the cut lands both ways: with the zero, the message is on screen;
**without it the screen is EMPTY and the message is in the file**. The corrected
position is in §5.2 — for the sub-hosted path the question is *bounded away*
(`ERROR n` cannot appear inside a `PRINT#`), not measured.

⚠️ **K5 corrected §3.2 too.** Code 26 stays green when the sparse routing is
reverted, because main's `Unprintable error` and the tenant's fallback are the
same text. 26 is a control for the mechanism being *sound*, not *present*.

### 10.4 Corpus — all green

`unit-test` **56/56** (two new files) · `deadcode` **0/0** both builds · all four
closure checks · `msgexact --gate` **50/50** · `msgexact --relock` OK ·
`lnblank-acceptance REPEAT=2` **530/530, allowlist EMPTY** ·
`lnblank-say-acceptance` **108/108, 6 pins** · `lnblank-echo` ·
`error-trap-acceptance` ALL PASS · `error-acceptance` · `abort-acceptance` ·
`array-acceptance` **151/151** · `logicops` · `float` · `arrdim` · `clearpool` ·
`badfnum` 93 cases 0 drift · `lof` 45 cases 0 drift · `chancost` 53 cases 0 filed
divergences · `linemax` 60/60 · `sysvarsweep` · `string` · `str-domain` · `math` ·
`input` · `direct-ctrl` 40/40 · `kwsweep` · `stop`/`strig`/`key`-trap ·
`fat-error` · `diskbasic` 34/34 · `bdos` 12/12 · `subrom` boot gate PASS.

🎯 **`error-trap-acceptance`'s own `msgtab_bound` row is a SECOND, INDEPENDENT
control on the new mechanism** and needed no edit: it compares `ERROR 23..26`
text against the reference, and 26 is now produced by the tenant. Two probes,
written years apart in this arc, hold the same fact.

⚠️ Standing and NOT caused by this work: `tools/audit_citations.py` still reports
its 2 gating findings (`basic/fat.asm`, `basic/missing.asm`) — re-checked before
and after, unchanged; `lnblank-echo` still reports `dec-eol`/`dec-eolctl`
MANGLED on all three sides (non-gating, exit 0).
