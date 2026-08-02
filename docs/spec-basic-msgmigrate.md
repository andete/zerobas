<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-MSGMIGRATE — migrating the EXISTING error messages into the sub-ROM tenant

**Status: implemented and measured 2026-08-02 — see §12.**

⚠️ **Sign-off changed the shape of the slice.** §11 Q1–Q4 were taken as
recommended; **Q5 was overruled — fix now, not file**. That turned out to be the
right call in a way this spec did not predict: the fix is what made a SIXTEENTH
string migratable and it *deleted* a branch rather than adding one, so it carved
16 B instead of costing 5. §6.4 and §12 carry the measurement.

Filed by [`docs/spec-basic-msgsub.md`](spec-basic-msgsub.md) §8, which built the
mechanism and sized the prize but deliberately did not widen into it.

Denominator: [`docs/msgexact-msx1-characterization.md`](msgexact-msx1-characterization.md)
§1/§2 (the verbatim text for all 41 ERR codes on both references). **This slice
changes no message text at all**, so that denominator is inherited, not re-taken —
and §7 explains why that makes the gate a pure control battery and the knives the
primary instrument.

---

## 1. The subject, and what the real work turned out to be

Main page 1 holds **252 B of message strings** (measured below) plus a 40 B phrase
table, against **22 B free**. Sub page 1 has **2740 B** idle. D-MSGSUB proved a
table-reached message migrates for **zero** main-side bytes: the `err_msgtab`
entry becomes `dw err_subhosted`, the string is deleted, the text moves into
`em_table`.

§8 named the follow-on's real work as *"which messages CANNOT move"*, because the
tenant is keyed on `ERRFLG` and a message can only migrate if **every** path that
prints it goes through `err_msgtab`. It listed eight strings as blocked on that
ground and proposed a 2 B-per-message second selector for them.

🎯 **THE ENUMERATION REFUTES THAT LIST, AND IN THE CHEAP DIRECTION.** §2 walks
every print site of every one of the nineteen strings. `err_msgtab` is not the
key — **`ERRFLG` is** — and `ERRFLG` is written before the print at almost every
direct site too:

* `rerr_sparse` opens with `ld a,(ERRFLG)` ([`basic/main.asm:349`](../basic/main.asm:349)).
  All five of the strings §8 called *"a different key"* are reached under an
  `ERRFLG` the code has just re-read. **Same key.**
* `raise_error_forced` writes `ld (ERRFLG),a` (A=22) before loading
  `err_resume_noerr` ([`basic/interp.asm:897`](../basic/interp.asm:897)).
* `ex_cont_no` writes `ld a,17 / ld (ERRFLG),a` before loading `err_cont`
  ([`basic/program.asm:998`](../basic/program.asm:998)) — D-DELETE's `dlt-cont`
  put that store there.
* `dl_overflow`'s 25-arm writes `ld (ERRFLG),a` (A=25) before loading
  `err_linebuf_overflow` ([`basic/program.asm:149`](../basic/program.asm:149)).

**No second selector is needed and none is specified.** Fifteen of the nineteen
strings migrate at zero main-side bytes. Four cannot, and §6 gives each one its
own reason — which are four *different* reasons, not one.

🎯 **AND THE SELECTOR CODE ITSELF BECOMES DELETABLE** (§4.3). Once all five sparse
strings point at `err_subhosted`, `rerr_sparse` and `rerr_sparse2` are two compare
chains whose every arm converges on `ld hl,err_subhosted / jp raise_error_hl` —
which is exactly what `rerr_unprintable` already is. 50 B of dispatch evaporates.
That was not in §8's sizing at all.

⚠️ **ONE §8 FIGURE IS CORRECTED HERE.** §8 and the TODO both describe the sparse
apparatus as low-region. It is not, and has not been since R1: `rerr_sparse` is at
**$7FAB**, `err_bad_filenum` at **$7FD0** — the whole S-FCH-2 block rode R1's
promotion into page 1 ([`basic/main.asm:275`](../basic/main.asm:275)). So this
slice relieves **page 1 only**; the low region's 23 B does not move. Measured from
`build/basic-reloc.sym`, not recalled.

---

## 2. The denominator — every print site of every page-1 message string

Enumerated mechanically over the non-comment text of `basic/*.asm` and `sub/*.asm`
(the script is `§2`'s own method: strip everything after `;`, then word-match each
label). Lengths and addresses read out of `build/basic-reloc.rom` +
`build/basic-reloc.sym` at HEAD `902d14d`, clean build.

