<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# D-CASTAIL — the tape twins of D-RUNTAIL

Closes the residual filed as [spec-basic-runtail.md](spec-basic-runtail.md) §9.
Reference reading: [castail-msx1-characterization.md](castail-msx1-characterization.md).
Gate: `make castail-acceptance`
([`probes/basic/basic_probe_castail.py`](../probes/basic/basic_probe_castail.py)).

## 1. What was filed, and what it turned out to be

Filed (§9): *"`dl_cas_close` (`LOAD"CAS:x",R`) and `dr_is_cas` (`RUN"CAS:x"`) end
in the identical `jp run_prog` from a statement context, so defect A is
structurally present there too"*, blocked on two things: **no cassette
instrument**, and **no measured CF-out contract on `do_tape_prog`**.

Measured: **both defects are present on tape, and both are now scored.** Six of
nine readings diverged from *two* independent references that agree with each
other row for row (characterization §1). The filed reading was right about the
code and understated the blocker on one side and overstated it on the other:

* 🟢 **The instrument already existed.** §9 says `omsx_repl.run_cases` "mounts a
  disk, not a `.cas`" — true of its signature, false of the module. The
  `prologue` seam runs raw Tcl before the timeline and `basic_probe_lnblank`
  already mounts tapes with `cassetteplayer insert`. **No library change.**
* 🔴 **But the failure ROW was the real problem, and it is not the one §9
  imagined.** There is no tape twin of `run-miss`: on an MSX1 a missing tape file
  is *not an error*, it is a search that runs past the end of the tape and waits
  forever (characterization §6). The only tape failure a reference **reports and
  returns from** is an operator **Ctrl-STOP**, which is therefore the only shape
  in which "did the resident program run afterwards?" is a question a reference
  can answer at all.

And the instrument found a divergence nobody had recorded: **zerobas prints no
tape-search progress line** (`Found:`/`Skip :`) where both references do
(characterization §5). Pinned, filed, **not** fixed here.

## 2. The mechanism — identical to D-RUNTAIL's, on two more call sites

`RUN"CAS:x"` is not the REPL's `RUN` command either (`is_cmd` needs the byte
after `RUN` to be end/space/`:`, and it is `"`), so it is crunched and reaches
`do_run` → `dr_is_cas` as a **statement**. `jp run_prog` there enters the run
loop **nested** inside the enclosing line's own loop and destroys `CURLINE`; on
return the enclosing loop resumes, walks off the loaded program's end marker
into `CURLINE := $0000`, finds the page-0 ROM's non-zero `DI / JP` there and
dispatches the byte at `$0004` as a BASIC statement. Symptom: `Illegal function
call in 3346` after **every** `RUN"CAS:x"` / `LOAD"CAS:x",R`, hit and abort
alike. The full chain is [runtail-msx1-characterization.md](runtail-msx1-characterization.md)
§6 and is not re-derived here.

**The same two independent defects, on the tape path:**

