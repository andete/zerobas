<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
# S1 — Make the build under test EXPLICIT AT THE CALL SITE

Step 1 of **RETIRE THE LEAN 16 KB CART** ([`../TODO.md:2778 (T-FE0E95)`](../TODO.md:2778)).
Touches **no assembly** and changes **no ROM byte**. Pure test-harness plumbing.

Status: ✅ **LANDED 2026-07-29.** Specced and measured at `1bbf6eb`; signed off; implemented;
falsification battery F1–F7 all observed; every gate re-run green. **0 ROM bytes changed.**

---

## 1. The problem, as measured

A probe today picks which zerobas build it boots from a hardcoded literal:

```python
ap.add_argument("--machine",
                default=os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_BASIC_DISK"))
```

Counts across `probes/` at `1bbf6eb`:

| default | count | build |
|---|---:|---|
| `C-BIOS_MSX1_EU_REPACK_DISK` | 33 | repack |
| `C-BIOS_MSX1_EU_BASIC_DISK`  | 27 | lean |
| `C-BIOS_MSX1_BASIC_DISK`     | 11 | lean |

### 1.1 Correction to the brief's scope claim

The brief states the 38 lean-defaulting probes "are ALL in `probes/disk/` — they are
exactly the Disk-BASIC corpus." The first half holds; **the second does not.** Measured
by cross-referencing `diskbasic_acceptance.py --list` against the grep:

* the acceptance registry has **34** entries;
* **33** of them carry a lean fallback;
* **1 registry probe carries none** — [`disk_probe_rdblk_roundtrip.py`](probes/disk/disk_probe_rdblk_roundtrip.py)
  delegates to `disk_probe_diff --machine both`, i.e. it boots the disk-ROM machines and
  is build-invariant. This is why `_check_repack_wiring`'s `DISK_ROM_DELEGATORS` escape
  hatch exists;
* **5 lean-defaulting probes are OUTSIDE the registry** — [`disk_probe_bdos.py`](probes/disk/disk_probe_bdos.py),
  [`disk_probe_dskio.py`](probes/disk/disk_probe_dskio.py), [`disk_probe_fwrite.py`](probes/disk/disk_probe_fwrite.py),
  [`disk_probe_init.py`](probes/disk/disk_probe_init.py), [`disk_probe_write.py`](probes/disk/disk_probe_write.py).
  All five default to `C-BIOS_MSX1_BASIC_DISK`. They are FDC/BDOS-layer probes; no
  acceptance target runs them, and **`disk_probe_dskio.py` is run by `make probe`**
  ([`Makefile:375`](Makefile:375)) with no machine argument at all.

So "38 = the Disk-BASIC corpus" is 33 + 5-not-in-the-corpus. `make probe` is a real
call site the plumbing has to cover; it would otherwise break under §4.

### 1.2 The coupling that bounds the slice

* [`diskbasic-acceptance`](Makefile:395) sets **no** env var → the corpus falls through to
  its lean literals. *This is the 34/34 lean gate.*
* [`diskbasic-acceptance-repack`](Makefile:418) sets `ZEROBAS_BASIC_MACHINE=$(REPACK_MACHINE)`.

Repointing the 38 defaults at repack would make the two targets **the same test**, both
still printing 34/34 — the lean gate would vanish with no red anywhere. Not done here.

### 1.3 Two things measured that the brief did not carry

**(a) The lean gate has no build dependency on the artifact it tests.**
`diskbasic-acceptance: $(DISK_ROM) $(DISK_TEST_DSK)` — neither `$(PATCHES)` nor the
installed machine is a prerequisite. The lean machine boots `zerobas-msx1.ips`, which is
built from `build/basic.rom`; `make -q zerobas-msx1.ips` at `1bbf6eb` returns **1
(out of date)**. The repack side was given a real file rule for exactly this reason
(see the `$(MAIN_ROM)` comment, [`Makefile:296`](Makefile:296),
[[ips-rebuild-after-basic-change]]); the lean side never was.

