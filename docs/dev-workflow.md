# zerobas dev workflow

How to add a feature to the interpreter and prove it correct. This is the
procedural companion to [`PROVENANCE.md`](../PROVENANCE.md) (the *what is
allowed* rules) and [`TODO.md`](../TODO.md) (the *what is left* list).

It exists so a fresh session can ramp fast: the per-feature knowledge below was
learned the hard way and is **not** otherwise recoverable from the code.

**Two deliverables, not one.** Implementing the feature is half the job; the
clean-provenance **documentation** the work yields — a behavioural spec, a
characterisation note, a corrected finding about how the original actually behaves —
is a **co-equal deliverable**, not a byproduct (see [`MISSION.md`](../MISSION.md)).
When a probe teaches you something the published sources don't capture, write it down
where it belongs (the component spec / characterisation doc), not just into the code:
where good documentation didn't exist, producing it is part of the point.

## Per-feature checklist

Each TODO item is largely independent — do one per session, and finish with:

1. **Read the anchors first, in order:** `README.md`, `PROVENANCE.md`,
   `TODO.md`, `basic/sysvars.inc`, then the source files the feature touches
   (`basic/interp.asm` for tokeniser/dispatch, `basic/expr.asm` for expression
   factors, `basic/program.asm` for stored-line handling).
2. **Honour the clean-room rule.** Every new constant / token byte / address /
   algorithm must trace to an allowed source, cited inline at its definition.
   Allowed: MSX2 Technical Handbook, MSX Assembly Page (`map.grauw.nl`), a
   public MSX-BASIC *language* reference, hardware datasheets, C-BIOS sources,
   or this project's own black-box oracle observations. **Forbidden:** any
   MSX-BASIC / GW-BASIC / BASIC-80 source or disassembly, and any reference
   BIOS / BASIC ROM disassembly. A reference ROM is only ever an oracle:
   identical inputs in, observed outputs out.
   **Cite only PUBLIC artifacts.** A citation must resolve to something a public
   auditor can reach — an in-repo finding/probe/doc or a published source — never
   a probe, spec, or note that lives only in the private `msx-preservation`
   workbench. A public finding whose provenance dead-ends in private is a chain
   break: re-home the probe (re-rooted, 0BSD; see `probes/`) or cite the public
   primary instead. `make audit-citations` enforces this (the PRIVATE-REF check)
   across the asm, every `PROVENANCE.md`, and the probe sources.
3. **Quarantine own-design.** If correct MSX behaviour needs a forbidden source
   to reproduce, ship a documented simplification instead and mark it
   `quarantined` in `PROVENANCE.md` (e.g. the USR integer-only convention,
   unsigned `/`, div-by-zero → 0).
4. **Build clean:** `rm -rf build && make basic-reloc` must assemble with no
   warnings and print its two wall numbers (low / page-1 free).
5. **Prove crunch is still byte-identical** (see below) — any tokeniser change
   can regress this.
6. **Run the regression probes** (control flow / loops / data / statements) —
   confirm no existing behaviour broke.
7. **Functional-test the new feature** in openMSX (see harness recipes).
8. **Update `TODO.md`** (check the item, note divergences) and append a
   `PROVENANCE.md` row. **If the work established something new about how the
   original behaves** (a quirk, an oracle-confirmed contract, a corrected finding),
   it owes **two distinct writes, not one** (see
   [`documentation-deliverable.md`](documentation-deliverable.md)): the **notebook**
   entry (the dated finding / characterisation note — provenance trail) *and*, once
   the contract is settled, its distillation into the component's **product spec**
   (`<component>/docs/spec-*.md`). The notebook is scaffolding; the spec is the
   deliverable. Writing only the notebook is how the doc deliverable drifts. Do
   **not** commit unless asked.

**Auditing it afterwards.** Item 2's inline citation is what makes compliance
*provable* later. To verify a target (especially after a sub-agent lands asm),
see [`clean-room-audit.md`](clean-room-audit.md): the **paper trail** check walks
the asm→finding→probe chain for provenance (cheap, read-only — the routine gate),
and the **full verify trail** adds re-running the probes for correctness (heavy,
milestone-gated). Probe execution does **not** catch a provenance breach — that
is what paper trail is for. Run the mechanical pre-check first — `make
audit-citations` (forbidden-source scan + per-file attestation, gating; disk
section-citation presence, advisory) — so the cheap, scriptable half can never
silently lapse between manual passes. A clean `make audit-citations` is the floor,
not the audit: it cannot make the "is each probe genuinely black-box?" judgement,
which is still a human paper-trail pass.

