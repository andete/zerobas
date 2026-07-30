# SPEC — land the transitive dead-code sweep as a standing gate

Status: **SIGNED OFF 2026-07-30** (Q1 = delete `gfx_border_read` + fix the three
stale comments; Q2 = hard gate in `basic-reloc`; both as recommended).
Parent: [`rom-region-structure-review.md`](rom-region-structure-review.md) §0.1/§4,
which built this sweep in a scratchpad, used it to find 122 B, and threw it away.
Baseline: `2aee774` (R1 landed), clean build, low **80 B** / page 1 **49 B** free.

---

## 1. Why this is worth a tool and not a note

pasmo's `Var x is never used` is **per-symbol**: it cannot see a routine that *is*
referenced, but only from code that is itself dead. That is how `var_find` and
`div_zero` hid. And the finding it *could* see had been printing on every build for
months, inside ~230 lines of warning noise nobody read — which is the actual failure
this gate exists to prevent. R1 found **122 B** where the warnings showed 80.

**A gate, not a report.** The review's whole lesson is that an unread finding is not a
finding.

---

## 2. What it measures

For each build, model every label as a **linear span** (its line to the next label's).
A span is LIVE if it is a seed, is mentioned by a live span, or is fallthrough-entered
from a live span whose last code line is not an unconditional terminator. Iterate to a
fixed point; anything still dead is unreachable ROM.

### 2.1 The four apparatus fixes it MUST keep

Each of these produced a confident wrong row during the review while missing a real
one. They are the tool's actual content — the fixed-point loop is the easy part.

| # | fix | what it prevents |
|---|---|---|
| 1 | terminator test = [`check_tenant_closure.py`](../tools/check_tenant_closure.py)'s `_is_terminator` | a naive `^(ret\|jp\|jr)` matches `jp nc,x` / `ret nz` and falsely kills fallthrough-entered routines (`ei_set`, `spr_set`) |
| 2 | lines before a file's first label → an always-live **prologue** span | references made there are invisible (falsely killed `sp_done`) |
| 3 | closure follows **every identifier a span mentions**, not just `call`/`jp`/`jr`/`djnz` | misses DATA references — `ld hl,zkey_hook` is how `keytrap.asm`'s `$0038` hook read as promotable |
| 4 | **each build walked separately, with its own include closure and seeds** | "dead" is per-build: `disk_putword` is dead in main, live in sub, and its caller sits outside `main.asm`'s closure entirely |

### 2.2 Seeds — and why the choice matters more than the algorithm

* **main build**: `init` (the cartridge header's entry) + every label named anywhere in
  `sub/` or `tools/`. ⚠️ **NOT `tests/` or `probes/`.** A test naming a routine is not
  a reason to keep ROM bytes — seeding on those hides the whole `vars.asm` block,
  because S3's ported tests still name it. **That one choice is the difference between
  16 dead spans and 4.**
* **sub build**: the page-0 and page-1 **entry-table** tenants (via `ctc.page0_seeds`
  / `page1_seeds`) + all prologues. This set is *closed and provably complete*: the
  main ROM can only reach sub code through `SUBROM_ENTRY_BASE_P0/_P1 + 3*index`, so
  the two tables are the entire external surface.

Every seed name is **asserted to resolve to a real label**. A renamed seed must fail
loudly, not silently shrink the seed set.

---

## 3. Measured starting state

| build | dead spans | bytes | detail |
|---|---|---|---|
| main (`basic/main.asm`) | **0** | 0 | R1 cleared it |
| sub (`sub/sub.asm`) | **2** | **40** | below |

| span | file | bytes | verdict |
|---|---|---|---|
| `gfx_border_read` | [`sub/graphics.asm:1690`](../sub/graphics.asm:1690) | 24 | **orphaned by a bug fix** — superseded by `gfx_paint_read` (the VG-8020 fix; `tests/test_graphics.py:565` names the swap). **DELETE.** |
| `fmt_menu_text` | [`basic/format-body.inc:118`](../basic/format-body.inc:118) | 16 | **DELIBERATE KEEP** — its own comment: "at its ORIGINAL position (do_format's era) … preserving the pre-eviction byte layout. Unused sub-side … but harmless — sub-ROM space is not tight". **ALLOWLIST.** |

⚠️ `gfx_border_read`'s removal has **doc debt attached**: three comments in
`sub/graphics.asm` (lines 1592, 1724, 1842) still describe it as the live border
reader. Fix them in the same slice or the next reader re-derives a routine that
isn't there.

---

## 4. The allowlist, and how it doubles as the vacuity canary

`tools/deadcode-allow.txt`: one `<build> <label> <reason>` per line, **reason
required** (a blank reason is a parse error).

🔴 **THE GATE ALSO ASSERTS THAT EVERY ALLOWLIST ENTRY IS STILL DETECTED AS DEAD.**

This is the answer to [[gate-can-be-green-while-measuring-nothing]]. The dangerous
failure mode for this tool is *not* a false red — it is going blind and reporting a
clean sweep. An over-broad seed set, a broken span model, or a path change would all
produce "0 dead spans" and read as success forever.

`fmt_menu_text` is **known-dead and staying dead**, so it is a live canary. If it
stops reading as dead, exactly two things are possible:

* someone gave it a caller → correct action: drop it from the allowlist;
* the sweep went blind → correct action: fix the sweep.

Either way the gate fires. **An allowlist that must keep matching is a control; an
allowlist that only suppresses is rot.**

---

## 5. Wiring

Run inside `make basic-reloc`, beside the three closure walks and
`check_resident_abi` — the same class of structural gate, and it needs both `.sym`
files which that target already produces. Non-zero exit on any non-allowlisted dead
span, or on any allowlist entry that is no longer dead, or on any seed that does not
resolve.

Also expose `make deadcode` to print the report without failing, for use while
developing a routine ahead of its caller.

⚠️ **`build/sub.sym` ordering.** `$(SUB_ROM)` already depends on `$(RELOC_SYM)`
through `sub/basic-resident-abi.inc`, and `$(RELOC_SYM)` must never depend back on
`$(SUB_ROM)` — that is the documented build-graph cycle the Makefile is shaped to
avoid. The gate therefore hangs off the **`basic-reloc` PHONY target** (which already
depends on `$(SUB_ROM)`), never off the `$(RELOC_SYM)` file rule.

---

## 6. Gates for this slice

It adds a gate and deletes 24 B of `sub.rom`, so:

| gate | expected |
|---|---|
| `rm -rf build && make basic-reloc` | **low 80 B free, page 1 49 B free — UNCHANGED.** R1's walls are the standing measurement; this slice must not move them. |
| `build/basic-reloc.rom` | **byte-identical** — nothing in `basic/` changes |
| `build/sub.rom` | **changes by exactly −24 B of content** (`gfx_border_read`); the image stays 32768 B padded, so compare the pre-pad content boundary, not the file size |
| `make unit-test` | 54/54 |
| `make deadcode` | main 0 dead, sub 0 non-allowlisted dead |
| full suite | diskbasic 34/34 · bdos 12/12 · fat-error 7/7 · abort 31/31 · error-trap ALL PASS · chancost 39/1 · probe · machines |
| graphics | ⚠️ **PAINT specifically** — `gfx_border_read` sits in the flood-fill file. `tests/test_graphics.py` + the graphics acceptance/probe rows must pass, and PAINT's rows named explicitly. |

### 6.1 Falsification — three rows, and the third is the one that matters

| row | edit | must |
|---|---|---|
| **red A** | inject a genuinely dead routine | reported |
| **green control** | give that same routine one live caller | not reported |
| **red B** 🔴 | **blind the instrument** — e.g. seed the closure with every label | **FAIL on the allowlist canary**, proving the gate cannot silently measure nothing |

Row B is the one the review's own harness lacked. A tool that finds injected dead code
still fails its job if it can go quietly blind.

---

## 7. Explicitly out of scope

* No new eviction/promotion — R1's walls must read exactly 80/49.
* No sweep of `disk/` (its own build; a separate seed problem, and it is not
  wall-constrained).
* Not `fmt_menu_text`'s 16 B — a documented deliberate keep, and it is more useful as
  the canary than as 16 recovered bytes of a ROM with 7411 free.

---

## 8. Open questions for sign-off

**Q1 — `gfx_border_read`: delete, or allowlist?** §3 proposes delete + fix the three
stale comments. It is orphaned by a bug fix, not deliberately kept, and leaving
superseded code in place beside comments that call it live is exactly the doc debt this
project treats as a co-equal deliverable. **Recommendation: delete.** The counter-case
is that `sub.rom` has 7411 B free so the bytes do not matter — true, but the confusion
does.

**Q2 — hard gate in `make basic-reloc`, or `make deadcode` only?**
**Recommendation: hard gate**, with `make deadcode` alongside for development. The
arc's lesson is that an advisory finding goes unread for months; the allowlist is the
escape valve, and it is cheap and self-documenting. The counter-case is that dead code
is hygiene, not a correctness bug, and a hard gate interrupts the normal "write the
routine, then its caller" order — which `make deadcode` and a one-line allowlist entry
both address.

---

## 9. OUTCOME — ✅ landed 2026-07-30

`tools/check_dead_code.py` + `tools/deadcode-allow.txt`, wired as a step of
`make basic-reloc`, plus `make deadcode` for the advisory report.

⚠️ One wart found by re-reading my own output and fixed: `--report` mode used to
head its findings **`FAIL:`** while exiting 0 — a red-looking readout on a green
exit, which is the precise signal class this tool exists to remove. Report mode
now says `REPORT:` and states that the hard gate is what fails. Verified all four
ways: gate/clean 0, gate/blind 1, report/clean 0, report/blind 0.

**Standing state:** main **0 dead spans** (1544 spans, 264 seeds) · sub **0
non-allowlisted** (1375 spans, 98 seeds, 1 allowlisted).

| gate | result |
|---|---|
| walls (clean build) | **low 80 B / page 1 49 B — UNCHANGED** ✅ |
| `build/basic-reloc.rom` | **byte-identical** to `2aee774` ✅ (nothing in `basic/` changed) |
| `build/sub.rom` page-0 content | `$302A → $3012` = **−24 B exactly** ✅; page 1 unchanged; file still 32768 B padded |
| sub page-0 free | 4054 B → **4078 B** |

Q1 taken as recommended: `gfx_border_read` **deleted**, and the three comments that
still described it as the live border reader
([`sub/graphics.asm`](../sub/graphics.asm) lines 1592, 1724, 1842) corrected to name
`gfx_paint_read`. Q2 taken as recommended: **hard gate**.

### 9.1 Falsification — all three rows, and the guards

| row | behaviour | verdict |
|---|---|---|
| **red A** | inject a dead routine into **each** build (`basic/poke.asm`, `sub/beep.asm`) | both reported, exit 1 ✅ |
| **green control** | give each the same one live caller | 0 dead both builds, exit 0 ✅ |
| **red B** 🔴 | `--blind` (seed the closure with every label) | prints **"0 dead"** for both builds — which reads as success — and the **allowlist canary fires**, exit 1 ✅ |

Row B is the one that matters, and the one the review's own scratchpad harness
lacked: a sweep that goes blind reports a clean tree forever. `fmt_menu_text` is
known-dead by design, so it is a permanent canary — if it ever stops reading as dead,
either it gained a caller or the instrument is broken, and both demand attention.

Allowlist guards, each verified to fire:

* entry with no reason → `FAIL: … a reason is MANDATORY`
* entry with a build other than `main`/`sub` → `FAIL: build must be main|sub`
* entry naming a label that is **not** dead (tested with `main init`) → the canary
  failure above

### 9.2 Gates — and a wider blast radius than §6 assumed

⚠️ **§6's gate table under-scoped this slice.** Deleting 24 B from sub page 0 shifts the
address of **every page-0 tenant after it** — `graphics`, `deftype`, `readdata`, `beep`,
`fldlook` and `kwtable` all moved down 24 B (the tokeniser/detok/arrays/strheap tenants
sit above `gfx_border_read` and did not). Dispatch is through the `$0010` jp table so a
shift is expected to be inert, but "expected to be inert" is what this project's gates
exist to distrust, so the FULL suite was run, not just graphics.

`graphics-acceptance`: **289 PASS / 0 FAIL**, `graphics-acceptance: PASS`. Its three
dedicated PAINT phases, named per §6 rather than folded into "suite green" — this is
the file the deletion came out of:

* **PHASE H** (PAINT fill differential vs the VG-8020, step 90 s) — 9/9:
  `box_bounded_c15b15`, `box_flood_c4b15`, `box_bounded_c9b9`, `step_form`,
  `defaults_c_and_b`, `comma_empty_c`, `border16_flood_ok`,
  `seed_on_border_still_floods`, `seed_on_wall_pixel`;
* **PHASE I** (PAINT-after-string-heavy aliasing stress) — `paint_after_string_heavy`;
* **PHASE J** (PAINT errors, all pre-tenant) — 9/9: `scr0_err`, `scr1_err`,
  `colour16_err`, `colour_neg_err`, `offscreen_pos_err`, `offscreen_neg_err`,
  `ovf_err`, `tile_str_err`, `fourth_arg_err`.

18 cases in total issue a `PAINT` statement across the probe.

🔴 **A MEASUREMENT ERROR WORTH RECORDING.** The first graphics run was invoked as
`make graphics-acceptance 2>&1 | grep …` and reported **exit 0** — which I read as the
gate passing. A pipeline's exit status is the **LAST** command's, so that 0 was
**grep's** (it had matched), and said nothing about `make`. The run had produced no
`ALL PASS` line at all. Re-run without the pipe, `exit 0` is make's and the result
above is real. Same family as S3's "a red row reads as success": **the status you read
must be the status of the thing you are measuring.**

### 9.3 Full-suite results, and one flake that is NOT this slice's

| gate | result |
|---|---|
| `make unit-test` | **54/54** |
| `make probe` | ALL PASS (make's own exit 0) |
| `make graphics-acceptance` | **289 PASS / 0 FAIL** — §9.2 |
| `make abort-acceptance` | **31/31** |
| `make error-trap-acceptance` | ALL PASS |
| `make bdos-acceptance` | **12/12** |
| `make fat-error-acceptance` | **7/7** |
| `make chancost-characterize` | **39 cases / 1 filed divergence** |
| `make machines` | OK |
| `make diskbasic-acceptance` | **34/34** — see below |
| `make deadcode` / the gate | main 0 dead, sub 0 non-allowlisted, canary verified |

⚠️ **`diskbasic-acceptance` came in 33/34 on its first run, `GET(RDBLK)` failing.**
Recorded rather than absorbed, because a green re-run does not by itself clear a red.

What the probe printed was its OWN misalignment guard:
`*** MISALIGNED — diff NOT meaningful ***`, with `stock reached anchor: NO (looped /
never hit occurrence #1)` and `ours reached anchor: YES`. Its source labels this class
"Anchor/keys/timing problem, not a `$27` result", and it **refused to report a memory
diff between two different logical points** — so it failed loudly instead of
fabricating a converged reading.

Why it is not this slice: the side that failed is the **stock oracle**, and this slice
changes 24 B of zerobas's own `sub.rom`, which cannot influence it. `GET(RDBLK)`
then **converged standalone AND in a full re-run of the byte-identical build**
(34/34).

🔴 **I speculated that host contention from my own overlapping runs caused it, then
withdrew that** — the timestamps do not support it (diskbasic ran 12:44–13:15, after
any overlap). The cause is unconfirmed. What is certain is that the probe injects keys
at a fixed wall-clock `--keys-at 20 --settle 40`, so reaching the anchor is
timing-dependent. **Filed as its own TODO item**: gate the readout on a `done`
sentinel instead of elapsed seconds. An intermittent gate row is a defect in the GATE
even when the subject is innocent.

Seed-vacuity guards in the tool: `init` must resolve to a label in the main build,
every sub entry-table seed must resolve, and fewer than 20 parsed tenants is a hard
error — so a rename or a broken table scrape fails loudly instead of silently
shrinking the seed set to nothing.
