# D-PREFLIGHT — a probe may not measure a machine it cannot vouch for

Apparatus slice. **Touches no `basic/`, no `sub/`, no `disk/`, no `tape/` source**
— build + probe infrastructure only, so no sign-off gate applies. It is written
up as a slice anyway, with predicted RED/GREEN sets fixed before the change and
knives that prove the guard refuses.

Companion: [`docs/spec-basic-dotgaps.md`](spec-basic-dotgaps.md) §9.2, where the
incident is recorded, and
[`docs/dotgaps-msx1-characterization.md`](dotgaps-msx1-characterization.md) §1,
the apparatus this line of work has been accumulating.

---

## 1. The failure

2026-08-03, during D-DOTGAPS (`b4f5f54`). A corpus script ran

```
rm -rf build && make basic-reloc
python3 probes/basic/basic_probe_msgexact.py --gate
```

`make basic-reloc` builds `build/basic-reloc.rom` and `build/sub.rom`; it does
**not** build `build/zerobas-main-eu.rom`, the merged repack main ROM. The
installed machine XML
(`~/.openMSX/share/machines/C-BIOS_MSX1_EU_REPACK_DISK.xml`) carries **absolute
paths** into `build/`, so it pointed at a file `rm -rf build` had deleted.

openMSX started anyway. Every row read `<none>`. The gate reported **55 red rows
including its own controls** — indistinguishable at a glance from a catastrophic
regression. Re-run after any `repack-machine` target: 55/55 green.

This is [[stale-machine-reads-as-unimplemented]] arriving through a new door, and
it is the **second** time the class has bitten: `$(MAIN_ROM)` got a real file
rule in an earlier slice for exactly this reason
([`Makefile:353`](../Makefile:353), [[ips-rebuild-after-basic-change]]).

### 1.1 Why the probe cannot see it

A probe names its machine as a **string** (`-machine C-BIOS_MSX1_EU_REPACK_DISK`)
and has no visibility into which files that name resolves to. Every failure mode
below produces output that looks like a *result*:

| gap | state | how it reads |
|---|---|---|
| **G1** — no make target | 94 of 146 probes are run by hand; nothing forces `repack-machine` | whatever the machine happens to be |
| **G2** — machine outlives its ROMs | `rm -rf build` leaves the XML in place | uniform `<none>` / uniform `ERR n` |
| **G3** — machine silently older than sources | nothing deleted, the ROM is just stale | the *previous* build's behaviour, reported as this one's |

G3 was thought to have a sharp edge of its own: `make` treats an **equal** mtime
as "not newer" and skips the rebuild, and `shutil.copy2` preserves mtime
([[make-mtime-race-skips-subrom]], [[echo-guard-never-saw-say-rows]] §3), so a
stale artifact can exist that `make` itself calls up to date. That edge is real
and turned out **not to be preflightable** — §8.2, and it is the finding of this
slice.

---

## 2. What already worked, and is left alone

* `repack-machine: $(MAIN_ROM) $(DISK_ROM) $(SUB_ROM)`
  ([`Makefile:523`](../Makefile:523)) is correct.
* `$(MAIN_ROM)` has a real file rule on `$(SRC) $(DEPS) tape/tape.asm`
  ([`Makefile:359`](../Makefile:359)) — a `basic/*.asm` edit does retrigger the
  merged ROM.
* `tools/install-repack-machine.py` validates `isfile` at **install** time
  (~:182). Install time is not measure time; that is the whole gap.

---

## 3. Design

### 3.1 Where the guard lives

`probes/lib/omsx_preflight.py`, called immediately before **every** openMSX
launch in the tree. Not in `omsx_repl` alone: 94 probes build their own command
line and would have been filtered away from the guard by construction
([[echo-guard-never-saw-say-rows]]).

The trigger is the **presence of `-machine` in the argv**, not the basename of
`argv[0]`. A basename test (`is this openmsx?`) is a filter, and a filter is
where a guard loses sight of its subject; `-machine` is taken by nothing else in
this tree, and preflighting a non-openMSX argv that happens to carry one costs a
stat.

### 3.2 What is checked, and what is exempt **by construction**

The machine XML is resolved by name (openMSX user dir first, then every share
candidate, recursively) and its `<filename>` elements are read.