| string | addr | B | print sites | `ERRFLG` correct at EVERY site? |
|---|---|---:|---|---|
| `err_type_mismatch` | $425D | 14 | `err_msgtab[13]` | ✅ 13 |
| `err_fp_divzero` | $4285 | 17 | `err_msgtab[11]` | ✅ 11 |
| `err_resume_noerr` | $4296 | 9 | `err_msgtab[22]`, `raise_error_forced` | ✅ 22 / 22 |
| `err_unprintable` | $4354 | 13 | `err_msgtab[23]`, `[14]` (non-CLEARPOOL) | — **pinned resident** |
| `err_line` | $442F | 22 | `err_msgtab[8]` | ✅ 8 |
| `err_verify` | $667B | 8 | `err_msgtab[20]`, `verify_error` | 🔴 **no** — see §6.3 |
| `brk_msg` | $769F | 6 | `do_break` (`print_string`) | 🔴 **no** — see §6.2 |
| `err_cont` | $7790 | 15 | `err_msgtab[17]`, `ex_cont_no` | ✅ 17 / 17 |
| `err_noret` | $79F9 | 14 | `err_msgtab[3]` | ✅ 3 |
| `err_nofor` | $7A07 | 10 | `err_msgtab[1]` | ✅ 1 |
| `err_data` | $7A47 | 7 | `err_msgtab[4]` | ✅ 4 |
| `err_missing_operand` | $7D8A | 16 | `err_msgtab[24]` | ✅ 24 |
| `err_input_pastend` | $7F60 | 15 | `rerr_sparse2` (55) | ✅ 55 |
| `err_seq_only` | $7F6F | 20 | `rerr_sparse2` (58) | ✅ 58 |
| `err_bad_filemode` | $7F83 | 10 | `rerr_sparse2` (61) | ✅ 61 |
| `err_linebuf_overflow` | $7F8D | 21 | `err_msgtab[25]`, `dl_overflow` 25-arm | ✅ 25 / 25 |
| `err_overflow` | $7FA2 | 9 | `err_msgtab[6]`, `dl_overflow` float arm | 🔴 **no** → ✅ **after §6.4's fix** |
| `err_bad_filenum` | $7FD0 | 12 | `rerr_sparse` (52) | ✅ 52 |
| `err_file_notopen` | $7FDC | 14 | `rerr_sparse` (59) | ✅ 59 |
| | | **252** | | |

**Migratable: 15 strings, 216 B. Blocked: 4 strings, 36 B.**

🎯 **AS BUILT: 16 strings, 225 B.** `err_overflow` joined them once §6.4's
defect was fixed — the sign-off overruled this spec's "file it" recommendation,
and the fix made both of that routine's arms `ERRFLG`-keyed.

⚠️ **THE ENUMERATION IS THE MEASUREMENT, AND IT DISAGREED WITH THE FILED LIST
TWICE.** §8 named `err_input_pastend`/`err_seq_only`/`err_bad_filemode`/
`err_bad_filenum`/`err_file_notopen` as blocked — they are not. And §8 did not
name `err_overflow` as blocked — it is, on one of its two arms. Assuming either
way would have been wrong in both directions, which is the same shape as
[[lnref-arming-list-slice]]'s finding.

### 2.1 The decoded text of each migrating string

Read out of the ROM through the phrase decoder, **not** transcribed from the `db`
lines and not from any published reference. These become plain (un-encoded)
strings sub-side, so this is what `sub/errmsg.asm` must spell:

| code | text | main B (encoded) | sub B (plain) |
|---:|---|---:|---:|
| 1 | `NEXT without FOR` | 10 | 17 |
| 3 | `RETURN without GOSUB` | 14 | 21 |
| 4 | `Out of DATA` | 7 | 12 |
| 8 | `Undefined line number` | 22 | 22 |
| 11 | `Division by zero` | 17 | 17 |
| 13 | `Type mismatch` | 14 | 14 |
| 17 | `Can't CONTINUE` | 15 | 15 |
| 22 | `RESUME without error` | 9 | 21 |
| 24 | `Missing operand` | 16 | 16 |
| 25 | `Line buffer overflow` | 21 | 21 |
| 52 | `Bad file number` | 12 | 16 |
| 55 | `Input past end` | 15 | 15 |
| 58 | `Sequential I/O only` | 20 | 20 |
| 59 | `File not OPEN` | 14 | 14 |
| 61 | `Bad file mode` | 10 | 14 |
| | | **216** | **255** |

---

## 3. What is being claimed, so the knives have something to cut

1. **`ERRFLG`, not `err_msgtab`, is the tenant's key**, and it is valid at every
   one of the fifteen migrating print sites (§2). *Cut: K2, K3.*
2. **Migration is text-neutral.** Every migrated code prints byte-identically
   before and after, on every path and in both run and direct mode. *Cut: the
   whole 53-row gate, which is why §7's predicted-RED set is empty.*
3. **`rerr_sparse`/`rerr_sparse2` become semantically identical to
   `rerr_unprintable`** once their five messages migrate, so deleting them is
   behaviour-preserving including the trap decision. *Cut: K4.*
4. **The absent-sub-ROM case degrades to `Unprintable error`, not to nothing**,
   for every migrated code — the same one-byte fall-through D-MSGSUB built.
   *Cut: K1, which measures it rather than arguing it.*
5. **`pm_sub`'s "only the ABORT path can reach me" precondition is retired by
   this slice, and paid for** (§4.5). *Cut: K5, which is aimed at the payment,
   not at the code.*

---

## 4. Design — the edit list

### 4.1 The fifteen table/pointer repoints — 0 B

| site | change | B |
|---|---|---:|
| `err_msgtab` 1, 3, 4, 8, 11, 13, 17, 22, 24, 25 | `dw <string>` → `dw err_subhosted` | 0 |
| `raise_error_forced` ([interp.asm:900](../basic/interp.asm:900)) | `ld hl,err_resume_noerr` → `ld hl,err_subhosted` | 0 |
| `ex_cont_no` ([program.asm:1000](../basic/program.asm:1000)) | `ld hl,err_cont` → `ld hl,err_subhosted` | 0 |
| `dl_overflow` 25-arm ([program.asm:150](../basic/program.asm:150)) | `ld hl,err_linebuf_overflow` → `ld hl,err_subhosted` | 0 |
| the 15 string bodies | **deleted** | **−216** |

🎯 **DELETING THE STRING MAKES A MISSED REPOINT A BUILD FAILURE.** Any `ld hl,` or
`dw` left pointing at a deleted label is an undefined symbol and pasmo exits 1.
So the "I forgot a site" failure mode cannot ship — which is why §7's knives aim
at the *keying* instead, the failure mode that assembles cleanly.

