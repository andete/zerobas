<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-MSGEXACT — reference-exact error message text, tree-wide

**Status: awaiting sign-off. No `basic/` or `sub/` edit has been made.**

Denominator: [`docs/msgexact-msx1-characterization.md`](msgexact-msx1-characterization.md),
measured 2026-08-02 on both references and the repack machine at `4d43294`.

## 1. The decision, and what it replaces

zerobas had a **house-style lowercase** policy for error wording, with a
documented per-message exception list (arrays §9.5 kept `Illegal function call`,
`Out of memory`, `Subscript out of range`, `Redimensioned array` capitalised
because the arrays arc wanted its error surface oracle-exact).

That policy is **withdrawn**. Every message zerobas prints is to be the
reference's verbatim text.

⚠️ **The `TODO.md` item that opened this slice misreads its own evidence.**
It cites [`basic/arrays.asm:608`](../basic/arrays.asm:608) — *"the same documented
deviation as every other zerobas syntax error"* — as a false claim disproved by
`Illegal function call`. It is not false: it is scoped to **syntax** errors, and
`err_syntax` is the only one. The same comment block, four lines down, names
Tier B as *"the reference-verbatim capitalised `Illegal function call`"*. arrays.asm
was never confused. **The tree's inconsistency was deliberate, documented policy,
not a defect** — which is why no gate ever caught it, and why withdrawing the
policy (not fixing a bug) is the right frame.

## 2. The two standing `array-acceptance` failures — resolved, and not what was filed

`ifc.instr.zero` / `ifc.instr.neg` have sat red at 149/151 for months. The TODO
suspected a message-CASE defect. **It is a stale probe expectation.**

`INSTR(0,…)` no longer reaches `ev_f_ifc`. D-MISS-2 folded INSTR's position check
into `eval_pos_arg` ([`basic/interp.asm:1449`](../basic/interp.asm:1449)), whose
reject path is `gb_illegal` → `ld a,5 : jp raise_error` → `err_msgtab[5]` →
`err_illegal_fn_arr` → **capitalised**. The deletion is documented at
[`basic/str-engine.asm:1340`](../basic/str-engine.asm:1340). The probe at
[`basic_probe_arrays.py:748`](../probes/basic/basic_probe_arrays.py:748) still
asserts the pre-D-MISS-2 lowercase route.

So zerobas already does what this spec wants for those two rows, and the fix is
to the **expectation**, not to `basic/`. 149/151 → **151/151**.

🔴 **Note what that means about the corpus.** A refactor silently changed a
user-visible message, two probe rows went red, and for months that was read as
"the probe's expectation is wrong" rather than investigated. A red row that is
assumed-stale is a red row that measures nothing.

## 3. Design

### 3.1 The policy is a CARVE, not a cost

The lowercase style is the *only* reason four strings and two code paths are
duplicated. Make the wording exact and the duplicates become byte-identical:

| pair | today | exact | |
|---|---|---|---|
| `err_illegal_fn` `$42B7` (p1) / `err_illegal_fn_arr` `$3D2B` (low) | `"i",ILLFN` / `"I",ILLFN` | both `"I",ILLFN` | **merge** |
| `err_mem` `$77F3` (p1) / `err_mem_arr` `$3D2E` (low) | `"o",UTOF,"memory"` / `"O",UTOF,…` | both `"O",UTOF,…` | **merge** |

Keep the **low-region** copy of each and delete the page-1 one; every reader is
an absolute address, so placement is free
([`basic/interp.asm:779`](../basic/interp.asm:779)).

Once merged, `fp_runtime_error`'s whole one-code-two-dispositions apparatus is
dead — the `cp 6`/`cp 3` interceptions and the three routines they feed
([`basic/interp.asm:662`](../basic/interp.asm:662)–709). Verified: `fre_arymem_oom`
and `fre_illegalfn_lc` have **no other callers**; `fre_store_raise` is reached
only from those two. `raise_error_hl` survives — `main.asm:365`, `missing.asm:612`
and `interp.asm:882` still use it.

`fperr_to_err`'s slots 3 and 6 stop being `db 0` placeholders and become real
entries (3→5, 6→7). Table size unchanged.

Repoint two aliases: `err_subrom_absent` ([`basic/subromcall.asm:67`](../basic/subromcall.asm:67))
and `err_stack` ([`basic/program.asm:1432`](../basic/program.asm:1432)).

### 3.2 Byte accounting — page 1 (sizes from `build/basic-reloc.sym`, not estimated)

**Carve**

| item | B |
|---|---:|
| `fp_runtime_error` head: two `cp`+`jp z` pairs | −10 |
| `fre_arymem_oom` (`$4284`→`$428B`) | −7 |
| `fre_illegalfn_lc` (`$428B`→`$4290`) | −5 |
| `fre_store_raise` (`$4290`→`$429B`) | −11 |
| `err_illegal_fn` string | −3 |
| `err_mem` string | −9 |
| **total** | **−45** |

**Cost** — the three places the encoder's leading-letter exclusion does *not* save us

