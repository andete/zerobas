# D-MUTRACE — two ways the battery lied, both found by refusing a verdict

**Status:** the parallel-mutator race FIXED 2026-08-28; the patch-freshness
blindness DIAGNOSED and its backlog cleared. Both were found in one battery run,
by not accepting a result the battery itself had already adjudicated.

## 1. A "FLAKE" that was a real race

`unit-test` went red, passed on the serial retry, and was classified
**FLAKE (green on retry)**. That classification is normally right — heavy
emulator gates do drop captures under contention. It was wrong here, and the
tell was cheap: **`unit-test` is deterministic and takes 22 s.** It has no
business flaking at all.

The log named the cause outright:

```
ERROR: Unexpected 'EQ' used as instruction  on line 4216 of file basic/sysvars.inc
```

Line 4216 is a valid `MSGESC_SUB equ 6`, and the file ends with a newline. pasmo
read that line **with its label missing** — a torn read of a static include.

**Cause.** [`tools/check_switch_builds.py`](../tools/check_switch_builds.py)
mutates `basic/sysvars.inc` and restores it — its own docstring says so — and
`switch-build-check` runs **in parallel** with `unit-test`, whose `test_float.py`
runs pasmo over `basic/main.asm`, which includes `sysvars.inc`.

### 🔴 The denominator: three gates, not one

One instance is never the class. Every gate that writes was checked:

| gate | mutates |
|---|---|
| `switch-build-check` | `basic/sysvars.inc` |
| `wall-literal-check` | tracked probe/tool sources |
| `diskdep-check` | **the `Makefile`** — while eight parallel `make` processes read it |

All three are already **exit**-safe under D-KNIFEGUARD: the original is held in
memory and restored by `try/finally` *and* `atexit`. 🎯 **But exit-safety is not
this hazard.** A knife guard protects against the runner dying between the write
and the restore; nothing protects against a **concurrent reader**, and a 43-unit
parallel battery is exactly that. Same family as the machine-XML race and the
openMSX settings flake: a shared mutable file read in parallel.

### The fix, and why `--solo` was not it

`run_gates.py` already had a `--solo` flag, and it does **not** grant
exclusivity — it only schedules a unit *first* (`solo first -> grabs a worker at
once`). It would not have prevented this.

The three now run in a **serial phase before the pool starts** — measured cost
**4 s** of a ~430 s battery. A red from one of them is excluded from the
flake-retry: a unit that already ran alone cannot have failed from contention, so
retrying it could only launder a real failure into a flake.

### Proof, not inference: the mechanism planted and reproduced

The 2026-08-26 item this closes
(`TODO.md`, filed by D-PASMOSAY) demanded *"do not close this on the next green
battery; close it on a captured message"*, and had already **driven its own repro
384 times without reproducing**. Its two arms were the wrong hypotheses. A fourth
arm was added to [`scratchpad/pasmoflake_repro.py`](../scratchpad/pasmoflake_repro.py)
that plants exactly the mechanism above — a background thread rewriting
`basic/sysvars.inc` while workers assemble `basic/main.asm`:

| arm | hypothesis | result |
|---|---|---|
| `SHARED` | two writers on one output pair | **0 / 16** |
| `PRESSURE` | resource exhaustion at 8-way concurrency | **0 / 48** |
| **`MUTATOR`** | **a GATE rewriting a source file in the same pool** | **13 / 16** |

```
ERROR: Symbol 'CLEARPOOL' is undefined  on line 107 of file basic/str-engine.asm
ERROR: Symbol 'RND_SEED' is undefined   on line 201 of file basic/subromcall.asm
```

Different messages from the battery's `Unexpected 'EQ'` — a torn read loses a
different amount each time — but the same defect. The arm restores the file by
`try/finally` **and** `atexit`, and asserts byte-identity afterwards.

🎯 **A repro that fails to reproduce has only excluded the hypotheses it
ENCODED.** 384 clean runs said nothing at all about the one it did not: the
writer was never another `pasmo`, it was a **gate**.

## 2. A gate that was structurally blind in the only workflow anyone uses

Fixing §1 changed the execution order, and `patch-freshness-check` immediately
went red — **on a ROM whose three hashes were byte-identical to the previous
green battery**. The verdict changed without the artifact changing, which is the
signature of a check that was never measuring what it claimed.

It reports staleness only when **every source is clean**, because only then can
it compare HEAD's copy of the patch pair against a fresh regeneration. But the
standing workflow is *edit → run the battery → commit*, so **the battery always
runs with a dirty tree** and that arm never fires. The check is not wrong; it is
unreachable from the one sequence anyone actually performs.

🔴 **It had a real backlog to report.** `zerobas-main-eu.ips` / `.bps` went stale
at HEAD across **six** commits on 2026-08-28 (`7e4b235` … `33cc77f`). The cause
was a misread convention: `git log` on the pair shows a
*"release: regenerate the tracked main patches"* commit, which read as "these are
refreshed periodically, not per slice". They are not — `0e90a37`, `52f81fc` and
`f595a8d` all carry the pair with an ordinary slice, and that release commit was
itself a catch-up after the same mistake.

**The pair belongs in every ROM-changing commit.**

## 3. What generalises

* **A deterministic gate cannot flake.** When one is called a flake, the
  classifier is wrong, not the gate — read the log before accepting the retry.
* **Exit-safe is not concurrency-safe.** D-KNIFEGUARD hardened 14 knife runners
  against dying mid-cut; none of that helps against a parallel reader.
* **A verdict that changes when only the ORDER changes was never measuring the
  artifact.** Both findings here have that shape.
