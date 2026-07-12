# Spec — acceptance-harness injection rework

**Status:** APPROVED 2026-07-12; S0–S2 + S4 DONE, S3 (string/other probes)
pending. Float-acceptance fully converted (floatlit stays on `omsx_run` --bp).

**Progress & findings:**
- **S0** (2b540cf): `probes/lib/omsx_repl.py` + self-test, green on both machines.
- **S1** (62858b2): `basic_probe_float_vars.py` converted, 56/56 identical to
  baseline, former-flaky cases now deterministic across repeats. Found+fixed a
  KEYBUF *circular-buffer* boundary bug: line+CR = 40 wraps PUTPNT onto GETPNT →
  the line executes TWICE; cap is `MAX_DIRECT = 38` (line+CR ≤ 39).
- **S2** (5169293): `float_fmt` (60/60) + `float_arith` (167/167) identical to
  baseline. Added **chunked KEYBUF injection** (write >38-char lines in ≤38-char
  pieces, CR on the last) → a direct line of any length works with no tokeniser,
  so the **TXTTAB fallback (§2.2) is never needed** and stays unbuilt.
- **S4** (docs): `probes/README.md` + `docs/dev-workflow.md` updated.
- **Batching (G4) originally dropped on the zerobas build:** the self-test
  established that zerobas `NEW`/`CLEAR` didn't reset variables/DEFtbl (the
  reference does — a real divergence). That divergence is now **FIXED** in the
  repack build (2026-07-12; `basic/clear.asm` + `basic/program.asm`, gated
  `IF ROM_BASE < $4000`; proven reference-identical by
  `probes/basic/basic_probe_var_reset.py` in the `float-acceptance` gate), so a
  bare `CLEAR` / `NEW` reset between cases in one boot is now viable on the
  repack machine (`run_batch(..., reset=("NEW",))`). `run_case` (boot-per-case)
  stays the default — it fully kills the flake (G1, the primary goal) and the
  batching wall-clock win under `throttle off` was modest — but batching is no
  longer *blocked* by a state-reset wall. The `--selftest` reports the
  batching-safety verdict.

---

**Original draft (approved as written below):**

**Track:** harness rework (parked next-up after F3; see memory
`acceptance-harness-injection-rework`)
**Mechanism decision (user, 2026-07-12):** *layered* — KEYBUF injection is the
default line driver; write_block→TXTTAB tokenised injection is a documented
fallback for the (currently empty) set of cases that can't be expressed in
≤40-byte lines.

---

## 1. Problem

The differential acceptance probes drive BASIC by openMSX `type`, which emulates
the **keyboard matrix** on a fixed emulated-time schedule. Two failure modes:

1. **Doubled leading key** — under load the first key of a line registers twice
   (`print`→`pprint` → spurious `syntax error`). Content-insensitive to the ROM
   but sensitive to CPU timing: adding one keyword shifts the schedule enough to
   tip it (the false `OPEN LEN=` failure; `probe-inject-idea`).
2. **Swallowed Enter** — a ~45-char line takes ~8 emulated s to type char-by-char;
   a fixed 3 s Enter gap fires mid-type, the line echoes but never executes (the
   F3 S3b `varptr` flake, `basic_probe_float_vars.py:253`).

Both are properties of the *matrix-scan* delivery path, not the ROM. One boot per
case also spawns one openMSX process per case (~0.7 s wall each under
`throttle off`; ~200 boots for `float-acceptance`).

### Goals

- **G1 — kill matrix-typing flakiness.** No probe touches the keyboard matrix.
- **G2 — keep the full differential.** Every converted probe still runs
  reference (Philips VG-8020) vs zerobas (repack disk machine) and asserts the
  same equality it does today. Machine-agnostic: published MSX2-TH sysvar
  contract only, **no ROM disassembly**.
- **G3 — preserve semantics under test.** The direct-mode vs stored-program
  distinction (float_vars `"value"`/`"abort"` vs `"stored"`; the FOR/NEXT resume
  divergence) survives the rework unchanged.
- **G4 — batch cases per boot** where the screen allows, for a wall-clock win.

### Non-goals