**(b) …but it is not currently testing a stale build, and cannot.** Regenerating
`zerobas-msx1.ips` / `.bps` from the 19:00 `build/basic.rom` produces **byte-identical**
files to the copies committed at `be486a4` (2026-07-27) — `cmp -l` reports 0 differing
bytes, `git status` stays clean. The reason is structural: `tools/check_reloc.py`'s
check #4 pins the lean ROM to a **frozen baseline**, so the lean image *cannot* drift
while that gate holds. The staleness is real but currently **timestamp-only**.

⚠️ This matters for the guard's design: a naive mtime-based staleness check would fire
**right now**, on a machine that is byte-correct. Freshness is Make's job (§3); the
runtime guard must check **identity and provenance**, not timestamps.

**(c) A missing machine is loud at openMSX but slow at the probe.**
Measured directly:

```
$ openmsx -machine NO_SUCH_MACHINE_XYZ
Fatal error: Error in "NO_SUCH_MACHINE_XYZ" machine: Couldn't find
machines/NO_SUCH_MACHINE_XYZ.xml in any of: /Users/joost/.openMSX/share, …
```

openMSX exits immediately — but a probe waiting on a capture file learns this only via
its own timeout. At the runner's 240 s default × 34 probes that is a ~2 h red run for a
one-word typo. A startup guard converts it to an instant, named failure.

### 1.4 🔴 A LIVE DEFECT, found by the sweep itself

[`disk_probe_format.py`](probes/disk/disk_probe_format.py) declared `--machine`,
defaulted it from `$ZEROBAS_BASIC_MACHINE`, called `ap.parse_args()` — **and threw the
result away**, then booted a hardcoded literal:

```python
ap.add_argument("--machine", default=os.environ.get("ZEROBAS_BASIC_MACHINE", "…_EU_BASIC_DISK"))
ap.parse_args()                                    # <- result discarded
...
    img = run("C-BIOS_MSX1_EU_BASIC_DISK", choice)  # <- hardcoded
```

So the `CALL FORMAT` cell of **`make diskbasic-acceptance-repack` had never once run on
the repack build.** It booted lean, converged, and scored PASS inside the repack column.

⚠️ **The wiring guard passed it because the env-var NAME appears in its source.**
`_check_repack_wiring` greps each registry probe for the string `ZEROBAS_BASIC_MACHINE`;
this probe *contains* that string while *ignoring* what it resolves to. That is the
[[oneflg-reset-scope-slice]] lesson — **the marker matched its own SOURCE ECHO** — live
in this corpus, and it is why the guard added in §2.2 asserts on the machine's *config*
rather than on a probe's source text.

Fixed here (`args = ap.parse_args()`, `run(args.machine, …)`). **The verb itself is
fine**: with the fix, CALL FORMAT converges on repack too. What was broken was the
*coverage claim*, not the behaviour — which is exactly the failure mode that leaves no
red anywhere to notice.

Scope check: `grep -rn '"C-BIOS_MSX1[A-Z_]*"' probes/disk/*.py | grep -v environ.get`
finds five other hardcoded literals; none is in the acceptance registry, and
`disk_probe_fat_error_disposition.py`'s is overridden by `make fat-error-acceptance`.
This was the only instance.

---

## 2. What this slice builds

### 2.1 Both gates state their subject (the headline)

```make
LEAN_MACHINE    := C-BIOS_MSX1_EU_BASIC_DISK
REPACK_MACHINE  := C-BIOS_MSX1_EU_REPACK_DISK
```

`diskbasic-acceptance` passes `ZEROBAS_BASIC_MACHINE=$(LEAN_MACHINE)` and
`--expect-build lean`; `-repack` passes `$(REPACK_MACHINE)` and `--expect-build repack`.
After this, no probe's hardcoded default decides what any gate measures, and retiring
lean is a two-line Makefile edit rather than a hunt through 38 files.

