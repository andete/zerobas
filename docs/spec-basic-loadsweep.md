# The gate D-RETLN asked for, and the nine sites D-EVSPDUP left behind

D-LOADSWEEP, 2026-08-19, on `main`, based on `3db99ae` (D-FORRET). Not a fidelity
slice — a **carve** plus the gate that makes the carve repeatable. No BASIC
behaviour changes and no reference row moves.

---

## 1. The item, filed 2026-08-02 and unfulfilled for seventeen days

D-RETLN carved 160 dead bytes of one shape — `call skip_spaces` immediately
followed by `ld a,(hl)`, where the callee already returns with `A = (hl)` — and
filed the **shape** rather than the bytes:

> The open question this leaves is not the 160 B (they are gone) but whether a
> gate should exist for the *shape*: a redundant-load sweep is a two-line
> matcher, and there are certainly other idioms like it. **That is the item.**

It also recorded why no existing gate can see it:

> 🔴 **THE DEAD-CODE GATE REPORTS 0 DEAD AND IS RIGHT.** These are reachable
> instructions computing a value already held — not unreachable code.

No sweep was written. **Seventeen days later D-EVSPDUP found the identical idiom
at `ev_sp` by hand**, while scouting 5 B for something else, and carved 72 B from
`basic/expr.asm`. That carve is what funded D-VPTRDOM and triggered
[`repricing-page1-2026-08-19.md`](repricing-page1-2026-08-19.md), whose §3.6
called this the highest-value open item in the roster.

🎯 **THE ITEM PREDICTED THE FIND THAT MADE IT URGENT.** It is the only open
entry that named, in advance, the class the next two slices would both trip over.

---

## 2. What the sweep found on its first run

`make redundant-load-check`, over **117 files / 61 410 lines / 2636 `call` sites**:

| callee | pointer | sites | bytes |
|---|---|---|---|
| `ev_sp` | `(ix+0)` | **9** | **27 B** |
| `bl_skip_spaces` | `(hl)` | 4 | 4 B |
| `edt_skip_spaces` | `(hl)` | 4 | 4 B |
| | | **17** | **35 B** |

🔴 **D-EVSPDUP'S CARVE WAS SCOPED TO ONE FILE, AND ITS HEADER SAID SO HONESTLY —
WHICH IS EXACTLY WHY IT READ AS COMPLETE.** It measured *"72 B in this file
alone"* and wrote the contract at `ev_sp` as *"24 CALL SITES DEPEND ON IT"*. The
tree has **36**. Six more sites sat in `basic/str-engine.asm` and three in
`basic/usr.asm`, untouched. **A count that is true of one file reads like a count
of the tree**, and the header is the first place anyone will look.

Two proven routines came back with **zero** dead loads — `skip_spaces`
(`sub/readdata.asm`) and `ldr_skipsp` (`sub/lineedit.asm`) — which is D-RETLN's
160 B carve still holding, measured rather than assumed.

---

## 3. 🔴 The price was right about the total and wrong about every byte's home

**Predicted: +27 B of main page 1.** Measured, clean `make basic-reloc`:

| region | before | after | delta |
|---|---|---|---|
| **page-0 low** | 5 B | **23 B** | **+18** |
| main page 1 | 41 B | 50 B | +9 |
| sub page 0 | 3295 B | 3299 B | +4 |
| sub page 1 | 1627 B | 1631 B | +4 |

The total is exactly the sweep's 35 B. **The distribution is not what was
priced.** The mistake was pricing by FILE: `str_eval_one` resolves to `$498F`,
main page 1, so `basic/str-engine.asm` was taken to be a page-1 file. It is not
one file's worth of anything — the six sites there live in `ev_str_arg`
(`$29F3`), `ev_f_instr` (`$2DAC`) and `ev_rel_str` (`$2E8F`), all **low region**.

