<!-- Copyright (c) 2026 Joost Yervante Damad — SPDX-License-Identifier: 0BSD -->

# D-DISKDEP — the generated disk fixture, its 48 undeclared dependents, and the silent half that does not exist

**2026-08-21.** Closes the residual D-COLDROW filed the same day
([`docs/valtyp-coldram-notes.md`](valtyp-coldram-notes.md) §6.6). **0 ROM bytes** —
apparatus only. Gate `make diskdep-check`, calibration `make diskdep-selftest`.

## 1. The subject

`disk/test720.dsk` is **generated** by `make test-dsk`, not tracked: `git ls-files`
does not list it. Forty-eight make targets ran a probe that needs it with no
`$(DISK_TEST_DSK)` prerequisite, so on a fresh clone each worked only because some
earlier target happened to build it. This is the **fourth** instance of the class
found in four slices, one at a time — `inputary` (D-ARYSITE), `namspc`
(D-FILESIDE), `stmtpend` (D-COLDROW), and the remaining 48 here. A class that gets
found one member at a time is a class whose enumerator nobody has written.

## 2. 🔴 The filed split was a static claim, and the measurement refutes it

D-COLDROW filed a classification: 35 probes name the image, a
`shutil.copy*(TEST_DSK` regex splits them **19 LOUD / 16 SILENT**, 24 dep-less
targets in each half, and *"only the silent half can AGREE while measuring
nothing"*. The item that carried it forward said, correctly, that the silent count
was **an upper bound, not a roster**, and that each member had to be read before
being called blind.

Reading them was not enough; they were **measured**. All seventeen candidates (the
sixteen silent-classified probes plus the acceptance runner behind one of them)
were run with `disk/test720.dsk` moved aside, on a fully built machine.

**Every one refused. There is no silent half.**

| mechanism | rc | probes |
|---|---|---|
| `omsx_preflight` — *"APPARATUS FAILURE … NOTHING WAS MEASURED"* | **2** | `inputary`, `arylv`, `forvar`, `nxary`, `nxlist`, `readvar` |
| the probe's own `if not os.path.isfile(...)` guard | **2** | `chancost`, `fat_error_disposition`, `lof` |
| a `shutil.copy` traceback before openMSX launches | **1** | `badfnum`, `lnblank`, `msgexact`, `sysvarsweep`, `disk_probe_dskio` |
| the `<NO DISK FIXTURE>` sentinel — eight rows named as unmeasurable | **1** | `lptverb` |
| a child probe's own guard, surfaced as DIVERGENCE | **1** | `diskbasic_acceptance` |

🎯 **THE REGEX KEYED ON A VARIABLE NAME.** `shutil.copy2?\(\s*[A-Z_]*TEST_DSK`
matches a copy whose first argument is spelled `TEST_DSK` and nothing else. Six
probes copy the image through a local (`shutil.copy(diska, tmp)`), three spell the
constant `SRC_DSK`, and one reaches it through an import — all ten read as
"silent". The static classification was not a weak reading of the class; it was a
reading of a naming convention.

🎯 **AND THE SIX ROWS THE REGEX GOT RIGHT ARE STILL NOT SILENT.** `inputary`,
`arylv`, `forvar`, `nxary`, `nxlist` and `readvar` do exactly what the split said
— hand `diska=TEST_DSK` straight to openMSX, no copy anywhere. They refuse anyway,
because `probes/lib/omsx_preflight.py` checks every argv-named image for existence
before launching, and `make preflight-check` proves *structurally* that every
openMSX launch in the tree goes through it. **The property that closes the silent
class was already enforced by a gate nobody thought to cite here.** The mechanism
that makes a class empty is worth more than the count.

## 3. ⚠️ Two readings were thrown away for measuring the wrong absence

Both are the same shape as a case that agrees for the wrong reason, and neither
would have been visible from the return code.

* **Round 1 was taken on a `make basic-reloc`-only tree.** `lptverb` and `msgexact`
  came back rc 2 from the preflight — but the preflight's own report named
  `build/zerobas-main-eu.rom` and `build/disk.rom`, not the disk. They refused
  because the **ROMs** were missing. Two of sixteen readings were void, and the
  tally would have been 16/16 either way. The whole roster was re-run after
  `make repack-machine`; only then did `msgexact` show its actual mechanism (a
  copy traceback).
