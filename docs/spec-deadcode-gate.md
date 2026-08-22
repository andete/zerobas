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

### 2.1 The six apparatus fixes it MUST keep

Each of these produced a confident wrong row during the review while missing a real
one. They are the tool's actual content — the fixed-point loop is the easy part.

| # | fix | what it prevents |
|---|---|---|
| 1 | terminator test = [`check_tenant_closure.py`](../tools/check_tenant_closure.py)'s `_is_terminator` | a naive `^(ret\|jp\|jr)` matches `jp nc,x` / `ret nz` and falsely kills fallthrough-entered routines (`ei_set`, `spr_set`) |
| 2 | lines before a file's first label → an always-live **prologue** span | references made there are invisible (falsely killed `sp_done`) |
| 3 | closure follows **every identifier a span mentions**, not just `call`/`jp`/`jr`/`djnz` | misses DATA references — `ld hl,zkey_hook` is how `keytrap.asm`'s `$0038` hook read as promotable |
| 4 | **each build walked separately, with its own include closure and seeds** | "dead" is per-build: `disk_putword` is dead in main, live in sub, and its caller sits outside `main.asm`'s closure entirely |
| 5 🔴 | the main seed scrape reads the **CODE COLUMN** of `tools/`, not whole files | a comment is not a reference: prose kept **24 B** of dead main code invisible to this gate, and the prose that hid it was the note explaining that span's removal from the other build — §10 |
| 6 🔴 | the main build is seeded from the **generated `sub/basic-resident-abi.inc`**, never from a scrape of `sub/` | a name is not a route: a `call` in `sub/` code seeded the MAIN label of that name even when it resolved sub-locally, which is the normal case. **20 B on main page 1**, orphaned and hidden by the same eviction commits — §11 |

### 2.2 Seeds — and why the choice matters more than the algorithm