- Not changing any *case matrix* or any *assertion*. Pure delivery-layer swap.
- Not converting the `--bp`-landmark crunch/BLOAD probes (they don't type a REPL
  line; `type` there is a single short trigger and is not flaky). Scope is the
  **REPL-driving** basic probes only.
- Not building the tokenise-once cache now (see §4 — deferred until a case needs
  it).

---

## 2. Mechanism (layered)

### 2.1 KEYBUF injection — the default line driver (already proven)

Write `"<line>\r"` into the BIOS type-ahead buffer and point the read/write
cursors at it; `CHSNS`/`CHGET` deliver the bytes and **the ROM tokenises them
normally**. No matrix scan ⇒ nothing can double, and the line lands atomically ⇒
no mid-type Enter. Published contract, no disasm:

- `KEYBUF $FBF0` — 40-byte circular type-ahead buffer
- `GETPNT $F3FA` / `PUTPNT $F3F8` — read/write cursors (empty when equal)

Reference implementation to lift: the `__inj` Tcl proc in
`probes/disk/disk_probe_getput.py:95` (proven on C-BIOS **and** CF-3300, both
zerobas and reference machines). Constraint: **line + CR ≤ 40 bytes**.

**Long lines (>40 bytes) split into a stored program.** Every over-cap line in
the current corpus is a `:`-joined multi-statement direct line that splits
cleanly at `:` into ≤40-byte program lines driven as `10 …` / `20 …` / `RUN`:

```
alias.all4:  A=1:A%=2:A!=3:A#=4:PRINT"[";A;A%;A!;A#;"]"   (42)   ->
   10 A=1:A%=2:A!=3:A#=4          (21)
   20 PRINT"[";A;A%;A!;A#;"]"     (26)
   RUN
```

The 4 over-cap lines (`alias.all4`, 3× `varptr.*`) are all pure
assignment+PRINT — direct-vs-stored is semantically identical for them, so
reclassifying them `"stored"` changes nothing observable. **Result: KEYBUF alone
covers 100% of the current corpus.**

### 2.2 TXTTAB tokenised injection — the fallback (designed, deferred)

Only needed when a **single unsplittable statement** exceeds 40 bytes, or a case
must stay genuinely *direct-mode* while >40 bytes. None exist today, so this is
**speced but not built** — the driver exposes the seam; we implement it on the
first real case (YAGNI, and it avoids premature tokenise-cache machinery).

When built: inject pre-tokenised program bytes into `TXTTAB $8001`, set
`VARTAB`/`ARYTAB`/`STREND` = `TXTTAB + len`, then `RUN`. Producing the bytes =
**tokenise-once cache**: seed by tokenising the source once (KEYBUF if splittable,
else a single matrix `type` — the *only* residual matrix use, off the differential
critical path and cached by source hash), `debug read_block TXTTAB..VARTAB`, cache
the blob, inject it on both machines thereafter. Tokenisation is standardised
(the crunch gate proves it byte-identical across ref/zb), so one blob is valid on
both machines.

---

## 3. Architecture

### 3.1 New shared module: `probes/lib/omsx_repl.py`

An **importable** REPL driver (Python API, not a subprocess CLI — batching needs
interleaved inject/capture callbacks on one emulated timeline, awkward as flags).
It generalises `disk_probe_getput.py`'s single-program Tcl generator to an
ordered list of *cases* run in one boot.

```python
Case = {
    "lines":   list[str],   # REPL lines to inject (each ≤40B, or auto-split)
    "mode":    "direct" | "stored",   # stored -> prefix "10 "/"20 ", append "RUN"
    "capture": "screen",    # VRAM SCREEN-0 name table (40x24) after settle
}

def run_batch(machine, cases, *, cf3300=False, step=None, timeout=...) -> list[str]:
    """Boot `machine` once, drive each case (KEYBUF inject -> settle -> capture
    VRAM -> CLS), return one raw 960-char screen string per case (None on
    capture failure). Emulated-time schedule is coarse per-case (inject, wait
    for consume+exec, capture, CLS) — robust, no matrix scan."""
```