### 4.2 The five sparse repoints — 0 B, and they empty their own selector

`rerr_sparse`'s 52/59 arms and `rerr_sparse2`'s 55/58/61 arms each load a message
and `jp raise_error_hl`. Repointing all five at `err_subhosted` makes every arm
identical to the fall-through, which is `rerr_unprintable`.

### 4.3 Deleting the selectors — −50 B

| site | change | B |
|---|---|---:|
| `rerr_sparse` + `rsp_go` ([main.asm:348..366](../basic/main.asm:348)) | **deleted** | −23 |
| `rerr_sparse2` + `rsp2_go` ([missing.asm:600..612](../basic/missing.asm:600)) | **deleted** | −27 |
| `jp nc,rerr_sparse` ([interp.asm:803](../basic/interp.asm:803)) | → `jp nc,rerr_unprintable` | 0 |

⚠️ **THE TRAP DECISION IS WHAT MUST BE SHOWN UNCHANGED, NOT THE MESSAGE.** Both
selector arms end at `jp raise_error_hl`; so does `rerr_unprintable`. 52/59/55/58/61
therefore keep trapping into an armed `ON ERROR` handler exactly as D-NOTOPEN2
measured. `oo_fail_bfn` and `err_notopen_raise` are untouched — they enter through
`raise_error`, not through the selector.

Verified there is no other entry into either selector: the only referents of
`rerr_sparse`, `rerr_sparse2`, `rsp_go`, `rsp2_go` in `basic/`, `sub/`, `tools/`
and `tests/` are the ones listed above.

### 4.4 The phrase table — −15 B, and one more phrase dies than §8 predicted

| escape | users | after migration |
|---|---|---|
| `MSGESC_ERROR` (1) | `err_syntax`, `err_io`, `err_verify`, `err_resume_noerr`, `err_unprintable` | 4 remain → **keep** |
| `MSGESC_UTOF` (2) | `err_subscript`, `err_mem_arr`, `err_data`, `err_out_of_str` | 3 remain → **keep** |
| `MSGESC_ILLFN` (3) | `err_illegal_fn_arr` | 1 remains → **keep** |
| `MSGESC_WITHOUT` (4) | `err_resume_noerr`, `err_noret`, `err_nofor` | **all three migrate → DELETE** (−9 B) |
| `MSGESC_FILE` (5) | `err_bad_filenum`, `err_bad_filemode` | **both migrate → DELETE** (−6 B) |

§8 flagged `MSGESC_FILE`'s two users. `MSGESC_WITHOUT`'s three are the bonus, and
they are only visible from the enumeration.

Both dying escapes are the **top two** values, so `MSGESC_HI` drops 5 → 3 with no
renumbering of anything below. `MSGESC_SUB` stays **6**: the invariant
`MSGESC_SUB > MSGESC_HI` that [`tests/test_msgenc.py`](../tests/test_msgenc.py)
pins gains slack rather than losing it, and `pm_lit`'s `cp MSGESC_HI + 1` follows
the equate for free.

### 4.5 `pm_sub` becomes register-transparent — +8 B *(sign-off Q2)*

[`basic/program.asm:832`](../basic/program.asm:832)'s own header states the
precondition this slice retires:

> *"Safe at the one site that can reach it: only the ABORT path resolves a message
> containing MSGESC_SUB … Every other print_msg caller passes a main-resident
> string, which cannot contain this byte."*

After §4.1 that is false. Three sites reach `pm_sub` instead of one:

| reacher | via | what is live across it |
|---|---|---|
| `fre_abort_low` | abort path | nothing — SP reset, statement abandoned |
| `ex_cont_no` | `jp print_msg` | statement level; `exec`'s frame is discarded |
| `dl_overflow` | `jp print_msg` | `dispatch_line`'s caller (`repl`, or `mrg_storeline` on the ASCII LOAD/MERGE path) |

The reasoned argument that this is safe is genuinely available — `dispatch_line`
already performs a CALSLT of its own (`call tokenise`), so every caller in that
chain demonstrably survives one — and `mrg_storeline` holds nothing in BC/DE/IX
across its `call dispatch_line`.

**But the argument has to be re-derived by whoever adds the next `print_msg`
caller, and `print_msg_stopcr`'s documented contract ("clobbers A, plus the HL
walk") is *already* a lie today.** For 8 bytes it becomes true again:

```
pm_sub:         push    bc                  ; +1  NEW
                push    de                  ; +1  NEW
                push    ix                  ; +2  NEW
                push    hl
                ld      ix,SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_ERRMSG
                call    subrom_call
                pop     hl
                pop     ix                  ; +2  NEW  (POP does not touch flags)
                pop     de                  ; +1  NEW
                pop     bc                  ; +1  NEW
                ret     nc
                jr      pm_lp
```

⚠️ **The `pop`s must sit between `pop hl` and `ret nc`, and `pop` does not affect
flags** — the `CF` tested by `ret nc` is still `subrom_call`'s. That is the same
property the existing `pop hl` already relies on.

**Recommended: pay it.** Against a 273 B carve, 8 B buys a structural guarantee
instead of a four-caller audit that has to be redone on every future edit
([[refactor-inherits-clobber-contracts]]). §8's K5 is aimed at this decision and
**predicts it reddens nothing** — see §8.

### 4.6 The tenant — `sub/errmsg.asm`