| item | B |
|---|---:|
| ERR 8 wording: `undefined line` (15, `$4452`→`$4461`) → `Undefined line number` (22) | +7 |
| ERR 6/25: the `err_linebuf_overflow`→`err_overflow` **fall-through breaks** (21 B blob → 21 + 9) | +9 |
| ERR 59: `File not OPEN` needs a **leading** capital, so it loses `MSGESC_FILE` (`"file "`, lowercase) | +4 |
| **total** | **+20** |

**Net: −25 B of page 1.** Page 1 goes from **14 B free to ≈39 B**. Every other
message change is a case flip inside an existing literal and is **byte-neutral**,
because the phrase escapes deliberately exclude the leading letter and their
bodies already carry the reference's own case.

⚠️ These are *predictions from the symbol table*. The figure that counts comes
from `rm -rf build && make basic-reloc` and nothing else
([[measure-the-wall-from-clean]]).

### 3.3 One free fix

`err_msgtab[20]` is `dw err_unprintable`, but `err_verify`
([`basic/cload.asm:494`](../basic/cload.asm:494)) already reads `Verify error`.
Repointing the entry costs **0 B** and makes `ERROR 20` exact.

### 3.4 The full edit list

Byte-neutral case flips: `err_nofor`, `err_syntax`, `err_noret`, `err_data`,
`err_mem_arr`(✓ already), `err_line`(also reworded), `err_fp_divzero`,
`err_type_mismatch`, `err_out_of_str`, `err_cont` (→ `Can't CONTINUE`),
`err_no_resume` (→ `No RESUME`), `err_resume_noerr` (→ `RESUME without error`),
`err_unprintable`, `err_missing_operand`, `err_bad_filenum`, `err_input_pastend`,
`err_seq_only` (→ `Sequential I/O only`), `err_bad_filemode`, `brk_msg` (→ `Break`),
`msg_redo` (→ `?Redo from start`), `msg_extra` (→ `?Extra ignored`).

Sized changes: `err_line`, `err_overflow`/`err_linebuf_overflow`, `err_file_notopen`.

## 4. SCOPE — the 14 holes, and the sub-ROM opening

### 4.1 What they cost main-resident

Codes **12, 15, 18, 19, 50, 51, 53, 54, 56, 57, 60, 62, 63, 64** print
`unprintable error` on zerobas where the references print real text. Those are
codes zerobas **never raises**; they are reachable only via `ERROR n`.

Filling them means adding 14 strings — measured from the characterization table,
≈**227 B**. Against ≈39 B of post-carve page 1 that is not fundable, and it is a
different kind of work (each hole is "should zerobas raise this code at all?").

**This slice makes every message zerobas EMITS exact. It does not add messages
for codes zerobas never raises.**

### 4.2 D-MSGSUB — host them in the sub-ROM (a follow-on slice)

Asked at sign-off: *can't we put error messages in the sub-ROM?* **Yes**, and the
prior objection does not apply.

[`spec-basic-msgenc-carve.md:286`](spec-basic-msgenc-carve.md:286) Q4 resolved
"does the encoding belong in the sub-ROM?" with **no**, because the decoder runs
on the abort path, *"which must work when the sub-ROM is absent"* —
`subrom_absent_error` prints `err_subrom_absent`, an alias of `err_illegal_fn`.

That argument is about the **decoder** and about **one** message. For the 14
holes it is void, and the build output says why: **`tokenise` is itself a sub-ROM
page-0 tenant** (`check_tenant_closure --page0` lists it among the 13). With no
sub-ROM you cannot tokenise a line, so **`ERROR 12` can never be typed**. The
degradation Q4 guards against is *unreachable* for `ERROR n`-only codes. The one
message that must stay main-resident is `err_subrom_absent` itself — and its
alias target `err_illegal_fn_arr` is exactly what §3.1 keeps, in the low region.

**Capacity**: sub page 1 has **≈3084 B** free (last symbol `$73F4`); the holes
need ≈227 B.

**The constraint that does bite**: `print_string` `$4673` and `print_msg` `$7717`
are **main page 1**. A sub-ROM tenant may call only main **page 0 (`<$4000`)** or
BIOS — `check_tenant_closure --page1` enforces "no main-page-1 escape". So the
sub-ROM **cannot call main's printer**.

🎯 **Sign-off input: duplicating print code in the sub-ROM is permitted.** That
removes the marshalling entirely — no RAM staging buffer, no main-side copy-back
head. The sub-ROM carries its own decoder + phrase table + emitter (D-MSGENC
measured those at 44 B + 40 B) and writes via BIOS `CHPUT`, which is page 0 and
therefore *inside* the closure rule. Cost lands in sub page 1, where there is
~3 KB spare, and main pays only a dispatch stub. This tree already accepts
contract-forced duplication (the standing 473 B case), so it is in keeping.

⚠️ **Not folded into D-MSGEXACT.** D-MSGEXACT is self-funding (−25 B) and its
knives target wording and merge claims; bolting an inter-slot mechanism onto it
would give one slice two unrelated failure modes, and a marshalling path needs
its own predicted-RED/GREEN set. D-MSGEXACT's characterization table is precisely
the denominator D-MSGSUB needs, so the order is natural.