You do not have to remember to run it: since 2026-08-06 it is a step of `make
basic-reloc` and of CI. It was on-demand-only for its first 761 commits and spent
268 of them red ([`spec-audit-citations-gate.md`](spec-audit-citations-gate.md)).
⚠️ It exits **2**, not 1, when its own rule self-test or its file-count floor
fails — that means the instrument is broken and nothing below it was measured.

**Never paste a decoded instruction listing into a doc or a comment**, whatever
its source. Since 2026-08-06 the same target sweeps **every** first-party text
file for the shape — a run of ≥2 consecutive `<address>  <mnemonic>` lines — and
refuses. State the observation instead: the PC range, the watchpointed read, the
observed value, the branch **target**. The forbidden-word scan is blind to
listings (measured: 0 recall on every recorded breach), so this is the only
mechanical thing standing between a hand-decode and the tree
([`spec-audit-citations-docs.md`](spec-audit-citations-docs.md)). If the decoded
code is genuinely from an admissible source, allowlist it **with the reason
written down** in `tools/citations-listing-allow.txt` — do not reword around the
gate.

### Delegating asm to a sub-agent — embed the firewall in the brief

The one provenance breach we have had (`provider-oracle-scope.md` §8.37) came
from a sub-agent that disassembled `MSXDOS.SYS` because its brief did **not**
carry the clean-room rule. The audit *caught* it after the fact; the cheaper fix
is to not let it happen. So when you spawn an agent to write or modify assembly,
its brief **must** state, up front:

- the clean-room rule (item 2 above) and the **forbidden** list — a reference ROM
  / `MSXDOS.SYS` / `COMMAND.COM` is **only ever an oracle**: inputs in, observed
  outputs out, never disassembled or byte-copied;
- the requirement to cite every new constant/address/algorithm inline at its
  definition (item 2), so the result is paper-trail-auditable;
- that producing forbidden-sourced asm fails the task even if it is *correct* and
  the probes pass — correctness never launders provenance.

Then audit what it lands (`make audit-citations` on the diff, then a paper trail).

## Build

```sh
make            # everything needing no C-BIOS checkout: build/disk.rom +
                #   build/sub.rom + tape/zerobas-tape-msx1.ips/.bps
make disk       # just build/disk.rom
make patches    # just the shipped BASIC .ips/.bps (needs CBIOS=<checkout>)
make release    # make + make patches
make machines   # install openMSX configs into ~/.openMSX (separate: see below)
make install    # make + make machines
```

Build artifacts (the ROMs) land in the gitignored `build/` dir, never the repo
root — so a stale copy can't linger where a probe or installer would pick it up.
The tracked `zerobas-main-eu.ips/.bps` deliverables stay at the root. REGENERATING
them needs a C-BIOS source checkout (`CBIOS=<path>`), which is why they are in
`make release` and not `make`; APPLYING them needs nothing but openMSX (the pristine
ROM they are diffed against is byte-identical to openMSX's own bundled
`cbios_main_msx1_eu.rom`). The tape patch target still just needs a stock C-BIOS ROM
(auto-detected from openMSX, or `STOCK=<path>`).

The openMSX machine configs are a separate `make machines` target, not part of
`make`: they embed absolute paths to your openMSX ROMs + this repo, so they're an
install regenerated per environment, not a portable artifact. `make machines`
writes, per C-BIOS MSX1 region, a `*_BASIC` and a `*_BASIC_DISK`; the
`*_ZEROBASDISK` provider-oracle is a test machine (`make machines-oracle`), not a
release config.

Assembler is pasmo. A linter hook auto-adds SPDX / copyright headers to new
source files — don't hand-write them.

## Knives — falsification runners (READ THIS BEFORE WRITING ONE)

Every slice here falsifies its own claim by **deleting the code under test** and
re-running the gate. The runner that does it is a throwaway script in the
scratchpad, never committed (`docs/spec-probe-injjudge.md` §1.3) — which is why
its discipline lives *here* instead of in a shared module, and why the same
faults keep being re-derived one runner at a time. The rules below are each a
landed defect, not advice.

**The runner:**

* **The subject is the PROBE, invoked directly — never `make <gate>`.** `make`
  exits **2** for any failed recipe, so a runner reading `make`'s status cannot
  tell rc 1 (the tree regressed) from rc 2 (the instrument broke). 8 of 11
  knives once scored CUT for that reason alone (`spec-probe-injjudge.md` §6.2).