`em_table` grows 14 → **29** rows; fifteen plain strings are appended. Nothing
else changes: no marshalling, no new index, no new file (so the `SUB_PARTS`
trap ([[makefile-subparts-stale-tenant]]) does not recur — `sub/errmsg.asm` is
already tracked at [`Makefile:191`](../Makefile:191); **re-verified, not assumed**).

⚠️ Two tenant comments become false and must be corrected in the same edit: the
`em_table` header's row-order note is fine, but the `em_bad_fat` block's remark
that *"61 `Bad file mode` is NOT here: zerobas RAISES it, so it is main-resident"*
is exactly what this slice reverses, and `em_unprintable`'s note about which codes
reach it needs 26..49/65..255 to stay accurate.

⚠️ [`tests/test_msgsub.py`](../tests/test_msgsub.py) bounds the table by *"the
table ends where the first target begins"*, taking `em_ill_direct` as the lowest
target. **The fifteen new rows must be appended to `em_table` and their strings
placed after it**, or that readout silently measures the wrong span.

### 4.7 Byte accounting — PREDICTIONS

⚠️ Predictions. Only `rm -rf build && make basic-reloc` counts
([[measure-the-wall-from-clean]]).

**Main page 1**

| item | predicted | AS BUILT |
|---|---:|---:|
| string bodies deleted (§2.1) | −216 (15) | **−225** (16, incl. `err_overflow`) |
| `rerr_sparse` + `rerr_sparse2` deleted (§4.3) | −50 | −50 |
| `MSGESC_WITHOUT` + `MSGESC_FILE` phrases deleted (§4.4) | −15 | −15 |
| `dl_overflow`'s branch collapses (§6.4) | — | **−7** |
| `pm_sub` register transparency (§4.5, Q2) | +8 | +8 |
| every repoint in §4.1/§4.2/§4.3 | 0 | 0 |
| **net** | **−273** | **−289** |

Predicted **295 B**, measured **311 B** — the 16 B difference is entirely §6.4's
fix, which was not in the prediction because this spec recommended deferring it.
Low region **23 B → 23 B**, unchanged (§1's correction: nothing here is
low-region).

**Sub page 1** (free at HEAD: **2740 B**, content ends $754C)

| item | predicted | AS BUILT |
|---|---:|---:|
| plain strings + NUL (§2.1) | 255 (15) | 264 (16) |
| `em_table` rows × 3 | 45 | 48 |
| **total** | **300** | **312** |

Predicted ≈2440 B free; measured **2428 B** (2740 → 2428). `em_table` is 30 rows.

### 4.8 Explicitly NOT in this slice

* **The four blocked strings** (§6). Each is filed with its own reason and its own
  price; none is fixed here.
* **`err_overflow`'s missing `ERRFLG` store** (§6.4). It is a real defect, it is
  filed, and fixing it needs an oracle reading this slice does not take.
* **Any low-region migration.** `err_subscript`/`err_redim`/`err_mem_arr`/
  `err_syntax`/`err_no_resume`/`err_too_complex`/`err_out_of_str`/`err_mem` are
  low-region, and `err_illegal_fn_arr` is pinned there (§6.1). Relieving the low
  wall is a different question with a different constraint set.

---

## 5. PRDEST — bounded, and deliberately NOT claimed as measured

Main's `pm_lit` prints through `pchar`, which honours `PRDEST`; the tenant prints
through `CHPUT`, which does not. On the abort path `fre_abort_low` zeroes `PRDEST`
first, so the two are indistinguishable — that is D-MSGSUB §4's claim 1, already
gated by `mid-ifc`.

The two new direct reachers do **not** pass through `fre_abort_low`:

* `ex_cont_no` runs as a statement under `repl`, which zeroes `PRDEST` at the top
  of every prompt iteration ([`basic/repl.asm:32`](../basic/repl.asm:32)).
* `dl_overflow` runs at line-**entry** time, before any statement executes.

🔴 **AND THAT IS WHERE THE HAZARD LIVES, SO SAY IT PROPERLY.** D-MSGSUB wrote two
rows into a spec *and* a denominator as its headline measurement, and they could
not go red because `PRINT#` restores `PRDEST` before the statement ends
([[gate-row-setup-can-expire]]). The same shape applies here: **there is no BASIC
program that can hold `PRDEST` non-zero across a `CONT` or across line entry**,
because the only writers restore it within their own statement. So this slice
states the condition as **bounded away by construction, not measured**, and adds
**no** gate row that pretends otherwise.

---

## 6. The four that cannot move — four different reasons

### 6.1 `err_unprintable` (13 B) — structurally pinned
`err_subhosted` is one byte whose fall-through neighbour must be this string; that
adjacency **is** the absent-sub-ROM degradation, and
[`tests/test_msgenc.py`](../tests/test_msgenc.py) pins it. Unchanged.

Its companion constraint also holds unchanged: **`err_illegal_fn_arr` stays
main-resident** because `err_subrom_absent` aliases it
([`basic/subromcall.asm:65`](../basic/subromcall.asm:65)) — the one message that
must survive an absent sub-ROM cannot be hosted in it. It is low-region and out of
this slice's scope anyway, but the alias is re-verified, not assumed.

### 6.2 `brk_msg` (6 B) — a different PRINTER, not a different key
`do_break` prints it with `call print_string`
([`basic/program.asm:671`](../basic/program.asm:671)). **`print_string` has no
escape decoder at all** — it is the raw CHPUT loop `pm_emit` itself calls for
phrases. A `MSGESC_SUB` byte there would be `pchar`'d as a literal $06. And
`Break` is not an error, so `ERRFLG` holds whatever the last error left.
Two independent blockers; migrating it needs a printer change, not a selector.