* **A — the nested entry** (`dl_cas_close`, `dr_is_cas`). Three hit rows.
* **B — the failed load runs anyway.** `do_tape_prog`'s failure exits `jp
  load_error`; `load_error` prints and **returns**, and its `ret` is
  `do_tape_prog`'s return, so both call sites fall into `jp run_prog` and run
  whatever was resident. Two `-res` abort rows.

## 3. The change

### 3.1 A — the two tape sites adopt `run_prog_top`

`run_prog_top` already exists (`basic/cload.asm`, D-RUNTAIL §3.1): `ld
sp,(SAVSTK)` + `jp run_prog`, the prompt-clean depth `dispatch_line` records
before any statement runs. Both tape sites change `jp run_prog` → `jp
run_prog_top` at **zero** delta. `SAVSTK` is valid at both for the same reason it
is at the disk sites, and `autoexec_run` keeps its plain `jp run_prog` for the
same reason it did there (called from `init`, before the REPL has written
`SAVSTK`, with no enclosing loop to corrupt).

### 3.2 B — `do_tape_prog` gets a CF-out contract, and it REUSES `dpl_err`

The contract is the disk one, stated on `do_tape_prog`'s own exits: **CF set =
the load failed and has already reported.**

🔴 **`load_error` ITSELF IS STILL NOT TOUCHED, FOR THE REASON D-RUNTAIL §3.2
GIVES**: ~50 `jp`/`call` sites across seven files, several of which resume into
their caller on purpose. A `scf` inside it would change the returned CF for all
of them.

🎯 **AND THE PRODUCER SHIM ALREADY EXISTS.** `dpl_err` is exactly `call
load_error` / `scf` / `ret` — five bytes that say "reported, and failed". Every
tape failure exit repoints from `load_error` to `dpl_err` at **zero delta**, so
defect B's producer costs **0 B** on the tape path. The `dpl_` prefix is now
shared by both program loaders; recorded in its header comment rather than
renamed, because a rename would churn eight disk sites and make
[spec-basic-runtail.md](spec-basic-runtail.md) §3.2's table stale for nothing.

| exit | was | becomes | Δ |
|---|---|---|---|
| `cas_open_match` CF (**the Ctrl-STOP abort — the measured one**) | `jp c,load_error` | `jp c,dpl_err` | 0 |
| header id neither `$D3` nor `$EA` | `jp nz,load_error` | `jp nz,dpl_err` | 0 |
| `CLOAD?` verify of an `$EA` file | `jp nz,load_error` | `jp nz,dpl_err` | 0 |
| data-block `TAPION` failed | `jp c,load_error` | `jp c,dpl_err` | 0 |
| `ctp_line` `TAPIN` failed | `jp c,load_error` | `jp c,dpl_err` | 0 |
| `ctp_link_err` / `ctp_err_pop` | `jp load_error` | `jp dpl_err` | 0 |
| `cas_ascii_load` setup / drive failure (×2) | `jp c,load_error` | `jp c,dpl_err` | 0 |
| `ctp_oom` (tokenised store overflow) | `jp print_msg` | `call print_msg` / `scf` / `ret` | +2 |
| `verify_error` (`CLOAD?` mismatch, 2 sites) | `jp print_msg` | `call print_msg` / `scf` / `ret` | +2 |
| `ctp_done` (tokenised success) | `call relink` / `ret` | `call relink` / `or a` / `ret` | +1 |
| `ctp_verify_done` clean (`or a` / `ret z`) | — | **unchanged**: `or a` already cleared CF | 0 |
| `cas_ascii_load` success (`ret` after a `jp c`) | — | **unchanged**: CF already clear | 0 |

⚠️ **`verify_error` is edited in place and that is safe HERE and only here**: its
only two callers are both inside `do_tape_prog` (`ctp_verify_done`, `ctp_oom`),
verified by grep over `basic/*.asm`. It is the opposite of `load_error` and the
reason is a count, not a principle.

⚠️ **COVERAGE, STATED EXACTLY.** Exactly **one** of those failure exits is
exercised by a row: `cas_open_match`'s CF, via Ctrl-STOP. The rest get the
contract for **completeness** — an exit that leaves CF undefined is a landmine
for the next caller — and no row scores them. The tokenised (`$D3`) exits
(`ctp_done`, `ctp_oom`) are not reachable from any row here at all, because the
references **hang** on a tokenised tape (characterization §6/§7); K-DONE-CAS
below is a declared **predicted miss** rather than a knife with a red set.
This is not claimed as more than it is ([[a-rule-can-claim-more-than-its-evidence]]).

### 3.3 The whole diff, priced

| site | change | bytes |
|---|---|---|
| `basic/cload.asm` `dl_cas_close` | `ret c`; `jp run_prog_top` | +1 |
| `basic/cload.asm` `dr_is_cas` | `ret c`; `jp run_prog_top` | +1 |
| `basic/cload.asm` `do_tape_prog` + `cas_ascii_load` | 9 exits repoint to `dpl_err` | 0 |
| `basic/cload.asm` `ctp_done` | `or a` | +1 |
| `basic/cload.asm` `ctp_oom` | `call`/`scf`/`ret` | +2 |
| `basic/cload.asm` `verify_error` | `call`/`scf`/`ret` | +2 |
| **total** | | **+7** |

## 4. Predicted GREEN, at exact values (fixed BEFORE the change)

| measurement | baseline `3e84afa` | predicted after |
|---|---|---|
| `castail-acceptance` | *(new)* | **9/9 scored readings agree**, 8 cases, 3 positive controls, 1 pinned divergence row, exit 0 |
| `runtail-acceptance` | 9/9 | **unchanged**, exit 0 |
| `fat-error-acceptance` | 8/8 + 5 dir checks, 8 of 8 verb controls | **unchanged**, exit 0 |
| main low region free | 3 B | **3 B** (no low-region code) |
| main page 1 free | 172 B | **165 B** (172 − 7) |
| sub p0 / p1 free | 3843 / 1540 | **unchanged** |
| `disk.rom` / `sub.rom` hash | `2c630d3d…` / `6ea374de…` | **unchanged** — no disk-ROM or sub-ROM source moves |
| `basic-reloc.rom` / `zerobas-main-eu.rom` hash | `9af44b5a…` / `e60a4248…` | **both change** |
| closure | `718+15 / 582+41` | **unchanged** |
| `preflight-check` | 181/86/95/95/0 | **unchanged** |
| `injector-check` | 330 | **331** — the new probe is a file under `probes/` |
| `unit-test` | 58 | **unchanged** |
| `deadcode` main spans / seeds | 1566 / 287 | **1566 / 287** — no new label (the producer is reused), and the slice writes no words under `sub/` or `tools/`, which is what moves the seed count |
| `audit-citations` files swept | 716 | **719** — three new files, all swept suffixes (`.py`, `.md`, `.md`) |
| `audit-citations` basic files / provenance-bearing | 107 / 185 | **unchanged** — no new file under `basic/`, and `cload.asm` already cites |
| `dskmsg` / `diskbasic` / `lptverb` | 5/5 · 34/34 · 44/44 | **unchanged** |

## 5. The knives — predicted RED **and** predicted GREEN survivors

Every cut is **byte-neutral** (`dev-workflow.md` §Knives), the subject is the
probe invoked directly (never `make`), each is run **twice**, and the runner
hashes all four ROMs after every cut build: a cut that lands byte-identical is
**DID-NOT-HAPPEN**, not a miss. The runner parses **all three** of the probe's
report shapes (exit 0/1 carry a tally line; exit 2 is a complete report with
`....` rows and **no** tally), and restores in a `finally`.

| # | cut | predicted RED | predicted GREEN survivors | rc |
|---|---|---|---|---|
| **K-CAS-A1** | `dr_is_cas`'s `jp run_prog_top` → `jp run_prog` | `cas-run-hit`, `cas-run-hit-res` | `cas-loadr-hit` (`dl_cas_close`'s own repoint — this SEPARATES the two sites), the 3 abort rows, both controls, the pin | 1 |
| **K-CAS-A2** | `dl_cas_close`'s `jp run_prog_top` → `jp run_prog` | `cas-loadr-hit` | both `RUN"CAS:"` hit rows, the 3 abort rows, both controls | 1 |
| **K-CAS-B1** | `dr_is_cas`'s `ret c` → `nop` | `cas-run-brk-res` | 🔴 **`cas-run-brk` HOLDS** (nothing resident → running the store is silent), `cas-loadr-brk-res` (its own `ret c`), all 3 hit rows | 1 |
| **K-CAS-B2** | `dl_cas_close`'s `ret c` → `nop` | `cas-loadr-brk-res` | `cas-run-brk-res`, `cas-run-brk`, all 3 hit rows | 1 |
| **K-PROD** | `dpl_err`'s `scf` → `or a` — the SHARED producer lies | `cas-run-brk-res`, `cas-loadr-brk-res` | `cas-run-brk`, all 3 hit rows, both controls | 1 |
| **K-ASC** | `cas_ascii_load`'s `jp c,dpl_err` → `jp dpl_err` — a SUCCESSFUL tape load reports failure | `cas-run-hit`, `cas-run-hit-res`, `cas-loadr-hit`, `cas-load-plain` | `cas-load-plain:listing` (the program still ARRIVED — only the run is skipped), the 3 abort rows, `bare-run` | **2** |
| **K-DONE-CAS** | `ctp_done`'s `or a` → `scf` | **nothing — a declared PREDICTED MISS** | every row | 0 |

⚠️ **K-CAS-A1 exits 1, not 2, and that is deliberate.** Under it `cas-run-hit`
reads `ZQ9 / Illegal function call in 3346`, which *contains* `ZQ9`, so its
control holds and the row merely DIFFs — D-RUNTAIL predicted 2 here and measured
1 (§6.4a). The control is a **containment** check by design: it fires when the
program produced no output at all, which is the dead-subject case it exists for.

⚠️ **K-ASC is the proof that the positive controls are load-bearing.** It makes
every hit row read `<load-failed>` — a perfectly agreeable answer for a machine
that runs nothing — and it is caught only because `cas-run-hit`'s reading is
required to contain `ZQ9` ([[gate-whose-answer-is-an-error-passes-a-dead-subject]]).
It is the only knife that exits 2, i.e. reports an instrument fault rather than a
regression, which is what a broken control is.

⚠️ **K-DONE-CAS IS A PREDICTED MISS AND IS RUN ANYWAY.** The tokenised `$D3`
success path is unreachable from every row in this battery (the references hang
on a tokenised tape), so its contract exit is shipped **unmeasured** and says so.
The knife is run to make the ROM-hash guard prove the cut reached the artifact:
that separates *"the cut landed and reddened nothing"* — the finding — from
*"the cut never happened"* ([[knife-runner-needs-a-rom-hash-guard]], and
`spec-basic-msgmigrate.md` §8's **DID-NOT-HAPPEN**).

⚠️ **K-PROD cuts a site the DISK battery also depends on.** `dpl_err` is shared,
so that cut also reds `runtail-acceptance`'s `run-miss-res` / `loadr-miss-res`.
The subject here is the castail probe; the disk effect is stated, not scored.

## 6. As-built

### 6.1 The change, and the walls

**+7 B on main page 1, to the byte** — the §3.3 price was exact. Measured from
clean (`rm -rf build && make basic-reloc`):

| wall | before | after |
|---|---|---|
| main low region | 3 B | **3 B** |
| main page 1 | 172 B | **165 B** |
| sub page 0 | 3843 B | **3843 B** |
| sub page 1 | 1540 B | **1540 B** |

ROM hashes: `disk.rom 2c630d3d…` and `sub.rom 6ea374de…` **unchanged** as
predicted (no disk-ROM or sub-ROM source moves); `basic-reloc.rom`
`9af44b5a… → 86ccd666…` and `zerobas-main-eu.rom` `e60a4248… → 7dfedd72…`.
The ROM moves, so the emulator gates are meaningful and were run in full.

🎯 **Defect B's producer cost 0 B**, exactly as §3.2 said it would: nine failure
exits repointed from `load_error` to the existing `dpl_err`, which already said
"reported, and failed" in five bytes written for the disk half. The whole +7 is
two `ret c`, one `or a`, and two `call`/`scf`/`ret` conversions on exits **no row
here scores** (§3.2's completeness half).

### 6.2 Predictions, scored

| prediction | outcome |
|---|---|
| `castail-acceptance` 9/9, exit 0 | ✅ **9/9 scored readings agree**, 8 cases, 3 positive controls, 1 pinned divergence row, exit 0, stable at `--repeat 2` on all three sides |
| page 1 172 → 165 B | ✅ exact |
| low / sub p0 / sub p1 unmoved | ✅ 3 / 3843 / 1540 |
| `disk.rom` + `sub.rom` hashes unchanged | ✅ |
| `runtail-acceptance` 9/9 unchanged | ✅ |
| `fat-error-acceptance` unchanged | ✅ 8/8 + 5 dir checks, 8 of 8 verb controls |
| `audit-citations` 716 → **719** files swept | ✅ exact |
| `injector-check` 330 → **331** | ✅ exact |
| `deadcode` main **1566 spans / 287 seeds** | ✅ exact — both halves |
| `preflight-check` 181/86/95/95/0, `unit-test` 58 | ✅ unchanged |
| `audit-citations` basic **provenance-bearing 185** | ❌ **186** — the slice's own footprint (§6.5) |
| corpus otherwise unmoved | ✅ 19 gates, all PASS — see §6.5 |

### 6.3 🎯 The knives — 7 designed, 7 run, each TWICE, both rounds identical

| # | cut (all byte-neutral) | rc | RED | HELD |
|---|---|---|---|---|
| **K-CAS-A1** | `dr_is_cas`'s `jp run_prog_top` → `jp run_prog` | 1 | `cas-run-hit`, `cas-run-hit-res` | 8 rows incl. `cas-loadr-hit` and both other controls |
| **K-CAS-A2** | `dl_cas_close`'s `jp run_prog_top` → `jp run_prog` | 1 | `cas-loadr-hit` | 9 rows, **both `RUN"CAS:"` hit rows included** |
| **K-CAS-B1** | `dr_is_cas`'s `ret c` → `nop` | 1 | `cas-run-brk-res` | 9 rows, **`cas-run-brk` and `cas-loadr-brk-res` included** |
| **K-CAS-B2** | `dl_cas_close`'s `ret c` → `nop` | 1 | `cas-loadr-brk-res` | 9 rows, **`cas-run-brk-res` included** |
| **K-PROD** | `dpl_err`'s `scf` → `or a` | 1 | `cas-run-brk-res`, `cas-loadr-brk-res` | 8 rows, all 3 hit rows + both controls |
| **K-ASC** | `cas_ascii_load`'s `jp c,dpl_err` → `jp dpl_err` | **2** | all 3 hit rows, `cas-load-plain`, **and the PIN** | `cas-load-plain:listing`, the 3 abort rows, `bare-run` |
| **K-DONE-CAS** | `ctp_done`'s `or a` → `scf` | 0 | **nothing — the declared predicted miss** | every row |

All seven reached the artifact (the ROM hashes moved on every cut build, so the
runner's guard never had to declare DID-NOT-HAPPEN — **including K-DONE-CAS**,
which is the whole reason that knife is run), and the tree hashed back to
baseline after the restore.

🎯 **A1/A2 AND B1/B2 SEPARATE THE TWO CALL SITES, ON BOTH DEFECTS.** Cutting
`dr_is_cas`'s repoint reds only the `RUN"CAS:"` rows while `LOAD"CAS:",R` stays
green on `dl_cas_close`'s own, and vice versa; the same pair of cuts separates
the two `ret c` consumers. K-PROD then reds **both** abort rows by lying at the
shared producer. That is the evidence that four independent edits are each
load-bearing, which no single cut could give.

🎯 **K-ASC IS THE PROOF THAT THE POSITIVE CONTROLS ARE LOAD-BEARING.** A
successful ASCII tape load reporting failure makes every hit row read
`<load-failed>` — a perfectly agreeable answer for a machine that runs nothing —
and it is caught only because `cas-run-hit`'s reading is required to contain
`ZQ9`. It is the only knife that exits **2**, i.e. reports an instrument fault
rather than a regression, which is what a broken control is.

🎯 **AND `cas-run-brk` HELD UNDER K-CAS-B1 AND K-PROD, EXACTLY AS PREDICTED.**
The row with nothing resident cannot see defect B at all: running an **empty**
program is silent, so "refused to run" and "ran an empty store" print the same
string. In D-RUNTAIL that cost a wrong prediction and became
[[an-empty-program-hides-a-wrong-run]]; here it was **predicted before the run**
and the `-res` rows were built because of it. The lesson transferred.

### 6.4 🔴 One prediction was WRONG, and the pin is why it matters

**K-ASC also reds `cas-load-plain:search` — the PINNED row — and §5 did not list
it.** Measured, twice. The pin says zerobas reads `<nothing>` where the
references read `Found:RT`; under K-ASC zerobas prints its error on that very
line, so the pinned reading moves and the pin **ROTS**.

That is the pin working, not failing: it is a per-side exact match, so it fires
whenever *either* the divergence closes *or* the subject's own reading moves.
The prediction treated it as inert — as if a row excluded from the agreement
tally were also excluded from measurement — and that was the error. A pinned
divergence is a **second detector on the same line**, not a comment.

### 6.5 Corpus — 19 gates, sequential from clean, all PASS

`unit-test` **ALL 58 files** · `audit-citations` CLEAN (**719** files swept —
predicted exactly) · `preflight-check` **181/86/95/95/0** · `injector-check` ALL
PASS, **331** files · `latch-check` **16/16** · `deadcode` main **1566 spans /
287 seeds** → 0 dead, sub 1512/102 → 0 dead (+1 allowlisted) ·
`lnblank-acceptance REPEAT=2` · `lnblank-say-acceptance` · `logicops-acceptance`
· `float-acceptance` · `linemax-acceptance` · `dexp5-pin` · `editverb-acceptance`
· `lptverb-acceptance` **44/44** · `dskmsg-acceptance` **5/5** ·
`diskbasic-acceptance` **34/34** · `fat-error-acceptance` **8/8 scored + 5
directory checks, 8 of 8 verb controls** · `runtail-acceptance` **9/9** ·
`castail-acceptance` **9/9 + 1 pin**.

⚠️ **One corpus count moved and §4 predicted it unchanged.** `audit-citations`
reports `basic` **186** provenance-bearing blocks where §4 said 185. It is the
slice's own footprint — `cload.asm`'s new `do_tape_prog` contract block cites
`spec-basic-castail.md` — and it was derivable before the run, so it is a miss,
not a surprise. **D-RUNTAIL made the identical miss one slice ago** (184 → 185,
its §6.5); predicting "unchanged" for a count whose definition is *"comment
blocks that cite a document"*, in a slice that writes comment blocks citing a new
document, is a habit rather than a prediction. The counts that were genuinely
hard — `deadcode`'s span and seed counts — were both predicted exactly, because
this slice adds **no new label** (the producer is reused) and writes nothing
under `sub/` or `tools/`.

## 7. Out of scope, said explicitly

* **The tape-search progress line** (`Found:`/`Skip :`), which zerobas does not
  print. Found by this slice, **pinned** by the gate, filed in `TODO.md`, not
  fixed: it is a property of the search, not of the tail after a load.
  ✅ **CLOSED 2026-08-07 by D-CASSEARCH** ([spec-basic-cassearch.md](spec-basic-cassearch.md)),
  for **57 B in sub page 1** — not the main page-1 bytes this slice's residual
  first guessed at. §6.4's pin ROTTED on the fix, exactly as designed, and was
  **re-measured and re-pinned**, never loosened.
* **`LOAD"CAS:"` accepting a tokenised tape**, the divergence D-DOTGAPS filed —
  the faithful behaviour is a hang, so no row can carry it.
* **The wording of the failure message.** Quarantined; normalised to one token
  per side so these rows can be scored on shape.
* **`CLOAD` / `CLOAD?` / `MERGE"CAS:"`.** `CLOAD` reaches `do_tape_prog` by `jp`
  and has no `,R`, so it consumes no return carry and has no defect A. The other
  two are separate verbs with their own batteries; their `do_tape_prog` exits
  carry the new contract, and no row here scores them (§3.2).