🎯 **The prize is larger than the 14 holes.** If the mechanism holds, *existing*
messages can migrate too. Page 1 is this tree's chronic wall and ~3 KB of sub
page 1 is idle — that is structural relief, not a one-off carve. Sizing that is
D-MSGSUB's job, not a claim made here.

### 4.3 `Verify error` — measured, and already exact

Measured 2026-08-02 on a real `CLOAD?` mismatch: the reference prints
**`Verify error`**, and zerobas's `err_verify` already reads exactly that. No
change needed; the `err_msgtab[20]` repoint of §3.3 is what makes `ERROR 20`
reach it. VG-8020 only — see the characterization doc for why the CF-3300 cannot
run that tape image.

## 5. Gate

Extend [`probes/basic/basic_probe_msgexact.py`](../probes/basic/basic_probe_msgexact.py)
with `--gate`: assert zb == both refs for every in-scope row, with the 14 holes
as a **named** expected-failure list (not a silent skip — a hole that starts
agreeing is itself a finding).

Oracle-locked on both references, `--repeat 2`, echo guard on all three sides.

### 5.1 Predicted RED — exact values, written before the build

25 rows, currently divergent, must go green:

`1 2 3 4 6 7 8 11 13 14 17 21 22 23 24 26 52 55 58 59 61` + `brk` `brk-run`
`redo` `extra`

### 5.2 Predicted GREEN — controls that must NOT move

`5 9 10 16 25` — the five already-exact messages. 🔴 **Two of them are load-bearing
controls of this slice's own design**, not decoration:

* **`5`** rides `err_illegal_fn_arr`, the string the merge keeps. If the merge
  goes wrong, 5 reddens.
* **`25`** rides `err_linebuf_overflow`, the string whose fall-through the slice
  breaks. If the break is done wrong, 25 reddens.

A control that cannot move its own subject is decoration
([[apparatus-is-part-of-the-measurement]]) — K4 and K5 below check that these two
*can*.

### 5.3 Knives — aimed at the JUSTIFICATION, not only the code

| # | cuts | target claim | predicted |
|---|---|---|---|
| K1 | revert only `err_syntax`'s `"S"`→`"s"` | "leading-letter flips are byte-neutral" | **build size IDENTICAL**, row 2 alone reddens |
| K2 | delete `fre_illegalfn_lc` outright after the merge | "it has no other callers" | **GREEN** — nothing references it |
| K3 | revert `fperr_to_err[3]` to `db 0` | "the merge preserves TRAPPING" — the S2b fix at [`interp.asm:690`](../basic/interp.asm:690) warns these paths exist *so `SQR(-1)` traps* | **RED** on `10 ON ERROR GOTO 100 : 20 B=SQR(-1)` |
| K4 | corrupt `err_illegal_fn_arr`'s leading byte | "row 5 is a live control" | **RED** on 5 |
| K5 | restore the `err_overflow` fall-through | "the +9 B was NECESSARY" | **RED** on 25 (`Line buffer Overflow`) |

🎯 **K5 is the one that can embarrass this spec.** If restoring the overlap leaves
both 6 and 25 green, the 9 bytes were not necessary and §3.2 is wrong. K1 is the
same shape for the byte-neutrality claim — the claim the whole funding argument
rests on.

⚠️ K2 is a knife **predicted GREEN**. A knife that reddens nothing is only a
finding if a red was predicted; here the green *is* the reading
([[knife-that-reddens-nothing-is-the-finding]]).

## 6. Blast radius

**154 hardcoded lowercase assertions across 27 files.** Heaviest:
`basic_probe_error_trap.py` 29 · `tests/test_msgenc.py` 21 ·
`basic_probe_arrays.py` 19 · `basic_probe_math_conv.py` 11 ·
`tests/test_str_compare.py` 10 · `diskbasic_probe_lof.py` 9.

Mechanical, but it is where a mistake hides: an assertion updated to match a
*wrong* new message would go green. Mitigation — update the probes from the
**measured characterization table**, never from what the build now prints.

🎯 **The `lst-comma` pin RETIRES**: delete it from `KNOWN_DIVERGE` in
[`probes/basic/basic_probe_lnblank.py`](../probes/basic/basic_probe_lnblank.py),
taking `lnblank-say-acceptance` to 108/108 with **6** pins.

Two docs need correcting with the fix (both currently state the withdrawn policy
as fact): [`error_acceptance.py:24`](../probes/basic/error_acceptance.py:24) and
the ERR table at [`spec-basic-error-handling.md:181`](spec-basic-error-handling.md:181)
— whose row 17 (`Can't continue`) is **measurably wrong** about the case.

## 7. Sign-off — answered 2026-08-02

| # | question | answer |
|---|---|---|
| 1 | scope of the 14 holes | → **D-MSGSUB**, §4.2. Not main-resident; a follow-on slice hosts them sub-side, with print-code duplication permitted. |
| 2 | `Verify error` wording | **measured** (§4.3) — already exact. |
| 3 | ERR 8 at +7 B | **in**. |

Outstanding: confirmation to begin editing `basic/` for D-MSGEXACT itself
(§3, §5, §6 — unaffected by the D-MSGSUB decision either way).