**Why `C-BIOS_MSX1_EU_BASIC_DISK` and not `C-BIOS_MSX1_BASIC_DISK`:** the repack machine
is built on C-BIOS **EU**. Pinning the lean gate to the EU machine too makes the two
gates a **controlled comparison** — they then differ only in the BASIC build, which is
the single thing they exist to isolate. Cost: 6 registry probes move from the
region-less machine to EU. Evidence this is safe: those same 6 already run green on the
EU-derived repack machine in `diskbasic-acceptance-repack`. **Verified by running the
gate**, not assumed.

### 2.2 The zerobas-side vacuity guard

New `_check_machine_provenance()` in [`diskbasic_acceptance.py`](probes/disk/diskbasic_acceptance.py),
numbered **§3.1.3–§3.1.5** to sit in the existing oracle-side guard family (§3.1.1
registry / §3.1.2 oracle-ran / the 0-denominator guard). It runs at startup, before any
probe boots. Three claims, each independently able to go red:

* **§3.1.3 — the machine RESOLVES.** `<name>.xml` must exist under the openMSX user
  machines dir or the share dir (same search order openMSX itself uses, via
  `tools/openmsx_paths.py`). Absent → die naming the machine and the dirs searched.
* **§3.1.4 — the machine is a ZEROBAS machine.** Its config must reference a zerobas
  artifact under the repo: an `<ips>` ending `/zerobas-msx1.ips` (⇒ **lean**), or a
  slot-0 `<filename>` equal to `build/zerobas-main-eu.rom` (⇒ **repack**). Neither ⇒
  **unknown** → die. This is the "pointed at stock C-BIOS and every probe reported
  nothing" case, which today looks like a mass functional failure rather than a
  wiring error.
* **§3.1.5 — the machine is the build the CALLER INTENDED.** The classification from
  §3.1.4 must equal `--expect-build`. Mismatch → die.

§3.1.5 is what makes the coupling in §1.2 **structurally impossible to reintroduce**: if
anyone ever points both targets at one machine, one of the two dies loudly instead of
both printing 34/34.

Also checked, cheap and non-timestamp: every repo-local path the config references
(`zerobas-msx1.ips`, `build/disk.rom`, `build/zerobas-main-eu.rom`, `build/sub.rom`)
must **exist**. A config naming a deleted `build/` artifact currently produces a boot
that fails in an unrelated-looking way.

Not built: a `probes/lib/zb_machine.py`. One caller does not justify a shared module;
extract it when a second gate wants it.

### 2.3 Freshness stays Make's job

`diskbasic-acceptance` gains `machines` as a prerequisite — which pulls in `$(PATCHES)`,
`$(TAPE_PATCHES)` and `$(DISK_ROM)`, so an edit to `basic/` regenerates the IPS **and**
reinstalls the config before the gate runs. This is the exact symmetry the repack gate
already has (`diskbasic-acceptance-repack: … repack-machine`), and it closes §1.3(a)
with Make's own mechanism rather than a hand-rolled mtime check that §1.3(b) shows
would misfire.

⚠️ Like `repack-machine`, this makes the gate write into the user's openMSX dir. That is
already true of every `-repack` target; the alternative is a gate that can silently test
a config the tree no longer describes.

### 2.4 Doc debt fixed in passing

[`tools/install-repack-machine.py:22`](tools/install-repack-machine.py:22) documents
`ZEROBAS_MACHINE_MAP=…` as the way to point the runner at the repack machine. **Grep
finds that name in exactly one place in the tree: that docstring.** The mechanism does
not exist; the real one is `ZEROBAS_BASIC_MACHINE`. One-line correction.

---

## 3. The 38 fallbacks — decision

**Recommendation: REMOVE them. Make the machine mandatory** — `--machine` defaulting to
`os.environ.get("ZEROBAS_BASIC_MACHINE")` (no literal), and `sys.exit(...)` with a
message naming both ways to supply it when neither is set.