* **Absolute paths outside every openMSX share/user dir** are this repo's (or
  another checkout's) build products. These are checked.
* **Bare / relative filenames, and paths inside an openMSX share or user dir**,
  are the user's own ROM set: openMSX resolves them through its systemroms search
  path and its sha1 database, so a missing *file* there is not necessarily a
  missing *ROM*. These are **not** checked.

⚠️ **This is what keeps the reference machines out of the guard's way, and it is
structural rather than a name list.** Measured: `Philips_VG_8020.xml` and
`National_CF-3300.xml` reference `vg8020_basic-bios1.rom` /
`cf-3300_basic-bios1.rom` / `cf-3300_disk.rom` as **bare filenames with sha1
siblings** — zero absolute paths, so a reference-only run
(`--sides vg8020,cf3300`) checks nothing and can never be refused. A name-based
exemption (`if machine in REFERENCE_MACHINES: return`) would have been a filter
with the same shape as the one that blinded the lnblank echo guard.

For each checked file:

1. **exists** — else `MISSING` (gap G2).
2. **fresh** — for files under *this* repo's `build/`, `make -q <relpath>` run in
   the repo root. Exit 0 = up to date, exit 1 = `STALE` (gap G3), exit 2 =
   `make` cannot judge it, anything else = `make` could not be run — all
   reported rather than swallowed, because a guard that cannot judge must say
   so.

**There is no third check.** One was built — for the equal-mtime race
[[make-mtime-race-skips-subrom]] — and the knife aimed at it killed it. See §8.2.

A file under a *different* checkout's `build/` (a worktree control run left
behind — `ZB_REPACK_BASE.xml` in the installed machine dir points at a deleted
`.claude/worktrees/…` today) gets the existence check but not the freshness
check: this Makefile cannot speak for another checkout.

Additionally, `-cart` / `-diska` / `-diskb` operands are existence-checked. A
missing cartridge or disk image is the same failure wearing different clothes.

### 3.3 🔴 The suggested freshness rule would have fired on every BASIC slice

