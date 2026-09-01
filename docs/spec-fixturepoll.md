# D-FIXTUREPOLL — a probe wrote into the test disk, and a "repair" froze the pollution

**2026-09-01.** D-UNCOLLECTED left two reds. Both are closed here, and neither
was the defect it looked like.

## `time-acceptance` — an equality where the file already knew a property belonged

`is_jiffy` POKEs JIFFY to `$3000` and reads `TIME` back, pinned to `12288`.
Measured **deterministically on all eight phases**, three runs: reference 12288,
zerobas 12289. Not jitter — my first instinct, and wrong.

What the row actually measures is **how many interrupts fit between the POKE and
the read**, i.e. interpreter speed. `TIME=0:PRINT TIME` reads **1 / 2 / 1** on
VG-8020 / CF-3300 / zerobas — every machine has already ticked before the read.
`PEEK(&HFC9F)` is `48` (`$30`) on all three, so `TIME` and `JIFFY` are the same
cell, which is the thing the row exists to show.

🎯 **THE FILE HAD ALREADY DRAWN THE RIGHT LINE.** `run_side`'s docstring says the
clock group is *"deliberately NOT an equality differential — the tick rate belongs
to the host BIOS/VDP, so it is asserted as a per-machine PROPERTY"*. `is_jiffy` is
that same kind of quantity, sitting in the equality group. Pinned at the VG-8020's
value it asserted that zerobas interprets at the VG-8020's speed — not a claim
this project makes. It is now an inclusive window, `12288..12304`.

⚠️ The module docstring exempts *"every row but `is_jiffy`"* from the tick race.
It is subject to exactly the same race; its window is merely long enough to be
deterministic per machine, which reads like immunity.
[[a-justification-parenthesis-is-an-unrun-claim]]

## `namspc-acceptance` — the constant was right and the FIXTURE was wrong

Its positive control wants `5 entries + OK` from the CF-3300 and got `6`, so the
probe refused: *"A POSITIVE CONTROL FAILED ON A REFERENCE, so nothing was
measured."* Correct behaviour, and the comment beside the constant predicted it:
*"FIXTURE-COUPLED ON PURPOSE … change that image and this goes red on a
REFERENCE, which is the correct loud failure."*

The sixth entry is `TS.DAT`, **attr `$00`** where every generated file is `$20`.

🔴 **`disk/test720.dsk` IS UNTRACKED AND GENERATED.** Commit `e7c5eab` ran
`git rm --cached` on it and added `*.dsk` to `.gitignore`, saying so out loud:
*"the test image is generated not committed"*, and *"also removes the openMSX
write-back hazard on a committed image."* The hazard did not go away — it stopped
being visible. A probe wrote `TS.DAT` into the local copy. A fresh generation has
**five** files.

🔴 **AND `make test-dsk` CANNOT CATCH IT.** make is timestamp-driven; a polluted
image is *newer* than its generator, so the rule is satisfied and nothing
rebuilds. `make test-dsk` on the polluted image was a no-op — the file had to be
deleted first.

## The part that matters: a repair froze the contamination

**D-FILESROT, earlier the same day**, was filed as "the audit's first genuine
rot" and did exactly what the filing prescribed — *re-measure the reference, never
edit the constant into agreement*. It booted the CF-3300 on **the polluted disk**,
read six fields, and froze `TS      .DAT` into **two** constants. Its own commit
message records the cause without recognising it: *"test720.dsk gained TS.DAT (a
zero-byte data file another probe's fixture work added)"*.

🎯 **RE-MEASURING IS NOT ENOUGH IF THE THING MEASURED IS CONTAMINATED.** The rule
is right and was followed to the letter. It cannot see a bad input.

Both constants are reverted to the five-file form and re-verified on a freshly
generated image: `disk_probe_files` passes both halves. The measuring *method*
D-FILESROT worked out is kept in the comment — clear the date prompt first, or
the prompt swallows both typed lines and the listing reads as nothing.

## The fix is the fixture, not the constants

`make fixture-integrity-check` (static tier, in the battery) regenerates each
generated image **hermetically into a temp dir** and compares the **directory**
(name + attribute byte) against the working copy. Not the whole image: sector
layout can legitimately differ, while a file appearing, vanishing or changing
attributes is always pollution.

Arms: `S1` live tree clean · `S2` a freshly generated fixture is clean (the
control) · `S3` an extra directory entry goes RED · `S4` the report calls it
EXTRA, not MISSING. The S3 plant is the exact pollution found in the wild —
`TS      DAT`, attr `$00`.

With both suites green, `time-acceptance` and `namspc-acceptance` **join the
battery**: **54 units** (28 static + 26 emulator), 25 of 68 acceptance targets collected.
