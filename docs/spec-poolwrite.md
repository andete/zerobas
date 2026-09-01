# D-POOLWRITE — giving the torn read a witness

**2026-09-01.** D-SELFMUT fixed the observable half of a race and filed the
unobservable half as a residual:

> While a plant is live, any parallel unit that assembles `basic/sysvars.inc` or
> reads the `Makefile` sees deliberately corrupted content. Serialising
> `selftest-check` closes the window *today*, by hand, on a list a human
> maintains.

That list — `MUTATORS` — **had already been wrong in both directions at the same
time**: three inert units serialised, the one live unit in the pool. A hand-kept
list whose only known measurement found it inverted is not a control. This
replaces it with one.

## What it measures

A snapshot of `(mtime, size)` for every tracked file, taken immediately **before
the pool starts** and again **after it finishes**. Anything that changed was
written by something running in between.

The cost is two passes of `os.stat` over the tracked tree — a few milliseconds,
against a ~450 s battery. There is no extra run: the battery already had all the
information and simply never looked.

## Why it can attribute and not merely detect

🎯 **THE MTIME IS A TIMESTAMP.** The file itself records *when* it was written,
and the runner already tracks each unit's start and end. The candidates for a
write at time *t* are exactly the units whose window contains *t*.

⚠️ **UNDER PARALLELISM THAT IS A CANDIDATE SET, NOT A CULPRIT**, and the report
says so rather than pretending to a single answer: with `J=8`, up to eight names.
It still turns a battery-wide *"something wrote to the tree"* into the handful
worth re-running alone. In the falsification below the set happened to be a
single name.

**The stated limit:** a restore that also restores the mtime is invisible here.
That is why the snapshot carries **size as well as mtime**, and why this is a
witness rather than a proof.

## Falsified by putting the real defect back

No synthetic plant. The plant is a one-line revert of D-SELFMUT — take
`selftest-check` back out of `MUTATORS` and let it run in the pool again:

| | plant (`selftest-check` in the pool) | control (fix restored) |
|---|---|---|
| verdict | **battery FAILS**, `make` exits 1 | `26/26 green`, exit 0 |
| files named | `Makefile`, `basic/sysvars.inc`, `probes/basic/basic_probe_clear.py` | none |
| attribution | `selftest-check` for all three | — |

The attribution logic is separately armed against synthetic windows, including
the case that matters: **a unit that had already finished before the write is
excluded**, so the set narrows rather than listing everything that ran.

## A pool write is a failure, not an advisory

It sets the battery's exit status. An advisory nobody collects is precisely the
shape `check_selftests.py` was built to end — *"a script outside the battery can
be RED FOR MONTHS and nobody learns"*. If a write turns out to be legitimate it
goes in `REGENERATED` **with its reason**, the way `EXPECT_ARG` entries do, so
the exemption list cannot quietly grow.

`REGENERATED` is not a new hand-kept list either: it is the six-path class
D-GENFRESH enumerated from make's own database (a tracked path that is also a
Makefile target). The two slices compose — one measured which files a build may
legitimately rewrite, and this one needed exactly that set to exempt.

## Reported after the verdict, measured before the retries

Both halves of that placement are load-bearing:

* **Measured before the serial retries**, which write the tree themselves and
  would blur the windows.
* **Printed after the gate tally**, because a `26/26 green` line landing
  underneath a red finding reads as the answer
  [[an-unnamed-outcome-reads-as-no-outcome]]. The headline names the distinction
  out loud: *the gate tally is about the gates; this is about the tree they ran
  on.*