Argued from what the guard can actually detect:

* The guard in §2.2 lives in the **runner**. It covers every gate invocation and nothing
  else. A probe invoked directly — which is how all 38 get debugged — never reaches it.
* **Leaving the fallbacks (option A)** makes the slice's headline claim true only for
  Makefile-driven runs. Worse, it is the option that decays: after lean retires,
  `make machines` keeps writing `*_BASIC_DISK` configs, so the literal keeps resolving
  and a directly-run probe keeps silently testing a build the project no longer ships.
  §1.3(c) shows the *loud* failure mode requires the machine to be **absent**; the
  fallback's failure mode is that it is **present and wrong**, which is the quiet one.
* **Repointing them at repack (option B)** is the §1.2 trap and is out.
* **Removing them (option C)** gives a failure that does not depend on openMSX's or a
  probe's timeout behaviour at all: no machine named ⇒ immediate `SystemExit` with a
  usable message. It is also the only option under which "no hardcoded default decides
  which build is under test" is literally true.

Cost: two lines per file × 38, plus the `make probe` call site (§1.1). No import added —
`argparse` default + an explicit `if not args.machine: sys.exit(...)`. The env-var name
stays in every source, so `_check_repack_wiring` (§3.1 guard) keeps passing.

**Sign-off question A:** do this in S1 (38 mechanical files, no assembly), or file it as
S1b? Recommendation: **in S1** — the headline claim is otherwise only half true.
→ ✅ **Signed off: done in S1.** All 38 rewritten; `grep 'ZEROBAS_BASIC_MACHINE", "'`
over `probes/disk/` returns nothing.

**Sign-off question B:** `zerobas-msx1.ips`/`.bps` are committed and are currently
byte-identical to a rebuild, so nothing needs regenerating. Confirmed no action. Noted
only because the shipped-artifact question (`zerobas-msx1.ips` vs `zerobas-main-eu.ips`)
is explicitly a later step.

### 3.1 Implementation note — the guard is INLINE, not shared

The spec's "no shared module" call (§2.2) was argued for the *provenance* guard, which
has one caller. The *no-default death* has 38, which normally argues the other way. It
is still inlined, for two measured reasons:

* **Import safety.** These probes import each other — `disk_probe_alloc_order.py` imports
  `disk_probe_wrblk_roundtrip.py`, and `disk_probe_bdos.py` is imported by 12 modules. A
  module-level `sys.exit` would fire on *import*, not on use. Every guard therefore sits
  **after** `parse_args()` (or at the top of `main()` where there is no CLI option), and
  the module-level constants merely become `None`.