🎯 **AND THE MISS LANDED IN THE CURRENCY THAT WAS SCARCEST.** The low region has
been the binding wall by a wide margin — it was **5 B**, and the standing note
against it reads *"5 B will not fund the next low-region slice — carve-scout
before assuming a budget."* It is now **23 B**. The slice bought four and a half
times more of the scarce thing than of the thing it was aiming at.

⚠️ This is the house rule *"ASK WHICH REGION EACH SITE LIVES IN — asked before
anything is priced"*, failed by sampling one symbol per file instead of resolving
each site. **The tool now does what the author did not**: every dead load is
resolved through its enclosing label to an address and a region, and the summary
is grouped by region, not by path. Without `build/basic-reloc.sym` it prints
`region UNRESOLVED` rather than guessing.

---

## 4. What it proves, and what it only flags

**PROVEN** — the tight skip loop, whose only exit is a conditional `ret` reached
with `A` already holding the byte at the pointer:

```
LABEL:  ld   a,(PTR)          ; PTR in {hl, ix+0, iy+0}
        cp   <imm>
        ret  nz|z
        inc  PTR
        jr   LABEL
```

For these, `call LABEL` followed immediately by `ld a,(PTR)` is dead — 1 B for
`(hl)`, 3 B for `(ix+0)`/`(iy+0)`. **This is the gating class.**

**CANDIDATE** — everything else that pattern-matches `call X` / `ld a,(ptr)`. 28
of them exist (`eval`, `var_name_key`, `fch_modes_ptr`, `tape_parse_name`, …).
They are printed with the reason they are not proven and **are not gating**: the
sweep does not guess at a routine's exits.

Three shapes are excluded deliberately and each is a defect someone could
otherwise ship:

* **a conditional `call cc,X`** — the reload is live on the not-taken path;
* **a pointer mismatch** — `ev_sp` leaves `(ix+0)`, so a following `ld a,(hl)` is
  a different value and must stay;
* **a label between the call and the load** — the load is then a jump target and
  another path reaches it with `A` unset. The matcher requires the load on the
  next *code* line and a label line fails the match, so these fall out
  structurally rather than by a rule anyone has to remember.

---

## 5. Falsification

🔴 **A GREEN SWEEP PROVES NOTHING UNTIL IT REDDENS**, and a sweep is exactly the
kind of tool that can report "clean" while measuring nothing.

**K-LS1** re-plants one dead load in each of two regions — after
`call ev_sp` in `ev_str_arg` (low) and in `ev_usr` (page 1). Predicted: exit 1,
two sites, one attributed `LOW` and one `page1`. Measured:

```
   ev_sp: 2 site(s), 6 B
       basic/str-engine.asm:576  (3 B)  LOW   $29F3
       basic/usr.asm:130  (3 B)  page1 $5347
   by REGION (resolved per site, not per file): LOW 3 B, page1 3 B
```

✅ **EXACT**, including the region split — the very distinction the author got
wrong by hand in §3, now made by the instrument.

The denominator is printed on every run (files, lines, `call` sites, and the
proven-routine roster), because a sweep that reports "clean" without saying what
it swept is a scope claim rather than a reading.

---

## 6. Gates

Seventeen gates, all green at the shipped tree:

| gate | result |
|---|---|
| `make redundant-load-check` | **0 dead loads** (the new gate, on itself) |
| `make unit-test` | **59/59** |
| `make deadcode` | 0 dead, both builds, allowlist still verified dead |
| `make audit-citations` | CLEAN |
| `make basic-reloc` | **23 B low** / **50 B page 1** / 3299 B sub p0 / 1631 B sub p1 |
| `make lnblank-say-acceptance` | **208/208** across all three sides |
| `make diskbasic-acceptance` | **34/34** verbs converged |
| `string` / `str-domain` | PASS — `basic/str-engine.asm` is where six of the nine sites were |
| `math` / `float` / `array` / `input` | PASS |
| `error` / `logicops` / `binfre` / `missing` | PASS |

