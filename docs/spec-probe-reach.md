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
