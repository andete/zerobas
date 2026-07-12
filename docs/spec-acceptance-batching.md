# Acceptance-gate batching — status + plan for the rest

Standing acceptance gates boot openMSX and drive BASIC differentially against a
reference ROM. Booting is the cost (~0.4–1.4 s/boot); a gate that boots **once
per case** pays it ×N. Since `5cde8a8` fixed `NEW`/`CLEAR` to reset variables +
DEFtbl on the repack build (`omsx_repl.py --selftest` now reports *batching
AVAILABLE*), a matrix can instead run in **one boot**, amortising it.

## Done — the float gate's `omsx_repl` trio (this slice)

`basic_probe_float_{fmt,arith,vars}` now deliver their whole matrix through
`omsx_repl.run_differential` (batched by default; `--boot-per-case` escape hatch).
See [`probes/lib/omsx_repl.py`](../probes/lib/omsx_repl.py) — `run_cases` (one
boot, `reset` between cases) and `run_differential` (batched + **self-heal**:
any case that fails the differential is re-run boot-per-case, so verdicts equal a
full boot-per-case run while clean cases keep batch speed).

The one hazard batching introduces: a case that **wedges** the interpreter (a
tokeniser-derail literal like `1e10#` leaves a stray token that spins the machine
— no `reset`, not even `NEW`/`CLS`/Ctrl-C, recovers it, and every follower in that
shared boot captures garbage). Handled two ways: declare known wedgers in
`isolate=` (kept out of the batch); the self-heal rescues undeclared ones (their
poisoned tail re-runs clean, just slower — add them to `isolate` to reclaim it).

Measured (repack machine, differential vs `Philips_VG_8020`):

| probe | cases | boot-per-case | batched | speedup |
|-------|------:|--------------:|--------:|--------:|
| float_arith | 160 +7 | ~180 s | **6.9 s** | ~26× |
| float_fmt   | 60 | ~60 s | **3.3 s** | ~18× |
| float_vars  | 56 | ~55 s | **3.5 s** | ~16× |

`make float-acceptance` (all 5 halves) is now **~3:20**, but that is dominated by
the two probes NOT yet batched: `floatlit` (~176 s) and `var_reset` (~8 s, stays
boot-per-case by design — it *tests* the reset). Batching the trio was the fast,
safe, fully-validated slice; the reference machine batches identically (real MSX
`NEW` always reset).

## The rest — prioritized by ROI

### 1. `floatlit` (~176 s, and flaky) — highest ROI

`basic_probe_floatlit` is the single biggest cost in `float-acceptance` AND still
rides the **matrix-typing** `omsx_run --type` path (observed to flake: a run
exited SOME-FAILED where the same cases pass on retry — exactly the flake class
this harness rework exists to kill). It boots once per literal and **freezes the
CPU** at the `TAPION` breakpoint with the line crunched in `KBUF`, so it can't
share a boot as-is.

**Approach (needs its own spec + sign-off):** replace the BLOAD-freeze capture
with a non-freezing one that reads the crunched literal from the *stored program*
instead of the crunch buffer. Injecting `1 A=<lit>` as a numbered line (no `RUN`)
via `omsx_repl`'s KEYBUF path leaves the crunched literal token in `TXTTAB` — for
a float literal that IS the stored representation (`$1D`+4 / `$1F`+8), the same
bytes this probe pins today. A stored line neither freezes nor executes, so all
66 literals batch in one boot behind `run_cases`, killing both the runtime and
the flake. Risk: confirm the `TXTTAB` bytes are byte-identical to the current
`KBUF`/`TOKBUF` capture across every literal (incl. the "both rejected"
`1e63`/`65535%` cases) before switching. Est. 176 s → ~5 s.

### 2. `string-acceptance` — convert its sub-probes off matrix typing first

`string_acceptance.py` dispatches to `crunch`, `str_cmp`, `str_fn`, `string`,
`strvar` — **all** still on `omsx_run --type` (flaky + boot-per-case). Two steps:
first port each to `omsx_repl` (the delivery-layer swap the float probes already
model — same `--type` line becomes a `run_case`), then batch the ones whose cases
allow a `("NEW","CLS")` reset via `run_differential`. `crunch`/`tokenise` are
breakpoint-synced like `floatlit` and follow the same TXTTAB redesign (item 1).

### 3. `input-acceptance` — stateful, batch with care

`basic_probe_input` types a program, `RUN`s it, then types a *separate* INPUT
response synchronised to the blocked read. Each case is a small stored program +
a response; batching means `NEW`+program+`RUN`+response per case in one boot. The
response injection must still land after the read blocks (the existing timing
concern), so this is a `run_cases(mode="stored")` variant with an extra
post-`RUN` injected line, not a plain matrix. Medium effort; validate the
response never races the next case's `NEW`.

### 4. `diskbasic-acceptance` / `bdos-acceptance` — different mechanism, separate track

These boot per *probe* (not per case) and drive disk `.COM` exercisers / FAT12
images, not REPL lines. Not an `omsx_repl` target; batching them is a distinct
design (share one booted DOS across exercisers) tracked separately if their
runtime becomes a bottleneck. Lower priority — they already boot far fewer times.

## Guardrails for any future slice

- **Differential-inert**: a converted probe must stay reference-identical AND
  keep the exact same pass/fail verdict per case (the self-heal guarantees this
  for `run_differential` probes — trust it, but still eyeball the full matrix).
- **Reset choice**: `("CLS",)` when no case assigns a variable; `("NEW","CLS")`
  when cases set typed vars / DEF defaults. When unsure, `("NEW","CLS")` is safe.
- **Wedgers**: any case whose differential logic pre-authorises a "both rejected"
  / dead-machine outcome is a wedger candidate — put it in `isolate=`.
- **Keep the escape hatch**: every converted probe keeps `--boot-per-case`.
- `var_reset` and CPU-freeze breakpoint probes stay boot-per-case by nature.
