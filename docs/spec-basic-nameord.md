# D-NAMEORD — `NAME`'s new-name operand is evaluated after the lookup now

The reference rule, established by D-TODOSWEEP tranche 65 and unchanged since:
**look the old file up first, then evaluate the new name**, which then faults like
every other verb's operand.

    NAME"X.DAT"AS 5     (old file ABSENT)   cf3300 ERR 53   zb ERR 2  ->  53  ✅
    NAME"HI.TXT"AS 5    (old file EXISTS)   cf3300 ERR 13   zb ERR 2  ->   2  🔴
    NAME 5 AS"X.DAT"    (old-name position) cf3300 ERR 13   zb ERR 13     ok

## What changed

`call fname_expr` for the NEW name moved from before `DISKSLOT_OK`/`fat_mount` to
after `fat_find` succeeds. The text cursor is parked in `FN_RESUME` across the
disk primitives — the same cell the OLD name's call already uses, and the reason
the error exits carry no `pop`. **+6 B**, exactly as priced.

🟢 **It deletes a claim rather than adding one.** The old comment argued that the
staged new name survives `fat_mount` + `fat_find` *by address* — 30 bytes of
margin against DSKIO's FDC work area at `$E29A..$E29F`. With the evaluation moved
after the lookup, nothing is staged across a disk primitive at all, so that
argument stops being load-bearing. It is kept, inverted, because the reasoning
about `STRSCR`'s span is still correct and still the answer if anything is ever
staged there again.

## 🔴 The filed design said this fixes both rows. It fixes one.

The entry's pricing read: *"THE REORDER ALONE FIXES BOTH ROWS, AND NOTHING NEW HAS
TO PRODUCE ERR 13 … with it present, `fname_expr` runs and faults → 13"*.

Measured: `name.as5` goes 2 → **53** and matches. `name.ex5` stays at **2** where
13 is due. All five controls hold.

**And the cause is not the ordering.** A bisect planted the round-trip with *no
disk primitive in between* — park the cursor, restore it, evaluate immediately —
and the row still read 2. So `FN_RESUME` is not being clobbered (it is `$E227`,
with no declared overlap, and only two writers in the tree), and the second
`fname_expr` call site produces `Syntax error` for a numeric operand for a reason
that predates this change and survives it. The same routine gives 13 from the
old-name position (`name.old5`, green). **That is a separate defect, still open.**

## ⚠️ Two apparatus faults on the way, both caught by controls

**A hand-rolled probe with no scratch disk.** The first attempt at localising the
second cause used its own fixture; every row came back `ERR 70 Write protected`
from the CF-3300 — *including* the must-succeed rename control. The control is
the only reason that read as a fixture fault instead of six findings.

**A control that mutated the fixture.** The second attempt added
`NAME"HI.TXT"AS"BYE.TXT"` as a must-succeed control to tranche 65's own row set.
The rows share one scratch disk and run in sequence, so it renamed `HI.TXT` away
and every later row — including the subject — then read `53 File not found`.
**A control that mutates shared state is not a control.** The shape rows that
remain all fault before any rename, so they leave the disk untouched; the scout
was discarded rather than trusted, and the readings above come from the
*unmodified* tranche-65 probe run twice.

## Still open

* `name.ex5` — `Syntax error` where `Type mismatch` is due, cause not the order.
* ✅ **The side-effect is measured, and it is benign.** [`probes/basic/basic_probe_namend.py`](../probes/basic/basic_probe_namend.py),
  **0/6 DIFF**: the VG-8020 answers `ERR 5` to every disk-verb form because it has
  no drive, and `zb-nodisk` matches exactly. `q.open5` gives **13** on both —
  `OPEN`'s type check precedes its disk check — and zerobas reproduces that shape
  too, which is what makes the reading a rule rather than one flat column of 5s.
  Gated as `make nameord-acceptance`, because an honest `rc` no battery collects
  is not an oracle.
  🔴 **And the gate caught me wiring it wrong.** The probe was written into
  `scratchpad/` and the recipe pointed there; `run_gates.py`'s own selftest **S6
  — "the LIVE premise holds: no emulator recipe leaves the fingerprint"** — went
  RED. The D-GATESKIP fingerprint covers ROMs and probe/test/tool sources, *not*
  `scratchpad/`, so editing that probe would not have invalidated the skip: the
  battery could have skipped the entire emulator tier while the gate's own probe
  changed underneath it. I had checked that convention earlier in the session and
  then broke it an hour later. Promoted to `probes/basic/`; S6 green.
* ⚠️ **The cf3300 side is still in no gate.** `name.as5` / `name.ex5` live only in
  `scratchpad/sweep_tranche65.py`, a sweep instrument. The row this slice fixed is
  therefore unguarded against regression on the disk build.