* **`diskbasic_acceptance` refused three times before it measured anything** —
  once for a missing `--machine`, once for a missing `--expect-build`, once
  because `--only DSKIO` matched no registry entry (its own vacuity guard, working
  as designed). A refusal on an unrelated argument is not a reading about the
  disk. The fourth run, `--only LOAD`, is the one in the table.

## 4. 🎯 `<NO DISK FIXTURE>` is the third answer, and it is the best one

`basic_probe_lptverb.py` neither crashes nor agrees. Its thirty-six non-disk rows
run and pass; its eight `lfl-*` rows read `<NO DISK FIXTURE>` on **both** sides and
are reported as **DIVERGENT anyway** — the sentinel is excluded from agreement by
construction, so two sides that "match" on it cannot score. That is the shape the
class should converge on: what could not be measured is *named*, not inferred from
silence and not confused with a result. `basic_probe_dskmsg.py` does the same.

Converging the other sixteen on it is **not** taken here and is not filed as a
defect: with the dependency in place the absence never occurs under `make`, and a
refusal is an honest answer to a hand-run probe. It is filed as a shape.

## 5. The fix

`$(DISK_TEST_DSK)` added to the prerequisites of all 48 targets — one token per
line, no recipe touched. Verified to do work rather than decorate: with the image
moved aside, `make -n readvar-acceptance` now schedules
`python3 tools/make_test_dsk.py disk/test720.dsk`, and the regenerated image is
byte-identical to the one it replaced.

## 6. The gate, and why its green run is not believed on its own

`tools/check_disk_deps.py` walks every Makefile target, finds the probes its recipe
invokes, and asks whether each needs the image — **by AST, not by text match**:

* a probe needs it if any **string literal** in its AST contains the basename, or
* it transitively **imports** a module under `probes/` that does.

⚠️ **A TEXT MATCH GETS THE DENOMINATOR WRONG IN BOTH DIRECTIONS AT ONCE, AND ONE
PROBE PROVES BOTH.** `diskbasic_probe_badfnum.py` names the image **only in its
module docstring** — so a text match calls it a user for a reason that is prose —
while its actual need comes from `from diskbasic_probe_lof import run_case`, which
a text match cannot see at all. Two errors that happened to cancel. The import
route is exercised: strip the docstring mention and the walk still reports
*"imports diskbasic_probe_lof.py which names the image"*.

🔴 **AND A FLOOR OF ZERO IS NOT A FLOOR.** An empty walk exiting 2 stops the
0/0-prints-ALL-CONVERGED shape and nothing else: narrow the walk to one target and
the gate still reports *"1 of 1 declare it — clean"*. The count is the claim, so
`MIN_TARGETS = 60` pins it (65 today) and five **witness targets** pin membership,
one per route into the class. The floor is a floor, not an equality — adding a
probe must not redden the gate; only losing coverage may.

🔴 **THE IMPORT ROUTE HAS ZERO LIVE MEMBERS, AND THAT IS A FINDING ABOUT ITS
VECTOR, NOT A REASON TO DELETE IT.** All 65 targets are reached by the literal
test, `badfnum` included, because its docstring names the image as well. So
blinding the import walk changes nothing, and a blindness vector for it passes
**vacuously** — the shape a knife wears when its subject is unreachable
([[a-shadowed-guard-has-no-knife]]). The route is **latent, not dead**: delete that
one docstring sentence, a plausible tidy-up, and the import walk becomes the only
thing keeping `badfnum` in the denominator. So B2 **constructs its own subject** —
blind the literal test for `badfnum` alone — and asserts the import route still
carries it. It is a positive control for a route nothing else exercises, and it
cuts: with the import walk removed it reports *"the walk LOSES it entirely"*.

**Six vectors, 6/6**: 4 findings, 1 blindness (B1, the literal test blinded → exit
2), 1 latent-route control (B2).

**Calibration — `make diskdep-selftest`, 4/4, baseline 0.** Each vector is applied
to a copy of the Makefile text and reverted; each is a defect this check exists to
catch: the dep stripped from a target, from the other half of a
characterize/acceptance pair, from a disk-side target, and — the one a substring
test would miss — **spelled as the literal path `disk/test720.dsk` instead of
`$(DISK_TEST_DSK)`**, which reads as a dependency and is not the one `make test-dsk`
maintains. D-WALLDATE's first draft caught 0 of the 4 defects it was built for and
reported CLEAN; a green run here is not believed without this.
