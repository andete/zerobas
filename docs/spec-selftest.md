# D-SELFTEST — collect the exit codes nobody was reading

*2026-08-28. `tools/check_selftests.py`, gate `make selftest-check`.*

## 1. The measurement

Of **15** scripts advertising a `--selftest`, **three came back non-zero** — and
none of them was in any gate, so nothing had ever collected their exit codes.

| script | why it was red |
|---|---|
| `scratchpad/popraise_sweep.py` | its known-answer set named `elas_abort_fp`, which **D-POPRAISE's own fix** had turned into an `equ` alias, so the sweep can no longer find a body for it |
| `tools/dupspan_indep.py` | matched the literal bytes `c39a42` — `jp $429A`, `raise_error`'s address *when the arm was written*. Every carve since relaid the ROM out, so the group matched nothing: *"got 0, want 6"*. One of the six spans had also been legitimately carved. |
| `probes/lib/omsx_repl.py` | **not red at all** — its `--selftest` takes a MACHINE argument, and running it bare is a usage error. A false positive of my first sweep. |

## 2. 🎯 THE CLASS

**A known-answer test keyed to a LIVE artifact rots every time the artifact
legitimately improves — and rots silently when nothing collects its exit code.**

The two real failures are the same defect wearing different clothes: one froze a
*symbol's meaning*, the other froze a *symbol's address*. Both went red at the
moment some later slice did exactly what it was supposed to do.

Both fixes **derive** the answer instead of freezing it. `dupspan_indep` now
resolves `raise_error` from the `.sym` and *reports* the surviving group size
rather than asserting a frozen count — a later carve is a legitimate change, not
a failure. What still has teeth: the pattern must match something, and every
surviving named span must carry it.

This is the D-WALLIT shape, where a README-listed probe had been failing for
months on a stale `STRSCR` address because no battery collected its honest
`rc=1`. [[wallit-slice]]

## 3. The gate, and the false positive it is built to avoid

`make selftest-check` runs every advertised `--selftest` and reports the tail of
any that fails.

⚠️ **A `--selftest` THAT REQUIRES AN ARGUMENT IS NOT A FAILING SELFTEST**, it is
a different interface — my first sweep ran them bare, got a usage error, and
counted them red. `EXPECT_ARG` declares those explicitly and **every entry must
carry a reason**, so the exemption list cannot quietly grow into a place where
red tests go to hide. One entry today: `omsx_repl.py`, whose selftest boots an
emulator and is therefore not a static check at all.

🔴 **And the first sweep had a worse fault than that**: it wrapped each run in
`timeout`, which does not exist on macOS, so **every one of the 15 returned
rc=127** — a uniform failure that looks exactly like "everything is broken".
An instrument that fails identically on every input is reporting about itself.

## 4. Falsification

Four arms on planted fixtures: only scripts advertising `--selftest` are picked
up; a passing one is rc=0; **a failing one is rc≠0 and would be reported**; and
every `EXPECT_ARG` entry carries a reason.