* **Restore from a scratchpad SNAPSHOT, never `git checkout --`** — a knife run
  in a dirty tree otherwise reverts the slice instead of the cut
  (`spec-basic-lnref.md` §7.0).
* **Build BEFORE taking the baseline.** Restoring a snapshot touches mtimes, and
  `omsx_preflight` then (correctly) refuses the run as stale.
* **Capture the baseline through the probe's own parse path, and refuse a SHORT
  one** — a runner whose row set comes back empty cannot distinguish that from
  "the knife moved nothing" (`[[knife-runner-false-negatives]]`).
* 🔴 **AND APPLY THAT TO THE KNIFED RUN, NOT ONLY THE BASELINE.** A probe that
  **crashes mid-report** prints a *prefix* of its rows and exits 1 — which a diff
  against the baseline renders as *"twenty rows moved"*, i.e. a spectacular CUT.
  Require the probe's own tally/footer line in every knifed run and **abort**
  without it. Measured 2026-08-07: a knife set scored three cuts as enormous CUTs
  when the probe was actually raising `AttributeError`.
  ⚠️ **The reason that lands here and not in the probe:** a control's
  FAILURE-formatting branch only ever runs **under a knife**, so a latent
  traceback there is invisible to every green run and to the whole corpus. Knives
  are the only thing that executes a gate's failure paths — expect to find bugs
  in the *gate* there, not only in the tree.
* **A failed build ABORTS rather than scoring** — a knife scored against a stale
  ROM reads as a CUT.
* **Score a predicted GREEN set as well as a predicted RED set.** A run where
  *nothing* moved, greens included, is an apparatus result, not a measurement.
* **Run every knife TWICE.** D-FEVERB's K-FE1 scored CUT in round 1 and MISS in
  round 2 from the identical cut; nothing else caught it.

🔴 **AND THE ONE THAT IS NOT OPTIONAL: HASH THE ROMs AFTER EVERY CUT BUILD.**
*"A failed build aborts"* is the wrong guard, because **`make` can exit 0 having
rebuilt nothing.** GNU Make 3.81 (what macOS ships, and what this tree builds
with — there is no 4.x here) compares mtimes at **one-second granularity**, so
any edit-then-build completing inside one tick is silently skipped and the knife
scores the **pre-cut** ROM.

```python
def assert_cut_reached(name, base_hashes):        # base_hashes: all four ROMs
    if rom_hashes() != base_hashes:
        return "incremental"
    subprocess.run(["rm", "-rf", "build"], cwd=REPO)   # make skipped it
    build()
    if rom_hashes() == base_hashes:
        sys.exit(f"ABORT {name}: the cut reached no ROM -- nothing was measured")
    return "CLEAN REBUILD (mtime race)"
```

⚠️ **`rm -rf build` alone is NOT the whole fix, and the record says it is.**
`spec-basic-dotline.md` §7 concluded *"the repo's own standing rule is the whole
fix — always `rm -rf build` first"*. **Measured 2026-08-07 (D-FEVERB): it is
not.** A cut that lands in a **comment** — the ordinary mis-siting, since cut
strings usually carry their trailing comment — produces byte-identical ROMs
**from a clean build**, and a runner without the hash check scores it as a MISS.
Clean building fixes the *race*; only the hash separates *"the cut reached the
artifact and reddened nothing"* (a finding) from *"the cut never reached the
artifact"* (nothing was measured). The distinction has a name in
`spec-basic-msgmigrate.md` §8: report it as **DID-NOT-HAPPEN**, not as
"reddened nothing".

⚠️ **A clean rebuild costs 5.1 s here** (measured; incremental is 0.08 s), so
there is no performance reason to prefer an incremental build in a runner. Do
both: `rm -rf build` per cut *and* the hash check.

**Prefer byte-neutral cut sites** — a `jr`/`call` target swap, or an
equal-length instruction. Inserting bytes pushes everything below down and takes
some nearby `jr` out of range; D-DSKMSG lost two knife sitings to exactly that,
and a build that fails is a knife that scored nothing.

⚠️ **A knife whose predicted result is "nothing moves" is indistinguishable from
a build that did not happen.** Those are the ones the hash check exists for. If
the miss is genuine, say so as a **predicted miss** and record what the tree
cannot see (`[[rule-gated-structurally-has-no-knife]]`).

## The validation harness (probes/)

The emulator-driven oracle harness lives **in this repo**, under `probes/`
(see [probes/README.md](../probes/README.md)). It is the heavy oracle layer that
complements the fast emulator-free `make unit-test`:

```
probes/
  lib/omsx_run.py                        # headless openMSX driver (--bp trigger path)
  lib/omsx_repl.py                       # typing-free KEYBUF REPL driver (VRAM probes)
  lib/cas_encode.py                      # build_cas() — make a .cas payload
  basic/basic_probe_*.py                 # differential + functional probes
  disk/disk_probe_*.py                   # zerobas-disk vs CF-3300 / MSX-DOS 1
  tape/bios_probe_*.py                   # cbios-tape cassette path
```

### omsx_repl.py — the typing-free REPL driver (use for VRAM-scraping probes)

A probe that types BASIC at the prompt and reads the result from VRAM must drive
lines through `omsx_repl.run_case(machine, mode, lines)`, **not** `omsx_run
--type`. `type` emulates the keyboard MATRIX on a fixed emulated-time schedule and
is timing-fragile (leading key doubles; Enter swallowed mid-type — the F3 S3b
`varptr` flake). `omsx_repl` injects each line into the BIOS type-ahead buffer
(`KEYBUF $FBF0` + `GETPNT`/`PUTPNT`; published MSX2-TH contract, no disasm) so the
ROM tokenises it with no matrix scan — deterministic, no per-char schedule.

```sh
python3 probes/lib/omsx_repl.py --selftest C-BIOS_MSX1_EU_REPACK_DISK   # + Philips_VG_8020
```

- `run_case(machine, "direct", [line])` — one direct line (auto-chunked past the
  40-byte KEYBUF cap, so any length works); `"stored"` numbers `body_lines`
  10/20/… + `RUN` (split a `:`-line with `as_stored`).
- Reuse `result_span` / `screen_tail` / `result_span_after_echo` for the
  `[…]`-bracket value + error-tail (machine-agnostic re `Ok` vs `ZB`).
- **Boot per case** (`run_case`) is the default — power-on-fresh state. Batching
  (`run_batch`) is UNSAFE on zerobas today: its `NEW`/`CLEAR` don't reset
  variables/DEFtbl (the reference does — a known divergence).
- Template: `basic_probe_float_vars/_fmt/_arith.py`. A `--bp`-landmark probe
  (crunch/tokenise) is not flaky — leave it on `omsx_run.py`.

### Byte-identical crunch probe (run after ANY tokeniser change)

```sh
python3 probes/basic/basic_probe_crunch.py --zb-machine C-BIOS_MSX1_EU_REPACK_DISK
# want: "ALL PASS — crunch is byte-identical"
```

It feeds the identical line to a real **Philips VG-8020** (reference) and to
zerobas, breaks both at `TAPION ($00E1)` mid-`BLOAD"CAS:",R` (so the whole line
is already crunched), and compares the reference `KBUF ($F41F)` against zerobas
`TOKBUF ($E160)` byte for byte. To exercise a new keyword/operator, add the test
line to `LINES` (executable; `bload` trails) or `CRUNCH_ONLY` (non-executing
body; `bload` leads) — **then restore the probe to pristine before finishing**;
those test-line edits are scratch, never committed.

Other regression probes (same shape, all on the repack machine — run
`make repack-machine` first): `basic_probe_statements.py`, `basic_probe_list.py`,
`basic_probe_strvar.py`, `basic_probe_cas_verbs.py`. The stored-program control-flow
and DATA/READ rows moved to `tests/test_control_flow.py`, which runs against the
shipped image with no emulator (RETIRE THE LEAN 16 KB CART S3,
[`spec-lean-retire-s3-gates.md`](spec-lean-retire-s3-gates.md)).

### omsx_run.py — the headless driver

```sh
python3 probes/lib/omsx_run.py --machine C-BIOS_MSX1_EU_REPACK_DISK \
    --type 'PRINT 12*12\r' --type-delay 8 \
    --bp 0x7FF0 --reg PC --mem memory:0xE000:4 --out cap.txt
```

Hard-won determinism rules:

- **Sync on an event, never on time.** Use `--bp ADDR` (a "done" landmark the
  test cartridge / line jumps to). Real-BIOS machines boot slower than C-BIOS,
  so `--time` is a last-resort fallback only.
- **`--type-delay` is ABSOLUTE emulated seconds**, paired by position with each
  `--type`. The capture window must outlast the last keystroke: if you type at
  t=8 and t=12, a `--time 6` capture fires *before* the keys and grabs nothing.
