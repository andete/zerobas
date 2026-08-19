<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# The untrapped abort returns into its caller (D-CUR-D) — implementation spec

**Status:** ✅ **LANDED 2026-07-28 — `make abort-acceptance` 23/23, falsified
6/23.** Ordering
signed off first: this slice runs **before** D-MISS-2 (the 🔴
string-argument-domain checks), because D-MISS-2's fix is four to five new
calls into the very convention this document repairs. S-AD-1 … S-AD-5 taken at
their recommended answers.

**As built:**

| step | low-region free | page-1 free | gate |
|---|---|---|---|
| baseline (`73b4842`, from clean) | 11 B | 44 B | — |
| `ld sp,(SAVSTK)` at the abort funnel | **7 B** (−4) | 44 B (unchanged) | **`make abort-acceptance` 23/23** |

`make unit-test` 53/53; lean `basic.rom` byte-identical (`LEAN_SHA256`
unmoved — the whole change is inside `IF ROM_BASE < $4000`).
**Falsified 23/23 → 6/23** (§6). All nine measured sites in §2 now match the
reference; both open sign-off questions were answered by measurement rather
than argument (S-AD-2 needs no boot init, S-AD-3 needs no tenant handling).

Implementation follows this document; where it deviates, this document is wrong
and gets corrected.

Inputs, all measured on a clean-built HEAD (`73b4842`, `rm -rf build && make
basic-reloc`: page-1 44 B free, low region 11 B), none assumed:

- §2 below — the untrapped differential vs `Philips_VG_8020`, boot-per-case,
  taken for this spec. Sixteen cases, two readouts.
- Roadmap: [`TODO.md`](../TODO.md) — the `get_byte_arg` item (D-CUR-D) and the
  🔴 string-domain item (D-MISS-2) it blocks.
- [`missing-vg8020-characterization.md`](missing-vg8020-characterization.md) §8
  — where D-CUR-3 was first recorded as "reported not gated".

## 1. The defect in one sentence

`raise_error`'s **trap** path resets the stack
([`basic/interp.asm:952`](../basic/interp.asm:952), `ld sp,(SAVSTK)` then
`jp rp_lp`); its **abort** path does not — `fre_abort_low`
([`basic/arrays.asm:90`](../basic/arrays.asm:90)) prints the message and
**returns**. So an error raised from a statement handler's own depth unwinds
correctly, and an error raised from anything the handler *called* consumes that
`call`'s frame and lands back **inside the handler**, one instruction past the
call, with `A` = the error code.

## 2. The measured surface

Untrapped (**no `ON ERROR` armed**), direct mode, boot-per-case, screen scraped
from VRAM. `ref` = `Philips_VG_8020`, `zb` = `C-BIOS_MSX1_EU_REPACK_DISK` built
from `73b4842`.

| case | reference | zerobas |
|---|---|---|
| `WIDTH 300` | `Illegal function call` | **no error at all**; screen left unusable |
| `WIDTH 99999` | `Overflow` | **no error at all**; screen left unusable |
| `PRINT "[";SPACE$(-1);"]"` | `[` · `Illegal function call` | `[` · error · **`]`** |
| `PRINT "[";SPACE$(99999);"]"` | `[` · `Overflow` | `[` · **`overflow` ×2** |
| `PRINT "[";STRING$(-1,65);"]"` | `[` · `Illegal function call` | `[` · error · **`syntax error` ×2** |
| `PRINT STRING$(99999,65)` | `Overflow` | **`overflow` ×2** · `syntax error` |
| `ON 256 GOTO 10` | `Illegal function call` | error · **`syntax error`** |
| `PRINT STICK(9)` | `Illegal function call` | error · **` 0`** |
| `PRINT VPEEK(-1)` | `Illegal function call` | error · **` 32`** |
| `PRINT ASC("")` (control) | `Illegal function call` | `illegal function call` ✅ |
| `PRINT LEN("abc")` (control) | `3` | `3` ✅ |

`WIDTH` is the severe one and the mechanism is legible in the symptom: the
abort returns into `ex_width` ([`basic/screen.asm:174`](../basic/screen.asm:174))
just past `call get_byte_arg` with `A` = 5, which then does `ld (LINLEN),a` and
re-initialises the screen **to width 5**. No error is printed at all — the
message is emitted and then overwritten by the screen re-init. The 40-column
scrape of the resulting 5-column screen reads
`'                    Z|                    B'`: the machine is left unusable.

Three things this table settles that the roadmap had wrong:

1. **The scope is not four statements.** [`TODO.md`](../TODO.md) scoped it to
   `WIDTH`, `STRING$`, `SPACE$` and `ON n` — the `call get_byte_arg` sites. But
   `ev_ff_arg` ([`basic/expr.asm:1094`](../basic/expr.asm:1094) ff.) calls the
   same leaf for `STICK`/`STRIG`/`PDL`/`PAD`, and `get_vram_arg` /
   `fac_to_int_addr` reach the same abort for `VPEEK`/`PEEK`/`INP`. Nine sites
   measured, all below handler depth, all wrong.
2. **The recorded fix was the expensive one.** The roadmap proposed "per-caller
   frame discipline across four statements, each with its own gate". The trap
   path already solves the general case in four bytes; §4 takes that instead.
3. **`SPACE$(-1)` was recorded clean and is not** — see §3.

## 3. ⚠️ Two ways the apparatus hid this, both live

**(a) The standing gate cannot see any of it.**
[`probes/basic/basic_probe_intarg.py`](../probes/basic/basic_probe_intarg.py) is
the D-F2-2 acceptance gate and it covers `WIDTH 256`, `WIDTH 99999`,
`STRING$(-1,65)`, `SPACE$(-1)`, `ON 256` and the whole `ev_ff_arg` family — 36
asserted rows, all green. Every row runs under `10 ON ERROR GOTO 100` and reads
`ERR`.
Arming a handler selects the **trap** path, which is the one path that unwinds
correctly. The gate is green because it exercises the working half of the
branch, and it would stay green with every defect in §2 present. This is the
gate-can-be-green-while-measuring-nothing shape again, in a gate that has been
green since the D-F2-2 arc closed.

The pairing is exact, and both halves were run on the same build on
2026-07-28:

| statement | `intarg` row (handler armed) | §2 row (no handler) |
|---|---|---|
| `WIDTH 99999` | `width_ovf` **PASS**, `zb=ERR6 ref=ERR6` | **no error printed; screen unusable** |
| `SPACE$(-1)` | `space_neg` **PASS**, `zb=ERR5 ref=ERR5` | error, then a stray `]` |
| `ON 256 GOTO …` | `on_ill` **PASS**, `zb=ERR5 ref=ERR5` | error, then `syntax error` |

`make intarg-acceptance` reports `ALL PASS` on the build every row of §2 was
measured on.

**(b) My own first readout reported `SPACE$(-1)` as clean.** The scrape
right-strips each row, and the junk `SPACE$(-1)` emits is *a run of spaces* —
`get_byte_arg`'s reject returns into `str_fn_space` with `A`=5, which duly
builds a five-space string. Re-run as `PRINT "[";SPACE$(-1);"]"` it prints the
error and then `]`. The first reading agreed with
[`missing-vg8020-characterization.md`](missing-vg8020-characterization.md) §8's
"D-CUR-3, already known" note for the wrong reason. **Every row in §2 that
prints "clean" is bracket-delimited for this reason**, and the gate in §6
inherits the rule.

## 4. The design — one reset, at the funnel

Make the abort path depth-independent exactly the way the trap path already is.
In `fre_abort_low`, after the message is printed:

```
                ld      sp,(SAVSTK)         ; abort is depth-independent, like the trap
                ret                         ; == the run loop's own end-of-program exit
```

This is not a new mechanism; it is the mechanism already used by the trap
branch four instructions away. Two properties make the `ret` exactly right
rather than merely safe:

- **Run mode.** `run_prog` does `ld (SAVSTK),sp`
  ([`basic/program.asm:265`](../basic/program.asm:265)) and then falls into
  `rp_lp`, whose normal end-of-program exit is `ret z` at that same depth. So
  `ld sp,(SAVSTK)` + `ret` **is** the normal end-of-RUN exit, reached early.
- **Direct mode.** `dl_cmd` does `ld (SAVSTK),sp`
  ([`basic/program.asm:60`](../basic/program.asm:60)) and then `jp`s (not
  `call`s) into the loop, so the same identity holds for a typed line: the
  reset-and-return is the normal end-of-line exit.

`ENDFLAG` stays set. It is still consumed by `rp_run`'s post-`exec` check on
every path that does *not* go through the reset (`END`, `STOP`, Ctrl-STOP), and
setting it on the abort path costs nothing and keeps the funnel single.

### 4.1 Why this adds no hazard class

The objection to blowing away the stack from arbitrary depth is that some
caller may need to run a restore on the way out — a sub-ROM tenant leaving page
1 switched, say. **That exposure exists today, unchanged, on every trapped
error**: the trap branch does this same reset from these same depths. The fix
makes abort match trap; it cannot create a hazard class that a single
`ON ERROR GOTO` does not already create. Two further facts bound it:

- `raise_error` is **page-1** code (`interp.asm` is included after
  `__MEAS_LOW_END`, [`basic/main.asm:119`](../basic/main.asm:119)), so a
  **page-1** sub-ROM tenant cannot reach it at all — `check_tenant_closure
  --page1` is the standing proof.
- **Page-0** tenants can reach it, and are the residual case. S-AD-3 (§8).

### 4.2 Build guard — the lean cart cannot move

`fre_abort_low`'s body, `raise_error`, `get_byte_arg` and `SAVSTK`'s two stores
are all inside `IF ROM_BASE < $4000`; the lean build aliases
`fre_abort_low equ print_string`
([`basic/interp.asm:599`](../basic/interp.asm:599)). So this change is
**repack-only by construction** and `LEAN_SHA256` must not move. `make
basic-reloc`'s "lean basic.rom byte-identical" line is the check.

### 4.3 Follow-on carve (optional, not required by this slice)

Four sites currently pay for this bug per-site, by discarding their own dead
return address before jumping into the abort chain: `cee_abort_tm` /
`cee_abort_fp` ([`basic/interp.asm:1148`](../basic/interp.asm:1148)),
`check_expr_errors_popbc`, and `check_preexp_bounds`
(`basic/float-arith.asm`). Once the funnel resets `SP`, those `pop`s are dead
weight. Removing them is byte-negative but touches four error paths with their
own recorded reasons, so it is proposed **after** the gate in §6 is green and
falsified — not in the same step.

## 5. Byte budget

| item | estimate | **as built** |
|---|---|---|
| `ld sp,(SAVSTK)` + `ret` at the funnel | +5 B | **+4 B** |
| restructuring the two message tails from `jp` to `call` + shared exit | +2…+4 B | **0 B — not needed** |
| boot-time `SAVSTK` init, **if** S-AD-2 shows a gap | +5 B | **0 B — no gap** |
| **total** | +7…+14 B | **+4 B** |
| §4.3 carve, if taken later | −4…−8 B | deferred |

⚠️ **The budget named the wrong wall.** It costed this against page 1's 44 B,
but `fre_abort_low` lives in `basic/arrays.asm`, which is **low region** — so
the 4 B came out of the low region's 11 B, leaving **7 B**. Page-1 free is
unchanged at 44 B. The estimate was right about the size and wrong about which
ceiling it pressed on; the low region is the tighter of the two and the next
low-region slice (D-MISS-2) must budget from 7 B, not 11 B.

The restructuring line came to nothing because the reset does **not** have to
go after the message: the printing routines push and pop *below* the new `SP`
and never touch the word *at* it, so `ld sp,(SAVSTK)` goes at the **top** of
the funnel and the existing tail-jumps (`jp print_string` / `jp
print_in_lineno`) `ret` straight to the anchored address. Four bytes, one
instruction, no control-flow change.

No carve or promotion was needed for this slice.

⚠️ **This paragraph used to predict that D-MISS-2 would need one, at "a page-1
cost of ≈45–50 B". That was wrong and is left here corrected rather than
deleted, because it is the second budget on this page to name the wrong
number.** D-MISS-2 landed the same day
([`spec-basic-str-domain.md`](spec-basic-str-domain.md)) at **−14 B on page 1
and +23 B BACK into the low region** — no promotion, no carve. The estimate
assumed register-guard bytes that `get_int16_checked` already provides, and it
costed *added* calls, missing that `call eval` was already at every site: a
shared `eval_byte_arg`/`eval_pos_arg` pair costs **zero bytes at the call site**
and can therefore be paid for on the other wall. The naive shape this estimate
was actually costing was built and measured too — +26 B, all low-region — so
the number was not absurd, it was costing a design nobody had to take.

## 6. The gate

A new probe, `probes/basic/basic_probe_abort_depth.py`, target
`make abort-acceptance`. It is the §2 measurement promoted to a two-sided
differential, and it exists because the standing `intarg` gate structurally
cannot cover this (§3a).

- **No handler armed.** Not one row may contain `ON ERROR`. That is the whole
  point of the probe and belongs in its docstring, or the next person will
  "improve" it into a copy of `intarg`.
- **Bracket-delimited output on every row** (`PRINT "[";…;"]"`), so trailing
  spaces are visible (§3b).
- **Boot-per-case.** `WIDTH` cases leave the machine unusable by construction;
  they cannot share a boot with anything.
- **Both readouts per row**: the screen tail (what the user sees) and, for the
  `WIDTH` rows, the raw 40-column scrape (the tail is unreadable once the
  screen width changes — an echo-anchored readout cannot measure a statement
  that moves the cursor).
