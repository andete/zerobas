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

## Done — `string-acceptance` (2026-07-12, this slice)

All six halves `string_acceptance.py` dispatches to (`crunch`, `string`,
`str_cmp`, `str_fn`, `inkey`, `mid_stmt`) are off `omsx_run` matrix typing and
onto `omsx_repl`; the whole gate went **~57 s → ~14.5 s** (originally minutes),
flake-free. Three mechanisms, by sub-probe shape:

- **`crunch`** (+ its ref-only sibling `str_tokens`) was BLOAD-freeze-at-TAPION
  like `floatlit`; redesigned to the same **stored-line TXTTAB capture**. Added a
  reusable `capture=("stored_line", PTR)` mode to `omsx_repl` that dereferences
  the first program line's **link pointer** for its exact bytes (link+lineno+
  tokens+00) — strictly stronger than the old first-0x00 trim (embedded-0x00
  lines like `goto 40`, `a=256` compared in full). Nothing executes, so the
  LINES-vs-CRUNCH_ONLY (bload-trails/leads) split collapsed. Proven byte-
  identical to the freeze capture on both machines before the switch. `--full`
  corpus ×2 sides ~minutes → ~4.6 s.
- **`string`** (single-machine execute+regex) — fully **batched** via
  `run_cases(reset=("NEW","CLS"))`: 19 boots → 1, ~1.3 s.
- **`str_cmp` / `str_fn` / `mid_stmt`** (differential: oracle-lock +
  zb==ref, bespoke extraction) — delivery-swapped, then **batched** one boot per
  side (str_cmp all three batteries; str_fn's CASES with `SPACE$.clamp` marker
  arithmetic left boot-per-case; mid_stmt overwrite battery + range-error). Each
  verified differential-inert against `--boot-per-case` (these string-op cases
  can't wedge the interpreter, so no self-heal needed). 14.8/24.2/11.6 s →
  2.0/3.2/1.9 s.
- **`inkey`** (stateful: poll-loop program + injected key) — the key is a
  trailing raw line; the line editor drains KEYBUF before RUN, so it lands while
  the loop spins on INKEY$. Boot-per-case (3 cases), ~2.7 s.

All keep a `--boot-per-case` escape hatch; all documented divergences still
asserted per-machine (STRMAX=64 clamp; MID$ range wording; type-mismatch case).

## The rest — prioritized by ROI

### 1. `input-acceptance` — stateful, batch with care

`basic_probe_input` types a program, `RUN`s it, then types a *separate* INPUT
response synchronised to the blocked read. Each case is a small stored program +
a response; batching means `NEW`+program+`RUN`+response per case in one boot. The
response injection must still land after the read blocks (the existing timing
concern), so this is a `run_cases(mode="stored")` variant with an extra
post-`RUN` injected line, not a plain matrix. Medium effort; validate the
response never races the next case's `NEW`.

### 2. `diskbasic-acceptance` / `bdos-acceptance` — different mechanism, separate track

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
