# SCREEN's error surface on an MSX1 — measurement notebook (2026-08-10)

Notebook for [`spec-basic-screenerr.md`](spec-basic-screenerr.md). Probe:
[`probes/basic/basic_probe_screenerr.py`](../probes/basic/basic_probe_screenerr.py),
gate `make screenerr-acceptance`. Sides: Philips VG-8020, National CF-3300,
zerobas on `C-BIOS_MSX1_EU_REPACK_DISK`. Both reference ROMs are black boxes.

## 1. 🔴 The instrument had to change before anything could be measured

D-STMTPEND left `u.scr.dz` **deferred rather than scored**, and the reason is the
whole methodological point of this slice: **the subject of the reading is the
screen, and the obvious reading is a screen scrape.** `SCREEN 0*(1/0)`
reinitialises the display before it reports, so the `RUN` echo `screen_tail`
anchors on is gone and the probe reads `<NO ECHO>` — not a wrong message, *no*
message. The same wall stopped D-STMTPEND's scouting from the other direction:
`SCREEN 1` returned `<NO CAPTURE>` on **both** references
([[readout-blind-to-its-own-subject]]).

The answer is to stop scraping the mode and **ask** for it. Every trapped row is

```basic
10 ON ERROR GOTO 100
20 Q$="A":SCREEN 1
30 <the statement under test>
40 E=0:M=PEEK(&HFCAF)
50 SCREEN 0:PRINT"[";E;",";M;"]":END
100 E=ERR:M=PEEK(&HFCAF):RESUME 50
```

and reads `[ ERR , SCRMOD ]`. `SCRMOD` (`$FCAF`) is a published MSX system
variable, already cited in `basic/sysvars.inc` for zerobas's own use — so the
reading needs no disassembly and works identically on all three sides.

Three properties make it work where a scrape cannot:

* **Line 50's `SCREEN 0` runs before the `PRINT`**, so the value is readable
  whatever mode line 30 left behind — and because it *clears*, the only `[` on
  the screen is the printed one.
* **`M` is captured in the handler**, before line 50 destroys it.
* **Line 20 seeds `SCREEN 1`.**

🔴 **THE SEED IS PART OF THE MEASUREMENT, NOT SETUP.** Without it the machine is
already in mode 0, so `SCREEN 0*(1/0)` reads ` 11 , 0 ` whether the mode was
applied or not, and the probe scores a live defect as AGREEING. This is exactly
the shape D-LOCARG filed as `[[t.zero-is-blind-to-a-cut-that-also-disables-its-seed]]`
— there it was found by a knife after the fact; here it was asked in advance, and
knife **K-SE5** measures it (§4).

## 2. What the references do

Both references agree on all 62 rows. Tables in
[`spec-basic-screenerr.md`](spec-basic-screenerr.md) §2. In one sentence: the
mode is `get_byte_arg` plus a `< 4` test, the whole argument list is byte-checked,
an empty required slot is `Missing operand`, and nothing is applied until it has
passed.

## 3. The four boundaries that identify the coercion

The mode's rejects are not "0..3 or else". They are two stages with **different
codes**, and four rows say which:

```
SCREEN 32767   ERR 5        SCREEN 32768   ERR 6
SCREEN -32768  ERR 5        SCREEN -32769  ERR 6
```

The int16 stage accepts the **range** −32768..32767, not the magnitude
|x| ≤ 32767. That asymmetry is already recorded in `basic/interp.asm` as
`get_byte_arg`'s contract, pinned there at `CHR$(-32768)`/`CHR$(-32769)` during
D-MISS-2. Arriving at the identical boundary from an unrelated verb is the
strongest evidence available that it is **one shared rule**, and is what licensed
a substitution instead of a new guard.

Two rows say the coercion **truncates**: `SCREEN 1.6` → mode 1, and `SCREEN 3.6`
→ mode **3**, where rounding would give a mode 4 that is ERR 5 — a different
CODE, not just a different mode. ⚠️ This was checked *before* the substitution was
written, not after: `eval` reaches the mode through a silent `flt_to_int16` and
`eval_byte_checked` re-derives it through `fac_to_int_strict`, and if those two
rounded differently the fix would have reddened two rows that were already green.
`PROVENANCE.md` records `fac_to_int_strict` as oracle-pinned truncating.

## 4. The rank rule, re-measured from a second verb

```
SCREEN 70000+0*(1/0)     ERR 11
SCREEN 70000+0*SQR(-1)   ERR  5
```

Both values overflow the coercion, which raises ERR 6 on its own. Both report the
**expression's** fault instead, and the two report **different** codes. So the
rule is "a fault that already happened outranks the coercion", not "division by
zero is special" — D-EVALCHK's rule at `WIDTH`, independently re-measured at
`SCREEN`. These two rows are also the only thing separating `eval_byte_checked`
from the cheaper `eval_byte_arg`, whose own coercion aborts on a pending code too
— just after overwriting it. Without them the design choice is unjustified by the
row set, which is why they were added before the asm was written.

🔴 **AND THAT LAST SENTENCE IS WRONG, WHICH IS WHY THE KNIFE EXISTS.** K-SE2
swapped the two routines and moved **nothing**, twice — these two rows included.
D-PENDERR's set-if-empty writers mean the coercion can no longer overwrite a
live code at all, so D-EVALCHK's stated reason for the checked leaf stopped
being true a few commits after it was written. The rows pin the RULE; they do
not pin the ROUTINE. See [`spec-basic-screenerr.md`](spec-basic-screenerr.md)
§8.1.

## 5. The ordering is per-ARGUMENT, not per-STATEMENT

```
SCREEN 2+0*(1/0)   ERR 11, mode left at the seed 1   <- never applied
SCREEN 2,0*(1/0)   ERR 11, mode left at 2            <- applied, then reported
```

Both references, both rows; zerobas already agreed on the second one before the
slice. So `SCREEN` does not validate everything and then act — it validates the
mode, applies it, and carries on. A "validate fully, then apply" restructure
would have been the wrong shape.

## 6. 🔴 The defect the fix exposed

See [`spec-basic-screenerr.md`](spec-basic-screenerr.md) §4. In short: the
argument position was counted **at the value**, the `,,` arm loops back without
producing one, so every argument after an omitted one was off by one slot and
`SCREEN 1,,99` applied 99 as the sprite size. Wrong since G7 landed, invisible
because the old `and $03` made it a legal size and **a wrong sprite size does not
appear in `SCRMOD`** — the one cell this probe reads. It surfaced only as a red
row in the *new* gate, on zerobas only, after the domain check turned it into an
error the reference does not raise.

Two lessons, both already in the record and both re-earned here:

* **A tightened check is a detector for the code around it.** The rows that catch
  a neighbouring defect are the ones you add for the fix, not for the defect.
* **An error code is a weak witness for a positional rule.** `a.clk` only detects
  the mis-slotting while the misplaced value happens to violate a domain. The
  rows that witness the *size* — `LEN(SPRITE$(0))`, 8 vs 32 — do so
  unconditionally, and `a.sprslot1` is the control proving that witness moves at
  all.
