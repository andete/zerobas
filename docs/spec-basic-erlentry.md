# D-ERLENTRY — a line rejected at ENTRY leaves `ERL` = 65535

*2026-08-30. `basic/program.asm` (`dl_ovf_report`). Probe
`scratchpad/val_probe.py` rows `c.erlovf` / `c.erlbadln` / `c.erlnone`; knife
K-EL1 in `scratchpad/crunch_knives.py`.*

## 1. What was wrong

Two errors are raised by the **editor**, not by a running program: a line whose
crunched body the tokeniser rejects (`70 X=1E99` -> `Overflow`), and a line
number past the ceiling (`70000 X=1` -> `Syntax error`). Both arms set `ERRFLG`
so `PRINT ERR` reads the right code — D-MSGMIGRATE fixed that — and **neither
ever wrote `ERRLIN`**, so `PRINT ERL` read whatever the last run left behind. On
a fresh machine that is `0`.

Both references read **65535**.

## 2. Why 65535, and why it is not a new constant

`basic/interp.asm`'s `record_error_line` already writes exactly this sentinel on
its `rel_direct` arm: a *runtime* error in direct mode has no line number, so ERL
gets 65535. A line typed at the prompt is direct mode too. The fix reuses the
value the machine already means by "not in a program", it does not invent one.

⚠️ **`ERRLIN` only.** A direct-mode error does **not** write `.` (`DOT`) — that
is measured and written up beside `rel_direct`, whose two stores are deliberately
*not* folded into a shared tail for this exact reason. The same asymmetry holds
here, so this slice adds one store, not two.

## 3. 🟢 Sited on the shared tail, and only after enumerating its arms

`dl_ovf_report` is reached by exactly two `jr`/fallthrough paths, and this
project's standing rule is that a shared tail is a label, not a decision
— [[a-shared-tail-is-not-a-decision]]. So both arms got a row **before** either
got a fix:

| row | typed behind an intact line 60 | vg8020 | cf3300 | zerobas (before) |
|---|---|---|---|---|
| `c.erlovf`   | `70 X=1E99`  | 65535 | 65535 | **0** |
| `c.erlbadln` | `70000 X=1`  | 65535 | 65535 | **0** |
| `c.erlnone`  | *(nothing)*  | 0 | 0 | 0 |

The rule is the same on both arms, so the tail is the right site — the point of
the rule is to **enumerate** the jumps, not to avoid sharing.

🎯 **The third row is what makes the other two readable.** Without a row that
types no bad line at all, "ERL is 65535" could have been ERL's resting value
rather than the error's doing.

## 4. The instrument, which had to be built before the finding could be read

The rows that first showed this were reading ERL *through* the harness's value
line having been rejected: line 60 never stored -> `RUN` falls through to the
handler -> `[ERR 6 AT ERL]`. That reads ERL, but it cannot say whether the 65535
belongs to the line-entry error or to the missing line. The three rows above
leave line 60 **intact** and read `ERL` as a value, with the bad line typed
behind it — so the reading has one cause.

Ten rows in the suite were carrying this defect as a second, silent difference
(`c.ovflit`, `c.underlit`, `c.pctbig`, `c.e66lit` … `c.e70lit`); all ten go green
with this store, and K-EL1 reddens exactly those ten plus the two dedicated rows.

## 5. Cost

7 bytes of main page 1 (`ld de,65535` + `ld (ERRLIN),de` — DE, because HL is
already the message pointer and is this tail's whole input). Run
`make basic-reloc` for the current wall; never quote one from a document.