### 6.3 `err_verify` (8 B) — `verify_error` sets no `ERRFLG`
[`basic/cload.asm:492`](../basic/cload.asm:492) is `ld hl,err_verify / jp
print_msg` with no `ld (ERRFLG),a`. Adding one costs 5 B to save 8 — a net 3 B
that is not worth taking blind, because it also makes `PRINT ERR` read 20 after a
`CLOAD?` mismatch, which is **an observable change with no oracle reading behind
it**. Filed, not fixed.

### 6.4 `err_overflow` (9 B) — a SPLIT, a latent defect, and (per sign-off) FIXED

`err_msgtab[6]` reaches it under `ERRFLG` = 6 ✅. `dl_overflow`'s **float arm**
(`TKOVF` = 1) reached it with **no `ERRFLG` store at all** — the `ld (ERRFLG),a`
in that routine sat inside the 25-branch only.

🔴 **So `PRINT ERR` after a float-literal overflow read whatever the previous
error left**, while the same routine's sibling arm had been deliberately fixed to
read 25 (*"ERRFLG is still set so PRINT ERR reads 25, as measured"*).

**MEASURED 2026-08-02**, boot-per-case on both references and zerobas, five rows
because one row could not have separated "the machine reads 0 here" from "the
readout cannot report anything else":

| row | drive | vg8020 | cf3300 | zerobas |
|---|---|---|---|---|
| `fovf-lit` | `20 A=1E99` → `PRINT ERR` | **6** | **6** | 🔴 **0** |
| `fovf-big` | `20 A=1E999` → `PRINT ERR` | 6 | 6 | 🔴 0 |
| `fovf-len` | sibling arm (`0#`×40) → `PRINT ERR` | 25 | 25 | 25 ✅ |
| `fovf-ctl` | `20 A=1E9` (no error) → `PRINT ERR` | 0 | 0 | 0 |
| `fovf-arm` | `ERROR 6` → `PRINT ERR` | 6 | 6 | 6 |
| — | the MESSAGE printed | `Overflow` | `Overflow` | `Overflow` ✅ |

`fovf-ctl` makes zerobas's `0` a real absence rather than the readout's floor;
`fovf-arm` proves the readout can report 6; `fovf-len` is the sibling arm, which
is what makes the asymmetry legible instead of looking like a whole-routine
property. **The message was always right, which is exactly why nothing noticed.**

