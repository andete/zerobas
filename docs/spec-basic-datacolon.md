# D-DATACOLON — a quoted `:` ends the DATA statement, and bare RESTORE ends the whole line

*2026-08-31. `basic/tokenise.inc` (`tk_data_rest`), `basic/interp.asm`
(`ex_data`), `basic/program.asm` (`ex_restore`). Probe
`scratchpad/datacolon_probe.py`, 7 rows × 3 machines: **6 DIFF → 0**.
**−33 B main page 1** (391 → 358) + sub-ROM bytes. Second verb group off
[review-tier-worklist.md](review-tier-worklist.md), and the reverse of the
trio's no-finding: three real defects from one read.*

## 1. Found by reading, confirmed by rows

The review flagged two smells; the rows confirmed both and found a third:

| row | | VG-8020 | CF-3300 | zerobas |
|---|---|---|---|---|
| `d.qcolon` | `DATA "A:B"` → `READ A$` | `A:B` | `A:B` | **ERR 2** 🔴 |
| `d.qrun` | `DATA "A:B":C=7` | 7 | 7 | **ERR 2** 🔴 |
| `ctl.plain` | `DATA 5:C=7` | 7 | 7 | 7 ✅ |
| `r.chain` | `C=0:RESTORE:C=9` | 9 | 9 | **0** 🔴 |
| `ctl.rest` | `READ A:RESTORE:READ B` | 2 | 2 | **1** 🔴 |
| `d.unterm` | `DATA "A:B:C=7` (open quote) | 0 | 0 | **ERR 2** 🔴 |
| `r.junk` | `RESTORE X` | ERR 8 | ERR 8 | **silence** 🔴 |

## 2. Defect 1: the DATA body scan had no quote state — twice

`tk_data_rest` ended the crunch-time body at the first `:` under a comment
claiming *"no strings"* — while the READ engine's own spec rows
([spec-basic-readvar.md](spec-basic-readvar.md)) prove a comma inside quotes is
content. `ex_data`'s runtime skip had the same blind scan. Both references:
a quoted `:` is item content; an **unterminated quote swallows the rest of the
line** (`d.unterm` — the row that decided the flag's EOL rule). Both loops now
carry an in-quote flag in C (free at both sites: `tk_loop` re-derives B from
`TKNAME`; statement handlers own their registers). The `d.qcolon` row proves
the READ tenant end-to-end: the quoted item comes back as `A:B`.

## 3. Defect 2: bare RESTORE's `ret` ended the whole line

The dispatcher enters handlers by `push de / ret` — a tail jump — so a
handler's `ret` returns past `exec_stmt` entirely. `ex_restore`'s bare arm was
an unconditional `ret` under *"nothing else on a bare RESTORE word"*: an
**assumption spelled as a comment**, false for `RESTORE:...`, and `ctl.rest`
shows the practical harm — the second `READ` never ran. The bare arm now
falls back into the statement loop.

## 4. Defect 3: junk after RESTORE was silently ignored

`RESTORE X` is **ERR 8** on both references — RESTORE-to-nothing (the failed
line-0 lookup), not ERR 2 and not silence. The junk arm now takes the line
path with BC=0 and fails the lookup there, sharing `ers_find` with the real
`$0E` path. (A program that *has* a line 0 would make `RESTORE X` succeed —
faithful to the mechanism the references exhibit.)

## 5. The apparatus lesson (again)

The first row set pre-numbered its lines and typed its own `RUN` — inside a
harness that *already* numbers setups into a stored program and appends `RUN`.
All six rows fenced on the references while zerobas answered values: an
asymmetric echo-fence that read exactly like six divergences. One control
(`ctl.plain`) surviving both cuts is what kept the reading honest.

## 6. After

7/7 SAME. Battery green; the worklist entry is crossed off with the findings.
