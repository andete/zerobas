# D-GATESKIP — skip the emulator tier only when it is *provably* inert

*2026-08-28. `tools/run_gates.py`; `make gates-fast`, `make gates`,
`make gates-full`.*

## 1. Where a battery's time actually goes

Split by **what a unit reads**, not by what it is about. A *static* unit reads
tracked files; an *emulator* unit boots a machine and reads the ROM. Measured
over a full battery:

| tier | targets | serial-seconds |
|---|---|---|
| static | 21 | **65** |
| emulator | 23 (31 units after `lineerr` sharding) | **2870** |

Essentially the whole cost of a battery is the emulator tier — and **both of
that day's real reds came out of the static one** (`unit-test`, which asserted a
divergence, and `todo-citation-check`).

## 2. `gates-fast` — the iteration loop

`make gates-fast` runs the static tier in **21s** against a battery's 440s. It
is not a loosening of anything; it is a tier that did not exist. Both of the
day's reds would have surfaced within seconds of the edit that caused them
instead of 450s later.

It **never records a green baseline**, and its report is stamped
`[STATIC TIER ONLY]` with the count of what did not run on the next line.

## 3. The skip, and why it is a proof rather than a judgement

`make gates` skips the emulator tier only when **all** of the following hold:

1. the **four** ROM images are byte-identical to the recorded baseline,
2. every `.py`/`.tcl`/`.sh` under `probes/`, `tests/`, `tools/` is
   byte-identical, and the `Makefile` is too,
3. the baseline was written by a **full battery that was itself fully green**,
   with nothing excluded and nothing skipped.

An emulator unit's only inputs are the ROM it boots and the code that drives it.
If neither moved, the unit *cannot* return a different verdict.

🔴 **THE REJECTED ALTERNATIVE IS THE INTERESTING PART.** The tempting version of
this is to skip by judgement — *"this change is in the string engine, it cannot
affect graphics"*. That is precisely the reasoning that failed three times in a
single day on 2026-08-26, each time caught by a gate nobody expected to fire.
D-STRLONG is a case in point: it touched a **dense** `fperr_to_err` table, so a
slip would re-map every error code in the language, and the gates that mattered
were `error-acceptance`, `penderr`, `stmtpend` and `lineerr` — none of which
looks related to "string concatenation".
[[a-mechanical-fix-can-break-a-different-invariant]]

⚠️ **A SKIPPED RUN NEVER WRITES THE BASELINE.** Otherwise a chain of skips would
end up vouching for nothing but its first link, and the proof would decay into a
habit.

## 4. Two defects this found in the existing battery

🔴 **`build/disk.rom` WAS NOT IN `IMAGES`.** The battery hashed three ROMs and
printed them as a footnote; the machine config names **four**. Nobody noticed
while the hashes were decorative. Turning them into the thing a skip is *proved*
against is what made the omission matter — a ROM the machine boots but the
fingerprint does not cover is a hole a regression fits through.

🔴 **THE FIRST `gates-fast` RUN PRINTED `21/21 green` WITH A RED UNIT ON THE
NEXT LINE.** The green tally added `int(lineerr_ok)` unconditionally, and
`lineerr_ok` is *vacuously* true when no shard ran — so excluding the emulator
tier minted a phantom green that exactly covered the real red. A count that
agrees for the wrong reason is worse than no count. Fixed, and the battery now
cross-checks its own arithmetic against its own verdict and says so out loud
when they disagree. [[a-case-that-agrees-can-agree-for-the-wrong-reason]]

## 5. The battery forces the refcache OFF

D-REFCACHE would otherwise let a gate pass by replay — 315 rows served from
disk, nothing booted, `ALL PASS` printed. The battery therefore measures always,
and *this* mechanism is what makes an unchanged tree cheap: loudly, nameably,
and only against a proof. See [`spec-refcache.md`](spec-refcache.md) §6.

## 6. What was deliberately NOT done

Trimming the emulator tier by hand — dropping gates that "look unrelated", or
sampling them. That is the judgement call §3 rejects, and nothing here should be
read as licence for it. `make gates-full` forces the whole battery and remains
the thing a commit is gated on whenever the ROM or the probe sources moved.
