# D-PROBEREACH — the count nobody had: 104 probes no `make` target runs

*2026-08-31. `tools/check_probe_reach.py` + `tools/probe-reach-allow.txt`, wired
as `make probe-reach-check` (static tier). No ROM change.*

## 1. The question, asked four days ago

D-WALLIT (`docs/spec-wall-literals.md` §3.1) found `basic_probe_cas_verbs.py`
failing two cases *"for an unknown number of months"*: it returns an honest
`rc=1`, it is documented in `README.md`, and **nothing ever ran it**. It was
found by accident. The item owed two things, and marked only the first
autonomous:

> **(a) COUNT the probes that no `make` target and no battery invokes — the
> denominator is unmeasured.**

## 2. The answer

| | |
|---|---|
| probes under `probes/` | **204** |
| invoked by a `make` recipe | 89 |
| imported by an invoked one | 11 |
| **unreached** | **104** |

## 3. 🔴 Three states, not two — and the middle one is why a naive count lies

`basic_probe_deffn.py` is the expression harness a dozen probes drive. It has no
`make` target of its own, and its code runs on **every** battery. A check that
asked only *"is it named in the Makefile?"* would report every harness as dead —
which is precisely the failure mode this tool exists to prevent.

So the tool walks the **import graph** from the invoked set and reports only what
neither reaches. `S2` is the control: a pure library harness must land in
IMPORTED, never in UNREACHED.

🔴 **And it refuses on a degenerate scan.** Fewer than 15 invocations found is an
instrument failure, exit 2, never a finding — `S5` drives that path with an
unreadable Makefile rather than asserting it.

## 4. Pinned as a ratchet, because the triage is not mine

104 entries are too many to fix in a slice, and **(b) — which of them earn a
battery slot — is a runtime-budget call `TODO.md` marks NEEDS-JOOST**: one tape
probe alone is ~4 min against a ~460 s battery.

So the 104 are **pinned with grouped reasons** (tape BIOS oracles, one-shot disk
oracles, BDOS fixture builders, closed-slice BASIC probes). That makes the number
a **ratchet**: it can only go down, and any probe added from here must either get
a target or be pinned on purpose — reported the same day rather than months
later. Same shape as `citations-advisory-allow.txt`: **the SET is pinned, the
judgement is not.**

🎯 **`S6` is the arm that makes the ratchet real**: drop one entry from the
allowlist and the check must go RED. An allowlist that pins everything is exactly
as useless as no check at all unless an unpinned name is still reported — so that
is driven, not asserted, and `S7` puts it back and confirms clean.

## 5. 🔴 The reasons in the first cut were written from FILENAMES, and 65 were wrong

The allowlist's first version grouped the 104 by directory and name and called
them all *"characterisation oracles whose answers are already in specs"*. Reading
them says otherwise: **65 of the 104 describe themselves as differential /
functional / regression / acceptance** — live verdicts nobody collects. That is
the D-WALLIT shape at scale, not a pile of spent oracles. The reasons now say
which is which.

**A grouping derived from filenames is a hypothesis, and it went into a committed
file as a statement.**

## 6. 🔴 Six name the retired lean cart — and running them says three different things

⚠️ **"Six cannot run at all" was my own over-claim, corrected by running them
serially on a fresh build.** The accurate breakdown:

| | probes | state |
|---|---|---|
| refuse **by design** | `disk_probe_autoexec`, `disk_probe_save_bas` | *"no zerobas machine: pass `--ours-machine`… one would silently pick the BUILD under test"* — the S1 rule **working**. They name the cart only in a usage comment. They need an argument, not a repair. |
| **crashed** | `basic_probe_cas_verify` | `os.path.exists(None)` before any check — could not run in its default mode at all. **Repaired; now ALL PASS.** |
| preflight-refuse | `basic_probe_printusing`, `disk_probe_crossbios`, `basic_probe_cas_match` | genuinely bound to `build/basic.rom` |

🎯 **The repair is a half-finished migration.** `cas_verify`'s own header says the
default rig carries BASIC in slot 0 and needs no cartridge — and the code still
built `-cart` unconditionally. **Half of the S3 lean-cart retirement landed in
the prose and not in the code**, and nothing noticed because no `make` target
runs the probe. It is now green over four cases asserting `CLOAD?` verify
behaviour.

⚠️ **And the preflight's advice is wrong for these**: it says *"FIX: make
repack-machine"*, which cannot help — the Makefile says *"there is no
`build/basic.rom` rule any more."*

⚠️ **The first count was 2, and it was wrong**: grepping `build/basic.rom` misses
`os.path.join(ZEROBAS, "build", "basic.rom")`, which splits the path across
arguments. Matching the FILENAME found six. *A literal-path grep is the same
instrument hazard this project keeps re-learning.*