⚠️ `msg-len` (the 90-character line's own screen tail) returned `None` on **all
three sides** — the echo match fails because the line wraps across screen rows.
Recorded as *the readout could not see it*, not as *the three sides agree*; that
arm's reading is carried by `fovf-len` and by `linemax-acceptance`.

**THE FIX IS A CARVE, NOT A COST.** `TKOVF`'s contract is already *"the reject
reason IS the ERR code"* — [`basic/tokenise.inc`](../basic/tokenise.inc)'s
`tke_fits` says so in those words and stores **25**. The float arm was the one
arm not honouring it. Storing **6** there instead of a bare flag
([`sub/tkfloat.asm`](../sub/tkfloat.asm) `tkf_overflow`) makes both arms
symmetric, so `dl_overflow`'s whole branch collapses:

```
                ld      a,(TKOVF)
                ld      (ERRFLG),a          ; the reject reason IS the ERR code
                ld      hl,err_subhosted    ; 6 -> em_overflow, 25 -> em_linebuf_overflow
                jp      print_msg
```

−7 B of code, and **only then** is `err_overflow` migratable at all (−9 B more).
Every other `TKOVF` reader is a nonzero test (`or a`), and `tokenise` zeroes it at
entry, so 6 is safe everywhere. `tests/test_float.py`'s `TKOVF == 1` expectation
was **stale, not broken**, and is updated with the reason.

## 7. Gate

`probes/basic/basic_probe_msgexact.py --gate`, currently **50/50, zero holes**.
Every one of the fifteen migrating codes already has an asserting row in the walk
(1, 3, 4, 8, 11, 13, 17, 22, 24, 25, 52, 55, 58, 59, 61) — verified against
`REF_TEXT`, not assumed.

### 7.1 The predicted sets, locked BEFORE the build

**Derived from the EDIT LIST (§4), not the scope list**
([[predicted-red-set-must-not-inherit-scope]]). The edit list is: fifteen pointer
operands, fifteen deleted strings, two deleted selectors, two deleted phrases, one
`jp` target, one `push`/`pop` fence, and fifteen tenant rows. **Not one of those
changes any byte of any message.**

```
MSGMIGRATE_PREDICT_RED   = frozenset()          # EMPTY
MSGMIGRATE_PREDICT_GREEN = every row in the gate, all 53
```

🔴 **AN EMPTY PREDICTED-RED SET IS A CLAIM, NOT AN ABSENCE, AND IT MAKES THE GATE
A PURE CONTROL BATTERY** ([[knife-that-reddens-nothing-is-the-finding]]). A green
gate here does not say "the migration happened" — it says "nothing broke". The
rows that say the migration *happened* do not exist in the readout at all; that is
what §8's knives are for, and why they are this slice's primary instrument rather
than its afterthought.

### 7.2 Three NEW rows — the direct paths the walk cannot see

`ERROR n` always enters through `raise_error` → `err_msgtab`. The walk therefore
exercises the **table** path for every code and the **direct** path for none. A
repoint that assembles cleanly but is keyed wrong (`ex_cont_no` storing the wrong
`ERRFLG`, say) would be **invisible to all 50 existing rows** — which is exactly
the [[readout-blind-to-its-own-subject]] shape.

Added to `EXTRA`, each asserting the exact text:

| row | drive | asserts | the site it is the ONLY witness for |
|---|---|---|---|
| `cont-bare` | `CONT` on a fresh machine | `Can't CONTINUE` | `ex_cont_no`'s `ERRFLG` := 17 |
| `res-noerr` | `10 RESUME` + `RUN` | `RESUME without error in 10` | `raise_error_forced`'s `ERRFLG` := 22 |
| `ovf-line` | `20 A=` + `"0#"*40` | `Line buffer overflow` | `dl_overflow`'s 25-arm `ERRFLG` := 25 |
| `sparse-trap` | `ON ERROR GOTO` + `ERROR 52` | `T 52|No RESUME in 40` | the **trap decision** for an out-of-dense code (added mid-slice, see below) |

`ovf-line`'s shape is lifted from
[`probes/basic/basic_probe_linemax.py:238`](../probes/basic/basic_probe_linemax.py:238)'s
`code-over`, which is the measured way to make the crunched body exceed
`TOKMAX_BODY` (float literals *expand* under crunching).

The first three are predicted **GREEN**, and all three predicted to go **RED under
K2** — which is what makes them rows rather than decoration.

🎯 **`sparse-trap` WAS ADDED MID-SLICE, AND SAYING SO MATTERS.** It is not part of
the 53-row prediction above; it was added when K4 was being aimed and it became
clear that **deleting `rerr_sparse`/`rerr_sparse2` is a change to the TRAP
DECISION, not to a message** (§4.3) — and that every other row in the file
*aborts*, so nothing covered it. It was green before and after, so it changes no
verdict; but a row added mid-slice and then counted in a "before" figure would be
a retro-fitted prediction. The gate is **53/53 predicted, 54/54 measured**, and
the extra row is this one.

### 7.3 The load-bearing controls

Rows that must stay green and whose greenness carries a specific claim:

| row | claim it guards |
|---|---|
| 5 (`Illegal function call`) | `err_illegal_fn_arr` still main-resident (§6.1) |
| 23 (`Unprintable error`) | the pinned fall-through neighbour is intact (§6.1) |
| 6 (`Overflow`) | the string §6.4 held back is still reachable on both arms |
| 20 (`Verify error`) | §6.3's held-back string, still reachable from the table |
| `brk`, `brk-run` | `brk_msg` still prints through the un-decoded `print_string` (§6.2) |
| 26 | D-MSGSUB's live tenant-fallback control, now carrying 29 rows in front of it |
| `mid-ifc` | the one row that actually sets `PRDEST` — and it rides a **resident** message, so it must stay green (§5) |

⚠️ **Can these controls move their own subject?** 5, 23, 6, 20 and `brk` all ride
strings this slice does **not** touch, so a green reading from them is compatible
with the migration being entirely broken. They are controls for the *unchanged*
half, and nothing more — stating that rather than letting five green rows imply a
verdict they cannot support ([[one-row-cannot-separate-two-rules]]). **26 is the
only pre-existing row that rides the mechanism itself**, and §7.2's three are the
only rows that ride the direct paths.

---

## 8. Knives — aimed at the JUSTIFICATION (MEASURED)

Scored by a runner that **fails loud, never toward "nothing to see"**
([[knife-runner-false-negatives]]): every cut must change the source *and* change
at least one built ROM before the gate's verdict counts as a reading at all. A cut
leaving both ROMs byte-identical is reported **DID-NOT-HAPPEN**, not "reddened
nothing" — the distinction that caught D-MSGSUB's missing `SUB_PARTS` entry. Every
revert is against the file the runner cut, and both ROMs are re-hashed against the
pre-cut baseline afterwards (all five: **CLEAN**).

| # | cut | aimed at | predicted | measured |
|---|---|---|---|---|
| **K1** | `POKE &HF107,0` (no rebuild) | claim 4: degradation, not silence | all migrated codes → `Unprintable error`; resident ones unchanged | ✅ **9/9 — after being RE-AIMED, see below** |
| **K2** | `ex_cont_no`'s `ld a,17` → `ld a,99` | claim 1: `ERRFLG` is right at every DIRECT site | `cont-bare` RED, code 17 GREEN | ✅ **exact** — `cont-bare` the only red row |
| **K3** | drop `em_table`'s row for 61 | the tenant answers each sparse code individually | 61 RED, 52/55/58/59 GREEN | ✅ **exact**; and `build/sub.rom` moved, so `SUB_PARTS` is live |
| **K4** | `rerr_unprintable` → `jp ra_abort` (skip the trap check) | claim 3: the selector deletion preserves the TRAP decision | `sparse-trap` **and** `hole-trap` RED | 🔴 **HALF REFUTED — `hole-trap` stayed GREEN** |
| **K5** | build **without** the `pm_sub` fence | **the payment**, not the code | **nothing reddens** | ✅ ROM moved (−8 B), gate **54/54 ALL PASS** |

🔴 **K1'S OWN SETUP DISABLED THE MECHANISM THAT DELIVERS ITS SUBJECT.** The first
run typed `ERROR n` *after* the POKE and read `Illegal function call` on **all
nine rows — including code 23**, a main-resident string with no business moving.
The control is what said so. `tokenise` is itself a sub-ROM page-0 tenant, so with
`SUBSLOT_OK` cleared the machine cannot crunch the line at all and answers
`err_subrom_absent` before any message resolves. Re-aimed to **store** the line
and POKE while the sub-ROM is still there, then `RUN` (which `dispatch_line`
recognises by name *before* `tokenise`), it reads 9/9 — and that ordering is
exactly the reachable case the design was built for: an already-tokenised program
on a sub-ROM-less machine. Same family as [[gate-row-setup-can-expire]], one step
further out: not the setup expiring, the setup **removing the delivery path**.

🔴 **K4 REFUTED HALF ITS OWN PREDICTION, AND THAT IS THE READING.** `sparse-trap`
went red (`Bad file number in 20` where the handler's output belongs), so the row
does measure the trap. `hole-trap` — predicted red on the same reasoning — stayed
**green**, because **code 12 has a DENSE `err_msgtab` entry and never passes
through `rerr_unprintable` at all**. The two rows reach the trap decision by
different routes, and one row could not have said so
([[one-row-cannot-separate-two-rules]]). The practical consequence: `hole-trap`
was never a control for the sparse routing, which is what I would have assumed.

✅ **K5 CONFIRMED THE HONEST FRAMING OF THE 8 B.** The cut is real (the ROM moved)
and nothing reddened, exactly as predicted up front. The fence is a **structural
guarantee retiring a precondition**, not a measured bug repair, and recording it
the other way round would be a false claim
([[knife-that-reddens-nothing-is-the-finding]]).

## 9. Blast radius

Bounded by the enumeration, not by intuition:

* **Every reader of the fifteen strings is in §2's table**, and each is edited or
  deleted. Anything missed is an undefined symbol (§4.1).
* **`print_msg` callers**: twelve sites. Nine pass strings this slice does not
  touch (`err_io`, `err_verify`, the two `INPUT` notes, two other tape messages,
  `err_subrom_absent`). Three reach `pm_sub` (§4.5's table).
  🔴 **AND THERE IS A FOURTH THAT THIS ENUMERATION STRUCTURALLY COULD NOT FIND.**
  `dispatch_line`'s line-number-out-of-range arm (ERR 2) reaches `print_msg` by
  `jr dl_ovf_report` — it never names `print_msg`, so a grep for
  `jp|call|jr .*print_msg` cannot see it. The **build** found it, by §4.1's own
  property: the label vanished with the collapsed branch. It passes `err_syntax`,
  a resident low-region string, so it does not reach `pm_sub` today — but it would
  have, silently, if `err_syntax` were ever migrated. **An indirect reacher cannot
  be enumerated by naming the callee**, and that is an argument for §4.5's fence
  that this spec did not have when it recommended paying for it.
* **`raise_error_hl` callers**: three, two of which are the deleted selectors.
  After this slice it is reached from `raise_error`'s fall-through and
  `rerr_unprintable` only — strictly simpler.
* **`tests/test_msgenc.py`** loses fifteen entries from its label→text dict and
  two phrases from its table read. 🔴 **That makes it WEAKER, and the text must
  not become unpinned in the handover** — every migrated string moves into
  `tests/test_msgsub.py`'s `EXPECT` dict with its exact text, so the count of
  pinned messages does not drop. This is the one place a green corpus could hide
  a lost assertion.
* **`sysvars.inc`**: `MSGESC_HI` 5 → 3; the two dead escape equates removed.
* **Dead-code gate**: deleting two routines and two phrases must leave 0/0 on both
  builds. Any residue names itself.

---

## 10. Corpus after the change

The full list, unabridged: `make unit-test` 56/56 · `deadcode` 0/0 both builds ·
`msgexact --gate` **53/53** · `msgexact --relock` · `lnblank-acceptance REPEAT=2`
530/530 allowlist EMPTY · `lnblank-say-acceptance` 108/108, 6 pins ·
`lnblank-echo` · `logicops` · `float` · `array-acceptance` 151/151 · `arrdim` ·
`clearpool` · `badfnum` · `lof` · `chancost-characterize` · `linemax` ·
`sysvarsweep` · `error-trap-acceptance` · `error-acceptance` · `abort-acceptance` ·
`string-acceptance` · `str-domain-acceptance` · `math-acceptance` ·
`input-acceptance` · `direct-ctrl-acceptance` · `kwsweep` · `stop`/`strig`/`key`-trap ·
`fat-error-acceptance` · `diskbasic-acceptance` · `bdos-acceptance` ·
`subrom-acceptance`.

Standing and NOT caused by this work: `tools/audit_citations.py`'s 2 gating
findings (`basic/fat.asm`, `basic/missing.asm`); `lnblank-echo`'s `dec-eol`/
`dec-eolctl` MANGLED on all three sides (non-gating, exit 0).

⚠️ `error-acceptance`, `error-trap-acceptance`, `abort-acceptance`, `linemax` and
`badfnum`/`lof` all read message text and all cross migrated codes. They are the
breadth this slice's own gate does not have, and a red row there is a finding
about the migration, not about them.

---

## 11. Sign-off — questions that change what gets built

| # | question | recommendation |
|---|---|---|
| **1** | **Migrate all fifteen?** After this, an absent sub-ROM prints `Unprintable error` for nearly every error the machine can raise. K1 measures it. The counter-argument: without the sub-ROM `tokenise` is gone, so the machine cannot accept a typed line at all — the loss is bounded to a tokenised program arriving from tape/disk, and `err_subrom_absent` itself still prints (§6.1). | **Yes, all fifteen.** One mechanism, one gate; splitting doubles a very expensive corpus run for no new reading. |
| **2** | **Pay 8 B for `pm_sub` register transparency (§4.5)?** Or keep the four-caller audit and document the widened contract? | **Pay it.** 273 B vs 265 B is not a difference; a lie in `print_msg_stopcr`'s contract is. K5 predicts it reddens nothing and says so up front. |
| **3** | **Delete `MSGESC_WITHOUT` and `MSGESC_FILE` (§4.4), dropping `MSGESC_HI` to 3?** −15 B; both are the top two values so nothing renumbers. | **Yes.** A phrase with no users is dead data the dead-code gate cannot see. |
| **4** | **Delete `rerr_sparse`/`rerr_sparse2` outright (§4.3)** rather than leaving them as a no-op chain? −50 B, and it removes S-FCH-2's dispatch entirely. | **Yes.** K4 falsifies the redundancy claim by construction. |
| **5** | **`err_overflow`'s missing `ERRFLG` store (§6.4)** — file it, or take the oracle reading now and fold the fix in? | recommended **file it**; 🔴 **OVERRULED at sign-off: fix now.** The right call — the reading took one probe run, the fix *deleted* a branch instead of adding one, and it unlocked a sixteenth string. Recommending deferral would have left 16 B and a live `PRINT ERR` defect on the table. |

---

## 12. The measurement

### 12.1 Walls — clean `rm -rf build && make basic-reloc`

| | HEAD `902d14d` | as built | predicted |
|---|---:|---:|---:|
| main page 1 free | 22 B | **311 B** | 295 B (before Q5 was overruled) |
| main page-0 low free | 23 B | **23 B** | 23 B ✅ |
| sub page 1 free | 2740 B | **2428 B** | ≈2440 B |
| sub page 0 free | 3913 B | 3913 B | untouched ✅ |

🎯 **A 289 B CARVE OF THE TREE'S CHRONIC WALL**, from 22 B free to 311 B — the
largest single relief page 1 has had. 16 B of it is §6.4's fix, which this spec
recommended deferring; the sign-off's overrule is what bought it.

### 12.2 Gate

`basic_probe_msgexact.py --gate`: **54/54, zero holes** (53 predicted + the
mid-slice `sparse-trap`). Predicted RED **∅**, measured RED **∅** — and §7.1 is
why that is a claim rather than a result. The three direct-path rows return real
payloads, checked by reading them rather than trusting the verdict:

```
cont-bare | Can't CONTINUE               res-noerr | RESUME without error in 10
ovf-line  | Line buffer overflow         sparse-trap | T 52|No RESUME in 40
```

### 12.3 Two defects found in apparatus, neither in the migration

🔴 **The host unit-test harness's page-1 island borrowed the caller's MEMORY but
not its TRAPS.** `tests/msxtest.py`'s `subrom_call` bridge built the page-1
sub-ROM image over a copy of the caller's low region and BIOS, then set
`sub1.traps = {}` — so a tenant's `call CHPUT` executed whatever bytes sat at
$00A2 instead of the test's capture hook. It surfaced as a 2-million-step runaway
at PC=$1FE4 in `test_str_compare.py`, a string test, because `errmsg_tenant` is
the **first page-1 tenant whose whole job is a BIOS call** and nothing reached it
from a unit test until ordinary error messages became sub-hosted. Fixed by
inheriting the caller's traps for the borrowed range only (`a < 0x4000`); a trap
on a `$4000..$7FFF` address belongs to main's page 1, which is exactly what the
island switches out.

⚠️ **`tests/test_float.py`'s `TKOVF == 1` was a STALE EXPECTATION, not a
regression** — the same shape as D-MSGEXACT's `ifc.instr.*` pair. It is updated
with the reason and a named constant rather than a bare `6`.

### 12.4 Corpus — all green

36 targets, every one exit 0. The pinned counts, checked rather than assumed:

| | |
|---|---|
| `make unit-test` | **56/56** |
| dead code, both builds | **0 dead, 0 allowlisted (main) / 1 (sub)** |
| `msgexact --gate` | **54/54**, zero holes |
| `msgexact --relock` | **all 41 locked reference values reproduce on the machines** |
| `lnblank-acceptance REPEAT=2` | **530/530**, allowlist **EMPTY** |
| `lnblank-say-acceptance` | **108/108**, 6 pinned |
| `lnblank-echo` | every gating payload typed verbatim on every side |
| `array-acceptance` | **151/151** |
| `logicops-acceptance` | **193/193** |

plus `error` · `error-trap` · `abort` · `linemax` · `arrdim` · `clearpool` ·
`float` · `math` · `string` · `str-domain` · `input` · `direct-ctrl` · `badfnum` ·
`lof` · `chancost-characterize` · `kwsweep` · `sysvarsweep` · `missing` · `width` ·
`stop`/`strig`/`key`-trap · `time` · `intarg` · `binfre` · `cursor` ·
`fat-error` · `subrom` · `diskbasic` · `bdos`.

⚠️ `--relock` matters more than usual here: it re-measures **both references** and
diffs them against `REF_TEXT`. This slice moved sixteen messages between ROMs, so
a green `--gate` alone would only say zerobas agrees with a locked table; `--relock`
says the locked table still agrees with the machines.

Standing and NOT caused by this work, verified identical: `audit_citations.py`'s
two gating findings (`basic/fat.asm:81`, `basic/missing.asm:1`); `lnblank-echo`'s
`dec-eol`/`dec-eolctl` MANGLED on all three sides (non-gating, exit 0).

### 12.5 What is left main-resident, and why

`err_unprintable` (13 B, the pinned fall-through), `brk_msg` (6 B, printed by
`print_string` which has **no escape decoder at all**), `err_verify` (8 B,
`verify_error` sets no `ERRFLG`) — 27 B, plus `err_subhosted`'s 1 B marker.
`err_illegal_fn_arr` stays low-region, as `err_subrom_absent`'s alias target, and
K1 measured that it still prints when the sub-ROM is gone.