The brief proposed "no ROM older than the newest file under `basic/ sub/ disk/
tape/`". That rule is **wrong**, and measurably so: `build/disk.rom` depends on
`disk/` only ([`Makefile:218`](../Makefile:218)), and `build/sub.rom` on `sub/`
only ([`Makefile:227`](../Makefile:227)). Edit `basic/list.asm`, run
`make repack-machine` — the correct, complete build for a BASIC slice — and both
are now older than the newest source under those four directories. The guard
would refuse **every ordinary slice**, and the first thing anyone would do is
switch it off.

`make -q` avoids the whole problem by asking the authority. The Makefile already
holds the per-artifact dependency map; duplicating it in the preflight would be a
second copy to drift, which is the failure this slice is about.

### 3.4 The escape hatch, and why it is loud

`ZEROBAS_PREFLIGHT=off` skips the check and prints a banner to stderr on every
launch. A preflight bug would otherwise wedge all 146 probes with no way out. The
banner is the price: a bypass nobody can see is worse than no guard.

### 3.5 Coverage is measured, not asserted

`tools/check_probe_preflight.py` walks the AST of every `.py` under `probes/`,
`tools/` and `tests/`, finds every `subprocess.Popen/run/call/check_output/
check_call` site, and classifies it:

* argv is a **list literal with no `-machine`** → provably not an openMSX launch,
  exempt **by construction**;
* argv is a **list literal containing `-machine`**, a **name** whose in-function
  assignments cannot be proven `-machine`-free, or **anything else** → the spawn
  must pass `omsx_preflight.guarded(argv)`.

The guard **wraps the argument** rather than sitting on the line above it. A
separate `guard_cmd(cmd)` statement is one careless edit away from guarding a
variable the spawn no longer uses — a guard filtered away from its own subject.
Wrapping makes that unexpressible and makes the checker's job a syntactic
identity rather than a dataflow guess.

It prints the denominator (`sites / exempt / required / guarded`) and exits
non-zero on any unguarded site. A new probe that spawns openMSX by hand fails
this gate.

---

## 4. Predicted RED and GREEN sets — fixed before the change

Baseline, measured on a clean fresh tree before any edit:
`make -q` exit **0** for `build/disk.rom`, `build/sub.rom`,
`build/zerobas-main-eu.rom`, `build/basic-reloc.rom`.
Static survey: **177** subprocess spawn sites in `probes/ tools/ tests/` —
83 list-literal-without-`-machine`, 27 list-literal-with-`-machine`, 64 name,
3 binop.

### 4.1 Predicted GREEN — the guard passes and nothing changes

| id | row | predicted exactly |
|---|---|---|
| **G1** | `basic_probe_msgexact.py --gate`, fresh tree | **55/55**, exit 0, preflight prints nothing |
| **G2** | `--sides vg8020,cf3300` (reference only), fresh tree | passes; **0 files checked, 0 `make -q` calls** |
| **G3** | `omsx_repl --selftest` on the repack machine, fresh tree | 5/5 PASS, batching AVAILABLE |
| **G4** | `tools/check_probe_preflight.py`, after wiring | **0 unguarded**, exit 0 |
| **G5** | `make unit-test` | **56/56 files** (the preflight is not on that path at all) |

### 4.2 Predicted RED — the guard refuses, and nothing is measured

Every row exits **non-zero with zero rows measured** — *not* with red rows.

| id | knife | predicted exactly |
|---|---|---|
| **K1** | `rm build/zerobas-main-eu.rom`, then `msgexact --gate` | `APPARATUS FAILURE`, names `build/zerobas-main-eu.rom`, reason `MISSING`, fix `make repack-machine`; exit 2; **0 rows**, not 55 red |
| **K2** | `touch -t 202001010000 build/disk.rom` | reason `STALE` naming `build/disk.rom` (`make -q` exit 1) |
| **K3** | tie `build/sub.rom`'s mtime to a `sub/` source | reason `MTIME-TIED` naming both. ⚠️ `make -q build/sub.rom` still exits **0** here — this row is what proves check 3 is not a duplicate of check 2 |
| **K4** | move `C-BIOS_MSX1_EU_REPACK_DISK.xml` aside | `APPARATUS FAILURE: machine not found`, exit 2 |
| **K5** | with K1 in force, run the **reference-only** side | **GREEN** — the paired control that says the guard is scoped, not blanket |
| **K6** | knife the guard itself: make `guard_cmd` ignore `-machine` | K1 goes **GREEN again** (55 red rows return) while `check_probe_preflight` still reports 0 unguarded — proves K1's redness comes from the guard and that the coverage gate alone cannot see a gutted guard |

### 4.3 Predicted RED — per entry point, the anti-filter matrix

With `build/zerobas-main-eu.rom` deleted, **each** of these must refuse
independently. A guard wired into `run_batch` only *looks* complete because the
other three funnel through it; that has to be measured, not reasoned
([[echo-guard-never-saw-say-rows]]).

| id | entry point | predicted |
|---|---|---|
| **E1** | `omsx_repl.run_case` | refuse |
| **E2** | `omsx_repl.run_batch` | refuse |
| **E3** | `omsx_repl.run_cases(batch=True)` | refuse |
| **E4** | `omsx_repl.run_cases(batch=False)` | refuse |
| **E5** | `omsx_repl.run_differential` | refuse |
| **E6** | `omsx_run.py` CLI (`--machine …`) | refuse |
| **E7** | own-cmdline probe — `basic_probe_tape_save.py` | refuse |
| **E8** | own-cmdline probe — `basic_probe_cas_ascii.py` | refuse |
| **E9** | `probes/disk/omsx_session.py` | refuse |
| **E10** | `probes/lib/psgtrace.py` | refuse |
| each | the same entry point against a **reference** machine | **pass** (paired green control) |

---

## 5. The other two gaps

### 5.1 Corpus-member probes with no make target

`basic_probe_msgexact.py` is named in the standing corpus list and is one of the
94 with no target — which is how it came to be run by hand, before any
`repack-machine`. It gets `make msgexact-gate` / `make msgexact-relock`, both
depending on `repack-machine`, so the ordering that produced the incident is not
expressible.

⚠️ **A make target is not a substitute for the preflight.** It fixes the *one*
path someone remembers to use; the preflight covers the path they type by hand.

### 5.2 `install-repack-machine.py` writes XML that is not well-formed

Found while building the parser: the PSG comment contains a literal `--`, which
is illegal inside an XML comment. `xml.etree.ElementTree` refuses the whole file
(`not well-formed (invalid token): line 63`); openMSX's parser tolerates it. The
preflight therefore strips comments and reads `<filename>` textually rather than
depending on a conforming parser — and the comment is fixed so the artifact is
valid either way.

---

## 6. What landed

| file | what |
|---|---|
| [`probes/lib/omsx_preflight.py`](../probes/lib/omsx_preflight.py) | the guard: `guarded(argv)` / `guard_cmd(argv)` / `preflight(machine)` + a `-v` CLI that prints the per-file denominator |
| [`tools/check_probe_preflight.py`](../tools/check_probe_preflight.py) | the coverage gate: 178 spawn sites classified, 0 unguarded |
| 90 probe/tool files | argv wrapped in `omsx_preflight.guarded(...)`, one import each |
| [`Makefile`](../Makefile) | `msgexact-gate`, `msgexact-relock` (both on `repack-machine`), `preflight-check` |
| [`tools/install-repack-machine.py`](../tools/install-repack-machine.py) | the illegal `--` inside an XML comment (§5.2) |

---

## 7. Gates

### 7.1 Predicted GREEN — all five as predicted

| id | row | measured |
|---|---|---|
| **G1** | `make msgexact-gate` | **55/55**, exit 0, preflight silent ✅ |
| **G2** | `Philips_VG_8020` / `National_CF-3300` | **0 files checked** on both — every `<filename>` is relative ✅ |
| **G3** | `omsx_repl --selftest` | 5/5 PASS, batching AVAILABLE ✅ |
| **G4** | `make preflight-check` | 178 sites, 85 exempt by construction, **93 required, 93 guarded, 0 unguarded** ✅ |
| **G5** | `make unit-test` | **56/56 files** ✅ |

### 7.2 Predicted RED — the knives

| id | knife | measured |
|---|---|---|
| **K1** | `rm build/zerobas-main-eu.rom`, then `msgexact --gate` | ✅ exact — `APPARATUS FAILURE`, `MISSING build/zerobas-main-eu.rom`, `FIX: make repack-machine`, **exit 2, zero rows** |
| **K2** | `touch -t 202001010000 build/disk.rom` | ✅ exact — `STALE build/disk.rom`, `make -q` exit 1 |
| **K3** | tie `build/sub.rom` to a `sub/` source | 🔴 **REFUTED — the check it tested cannot exist. §8.2** |
| **K4** | machine XML moved aside | ✅ exact — `NO-MACHINE`, exit 2 |
| **K5** | reference side under K1 | ✅ **GREEN on every one of the 8 dynamic entry points** — the guard is scoped, not blanket |
| **K6** | gut `guard_cmd` so it ignores `-machine` | ✅ exact — the incident returns **verbatim (55 red, every row `<none>`)** while `preflight-check` still reports **0 unguarded** |

⚠️ **K6 IS THE ROW THAT MAKES K1 ATTRIBUTABLE, AND IT ALSO INDICTS ITS OWN
COVERAGE GATE.** With the guard gutted, `check_probe_preflight` is still perfectly
happy: 93/93 guarded, ALL PASS. **Coverage is not efficacy.** The gate proves the
call is *there*; only K1/K6 prove the call *does* anything. A tree that had only
the coverage gate would read as fully protected while measuring `<none>`.

### 7.3 The anti-filter matrix — 10 entry points, each measured separately

With `build/zerobas-main-eu.rom` deleted. Every row refuses (exit 2, banner, zero
measurement); every row's **reference** control passes.

| | E1 `run_case` | E2 `run_batch` | E3 `run_cases` batch | E4 `run_cases` per-case | E5 `run_differential` |
|---|---|---|---|---|---|
| zb | RED | RED | RED | RED | RED |
| ref | GREEN | GREEN | GREEN | GREEN | GREEN |

| | E6 `omsx_run` CLI | E7 `tape_save` | E8 `cas_ascii` | E9 `omsx_session` | E10 `psgtrace` |
|---|---|---|---|---|---|
| zb | RED | RED | RED | RED | RED |
| ref | GREEN | n/a | n/a | GREEN | GREEN |

E7/E8 are the two own-command-line probes named in the brief, driven as whole
processes: exit 2, banner present, `build/zerobas-main-eu.rom` named.

### 7.4 Standing corpus — sequential, never two emulator gates at once

| gate | measured | baseline |
|---|---|---|
| `unit-test` | **56/56 files** | 56 |
| `deadcode` (both builds) | **0 dead** (main 1556 spans/283 seeds, sub 1443/100, 1 allowlisted) | 0/0 |
| `msgexact-gate` | **55/55**, 0 named holes | 55/55 |
| `preflight-check` | **0 unguarded** | new |
| `lnblank-acceptance REPEAT=2` | **536/536**, allowlist EMPTY | 536 |
| `lnblank-echo` | green — only the three standing informational rows (`num-tab`, `dec-eol`, `dec-eolctl`), on all three sides | same |
| `lnblank-say-acceptance` | **204/204**, 5 allowlisted `KNOWN_DIVERGE` pinned to their exact values | 204/204, 5 pinned |
| `logicops` · `array` | **193/193** · **151/151** | same |
| `kwsweep` · `sysvarsweep` | MISSING=1 DIVERGENT=1 NO-ORACLE=5 SUPPORTED=29 · apparatus OK | same |
| `string` · `error` · `error-trap` · `abort` · `stop-trap` · `direct-ctrl` | ALL PASS · ALL PASS · ALL PASS · ALL PASS · ALL PASS · **40/40** | same |
| `linemax` · `arrdim` · `clearpool` · `float` | **60/60** · ALL PASS · ALL PASS · ALL PASS | same |
| `diskbasic-acceptance` | **34/34 verbs** | 34/34 |
| `bdos-acceptance` · `fat-error-acceptance` | 12/12 · ALL PASS | same |
| `subrom-acceptance` · `subrom-inttest` | green · green | same |
| `sound` · `play` · `beep` · `math` · `input` · `time` · `intarg` | ALL PASS ×7 | same |
| `graphics-acceptance` | 🔴 **FAIL (2)** — `put_pat64_16`, `rd_base_s0`. **PRE-EXISTING, §8.5** | not in the standing list |

ROM hashes: `build/{zerobas-main-eu,disk,sub}.rom` byte-identical to the
pre-slice baseline throughout (`cmp` against copies taken before the first
knife). `git status basic sub disk tape` empty at every point.

---

## 8. Findings

### 8.1 🔴 The guard was wired in and FAILED OPEN, and its own E-matrix found it

The first run of the anti-filter matrix reported **all 8 entry points passing
with the ROM deleted**, while the same machine refused from the CLI. The guard
was not at fault for *reaching* the launch — it was at fault for *how it failed*.

The E-matrix's test double replaced `subprocess.Popen` globally to detect a
launch. `subprocess.run` uses that same module global internally, and the guard's
own freshness check runs `subprocess.run(["make","-q",...])`. So the double's
exception was raised **inside `preflight`**, after the `MISSING` fault for
`zerobas-main-eu.rom` had already been recorded and **before** `_fail` could
report it. `except OSError` did not catch it. The accumulated fault was thrown
away and the machine went through.

Fixed in the product, not just the harness: `_make_q` now catches
`BaseException` and answers "cannot judge", which is a **fault**, not a pass. A
guard that cannot judge must say so, never fall silent.

⚠️ The harness was wrong too (it now intercepts only argv carrying `-machine`),
but the important half is that a plausible, narrow `except` clause was the
difference between refusing and measuring. **Both halves of the apparatus
produced output that looked like a result** — the matrix said GREEN and the
gate would have said 55 red.

### 8.2 🔴 The mtime-race check CANNOT EXIST, and the knife is what said so

Check 3 shipped in the first version: fail if a build artifact shares an exact
`st_mtime_ns` with a source, the `copy2`/equal-mtime signature
[[make-mtime-race-skips-subrom]]. The K3 knife refuted it three times over.

1. **The predicted value was wrong.** K3 predicted `make -q build/sub.rom` would
   exit **0** (make reads an equal mtime as "not newer"). It exited **1**.
2. **The knife had not made the cut it claimed.** `touch -r` had tied `sub.rom`
   to `sub/lineedit.asm` exactly — verified, `delta = 0 ns` — but `lineedit.asm`
   is not the *newest* prerequisite, so the artifact became genuinely older than
   the others and `make -q` was right. Check the cut before believing the verdict.
3. **The mechanism is not what the memory records.** Measured on a two-file
   scratch Makefile: **GNU Make 3.81 compares at ONE-SECOND granularity** — with
   the target **1 ns older** than its prerequisite it still answers "up to date".
   The hazard is not *equal* mtimes, it is *any pair inside the same whole
   second*.
4. **And the corrected check fires on a correct, just-built tree.**
   `sub/basic-resident-abi.inc` is **generated by the build**
   ([`Makefile:261`](../Makefile:261), `tools/gen_resident_abi.py`) 68 ms before
   `build/sub.rom` consumes it, so **every clean build** produces the signature.
   The guard refused the clean tree before the knife ever cut it.

Narrowing the predicate to "source newer by a whole second" makes it identical to
`make -q` — it stops being a second opinion. So: **the sub-second race is real
and not preflightable.** From mtimes alone, "raced" and "built fast" are the same
observation. It stays where the memory already puts it — hash the artifact in the
knife runner, and `rm -rf build` before a build whose input you just wrote. Check
3 was removed rather than left in as a check that can only fire falsely.

### 8.3 🔴 A heuristic for "will this import resolve?" is not a substitute for running it

The codemod decided whether a file already had `probes/lib` on `sys.path` by
looking for the string `lib` in its source. `probes/disk/omsx_session.py` matched
and did not in fact have it, so `disk_probe_diff.py` died with
`ModuleNotFoundError: omsx_preflight` and `diskbasic-acceptance` came back
**30/34**. Four verbs failed — for the import, not for the disk.

The fix is not a better heuristic: every one of the 90 files now carries a
`sys.path` insert computed from **its own location**, and a sweep imports all 91
edited files the way a sibling probe imports them. `diskbasic-acceptance` is back
to **34/34**.

⚠️ Note which instrument caught it. `python3 -m compileall` was clean, the
coverage gate was ALL PASS, and 91 files "imported fine" in a sweep that had
pre-seeded `probes/lib` onto `sys.path` — **the sweep had removed the very
condition it was testing.** Only running the gate found it.

### 8.4 The guard caught a staleness nobody would have suspected — its own

Late in the slice the E-matrix's **clean-tree** run refused on E9/E10 with
`STALE build/zerobas-main-eu.rom`. The tree was not clean: two minutes earlier
`tools/build_patches.py` and `tools/build_repacked_cbios.py` had been edited, and
both are prerequisites of `$(MAIN_ROM)` ([`Makefile:359`](../Makefile:359)). The
merged ROM genuinely was out of date, and `make -q` said so.

Worth recording because it is the class the brief's mtime-sweep proposal could
not have covered at all: **the stale artifact's trigger was a `tools/*.py` edit**,
not a `basic/` one. Asking `make` is what makes the guard track the real
dependency graph instead of a hand-copied list of source directories. (The
rebuild that followed was byte-identical, as expected for an import-only edit.)

### 8.5 `graphics-acceptance` has two standing red rows and is in nobody's corpus

`put_pat64_16` (`ref='ZE 5'`, `zb=None`) and `rd_base_s0` (`ref='ZK 6144'`,
`zb='ZE 5'`). Attributed away from this slice two ways: identical under
`ZEROBAS_PREFLIGHT=off`, and **identical on the stashed pre-slice tree**. It is
not in the §9.2 standing list — the same shape as `logicops-acceptance` before
D-EXPKW, where *a gate nobody runs is not a gate*. Filed, not fixed here.

### 8.6 Every machine config this tree has ever written was invalid XML

§5.2. One `--` in one comment, in all five installed `ZB_*` / `C-BIOS_*_REPACK_*`
machines. openMSX tolerates it; a conforming parser refuses the **whole file**.
Found only because something finally tried to read a config back. The preflight
strips comments textually regardless — a guard that cannot read the artifact it
vouches for fails open.

### 8.7 A live specimen of the failure was already installed

`ZB_REPACK_BASE.xml` in the machine dir points at
`.claude/worktrees/brave-curie-382b17/build/{zerobas-main-eu,disk,sub}.rom` — a
worktree deleted long ago. That is [[stale-machine-reads-as-unimplemented]]'s
2026-07-26 incident, still sitting there, still bootable, still able to produce a
screenful of plausible wrong answers. The preflight refuses it by name today.