* **Standalone-script is a design property of this corpus** — the runner's own docstring
  leans on it ("every Disk-BASIC differential probe is a STANDALONE script whose process
  exit code IS its verdict"). A 3-line inline guard preserves that; an import does not.

Six probes expose `--ours-machine`; their guard checks the **parsed** value, so that flag
still works with no env var set. (First cut guarded the module constant and would have
blocked it — caught before landing.)

---

## 4. Falsification — the guard must be made to FIRE

A guard that never goes red in testing is not a guard. Each row is run, and its
observed output recorded in this doc before the slice is called done.

| # | Perturbation | Guard | Observed |
|---|---|---|---|
| F1 | `--machine C-BIOS_NO_SUCH_MACHINE` | §3.1.3 | ✅ rc=1, `does not resolve — no …xml in any of:` + both dirs. **No probe booted.** |
| F2 | lean target → `C-BIOS_MSX1_EU` (stock, no zerobas) | §3.1.4 | ✅ rc=1, `references NO zerobas artifact — it is not a zerobas machine` |
| F3 | `--expect-build lean` + `$(REPACK_MACHINE)` | §3.1.5 | ✅ rc=1, `but 'C-BIOS_MSX1_EU_REPACK_DISK' … is a REPACK machine` — **the §1.2 trap, caught** |
| F4 | `--expect-build repack` + `$(LEAN_MACHINE)` | §3.1.5 | ✅ rc=1, `… is a LEAN machine` |
| F5 | `mv build/disk.rom` aside | §3.1.4 refs | ✅ rc=1, names the missing path; restored 16384 B |
| F6a | `python3 disk_probe_files.py` (argparse shape) | §3 | ✅ rc=1, `pass --machine or set $ZEROBAS_BASIC_MACHINE` |
| F6b | `disk_probe_open_device.py` (module-const shape) | §3 | ✅ rc=1, `pass --ours-machine or set …` |
| F6c | `disk_probe_wrblk_roundtrip.py` (no CLI option) | §3 | ✅ rc=1, `set $ZEROBAS_BASIC_MACHINE` |
| F6d | runner with no machine at all | §3 | ✅ rc=1, `no default — a hardcoded one silently decides which BUILD this gate measures` |
| F6e | runner with a machine but no `--expect-build` | §3.1.5 | ✅ rc=1, refuses to guess |
| F7 | **control:** unperturbed `make diskbasic-acceptance` | — | ✅ **34/34**, header line `[runner] zerobas machine: C-BIOS_MSX1_EU_BASIC_DISK build=lean` |

F7 is the two-sided half: F1–F6 prove the guard *can* fire, F7 proves it does not fire
on the real thing ([[control-that-fails-must-be-fixed]], and the two-sided-control
lesson from [[clearpool-slice]]).

⚠️ **F3/F4 are perturbations of the Makefile, reverted immediately.** They are the only
rows that prove the two gates cannot silently merge.

---

## 5. Gates to keep green

Run, not assumed. All green after the change:

| gate | result |
|---|---|
| `make unit-test` | ✅ ALL 54 |
| `make diskbasic-acceptance` | ✅ **34/34, `build=lean`** — still the lean gate |
| `make diskbasic-acceptance-repack` | ✅ 34/34, `build=repack` — incl. CALL FORMAT, **for the first time** (§1.4) |
| `make bdos-acceptance` | ✅ 12/12 |
| `make fat-error-acceptance` | ✅ 7/7 |
| `make abort-acceptance` | ✅ 31/31 |
| `make error-trap-acceptance` | ✅ ALL PASS |
| `make chancost-characterize` | ✅ 39 cases / 1 filed divergence |
| `make probe` | ✅ smoke OK (disk + basic + tape) — dskio now on `$(LEAN_MACHINE)` |
| `rm -rf build && make basic-reloc` | ✅ **low 0 B, page 1 7 B, lean byte-identical** — unchanged |

Since the slice touches no assembly, `basic-reloc` reporting byte-identical is the
cheapest proof it stayed in its lane. Confirmed independently:
`git diff --stat -- basic/ sub/ disk/ tape/ '*.ips' '*.bps'` is **empty**.

`tools/check_reloc.py` is **not touched**. Its four checks and the
`__MEAS_LOW_END`/`__MEAS_PAGE1_END` wall readout are what every slice is costed against.

---

## 6. Also corrected in `TODO.md`

The lean-cart entry says "**276** `IF ROM_BASE` gates". Measured now:
`grep -rn 'IF ROM_BASE' basic/ | wc -l` → **311**. Corrected in place.

---

## 7. Explicitly NOT in this slice

* `make probe` passing `--cart $(ROM)` (the lean ROM directly) — later step. This slice
  only gives `disk_probe_dskio.py` an explicit machine so §3 does not break it.
* The shipped-artifact decision (`zerobas-msx1.ips/.bps` from lean vs
  `zerobas-main-eu.ips/.bps` from repack) — user-facing release call.
* Deleting the 311 `IF ROM_BASE` gates, or `tools/check_reloc.py`'s frozen baseline.
* Any claim that retiring lean frees ROM space. **It frees none** — deleting
  `IF ROM_BASE >= $4000` branches does not change one byte of the repack binary.
