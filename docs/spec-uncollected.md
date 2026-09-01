# D-UNCOLLECTED — `make gates` collects 22 of 68 acceptance suites, and three of the rest are RED

**2026-09-01.** The review tier's last open task was *"the arc-covered groups —
spot-verify each arc actually reads the MECHANISM before trusting the name."*
Two of the named arcs (`print/lprint/llist`, via `basic_probe_lptverb.py`'s
printer-log readout) verify immediately: they read the mechanism, not the name.

Then a different question surfaced, and it was the load-bearing one.

## The gap between "reachable" and "collected"

`probe-reach-check` already gates *"which probes does no `make` target ever
run?"* — written after D-WALLIT found a probe failing "for an unknown number of
months" because nothing ran it. **That is weaker than it looks.** It asks whether
*some* target runs the probe. It does not ask whether the **battery** does.

Measured: the Makefile has **68 `*-acceptance` targets with recipes**.
`make gates` collects **22**. All 46 of the rest pass `probe-reach-check`.

**Nothing recorded that.** There is no aggregate `acceptance` target, and no
target runs one. Exactly one exclusion in the tree carries a written reason
(`omsx-diag-teeth`, which SIGKILLs `openmsx` by name). The project's own memory
describes `make gates` as *"the whole acceptance-gate battery"* — measurably
false, and the kind of belief that lets a suite rot.

## Running the other 46

41 run serially with `ZEROBAS_REFCACHE=0` (5 held back and named rather than
assumed about: the three Tier-2 disk-provider arcs, `input-devices-acceptance`,
and a `--say` variant). **Three are RED, and they fail three different ways:**

| suite | what it is |
|---|---|
| `cursor-acceptance` | a **real zerobas divergence**: `X=TAB(5)` / `X=SPC(5)` / `IF TAB(5)=0` outside a `PRINT` give `Missing operand` here, `Syntax error` on the reference. **And its `KNOWN_RED` exemption is stale** — all 8 exempted rows now AGREE, so the exemption suppresses nothing while the suite is red for a reason it never names. |
| `namspc-acceptance` | a **POSITIVE CONTROL fails on the reference** (`f.filesbare` wants `6 entries + OK` from the CF-3300), so the probe refuses: *"nothing was measured."* A frozen expectation that rotted — the D-FILESROT class, which this session already repaired once elsewhere. |
| `time-acceptance` | `is_jiffy` reads **12289**, want **12288**. |

38 measured **green**. Two suites that pass in ~0 s were checked rather than
assumed: `graphics-floor-acceptance` is two assertions and
`subrom-acceptance` is two CALSLT pings — both legitimately that small.

🎯 **THE EXEMPTION AND THE FAILURE WERE DIFFERENT THINGS.** `cursor-acceptance`
carries a banner reading *"D-CUR-3 — KNOWN RED, reported not gated: a
mid-statement error does not abort the statement"*. Every row that banner covers
now agrees. The rows that actually fail are not in the exempt set at all. A
suite excluded for being knowingly red was red for something else entirely.

## The fix is the membership, not the three suites

`make battery-membership-check` (static tier, in the battery) fails if an
acceptance target is neither in `run_gates.py`'s `STATIC`/`EMULATOR` nor listed
in `tools/battery-exclusions.txt` **with a reason**. Excluding a suite stays
legitimate; excluding it silently does not. Same discipline as
`check_selftests.py`'s `EXPECT_ARG` and D-GENFRESH's `REGENERATED`: the list may
grow, but never quietly.

**38 of the 46 entries say `UNREVIEWED — no reason was ever recorded`**, each
carrying its measured colour from this sweep. That is the honest state: the debt
is now visible and counted rather than invisible. Inventing rationales for 38
decisions nobody wrote down would have been worse than naming the gap.

## Arms

`S1` the live tree is clean · `S2` a target with neither a battery slot nor an
entry goes RED · `S3` putting the entry back goes green (the control) · `S4` a
degenerate battery parse **refuses (rc 2)** rather than reporting a finding.

🔴 **S4 IS NOT HYPOTHETICAL.** The first cut of this very measurement used a
regex that expected `GATES = [...]`; the lists are triple-quoted strings, so it
parsed **zero** gate names and produced a tidy table declaring all 86 probes
uncollected. The floors exist because the instrument already failed that way
once, in this slice [[an-instrument-can-fail-the-way-the-thing-it-replaced-failed]].

Battery: 26 → **27 static** units, 50 total.