- **Controls first.** `PRINT ASC("")` and `PRINT LEN("abc")` prove the abort
  mechanism is reachable and the readout works, before any other row is read as
  a finding.
- **Falsification, recorded in the commit:** reverting the `ld sp,(SAVSTK)` must
  take the gate red. A gate that stays green with the fix removed is measuring
  nothing. ✅ **RUN 2026-07-28: 23/23 → 6/23**, rebuilt from clean (the low
  region went back to 11 B free, so the instruction really was out of the
  image). And the **six survivors are the right six** — `ctl_value`,
  `ctl_abort`, `boot_first`, `tenant_ary`, `tenant_after` and `run_suffix` all
  raise at the statement handler's own depth, which is exactly where the abort
  was already correct. A falsification that had killed those too would have
  meant the gate was measuring the abort chain in general rather than its
  *depth*.
  ⚠️ **So `tenant_ary`/`tenant_after` (S-AD-3) are CONTROLS, not
  discriminators.** They pass with and without the fix: the page-0 sub-ROM
  tenant path raises `Subscript out of range` at handler depth and was never
  part of this defect. What those rows prove is that the SP reset does not
  BREAK the tenant path — not that it repaired it. Recorded because the green
  run alone reads like the latter.
- **Regression:** `make intarg-acceptance` (36/36) and `make
  missing-acceptance` (214/214) must both still pass — the trapped ERR codes
  are not allowed to change. ✅ Both green (`unit-test` 53/53 too).
  ⚠️ **`missing-acceptance` went RED first, and it was right to.** Its own
  stale-marker check fired: `d2-string-neg`, `d2-string-256` and `d2-space-neg`
  were recorded as expected-divergent and now AGREE, so its expected-divergent
  count drops **20 → 17**. Those three are D-CUR-3 rows —
  `STRING$`/`SPACE$` always HAD their `get_byte_arg` domain check; only the
  abort SHAPE diverged. **This slice implements no part of D-MISS-2**; the four
  `d2-chr-*` and the `LEFT$`/`RIGHT$`/`MID$` rows stay marked.

## 7. Out of scope

- **D-MISS-2** — the missing `CHR$`/`LEFT$`/`RIGHT$`/`MID$` domain checks. This
  slice makes them safe to add; it does not add them. Its 7 silent rows were
  re-measured on `73b4842` and all still reproduce.
- **The two spellings of one message.** `overflow` vs `Overflow`,
  `illegal function call` vs `Illegal function call` — the deliberate
  house-style/arrays split documented at
  [`basic/arrays.asm:44`](../basic/arrays.asm:44). It shows up in §2 and is not
  a finding.
- **The `WIDTH 300` screen-width surface itself.** Once the error aborts
  correctly, `LINLEN` is never written; whether `WIDTH`'s *valid* domain matches
  the reference is a separate question this slice does not open.

## 8. Sign-off questions

- **S-AD-1 — the design.** One reset at the funnel (§4), rather than the
  roadmap's per-caller frame discipline. Recommended: take it. It is the trap
  path's own mechanism, it fixes all nine measured sites at once, and it makes
  every future `jp raise_error` correct by construction regardless of depth.
- **S-AD-2 — `SAVSTK` validity.** `SAVSTK` is written in exactly two places,
  both immediately before entering the loop, and is **not** initialised at cold
  boot. Every typed line passes through `dl_cmd`, so the ordinary paths are
  covered — but this must be *measured*, not argued, for the first line after a
  cold boot and for an error raised outside both anchors. If a gap shows,
  §5 budgets a 5 B boot init. Recommended: measure first, add the init only if
  the measurement demands it.
- **S-AD-3 — page-0 tenants.** A page-0 sub-ROM tenant (`tokenise`,
  `ary_engine`, `strheap_engine`, …) can reach `raise_error`. The exposure is
  identical on today's trap path (§4.1), so this slice does not worsen it —
  but is it worth one measured row in the gate (a tokeniser or array error
  raised untrapped from inside a tenant) to pin it? Recommended: yes, one row.
- **S-AD-4 — the follow-on carve** (§4.3). Recommended: defer to a separate
  step after the gate is green and falsified, and note it in the commit.
- **S-AD-5 — documentation.** This spec carries its own measured surface rather
  than a separate `*-vg8020-characterization.md`, because it is sixteen cases
  and the probe in §6 is the durable re-derivable artifact. Recommended:
  accept the deviation; if the surface grows past ~40 rows during
  implementation, split it out.
