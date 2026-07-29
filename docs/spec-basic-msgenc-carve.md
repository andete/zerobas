<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# D-MSGENC — phrase-escape message encoding, as the S-FCH-2 funding carve

Status: **SPEC, NOT BUILT.** Every byte count below §3 is ARITHMETIC over the
measured corpus, not a measurement of a build. This arc has now been wrong about
a cost three times (8× too big, then "the cost was SITING", then 77 B → 45 B on
an apparatus bug), so nothing here is final until §6's cost probe is built.

Scouted 2026-07-29 against `860d1bc`, tree clean and green.

## 1. What this is for

[`docs/spec-basic-filechan-alloc.md`](spec-basic-filechan-alloc.md) §5c leaves
S-FCH-2 (ERR 52 / ERR 59) **26 B over budget** — 20 B of page 1, and 15 B of low
region against 9 B free. ERR 5 is landed and free (`61e3a48`); the remainder is
measured and needs a carve. §5c's own verdict: *moving more code down only trades
one wall for the other — only a carve closes it.*

Measured walls, clean `rm -rf build && make basic-reloc` at `860d1bc`:

```
low region ($2812-$3FFF):  9 B free
page 1     ($4000-$7FFF):  0 B free   <- $8000 exactly
```

## 2. Why the conventional carves are closed at this size — MEASURED

Both scouts were run before this design was written, per
[[carve-scout-before-proposing]].

* **`python3 tools/clone_scout.py --min 20`** — ONE candidate group, **21 B**
  (`ev_and_lp`/`ev_idiv_lp`/`ev_mod_lp`/`ev_or_lp`/`ev_xor_lp` in
  [`basic/expr.asm`](../basic/expr.asm)). Below the 26 B requirement on its own.
  The structural-clone frontier is effectively exhausted.

* **Whole-file eviction** — every mid-size page-1 file fails **page-0** tenancy
  outright: `carve_scout --files ... --entries ...` reports 300+ callees reached
  *through* resident main page 1 for both `basic/sound.asm` and `basic/list.asm`
  (`ex_sound -> eval -> ...` and `ex_list -> list_walk -> pchar -> ...` all land
  in the BIOS). Their **page-1** tenancy frontiers are all live work:

  | file | movable | frontier to dissolve |
  |---|---|---|
  | `basic/list.asm` | 102 B | `exec_stmt` 29, `pchar` 17, `print_crlf` 10, `print_string` 9 |
  | `basic/sound.asm` | 88 B | `exec_stmt` 29, `raise_error` 26, `eval` 19, `stmt_error` 14, `get_byte_arg` 9, `skip_spaces` 7 |
  | `basic/clear.asm` | 68 B | `exec_stmt` 29, `clear_vars` 19, `eval` 19, +4 more |
  | `basic/time.asm` | 58 B | `str_eval_one` 65, `exec_stmt` 29, `raise_error` 26, `fp_runtime_error` 25 |

  Dissolving `eval`/`exec_stmt`/`raise_error` to buy 26 B is disproportionate
  surgery under the interpreter's hottest gates.

**`clone_scout`'s own docstring names the blind spot that decides this slice:**
it finds only structurally identical *label blocks*, and *"does not see ...
duplicated DATA."* The remaining redundancy in page 1 is message text.

## 3. The corpus — MEASURED from `build/basic-reloc.sym`

25 distinct resident message strings. Aliases (`err_stack`, `err_prog_mem`,
`err_subrom_absent`) collapse onto their targets and are **already** deduped
under `IF ROM_BASE < $4000`; exact-duplicate sharing is fully harvested.

| region | strings | bytes |
|---|---|---|
| page 1 | 14 | **254** |
| low region | 11 | **212** (after the existing `Line buffer `→`overflow` fall-through) |

⚠️ That low-region figure is **corrected**. A naive per-label sum reads 223 B
because [`basic/main.asm:117`](../basic/main.asm:117) already suffix-shares
`err_linebuf_overflow` into `err_overflow` — 11 B that a source-text scan
double-counts. **A byte already saved is not a byte available to save again.**

## 4. The design

### 4.1 Phrase escapes

Message bytes `$01..$04` become escapes indexing a table of NUL-terminated
phrases; everything `>= $20` is a literal. Chosen by greedy search over every
substring occurring twice or more:

| esc | phrase | len+NUL |
|---|---|---|
| `$01` | `" error"` | 7 |
| `$02` | `"ut of "` | 8 |
| `$03` | `"llegal function call"` | 21 |
| `$04` | `" without"` | 9 |
| | **phrase table** | **44 B** |

