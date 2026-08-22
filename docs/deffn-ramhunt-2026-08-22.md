# SCOUT — `DEF FN`'s RAM: the map, walked; and the window, measured

Status: **candidate found and empirically survived; NOT SPENT.** No ROM byte and
no RAM cell changed by this work — both images are byte-identical to `3df6e7c`.

Filed by [`deffn-design-2026-08-22.md`](deffn-design-2026-08-22.md) §7 obstacle
(2), which became the sole blocker once [D-DUPSPAN](spec-basic-dupspan.md) closed
obstacle (3) (main page 1: 4 B → **54 B**).

---

## 1. Why this is a tool and not a reading

`basic/sysvars.inc` advertised *"-> top `$E3E8`, well below the disk WBUF wall at
`$E560` (376 B spare)"*. **Ten bytes were free.** Three slices had spent the
window while the header still offered it, and what caught it was the
**assembler**, not the reading
([[the-ram-map-said-376-bytes-spare-and-10-were]]).

🔴 **`make wall-assertion-check` polices ROM free-space claims. NOTHING polices
RAM ones.** So this scout produces the map mechanically and then asks the machine
to confirm it.

---

## 2. `scratchpad/rammap_sweep.py` — the map, walked

Resolves every `NAME equ <expr>` in the components' `.inc` files — iterating to a
fixed point so `X equ Y + N*M` chains resolve — keeps those landing in a RAM
window, and prints the **delta to the next name**.

    denominator: 990 equ definitions in 35 .inc files; 989 resolved;
                 494 land in [E000,F380)

🔴 **A DELTA IS NOT FREE SPACE, AND THAT IS THE TOOL'S WHOLE CAVEAT.** An address
says where a cell *starts* and never how long it is. The two largest deltas prove
it:

| name | delta | actually free |
|---|---|---|
| `TOKBUF` `$EC00` | 612 B | **36 B** — it is 576 B of crunch buffer (`TOKBUFSZ`) |
| `LINEBUF` `$EB00` | 256 B | **0 B** — `LINEMAX` is 255 + terminator |

### 2.1 The selftest failed twice, and both were real

⚠️ `--selftest` plants a synthetic pair and asserts the walk finds it.

* 🔴 **First failure: 175 of 990 resolved, 0 in the window.** `$E3E8` becomes
  `0xE3E8`, and a bare `[A-Za-z_]\w*` identifier scan reads `xE3E8` out of it —
  so **every hex literal looked like an unresolved symbol** and the map collapsed
  to nothing. Without the calibration the run would have printed *"0 names in the
  BASIC workspace"* and looked like an answer.
* 🔴 **Second failure: the plant was wrong, not the walk.** Planted by hand at
  `$E7A0..$E7F0`, expecting a 72 B gap; the walk reported **24**, because a REAL
  name sits at `$E7C0` between the two plants. The fixture now resolves the map
  first, takes its largest genuine gap, and plants inside that.

---

## 3. The candidate: `$EA92..$EB00`, 110 bytes

| | |
|---|---|
| **span** | `$EA92..$EB00` — **110 contiguous bytes** |
| **names claiming it** | **none**, in `basic/`, `sub/` *or* `disk/` |
| **below** | `FOR_STK` `$EA3A..$EA92` — 8 frames × 11 B, bounded in code |
| **above** | `LINEBUF` `$EB00` (256 B), then `TOKBUF` `$EC00` (576 B) |
| **page** | 3 — always mapped, **not** paged out by a sub-ROM `CALSLT` |
| **text ceiling** | `TXTMAX equ $BB00`, far below |
| **history** | inside the `$EA64..$EE63` window S-FCH-1 freed |

`FOR_STK_END` is an **end marker**, which is what makes this delta different from
`TOKBUF`'s: `FOR_STK + FOR_DEPTH*FOR_FRAME` is arithmetic the source states, so
the cell's true extent is known and not inferred.

**And the stack bounds itself.** [`basic/program.asm`](../basic/program.asm)
tests `FSP` against `FOR_STK_END` before every push
(`ld hl,-FOR_STK_END / add hl,de / jr c,ef_over` → ERR 7), so a ninth frame
faults rather than writing past the wall.

---

## 4. `scratchpad/ramfree_probe.py` — the window, measured

**A map is still a reading.** So: fill the window from BASIC with a known
pattern, work one subsystem hard, read every byte back, print how many changed.
A byte that moves was written by something no map names.

⚠️ **This is a claim about zerobas's own RAM layout, not about MSX-BASIC.** The
references have an entirely different map, so there is no oracle and the probe
runs `zb` only — stated rather than silently assumed.

**13 of 13 rows as expected:**