⚠️ **THE FIRST RUN OF THIS BATTERY REPORTED `exit code 0` HAVING WRITTEN NO LOGS
AT ALL** — the session scratchpad was cleared underneath it, so every `>` target
vanished and the driver's status was reported as green before any log was read.
It was believed for one message. **`ls` the log before believing a driver's
return code**: an rc is a claim about a process, not about a measurement, and a
`set -e` driver that never ran its first command exits 0 just as happily as one
that ran all seventeen.

---

## 7. What is NOT claimed

* No BASIC-visible behaviour changes and **no reference row moves** — every one
  of the 17 deletions removes an instruction that recomputes a value the
  register already holds. The emulator gates above are regression, not oracle.
* The sweep still asserts nothing about a candidate's liveness on its own — see
  §8, where all 28 were read by hand and the verdicts written down.
* The sweep proves a SHAPE, not an intent. A future edit that gives `ev_sp` a
  second exit would keep the shape green while breaking all 36 call sites — the
  header at `ev_sp` says so, and that remains a comment, not a gate.


---

## 8. The 28 candidates, read — a MEASURED ZERO

The sweep defers candidates to a human. That deferral was taken the same day:
**all 28 sites across 14 callees were read, and every one is LIVE.** No further
carve exists in this class — a measured zero, not an absence of looking.

Two reasons account for all 28, and the split is the interesting part:

| verdict | callees | sites |
|---|---|---|
| **POINTER** — the callee RETURNS a computed pointer in HL | `fch_modes_ptr`, `pu_deref_body`, `ztrap_entry`, `tgt_desc_fix`, `gfx_pstk_addr`, `df_entptr` | **11** |
| **CLOBBER** — the callee leaves something else in A | `eval`, `var_name_key`, `tape_parse_name`, `parse_disk_fcb`, `cas_capture_name`, `print_crlf`, `check_vartype_num`, `eval_byte_arg` | **17** |

🎯 **THE `POINTER` CLASS IS THE EXACT INVERSE OF THE CARVE CLASS, AND IT LOOKS
IDENTICAL TO IT.** `call fch_modes_ptr` / `ld a,(hl)` matches the same two-line
pattern as `call ev_sp` / `ld a,(ix+0)` — but `fch_modes_ptr` *returns* `HL =
FCH_MODES + A`, so the load is not a reload of anything: it is **the dereference
the call exists to enable**. Deleting it would not save a byte, it would delete
the point of the call. Eleven of the 28 are this shape, and they can never be
dead *by construction*.

That is why the sweep proves a shape instead of pattern-matching one, and why
the candidate list is printed rather than acted on.

### 8.1 The verdicts are a CONTROL, not a suppression list

They live in [`tools/redundant-load-reviewed.txt`](../tools/redundant-load-reviewed.txt),
and the sweep **still prints every candidate site** — the file changes nothing
about what is reported. What it buys is that the zero stops being re-derived:

* a candidate callee **not** on file is reported `UNREVIEWED` and **fails** the
  gate — so a newly-introduced call site surfaces as a question instead of
  blending into a list of 28 already-dispositioned ones;
* an entry **on** file whose sites have all gone is reported `STALE` and **fails**
  — an entry that asserts nothing is how a control goes blind, which is the same
  argument `tools/deadcode-allow.txt` carries.

**Falsified both ways:**

| knife | cut | predicted | measured |
|---|---|---|---|
| **K-LS2** | drop `eval` from the file | `UNREVIEWED eval`, rc 1 | exactly that | ✅ EXACT |
| **K-LS3** | add an entry with no sites | `STALE bogus_routine`, rc 1 | exactly that | ✅ EXACT |

⚠️ **WHAT IT STILL DOES NOT PROVE.** A verdict on file is one human's reading of
a callee on one day, and nothing re-checks the *reasoning* — only that the callee
still has candidate sites. If `var_name_key` were someday changed to return
`A = (hl)`, the entry would keep asserting `CLOBBER` and the gate would stay
green over a real dead load. The tight-skip prover has no such hole, which is
the difference between the two halves of this tool and the reason the proven
class is the one that gates on bytes.