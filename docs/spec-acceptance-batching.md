# Acceptance-gate batching — status + plan for the rest

Standing acceptance gates boot openMSX and drive BASIC differentially against a
reference ROM. Booting is the cost (~0.4–1.4 s/boot); a gate that boots **once
per case** pays it ×N. Since `5cde8a8` fixed `NEW`/`CLEAR` to reset variables +
DEFtbl on the repack build (`omsx_repl.py --selftest` now reports *batching
AVAILABLE*), a matrix can instead run in **one boot**, amortising it.

## Done — `floatlit` (2026-07-12, this slice)

`basic_probe_floatlit` no longer freezes the CPU at `TAPION` with the literal in
`KBUF`. It now injects each literal as the **stored line** `1 A=<lit>` (numbered,
so tokenised into the program but never executed) via `omsx_repl`'s KEYBUF path,
then reads the crunched line back from **TXTTAB** (`$F676`) — a new
`capture=("mem_indirect", PTR, LEN)` mode on `run_batch`/`run_cases`/
`run_differential` that dereferences a 2-byte LE pointer and dumps LEN bytes.
Because a stored line neither freezes nor executes, all 66 literals share ONE
boot behind `run_differential` (`reset=("NEW",)`), killing both the runtime and
the matrix-typing flake.

Two facts made this correct:
- The stored-line TXTTAB bytes were proven **byte-identical** to the former
  BLOAD-freeze `KBUF`/`TOKBUF` capture across all 66 literals on BOTH machines
  before the switch (incl. the "both rejected" `1e63`/`1e64`/`65535%` cases).
- Rejection is detected by the **link pointer**, not the `A=` marker: `NEW`
  rewrites the 2-byte link at the text base to `00 00` but does NOT wipe the
  prior line's bytes, so a raw marker search reads STALE data past a zero link.
  A stored line's link high byte is always ≥ `$80` (program in page 2), so
  `link == 00 00 ⇔ empty ⇔ rejected`. (Caught in review: without this the three
  rejection cases silently passed on leaked prior-case bytes.)

Measured: **~176 s → ~3.5 s** (~50×), differential-inert (batched == boot-per-
case on both machines; `--boot-per-case` escape hatch kept). `make
float-acceptance` (all 5 halves) is now **~32 s** (was ~3:20).

## Done — the float gate's `omsx_repl` trio (earlier slice)

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

After the floatlit slice (above), the only non-batched `float-acceptance` probe
left is `var_reset` (~8 s, stays boot-per-case by design — it *tests* the reset).

## The rest — prioritized by ROI

### 1. `string-acceptance` — convert its sub-probes off matrix typing first

`string_acceptance.py` dispatches to `crunch`, `str_cmp`, `str_fn`, `string`,
`strvar` — **all** still on `omsx_run --type` (flaky + boot-per-case). Two steps:
first port each to `omsx_repl` (the delivery-layer swap the float probes already
model — same `--type` line becomes a `run_case`), then batch the ones whose cases
allow a `("NEW","CLS")` reset via `run_differential`. `crunch`/`tokenise` are
breakpoint-synced like `floatlit` was, and can now follow the same TXTTAB
stored-line redesign (see the floatlit "Done" slice above + its reusable
`capture=("mem_indirect", …)` mode on `run_batch`).

### 2. `input-acceptance` — stateful, batch with care

`basic_probe_input` types a program, `RUN`s it, then types a *separate* INPUT
response synchronised to the blocked read. Each case is a small stored program +
a response; batching means `NEW`+program+`RUN`+response per case in one boot. The
response injection must still land after the read blocks (the existing timing
concern), so this is a `run_cases(mode="stored")` variant with an extra
post-`RUN` injected line, not a plain matrix. Medium effort; validate the
response never races the next case's `NEW`.

### 3. `diskbasic-acceptance` / `bdos-acceptance` — different mechanism, separate track

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