- **zerobas REPL drops a trailing CR** in the same burst under `throttle off` —
  inject Enter as a *separate*, later `--type "\r"` event (see how the crunch
  probe sets `separate_enter=True`).
- **`CHPUT ($00A2)` / `CHGET ($009F)` guarantee no registers** — guard every
  register across a call to them.
- **One feature per run.** A long chained test line can error before reaching
  the breakpoint, leaving no capture file (a `FileNotFoundError`); test
  operators / statements one per run.

### Capture techniques

- **BLOAD-landmark freeze:** point a `.cas` payload at a `jr $` self-loop
  (`bytes([0x18,0xFE])`) loaded somewhere you control, break at the loop, and
  read RAM — freezes interpreter state after the line has fully executed.
  `build_cas("TOK", load, run, payload)` builds the tape.
- **PRINT / screen output:** dump the SCREEN 0 name table from VRAM with
  `--mem VRAM:0x0000:N` and decode the MSX character codes.

## Tokeniser quirks (the expensive lessons)

These govern `basic/interp.asm`'s `tokenise:` / `tk_loop:` and **must** be
preserved or the crunch probe regresses:

- **Keywords match at EVERY position mid-identifier**, exactly like MS-BASIC.
  `SCORE` crunches as `SC` + `OR` (`$F7`) + `E`, *not* as a single name. Do not
  try to consume a maximal identifier — emit char by char and let each position
  attempt a keyword match.
- **Digits stay verbatim only when already inside a name.** That is the entire
  job of the `TKNAME` in-name flag (`$E028`): a letter sets it; at each loop top
  it is read into `B` then cleared; a digit copies verbatim iff `B` says we were
  mid-name, otherwise it begins a number literal. `a1`, `x2`, `ab9` round-trip
  byte-identically because of this.
- **`OFF` has its own token `$EB`** (oracle-observed via `KEY OFF`).
- Token bytes come from MSX2 TH Table 2.20; line-number identification codes
  from Figure 2.12. New tokens go in `basic/sysvars.inc` with a cited source and
  in `kwtable` (layout: `[klen][UPPERCASE chars][tlen][token…]`, 0-terminated).

## Layout cheat-sheet

- **Expression precedence ladder** (`basic/expr.asm`, lowest binds last):
  `eval → ev_xor → ev_or → ev_and → ev_not → ev_rel → ev_e (+ -) →
  ev_mod → ev_idiv (\) → ev_t (* /) → ev_f`. Factors live in `ev_f`; add a new
  function/literal there. Cursor in `IX`, value out in `DE`; `eval` bridges
  `HL ↔ IX`.
- **Variables** (`basic/vars.asm`): 2-significant-char keys. LEAN build:
  4-byte entries `[name0][name1][value:2]` at `VARTAB ($E1C0)`, via
  `var_name_key` (HL→BC key) + `var_get_key`/`var_set_key`. REPACK build
  (typed, F3+): variable-width entries `[name0][name1][type][value:2/4/8]`,
  key (name0,name1,type). Through slice-4a these ALSO lived at `VARTAB`;
  arrays slice-4b (docs/spec-basic-arrays-slice4b-scalar-reloc.md) relocated
  them into the real-MSX contiguous chain (`program text → scalars → arrays
  → free → string heap`), sharing arrays' own `[PRGEND+2, FRETOP)` region and
  its insert-and-shift/GC-retry mechanism — `VARTAB` is now DEAD RAM in the
  repack build (128 B freed; `ARYTAB`, the new scalar/array boundary cell,
  lives at its foot). `var_find_typed`/`var_alloc_or_find` (vars.asm) are thin
  glue over the ARY sub-ROM tenant's `SCALAR_FIND`/`SCALAR_ALLOC` ops
  (sub/arrays.asm); `var_load_fac`/`var_store_fac` (the value codec) and the
  single-letter FOR/NEXT/READ shims are unchanged above that glue.
- **Statement dispatch** is by token in `basic/interp.asm`; one source file per
  verb (`basic/clear.asm`, `basic/usr.asm`, `basic/print.asm`, …) added to both
  `basic/main.asm` (include) and the `Makefile` `DEPS`.
- **Out of ROM space?** The repack main ROM is near-full; overflow goes to a
  zerobas-sub tenant. See the [sub-ROM tenant playbook](subrom-tenant-playbook.md)
  for the decision tree (leaf → whole tenant; non-leaf touching `eval`/`float-arith`
  → glue-in-main + pure-RAM-leaf split), the ABI recipe, and the gates. Measure the
  wall + classify *before* implementing (the arrays lesson).
