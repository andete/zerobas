# D-CLRTRAP — `CLEAR` did not touch the event traps, and that was two defects

*2026-08-30. `basic/vars.asm` (`clear_vars`). Probes
`scratchpad/clrarm_probe.py` (new) and `scratchpad/clrtrapstk_probe.py`
(2026-08-26); knife `scratchpad/clrtrap_knives.py`. **3 bytes of main page 1.***

## 1. Two rows, one missing reset

| | vg8020 | zerobas (before) |
|---|---|---|
| an **armed, live** `ON INTERVAL` — fires in the window after `CLEAR` | **0** | **17** |
| a trap the program **killed**, then `CLEAR`, then an unrelated `GOSUB`/`RETURN` | **1** | **17** |

The second row is the defect filed in
[`docs/spec-basic-trapsvc.md`](docs/spec-basic-trapsvc.md) §7 and confirmed live
on 2026-08-26: `clear_vars` reset `GSP` to the base **without** resetting
`TRAPSTK`, so the first unrelated `GOSUB` landed back on a stale record's saved
gsp and `trap_return_check` re-enabled a trap the program believed dead.

**The first row is new, and it is the simpler half**: `CLEAR` did not disarm an
armed trap at all. Both are the same missing reset.

## 2. 🎯 The question that had to be asked before the fix

The filed item proposed `clear_vars` calling `trap_init`. `clear_vars` has
**exactly four call sites** — cold boot, `RUN`, `NEW`, `CLEAR` — so that hook
wipes the whole trap block on `CLEAR` as well, and **that is only correct if the
reference also stops an armed trap there.** Nobody had asked: the measured
defect was about a trap the program had *killed*.

`scratchpad/clrarm_probe.py` asks it. On a VG-8020 an armed `ON INTERVAL` fires
**16 times in the window before `CLEAR` and 0 in the window after**, against a
no-CLEAR control that fires 16 and 16. So the broad hook is not broad — it is
the reference's own behaviour, and it closes both rows at once.

⚠️ **The control's total jitters by one** (32 on one machine, 33 on the other): a
160-frame window at a 10-tick interval yields 16 or 17 fires depending on where
it opens. The row under test does not jitter — it is 0-versus-nonzero, which is
why the second window's count is reported separately rather than subtracted
after the fact.

⚠️ **One reference, and the reason is the harness.** The CF-3300 needs a longer
boot and its own reset, which `basic_probe_interval_trap.run` does not carry;
both CF-3300 runs reached no done sentinel and the probe **refused** rather than
reporting their zeros as disarmed traps. `ON INTERVAL` is core MSX1 BASIC, so a
VG-8020 is a legitimate oracle alone here — the sibling probe drops it too.

## 3. Why it is three bytes, and why the filed price was not

The item read *"NOT PRICED, AND THE FIX IS A SPEND … a budget decision, not an
edit"*, and its sibling was declined at *"~25–30 B of main page 1 against **2 B
free** (measured `b8a8137`)"*. **That wall reading is from a different tree.**
Main page 1 stood at 336 B free before this change and 333 B after: one
`call trap_init` on a hook that already exists.

🔴 **A PRICE ROTS EXACTLY LIKE A WALL, AND IT TAKES THE MARKER WITH IT.** The
`🔭 SCOUT-THEN-ASK` on that item was justified *by the cost*, and the cost
premise had been false for days. Re-pricing is what the marker itself says is
not Joost's to do.

## 4. The arm

One cut — `clear_vars`'s `call trap_init` — with **two independent witnesses**,
because the arm-state reset and the service-stack reset are the same three bytes
but not the same defect:

| witness | with the cut |
|---|---|
| `clrarm` — armed trap, 2nd window | **17** (want > 0) |
| `clrtrapstk` — killed trap, fires | **17** (want ≥ 2) |

🟢 And a free self-check: with the three bytes cut the ROM hashes **exactly**
back to the previous commit, so the cut is precisely this change and nothing
else.

⚠️ The knife's first readback died on `int('zb')`. Both probes left-justify a
label containing spaces and the two labels have **different word counts**, so a
fixed column index reads the side name as a number on one and the right cell on
the other. It now splits on the `zb` field itself.

## 5. What this does NOT close

The **six-event `TRAPSVC` cap** (`docs/spec-basic-trapsvc.md` §4/§6, row
`int.six`: `6 18` against both references' `9 18`) is untouched. That one is a
real design question — its §6 rejects the two cheaper fixes on principle, and one
of them makes a trap *silently* dead — so it stays 🙋. Only its **price** was
corrected here.