⚠️ **`$02` and `$03` deliberately drop the leading letter.** That makes
`Out of`/`out of` and `Illegal`/`illegal` share a single entry with **no
case-fold flag in the decoder** — [arrays §9.5's](spec-basic-arrays-slice3-strings.md)
deliberate capitalisation split survives untouched, and PROVENANCE §851's
lowercase-strings policy is unaffected. A case-folding variant was costed too and
scores only 84 B vs 79 B gross: **not worth the decoder.**

### 4.2 Implicit CRLF

Every message currently bakes `,13,10,0`. The decoder emits the CRLF itself, so
each message drops 2 B (the NUL stays as the terminator). 25 messages = **50 B**,
and it is what retires `print_string_stopcr` (§4.3).

### 4.3 The decoder — and the one thing that must NOT change

🔴 **The escape check CANNOT go into `print_string`.** `print_string` also
carries **user-controlled data**: `DETOKBUF` (LIST output, 3 sites), `NUMBUF`
(5 sites), `FOUTBUF` (2 sites). A `CHR$(1)` inside a LISTed string literal would
expand a phrase into the user's program text. Messages get their **own entry**;
`print_string` is untouched and still emits the phrases themselves.

Run mode and direct mode already split at
[`basic/arrays.asm:152`](../basic/arrays.asm:152) (`DIRECTF` picks
`print_string` vs `print_string_stopcr` *before* printing, so `print_in_lineno`
can append `" in <line>"`). With an implicit CRLF that split gets simpler: the
body-only routine is the primitive and the CRLF is the wrapper.

```
print_msg_stopcr:                       ; run mode: body only
pm_lp:          ld      a,(hl)
                inc     hl
                or      a
                ret     z
                cp      5                   ; $01..$04 -> phrase
                jr      nc,pm_lit
                push    hl
                ld      hl,phrase_tab
                dec     a
                jr      z,pm_emit
                ld      b,a
pm_skip:        ld      a,(hl)              ; skip B whole phrases
                inc     hl
                or      a
                jr      nz,pm_skip
                djnz    pm_skip
pm_emit:        call    print_string        ; phrases are plain NUL-terminated
                pop     hl
                jr      pm_lp
pm_lit:         call    pchar
                jr      pm_lp

print_msg:      call    print_msg_stopcr    ; direct mode: body + CRLF
                jp      print_crlf
```

**34 B + 6 B = 40 B**, replacing `print_string_stopcr` (**10 B**, measured at
`$77F5`). Net decoder cost **+30 B**. `pchar` preserves every register, so
`print_msg` inherits `print_string`'s clobber contract (**A**, plus the HL walk)
— which §7/Q3 makes a gate assertion rather than a claim.

### 4.4 What each message becomes — ARITHMETIC over §3's measured corpus

Page 1, `254 -> 156`, **frees 98 B**:

| label | now | enc | encoded form |
|---|---|---|---|
| `err_illegal_fn` | 24 | 3 | `i\03` |
| `err_resume_noerr` | 23 | 9 | `resume\04\01` |
| `err_noret` | 23 | 14 | `return\04 gosub` |
| `err_unprintable` | 20 | 13 | `unprintable\01` |
| `err_nofor` | 19 | 10 | `next\04 for` |
| `err_fp_divzero` | 19 | 17 | `division by zero` |
| `err_missing_operand` | 18 | 16 | `missing operand` |
| `err_line` | 17 | 15 | `undefined line` |
| `err_cont` | 17 | 15 | `can't continue` |
| `err_type_mismatch` | 16 | 14 | `type mismatch` |
| `err_mem` | 16 | 9 | `o\02memory` |
| `err_verify` | 15 | 8 | `Verify\01` |
| `err_data` | 14 | 7 | `o\02data` |
| `err_io` | 13 | 6 | `load\01` |

Low region, `212 -> 153`, **frees 59 B**: `err_illegal_fn_arr` 24→3 (`I\03`),
`err_mem_arr` 16→9, `err_subscript` 25→18, `err_out_of_str` 22→15,
`err_syntax` 15→8, and the rest at −2 each from §4.2.

⚠️ **The `Line buffer `→`overflow` fall-through must be PRESERVED, not
re-encoded.** Encoding the pair as two independent strings costs 30 B against
the 23 B they share today — a **7 B LOSS** hidden inside a column that still
reads as a saving. Keeping the fall-through (12 B + 9 B = 21 B) makes it a 2 B
gain. This is the same trap §3 flagged, one layer down.

## 5. Placement — the tuning knob, and the tenancy risk

Freed: **page 1 98 + 10 (`print_string_stopcr` retires) = 108 B**; **low 59 B**.
To place: phrase table 44 B + decoder 40 B = **84 B**.

| option | table | decoder | page 1 after | low after | promotion needed |
|---|---|---|---|---|---|
| **B (primary)** | page 1 | low | 64 free, need 20 → **44 spare** | 28 free, need 15 → **13 spare** | none |
| **C (fallback)** | page 1 | page 1 | 24 free, need 20 → 4 spare | 68 free, need 15 → 53 spare | none (demote for margin) |
| A | low | low | 88 free → 57 spare | −16, needs 31 B promoted up | 31 B |

🔴 **Option B's risk is tenancy, and it is exactly the "walk THROUGH page 1"
rule.** `print_string` sits at `$4696` — *page 1* — so it is reachable by
**page-0 sub-ROM tenants**, which cannot see the low region. Moving message
printing into the low region breaks any page-0 tenant that prints a message.
**This is not something to reason about: `check_tenant_closure --page0` already
runs in the build and decides it.** If it fails, take option C.

Option C's 4 B of page-1 margin is thin, but low then holds 53 B spare, so an
ordinary demotion restores margin without touching the design.

## 6. Cost probe — build this BEFORE landing anything

Per [[answer-signoff-questions-by-measuring]] and this arc's three prior
mis-costings, §4–§5 are arithmetic and must be replaced by a measurement:

1. `rm -rf build` first, always ([[measure-the-wall-from-clean]]).
2. Implement §4.3's decoder and §4.1's table, convert **only the page-1
   messages**, build, and read both walls. That alone should show ≥ 20 B of
   page 1 and validates the decoder's real size against the 40 B estimate.
3. Then convert the low-region messages and re-read.
4. ⚠️ If a wall must be relaxed to measure an over-budget intermediate, **pin
   the header with an explicit `org $4000`** — removing the low region's
   `ds $4000 - $` pad slides page 1 down with it and `__MEAS_PAGE1_END` then
   measures page 1 *plus* the low region. This apparatus bug read 77 B where the
   truth was 45 B (filechan §5c).
5. Never rebuild while a differential is running; `make repack-machine` before
   any probe, or you measure a stale ROM.

## 7. The gate

The output bytes are user-visible and must not move. Existing coverage is
unusually good here — `error-trap-acceptance`, `linemax-acceptance` (ERR 25),
`arrdim` (ERR 9/10), `clearpool` (ERR 14) and `chancost-characterize` all drive
the error print path — but none of them is a *decoder* test.

* **New host unit test (`make unit-test`): decode every encoded message and
  byte-compare against its literal text.** ⚠️ **Falsify it by deleting a
  phrase-table entry** — if the suite stays green, the test is measuring nothing
  ([[gate-can-be-green-while-measuring-nothing]]).
* **Two-sided**: assert direct mode emits body+CRLF *and* run mode emits body
  with no CRLF, then `" in <line>"`. A one-sided check passes a decoder that
  never emits the CRLF at all.
* **Assert the clobber contract**, don't claim it: `print_msg` must preserve
  exactly what `print_string` preserved. A refactor inherits clobber contracts
  [[refactor-inherits-clobber-contracts]], and the abort path is depth-sensitive
  (D-CUR-D, [`basic/arrays.asm:92`](../basic/arrays.asm:92)).
* **The lean cart must stay byte-identical** — `tools/check_reloc.py` gates it.
  Everything here is gated `IF ROM_BASE < $4000`; the lean build keeps plain
  strings and `print_string`. This is the established pattern already used by
  `err_syntax`, `err_stack` and `err_prog_mem`, so the risk is low — but the
  gate, not the pattern, is what proves it.

## 8. Scope boundary

This slice funds S-FCH-2. It does **not** land ERR 52/59, and it does not touch
the two open correctness questions in filechan §5c, which are independent of
funding and must still be settled before any of S-FCH-2 lands:

1. `err_bad_filenum` forces `ONEFLG=1` to reach `raise_error`'s abort arm and
   **leaves it set**; whether the return to the REPL clears it is unestablished.
   A stale `ONEFLG` would force-abort the *next* error instead of trapping it.
2. The ten repointed `jp` sites are unconditional in the cost probe, so the lean
   cart would not assemble.

## 9. Sign-off questions

* **Q1 — does this carve make S-FCH-2's sub-ROM eviction unnecessary?** Under
  option B the carve leaves 64 B of page 1 and 28 B of low. S-FCH-2
  **all-resident** costs 45 B page 1 + 32 B low (filechan §5c) — page 1 fits with
  19 B spare and low is 4 B short, closable by demotion. If it lands all-resident
  there is **no tenant op 19, no `ERRMSG_BUF` staging, and no ten repointed `jp`
  sites** — which dissolves §8's second correctness question entirely. That is a
  materially better outcome than the 26 B eviction, and it is the first question
  the cost probe should answer. **Recommended: probe for it.**

* **Q2 — how many phrases?** Four is the knee (net 65 B before the decoder);
  eight reaches 79 B for 25 B more table. **Recommended: four**, since §5 already
  closes both walls with margin and each extra phrase widens the blast radius for
  a diminishing return. The scheme is incremental — more can be added later
  without redesign.

* **Q3 — one entry point or two?** §4.3 proposes `print_msg` /
  `print_msg_stopcr`, mirroring today's split. The alternative (a single entry
  plus a flag) is smaller on paper but adds a parameter to the abort path.
  **Recommended: two**, matching the existing shape.

* **Q4 — does the encoding belong in the sub-ROM instead?** No. The decoder runs
  on the abort path, which must work when the sub-ROM is absent
  (`subrom_absent_error` prints `err_subrom_absent`, itself an alias of
  `err_illegal_fn`). A sub-ROM phrase table would make the "sub-ROM is missing"
  message depend on the missing sub-ROM. **Resolved: main ROM.**
