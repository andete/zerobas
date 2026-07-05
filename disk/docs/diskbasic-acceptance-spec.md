<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Disk-BASIC acceptance gate — spec (for sign-off, not yet built)

**Status:** DRAFT, awaiting sign-off. Nothing here is implemented yet.
**Companion:** [diskbasic-verb-coverage.md](diskbasic-verb-coverage.md) (the scoreboard
this gate maintains) and, as the proven precedent, the BDOS gate
`probes/disk/disk_bdos_acceptance.py` + [tier2-bdos-coverage.md](tier2-bdos-coverage.md).

## 1. Goal

Give the Disk-BASIC verb surface the one coverage layer it lacks (finding **F2** of the
coverage doc): a **standing acceptance gate** — `make diskbasic-acceptance` — that re-runs
the self-asserting Disk-BASIC differential probes and re-asserts each converges to the
oracle, printing an `N/N` scoreboard. Turns "proven once, by hand" into "proven every
release," exactly as `make bdos-acceptance` did for BDOS.

## 2. Non-goals

- **Not** a new probe framework. The ~18 `disk_probe_*` differentials already exist and
  already self-assert; this is a *runner* over them, nothing more.
- **Not** in `make unit-test`. Like the BDOS gate it is oracle-dependent (boots openMSX for
  both the zerobas machine and the CF-3300 black box), so it needs `make machines-oracle` +
  your own reference ROMs and stays out of the fast emulator-free layer.
- **Not** re-deriving the matrix. The gate's *output* is what makes the scoreboard
  authoritative (replacing today's static-analysis seed).

## 3. Design — why it's simpler than the BDOS gate

The BDOS gate is complex because its exercisers are `.COM` files whose exact differential
invocation is computed by build scripts, so it must *harvest* command lines and carry an
address **allowlist** for documented divergences. The Disk-BASIC probes are different in the
way that matters:

> Each `disk_probe_*.py` is a **standalone script whose process exit code is its verdict** —
> `raise SystemExit(main())`, where `main()` boots the zerobas machine *and* the CF-3300
> reference, compares, and returns `0` on convergence / non-zero on divergence. `--no-ref`
> exists to skip the oracle (must **never** be passed by the gate).

So the runner is a thin **registry-driven subprocess dispatcher**:

```
for each (label, script, argv) in REGISTRY:
    rc = subprocess.run(["python3", script, *argv], cwd=ROOT).returncode
    pass = (rc == 0)
print N_passed / N_total   ; exit 1 if any failed
```

No command harvesting, no allowlist, no verdict-line parsing — the probes already own all of
that. The runner mirrors `disk_bdos_acceptance.py`'s CLI surface (`--only`, `--list`,
`N/N` summary, `/tmp` disk-copy hygiene) so the two gates feel identical to run.

### 3.1 Vacuity guard (the BDOS-gate lesson, applied up front)

The BDOS gate was bitten twice by *vacuous* passes (an anchor firing at boot; `rc=0`
despite byte diffs — see `disk_bdos_acceptance.py` docstring). We pre-empt the analogue here
with two rules baked into the runner's acceptance criteria:

1. **Never pass `--no-ref`.** A probe run without the oracle can't diverge — it would be a
   green cell proving nothing. The runner asserts the oracle ran (probe prints a
   `ref`/`stock` capture line; its absence fails the cell).
2. **One-time falsification per probe.** Before a probe is admitted to the registry, confirm
   it exits **non-zero** when the expectation is deliberately corrupted (a throwaway local
   edit, reverted). A probe that can't fail isn't a gate. Record the check in the coverage
   doc's Notes, not in committed code.

## 4. Probe registry (the gated set)