| row | what it drives | window changed |
|---|---|---|
| `ctl.self` | POKEs one byte of the window | **1** ✅ |
| `ctl.forstk` | a `FOR` loop, watching the 8 bytes *below* | **6** ✅ |
| `base.none` | nothing | 0 |
| `n.for8` | 8 nested `FOR`s — a **full** stack | 0 |
| 🎯 `n.for9` | a **ninth** frame, past `FOR_DEPTH` | **0** |
| `n.gosub` | `GOSUB`/`RETURN` | 0 |
| `n.crunch` | a long source line — `TOKBUF`'s real input | 0 |
| `s.paint` | a SCREEN-2 flood (the 376 B span-stack window) | 0 |
| `s.draw` | `DRAW`, which aliases that same window | 0 |
| `s.play` | `PLAY` — the `H.TIMI` ISR | 0 |
| `s.str` | 30 concatenations + `MID$` | 0 |
| `s.disk` | `OPEN`/`PRINT#`/`CLOSE`, read back | 0 |
| `s.files` | `FILES` — the FAT directory walk | 0 |

🎯 **`n.for9` is the row that matters.** It is the one place a stack that did not
bound itself would write *straight into the window*, and it is measured rather
than argued from the source.

---

## 5. 🔴 The instrument was wrong SIX ways, and every one of them would have printed the answer I wanted

`0 bytes changed` is also exactly what a probe that never ran prints. Every fault
below produced, or would have produced, a green row.

1. **A CONTROL THAT PASSED VACUOUSLY.** `ctl.forstk` watched 8 bytes the fill
   never wrote, so *"8 of 8 changed"* was guaranteed whether or not the workout
   ran. It scored OK and proved nothing. **A control is honest only about the
   cell it reads — and only if that cell was SET.** The fill now covers
   `FOR_STK` and the window alike, and it reads **6**, a real number.
2. **THE INSTRUMENT WROTE ITS OWN SUBJECT'S NEIGHBOUR.** The fill and check
   loops were `FOR` loops, and a `FOR` loop writes `FOR_STK` — the window's lower
   bound. Both are now `GOTO` loops that touch no stack.
3. **THE READOUT RETURNED ITS OWN ECHO.** `BR.search` finds the FIRST `[...]` on
   screen, which is the echo of the typed `PRINT"[";D;"]"` line — returning
   `";D;"`, an artifact shaped like a reading.
   🎯 **And the shipped gate already knows this class**:
   [`probes/basic/basic_probe_deffn.py`](../probes/basic/basic_probe_deffn.py)
   defends with an explicit `CLS` (*"without the CLS the line's own ECHO carries
   the `[...]` fence and every row returns its own SOURCE TEXT — eleven rows"*).
   ⚠️ **The scratch probes are defended only ACCIDENTALLY**: their fixtures enter
   a graphics mode and the closing `SCREEN 0` clears the screen. A fixture that
   never leaves SCREEN 0 has no defence at all — which is exactly which rows
   failed. Filed.
4. **A ROW STILL RUNNING READS AS A ROW THAT PRINTED NOTHING.** Two rows were
   captured mid-run at `step=12`; the raw screen showed `RUN` **and nothing
   after it**. An 8-deep `FOR` nest re-executes ~2000 statements and a FAT write
   is slower still. **Read the screen before believing a red row.**
5. **A DISK FIXTURE THAT NEVER OPENED ANYTHING.** `OPEN"A:T.T"...` printed
   `load error` and carried on; the next line said `File not OPEN in 60`. Neither
   was visible in the reported face.
6. **A DISK ROW ON A MACHINE WITH NO DISK.** The probe booted bare while the
   shipped batteries pass `diska=` a **writable copy** of `disk/test720.dsk`
   (mounting the original mutates the fixture). Without it the row answered
   **ERR 59** — which reads exactly like a channel-ceiling rule and is nothing of
   the kind.

🎯 **And the row that now passes had a SECOND CAUSE OF GREEN.** `s.disk` reports
`0` just as happily when the `OPEN` fails *without raising* — which this fixture
did twice. The row therefore reads the file **back** and raises `ERROR 99` if the
round trip did not happen, so a disk row that never touched the disk reads
`ERR 99` rather than `0`.

---

## 6. What is NOT claimed

* **The window is not spent.** Nothing is allocated there; this scout establishes
  a candidate, and the `DEF FN` slice that takes it must ship the
  `IF FN_PAREA_END > $EB00` build assert alongside — **put the assert in the
  DRAFT, not after it**, which is the only reason obstacle (2) was a build error
  and not a probe reading garbage out of the PLAY parser's stack.
* **110 B is not confirmed sufficient.** §2 of the design derives a 9-formal
  ceiling from the reference's own `100/11`; whether zerobas's slot needs 11 B is
  its own measurement.
* **Not swept:** cassette (`CLOAD`/`CSAVE`), `DIM`/array growth, `LINE INPUT`
  through the editor at a maximal line, `MERGE`, and any path taken only while
  MSX-DOS is booted. The last is deliberate — that context is mutually exclusive
  with a live interpreter, which is the aliasing argument this tree already
  relies on in both directions.
* **No lifetime decision is made here.** The design's `o.nestsame` row
  (`FNB(3)` → 7) proves two shadows coexist and nothing is unwound, but a shadow
  is rewritten at every call — so whether the area must survive *between*
  statements, and therefore whether it could instead alias graphics scratch, is
  open. ⚠️ `DRAW`'s co-routine split is the hazard for that alternative: the
  resident resolves `=expr;` substitutions **while the tenant's buffers are
  live**, so an `FN` call inside one would not be a mutually-exclusive context at
  all. Unmeasured.