- **Screen isolation:** `CLS` between cases resets the 40×24 buffer; each case's
  output is scraped from its own post-CLS screen. The `[...]` bracket technique
  (already in the probes) isolates the value within a screen.
- **Auto-split:** a line >40B is split at `:` into a stored program
  transparently; if unsplittable and >40B, route to the TXTTAB seam (or raise a
  clear "needs TXTTAB fallback" error until that's built).
- **Machine-agnostic prompt handling:** reference closes with `Ok`, zerobas with
  `zb>` — the existing `screen_tail` / echo-match conventions
  (`basic_probe_float_vars.py:330`) move into the shared module.
- **Reuse over rebuild:** lift `__inj`, `__hex_v`, throttle-off boot, the
  `renderer none` invocation from getput; keep `omsx_run.py` as-is (the
  `--bp`/state-capture core stays the crunch/BLOAD path).

### 3.2 Self-test (harness-first MO: earn trust by reproduction)

`omsx_repl.py --selftest <machine>` drives a tiny hand-verified matrix on a real
machine before any probe relies on it, and is wired as a cheap gate:

- `PRINT 1+1` → ` 2 ` (direct value)
- `A%="X"` → abort shape (no span, non-empty tail)
- `FOR I=1 TO 3:NEXT:PRINT I` as a **stored** program → ` 4 ` (resume path)
- one ≤40B and one auto-split >40B line → identical result

The driver draws **no conclusions**; it delivers bytes and scrapes screens.

---

## 4. Rollout plan (one probe per commit, differential-invariant)

Each step asserts the converted probe returns **byte-identical PASS/FAIL verdicts**
to the pre-conversion probe on the current build — the rework must be observably
inert on results, only changing *how* lines are delivered.

- **S0 — driver + self-test.** Build `omsx_repl.py`, self-test green on VG-8020
  and the repack machine. Commit.
- **S1 — float_vars (the probe that flaked).** Convert
  `basic_probe_float_vars.py` to the driver; reclassify the 4 over-cap lines
  `"stored"`. Assert same verdicts as today. Commit.
- **S2 — the rest of `float-acceptance`.** `floatlit`, `float_fmt`,
  `float_arith`. Commit each.
- **S3 — string/other REPL probes** opportunistically (`string`, `str_cmp`,
  `str_fn`, `inkey`, `mid_stmt`, `input`, `print`, `list`, …). Batch where the
  screen fits (G4). Commit per probe.
- **S4 — docs.** Update `docs/dev-workflow.md` §"validation harness" and
  `probes/README.md` to point new REPL probes at `omsx_repl.py`; note `omsx_run
  --type` is retained only for the `--bp` trigger path.

TXTTAB fallback (§2.2) is implemented **only if** a future case needs it; a
`# TODO: TXTTAB fallback (spec §2.2)` seam marks the spot.

---

## 5. Acceptance criteria

1. `make float-acceptance` and `make string-acceptance` pass, with **every
   probe** driven through `omsx_repl.py` (no matrix `type` for REPL lines).
2. Re-running any converted probe N× on the same build yields the same verdict
   every time (no timing-luck flake) — spot-checked with a repeat loop on the
   former-flaky `varptr.*` / `alias.all4` cases.
3. The self-test is green on both machines and runs as a gate before the suites.
4. No case matrix or assertion changed (diff shows only delivery-layer edits +
   the 4 `"value"`→`"stored"` reclassifications).
5. Clean-room intact: no reference-ROM disassembly; injection uses only the
   published sysvar contract.

---

## 6. Open questions for sign-off

- **Q1 — batching aggressiveness (G4).** Batch all cases of a probe into one boot
  (max wall-clock win, one long timeline), or keep a small batch size (e.g. 8/
  boot) for easier failure triage? *Proposed: batch per probe, but capture each
  case into its own keyed screen so a single failure is still pinpointed.*
- **Q2 — retain `omsx_run --type`?** Yes for the `--bp` crunch/BLOAD trigger
  path (not flaky, not a REPL line). *Proposed: keep it, scope note in §4 S4.*
- **Q3 — module name.** `omsx_repl.py` vs folding into `omsx_run.py`. *Proposed:
  new module; keeps the state-capture core lean.*