## 7. 🔴 And I nearly reported six false failures

Running six of the uncollected probes **in parallel**, on a tree whose ROM was
stale after a Makefile edit, produced `rc != 0` on all six. Read at face value
that is a headline: *"every uncollected probe is failing."*

Re-run **serially on a fresh build**: five green, one refusing (the lean-cart
one). The reds were entirely my own apparatus — six emulators at once plus a
stale ROM — which is the contention lesson from this morning's D-NOSLEEP2,
re-learned in the same session.

## 8. What this does not claim

It does **not** say those 104 probes are worthless — most are characterisation
oracles whose answers are already written into specs, which is a legitimate
end state. It says only that **their `rc` is collected by nothing**, so a break
in any of them is silent. That is the shape D-WALLIT hit, and it is now counted
and watched instead of rediscovered by accident.


## 9. D-PROBEREACH4 — the BASIC batch: 23 of 26 still re-provable

*Joost's framing, and it is the right one:* **a probe that proved a documented
fact is worth keeping as an ARCHIVE, because the fact stays re-provable.** The
criterion that follows is sharper than "does it deserve a battery slot":

> **An archived probe is only worth keeping if it still RUNS.** Otherwise it is
> not an archive but a fossil — the fact is no longer re-provable, and nobody
> finds out until they try.

All 26 unreached `probes/basic/` probes, run **serially on a fresh build**:

| | count | |
|---|---|---|
| green | **22** | archived and re-provable |
| refuses legibly, runs on the merged rig | 1 | `cas_leader_budget` — repaired here |
| `--cart` REQUIRED by design | 2 | `bload_openstack`, `cload_ondevice` — they test cartridge behaviour |
| genuinely rotten | **1** | `printusing` — bound to the retired lean cart |

🎯 **`basic_probe_cas_verbs` is GREEN.** That is the probe D-WALLIT found failing
*"for an unknown number of months"* and which opened this whole item. It got
fixed — and **nobody knew, because nothing ran it.** An archive that nothing ever
runs cannot tell you the good news either.

🎯 **A third instance of one defect.** `cas_leader_budget` handed openMSX a
literal `None` for its cart, so the preflight said `MISSING None` — accurate and
useless. After `cas_verify` and `cas_match`, that is three probes with the same
half-finished lean-cart migration, all invisible because unreached. Its refusal
now names the cause, and **the fix its message suggests was verified**:
`--machine C-BIOS_MSX1_EU_REPACK_DISK` runs it green.

⚠️ **Only `probes/basic/` has been run.** The other 78 entries (disk, tape, lib)
are pinned but UNVERIFIED — their reasons say so rather than implying a verdict.


## 10. D-PROBEREACH5 — the disk batch: 47 of 65 green, and TWO genuinely rotted

🔴 **The first disk batch asked the wrong question, and the timing said so.**
Every failure came back in **0.1 s** — no emulator ever started. `probes/disk/`
almost all refuse with *"no zerobas machine: pass `--machine` … there is no
default, one would silently pick the BUILD under test"*, which is the S1 rule
**working**. A bare run measures *"does it have a default"* (deliberately no),
not *"is the archived fact re-provable"*. Re-run with `ZEROBAS_BASIC_MACHINE`
supplied:

| | count |
|---|---|
| green — archived and re-provable | **47** |
| need `--dos-disk` (a DOS image this repo does not ship) | 10 |
| need another argument / preset | 4 |
| bound to the retired lean cart | 2 |
| **genuinely rotted** | **2** |

⚠️ *A 0-second refusal is not contention* — the tell `probe_awake`'s own header
records — and here it was the difference between a meaningless batch and a
useful one.

### The two that rotted

**`disk_probe_files` — rotted against its FIXTURE.** `disk/test720.dsk` gained
`TS.DAT`; the probe's hardcoded `EXPECT` and `CF3300_W29` still list only the
five older files, so it reports *"wrap/format differs from CF-3300"*. The fixture
legitimately changed and the probe never learned. **The reference column is a
frozen reading**, so the fix is to RE-MEASURE the CF-3300 against the current
disk, not to edit the constant into agreement.

**`disk_probe_bload_fcb` — its SUBJECT MOVED.** It reports *"landmark 0x5355 not
hit? refresh do_disk_bload addr"*, which reads like a stale number. It is not:
`do_disk_bload` is **absent from `build/basic-reloc.sym`** and lives only in
`build/sub.sym` at `$73FB` — the routine was **evicted to the sub-ROM**. The
probe breaks at a main-ROM address on a diskless machine, which cannot work at
all any more. Re-siting the breakpoint into a sub-ROM tenant is a design job, not
a refresh.

🎯 **Both are the D-WALLIT shape**: a documented fact whose proof quietly stopped
working, invisible because nothing runs the proof. Two in 65, found by running
them.