From the ✅ rows of [diskbasic-verb-coverage.md](diskbasic-verb-coverage.md) §2. Two oracle
styles, both run by the same dispatcher (they differ only in the machine each probe defaults
to — the runner passes **no** `--machine`, letting each probe's own default stand):

**Live CF-3300 differentials** (`--ref-machine National_CF-3300`, default
`C-BIOS_MSX1_EU_BASIC_DISK`):

| Verb(s) | Probe |
|---------|-------|
| FILES | `disk_probe_files` |
| KILL | `disk_probe_kill` |
| NAME | `disk_probe_name` |
| MAXFILES | `disk_probe_maxfiles` |
| MERGE | `disk_probe_merge` |
| FIELD / LSET / RSET | `disk_probe_field` |
| GET / PUT (record) | `disk_probe_getput` |
| GET (RDBLK round-trip) | `disk_probe_rdblk_roundtrip` |
| PUT (WRBLK round-trip) | `disk_probe_wrblk_roundtrip` |
| MKI$/CVI family | `disk_probe_mkicvi` |
| EOF / LOF | `disk_probe_eof` |
| DSKF | `disk_probe_dskf` |
| PRINT# (seq write) | `disk_probe_filewrite` |
| PRINT# append | `disk_probe_append` |
| INPUT# (seq read) | `disk_probe_fileread` |
| PRINT# USING | `disk_probe_printusing_file` |
| INPUT$ | `disk_probe_inputdollar` |
| CALL FORMAT | `disk_probe_format` |

**Read-only FAT12-artifact oracle** (default `C-BIOS_MSX1_BASIC_DISK` + seed image):

| Verb(s) | Probe |
|---------|-------|
| SAVE / BSAVE | `disk_probe_save` |
| LOAD | `disk_probe_load_disk` |
| LOAD (embedded-NUL regression) | `disk_probe_load_embedded_nul` |
| RUN "file" | `disk_probe_run_disk` |
| BLOAD | `disk_probe_bload_disk` |

Registry entries carry a `label` (the verb, for the scoreboard line) and optional fixed
args; almost all need none.

## 5. Makefile target

```make
diskbasic-acceptance: $(DISK_ROM)
	python3 probes/disk/diskbasic_acceptance.py $(if $(ONLY),--only $(ONLY),)
```

Same shape and `ONLY=` override as `bdos-acceptance`. Prerequisites (documented in the
target's help + probes/README.md): `make machines-oracle`, the seed FAT12 image
(`tools/make_test_dsk.py`), and user-supplied CF-3300 reference ROMs.

## 6. Scoreboard maintenance

The gate's `N/N` output is transcribed into
[diskbasic-verb-coverage.md](diskbasic-verb-coverage.md): flip each gated verb's **Gated**
column ❌→✅, record a dated **green-baseline** line (mirroring the BDOS doc's
"Green baseline 2026-07-04: 6/6"), and drop the "provisional / static-analysis" caveat once
every cell is backed by a real run. From then on the scoreboard is *gate-maintained, not
hand-maintained* — the BDOS rule.

## 7. Adopted decisions (provisional — flagged for your veto)

The three §4 open decisions in the coverage doc were left to your call; you said *continue*,
so this spec adopts my recommended defaults **provisionally**. Say the word to change any:

1. **Gate-first, backfill after.** Ship the gate over the strong existing set above **now**;
   the two thin cells (**F4**: `CLOSE`, `LINE INPUT#`) get dedicated differentials *after*,
   then join the registry. Rationale: fastest path to a live regression net.
2. **Retire the smoke probes.** `diskbasic_probe_filechannel` / `diskbasic_probe_files` /
   `diskbasic_probe_format` assert nothing and are superseded by the `disk_probe_*`
   differentials above — remove them so they can't read as coverage. (Their scenarios are
   already covered by the gated probes; this loses no real assertion.)
3. **Plain BASIC next.** After Disk-BASIC lands, the same audit + gate for the 21
   `basic_probe_*` (vs Philips VG-8020). Tracked as a follow-on, not part of this spec.

## 8. Acceptance criteria for the gate itself

- `make diskbasic-acceptance` runs every registry probe, prints `N/N`, exits 0 only if all
  converged; `ONLY=<probe>` narrows it; `--list` prints the plan without running.
- Every cell ran **with** its oracle (no `--no-ref`); the runner fails a cell whose oracle
  capture is absent (vacuity guard §3.1.1).
- Each admitted probe passed the one-time falsification check (§3.1.2).
- Green baseline recorded in the coverage doc; the two `F4` backfill items and the smoke-probe
  retirement listed there as the remaining open work.

## 9. Rough size / sequencing

1. Retire the 3 smoke probes (decision 2) — deletions + README table note.
2. Write `probes/disk/diskbasic_acceptance.py` (registry + dispatcher + §3.1 guards),
   modelled on `disk_bdos_acceptance.py` minus the harvest/allowlist machinery.
3. Add the Makefile target; run it; capture the green baseline into the coverage doc.
4. (Backfill, decision 1) dedicated `CLOSE` + `LINE INPUT#` differentials; add to registry.

Steps 1–3 are the gate; step 4 closes the last two coverage cells. Each is a commit.

---

**Sign-off needed on:** §7 adopted decisions and the §4 registry set. On approval I'll
execute §9 in order (spec → implementation, per our workflow).