* **main build**: `init` (the cartridge header's entry) + the **generated
  resident-ABI import** `sub/basic-resident-abi.inc` (fix 6, §11) + every label named
  in the **code column** of `tools/` — prose does not seed, see fix 5 and §10.
  ⚠️ **NOT `sub/`** — fix 6: the sub build reaches main only through that import, so
  scraping `sub/` seeded 53 names that resolve sub-locally.
  ⚠️ **NOT `tests/` or `probes/`.** A test naming a routine is not
  a reason to keep ROM bytes — seeding on those hides the whole `vars.asm` block,
  because S3's ported tests still name it. **That one choice is the difference between
  16 dead spans and 4.**
* **sub build**: the page-0 and page-1 **entry-table** tenants (via `ctc.page0_seeds`
  / `page1_seeds`) + all prologues. This set is *closed and provably complete*: the
  main ROM can only reach sub code through `SUBROM_ENTRY_BASE_P0/_P1 + 3*index`, so
  the two tables are the entire external surface.

`init`, the sub entry-table tenants and the resident-ABI import are each **asserted
to resolve to a real label**. A renamed seed must fail loudly, not silently shrink the
seed set. ⚠️ **The `tools/` arm is not asserted** — it is an *intersection* with the
label set, so a routine renamed out from under a `tools/` lookup drops out of the
seeds quietly. That arm over-seeds by construction, so its failure direction is a
missed finding rather than a false one; §11.4 files it rather than pretending §2.2's
old sentence was true of it.

---

## 3. Measured starting state

| build | dead spans | bytes | detail |
|---|---|---|---|
| main (`basic/main.asm`) | **0** | 0 | R1 cleared it |
| sub (`sub/sub.asm`) | **2** | **40** | below |

| span | file | bytes | verdict |
|---|---|---|---|
| `gfx_border_read` | [`sub/graphics.asm:2084`](../sub/graphics.asm:2084) | 24 | **orphaned by a bug fix** — superseded by `gfx_paint_read` (the VG-8020 fix; `tests/test_graphics.py:525` names the swap). **DELETE.** |
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

---

## 10. D-SEEDPROSE — ✅ a COMMENT was a seed (2026-08-21)

**A fifth apparatus fix, and the one that had been silently wrong the longest.**
`external_names()` scraped every identifier out of whole FILES under `sub/` and
`tools/` — comments included — and every main label whose name it found became a
seed. So:

> **A main-build span was invisible to this gate for as long as its label's name
> appeared in PROSE anywhere under `sub/` or `tools/`.**

🎯 **The prose that hid the first one was the comment explaining that span's
removal from the OTHER build.** D-FNRUN killed `parse_close_run`'s 6 B head and
noticed the gate had never asked for it; D-FNEXPR2's note in `sub/bload.asm`,
written one commit earlier to record that the head was dead on the sub side, was
what kept the main label alive. **Documenting a removal is what stopped the gate
asking for the same removal in the other build** — see
[`spec-basic-fnrun.md`](spec-basic-fnrun.md) §4.

### 10.1 The class, measured — 254 → 6 → 2 → 24 B

Re-verified on `261049d` before it was fixed, not carried forward from the filing:

| | |
|---|---|
| main labels | 1602 |
| seeded via `sub/` + `tools/` | **254** |
| of those, NOT reachable from `init`'s own closure | **6** |
| of those, named **only** in comments | **2** |
| reported when those two mentions are mangled | **3 spans, 24 B**, all page-0 LOW |

The third span (`sha_oom`) is reached only from the second (`str_heap_alloc`), so
two comment mentions were holding three spans. The remaining 4 of the 6 are
`write_sector` / `fat_read_fat_sector` / `fat_alloc_cluster` / `fat_write_fat_entry`
— seeded from real CODE under `sub/`, and therefore **still** seeded after this
fix. That is a *different* hole and it is filed as one; see §10.4.

### 10.2 The fix — the code column, and string literals stay

`_code_column()`:

* `.asm` / `.inc` — the `;` tail goes. The same split the span model itself already
  uses, so the scrape and the walk now read the same thing. (Five lines in the tree
  put a `;` inside a quote — `cp ';'`, `db "Can't CONTINUE"` — and none of them
  carries an identifier past it, checked.)
* `.py` — `#` comments **and docstrings** go, via `tokenize` + `ast` rather than a
  regex, because a `#` inside a string is not a comment. Docstrings go because a
  triple-quoted module header is prose by any other name: this tool's own docstring
  names a dozen labels in both builds. Worth **19 further seeds**, and **0 B** of
  findings today — measured, and recorded here so the next reader knows the
  docstring arm was not shipped on a hunch.
* **String literals STAY.** A tool naming a symbol it looks up in the `.sym` file
  does so in a string, and that IS a reference.
* A `.py` under `tools/` that does not parse is a **loud** failure. Falling back to
  the raw text would silently restore the blindness this section exists to remove.

Seeds: **303 → 123**. Findings after the D-SEEDPROSE carve: **0** in both builds.

⚠️ **The old justification is inverted, not deleted.** *"Deliberately coarse:
over-seeding keeps a live routine alive, which is the safe direction"* is sound for
a genuine reference made somewhere odd, and false for prose — a comment cannot
execute, so over-seeding on prose is not the safe direction, it is the **silent**
one.

### 10.3 Falsification — 6 rows, all EXACT, predictions written before the run

`_selftest_code_column()` runs on **every** invocation, against a floored table of
seven vectors carrying **both senses** (something the stripper must keep, something
it must remove). K1–K3 knife the stripper; K4–K6 knife the sweep with a planted dead
span in `basic/poke.asm`. **K5 and K6 are the same plant and the same mention text
under `sub/`, differing by two characters: `; `.**

| row | knife | want | got |
|---|---|---|---|
| K1 | `_CC_VECTORS = []` | rc 1, floor fires | ✅ EXACT |
| K2 | `_code_column` returns `txt` (the pre-slice behaviour) | rc 1, "which is PROSE" | ✅ EXACT |
| K3 | `_code_column` returns `""` | rc 1, "which is a REFERENCE" | ✅ EXACT |
| K4 | plant, no mention anywhere | reported by **both** scrapers | ✅ EXACT |
| K5 🔴 | plant + the mention as a **comment** under `sub/` | **new reports, old blind** | ✅ EXACT |
| K6 🟢 | plant + the same text as **code** under `sub/` | **neither reports** | ✅ EXACT |

K4 is what makes K5 readable: without it, "the new gate reports the plant" could be
the plant being dead for some other reason. K6 is what makes it honest: a real
reference still seeds, so the fix removed prose and nothing else.

⚠️ **These knives build no ROM.** The sweep decides from SOURCES; the `.sym` files
only decorate a finding with an address and a size. That is why a planted span with
no symbol still reports (`~? B`) and why the runner does not need `rm -rf build`
between rows — but it still restores by **writing the bytes**, and asserts all three
files byte-identical afterwards.

The three §6.1 rows are unchanged and re-verified: gate/clean **rc 0**, gate/blind
**rc 1 with the allowlist canary firing**, report/clean rc 0, report/blind rc 0.

### 10.4 What this does NOT close — the second seeding hole, 16 B on PAGE 1 ✅ CLOSED §11

The scrape is a **proxy** for the real question, "what can reach main code from
outside main?", and the proxy is coarse in a second way this fix does not touch: a
name referenced in `sub/` code seeds the main label of the same name **even when the
sub reference resolves sub-locally**. Four labels are in exactly that position —
`sub/fatprim.asm` calls `fat_read_fat_sector` / `fat_alloc_cluster` /
`fat_write_fat_entry` and `sub/format.asm` defines its own `write_sector` — and each
main label of that name is a 4 B `DISKOP_SEL_*` bounce in
[`basic/fat.asm`](../basic/fat.asm) that the sweep cannot reach from `init`.

**Measured 2026-08-21: dropping those four names from the seed set reports 4 spans,
16 B, all PAGE 1** — where the wall reads 11 B. Not shipped: the true main-external
surface is the generated [`sub/basic-resident-abi.inc`](../sub/basic-resident-abi.inc)
(**12** symbols, none of them these four) plus whatever `tools/` looks up by name, and
re-seeding from that is a redesign, not a strip. Each of the four also needs the same
per-span triage the 24 B got — they are 4 of ~15 sibling bounces, and deleting part of
a bounce table is a different kind of claim from deleting an orphan. Filed in
`TODO.md`.

✅ **CLOSED 2026-08-22 by D-SEEDHOLE2 — §11.** The measurement above re-verified
exactly (4 spans, 16 B, all page 1). Two things it got wrong, both in the direction
of *under*-counting: there are **17** sibling bounces, not ~15, and the carve is
**five** spans / **20 B**, not four / 16 — `read_sector` is dead too and was hidden by
a *different* apparatus hole (§11.4). And the "~15 sibling bounces" worry turned out
not to be the hard part: they are not a table at all.

---

## 11. D-SEEDHOLE2 — ✅ a NAME is not a ROUTE (2026-08-22)

**A sixth apparatus fix, and the one §10 filed against itself.** Fix (5) made the
seed scrape read the code column. It did not make the scrape *correct*: the scrape
was still a **proxy** for "what can reach main code from outside main?", and

> **a name referenced in `sub/` CODE seeded the MAIN label of that name even when
> the sub reference resolved SUB-LOCALLY** — which is the normal case, not an odd
> one.

`sub/fatprim.asm`'s `call fat_read_fat_sector` reaches `basic/fat-prim-body.inc`'s
own copy. `sub/format.asm` **defines** its own `write_sector`. Neither has anything
to do with the 4 B `DISKOP_SEL_*` bounce of that name in `basic/fat.asm` — and each
of those bounces was kept alive by it.

### 11.1 The mechanism is an EVICTION, and it will recur

🔴 **The commit that orphans the span is the commit that hides it.** An eviction
moves a *caller* into the sub-ROM and leaves its main-side shim standing; the moved
body's own `call <name>` then reads, to a seed scrape keyed on names, as a live
external reference to the main label. `git log -S` names them:

| commit | what it evicted | shims orphaned |
|---|---|---|
| `d3885b3` | `fat_rand_*` random-access engine → sub-ROM | `write_sector`, `fat_read_fat_sector`, `fat_alloc_cluster`, `fat_write_fat_entry` |
| `0cbf495` | the FILES walk → sub-ROM tenant | `read_sector` |

This is §10's lesson one turn further out. There a **comment** was a seed; here a
**real `call`** is a seed — for the wrong build.

### 11.2 The carve — 5 spans, 20 B, main page 1 free 11 → 31 B

Triaged per span, not on the strength of the hole. Of the **17** sibling bounces
(§10.4 said "~15"), **seven** have no main-closure caller; three of those seven are
live and read otherwise only because the first grep excluded `basic/fat.asm` itself,
where `fia_walk` / `fia_empty` really do call `fia_walked` / `fat_delete`.

**The symmetry question, answered rather than omitted.** §10.4 worried that "deleting
part of a bounce table is not deleting an orphan". They are **not a table**: no
dispatch array, no index — 17 independent 4 B entry points, one per primitive. The
header's only ordering claim is *reach* ("the stubs are contiguous so every `jr`
lands within range"), and deleting stubs only **shortens** that distance, so reach
survives a fortiori. The assembler is the backstop: a shim with a caller fails the
build loudly on an undefined symbol.

⚠️ **The counter-example §10.4 flagged, settled per body.** `basic/format-body.inc`
and `basic/randio-body.inc` both `call write_sector`, and `basic/fat-prim-body.inc`
calls the other three *and defines three of the names*. All three bodies are in
`sub/sub.asm`'s include closure and **none** is in `basic/main.asm`'s — checked per
file, not inferred from the sweep's own answer. `disk/` is a third build entirely,
with its own `disk/fat.asm` defining its own `read_sector`; it includes nothing from
`basic/`.

A stale citation found on the way: the `fat_alloc_cluster` comment cited
`field.asm:576/599` as its "HL is a real caller-read output" evidence. Those lines
are now D-LRVAR's `lrset_notfld`; the HL-reading callers live in
`basic/randio-body.inc`, **on the sub side** — which is precisely why the main shim
went callerless.

### 11.3 The fix — the real surface, not a narrower proxy

`sub/basic-resident-abi.inc` is **GENERATED** (`tools/gen_resident_abi.py`) and is
the **only file in the tree that imports a main address**. Anything else a sub file
names resolves sub-locally, or the sub build does not assemble. So that import list
**is** the sub→main surface rather than a proxy for it — a strictly stronger claim
than "the scrape is coarse", and the reason this is a redesign and not a strip.

Measured before shipping, on the whole set rather than the four:

| | |
|---|---|
| main labels named in `sub/` code | **65** (60 after the carve) |
| of those, resolvable **inside** the sub build | **65** — 12 via the ABI, 53 sub-local |
| **escapes** (neither ABI nor sub-local) | **0** |
| main seeds | **118 → 73** |
| findings after the §11.2 carve | **0**, both builds |

`_assert_sub_resolves_locally()` ships as the **standing control on exactly that
claim**. The invariant is enforced by the assembler — but *"the assembler owns it"*
is the kind of reasoning that rots when nothing re-runs it, and this sweep would go
**quiet** rather than loud if it stopped holding.

⚠️ **Fix (5) is not undone** — `tools/` still seeds, and a `#` comment there must
still not. `_selftest_code_column()` still runs on every invocation.

### 11.4 Falsification — 7 rows, all EXACT, run twice

`scratchpad/seedhole2_knives.py`, every `want` written before the run. No ROM is
built (the sweep decides from sources).

| row | knife | want | got |
|---|---|---|---|
| K1 | the ABI import emptied of equates | rc 1, floor fires | ✅ EXACT |
| K2 | an ABI name that is not a main label | rc 1, "do not resolve" | ✅ EXACT |
| K3 | plant, no mention anywhere | reported by **both** scrapers | ✅ EXACT |
| K4 🔴 | plant + `call` in `sub/` code **+ a sub-local definition** | **new reports, old blind** | ✅ EXACT |
| K5 | plant + `call` in `sub/` code, **not** sub-resolvable | rc 1, the escape control fires | ✅ EXACT |
| K6 🟢 | plant + a `tools/` **string** lookup | **neither reports** | ✅ EXACT |
| K7 🟢 | plant + its name **in the ABI import** | **neither reports** | ✅ EXACT |

K3 is what makes K4 readable. **K4 is the slice**, and it is deliberately the
real-world shape — the same name, called from sub code, *with* the sub-local
definition that makes the call resolve there. K6 and K7 are what make it honest:
without K6, "we dropped `sub/`" could be "we broke the code column too"; without K7,
it could be "we seed nothing but `init`". §6.1's four modes re-verified: gate/clean
rc 0, gate/blind **rc 1 with the allowlist canary firing**, report/clean rc 0,
report/blind rc 0.

### 11.5 What this does NOT close — and one of them is a THIRD hole

🔴 **THE PROLOGUE FALLTHROUGH: EVERY FILE'S FIRST LABEL IS UNCONDITIONALLY LIVE.**
Fix (2) gives each file an always-live **prologue** span (lines before its first
label) so references made there stay visible. But the prologue also gets a
**fallthrough edge into the first label** — and **42 of 49** main files (and 53 of
66 sub) have a prologue that is *comments only*, emitting no bytes at all. A
comment block cannot fall through into anything, so those 42 first labels can never
be reported dead, whatever the seed set says.

This is how `read_sector` hid. It is the first label in `basic/fat.asm`, and it
survived the §11.3 seed rebuild for that reason alone. It was carved anyway, on an
argument that does **not** depend on this hole: no code-column reference exists
anywhere in main's include closure, and its physical predecessor `basic/list.asm`
ends `jp print_string`, an unconditional terminator — so nothing falls into it in
the ROM either.

**Measured 2026-08-22, dropping the fallthrough edge for emitting-nothing prologues:**
main **+1 span** (`read_sector`, now carved), sub **2 spans / 20 B** —
`fat_io_open` (`basic/fatio-body.inc`, 4 B) and `fmt_menu_text` (16 B, *already* the
allowlist's vacuity canary, so only 4 B is new). Not shipped here: this is a change
to the **span model**, whose failure direction is *under*-seeding — reporting live
code as dead — so it needs its own knives and its own per-span triage, exactly as
§10 shipped carve-first and filed this one. Filed in `TODO.md`.

⚠️ **The `tools/` seed arm is an intersection, not an assertion** — see §2.2. A main
routine renamed out from under a `tools/` by-name lookup drops out of the seed set
silently. It over-seeds by construction, so the failure is a missed finding rather
than a false one, but §2.2's blanket *"every seed name is asserted to resolve"* was
**never true of that arm** and now says so.

⚠️ **`disk/` is a third build this gate does not walk at all.** Out of scope since
§7, restated here because the denominator moved: `disk/disk.asm` includes nothing
from `basic/`, so it cannot make a main span live — but nothing checks that.
