# The screen editor: Enter reads the logical line from VRAM (D-SCREDIT)

TIER 1 by Joost's ruling of 2026-09-10 (*"the basic line and screen editor
should also be in the list"*). D-EDITSCOUT (2026-08-26) placed it, D-EDITLINE
(2026-09-07) measured the boundary rule and priced one cost as "not zero"; this
spec re-measures that cost at zero and adds the two happy-path faces the gate
will carry. All rows measured 2026-09-11 unless dated otherwise.

## 1. The continuation table is already kept — on both machines

MSX publishes a per-row table, `LINTTB` ($FBB2..$FBC9, one byte per row):
**zero = the row continues onto the next**, non-zero = the row ends a logical
line. Measured with `PEEK`:

| after | vg8020 `LINTTB[0..5]` | zb `LINTTB[0..5]` |
|---|---|---|
| `CLS:PRINT STRING$(40,"a");"b"` (a wrapped PRINT) | `0 23 22 21 20 19` | `0 1 1 1 1 1` |
| `CLS`, 40 × `VPOKE` into row 0, `PRINT:PRINT"b"` | `24 23 22 21 20 19` | `1 1 1 1 1 1` |
| `CLS:PRINT"ab":PRINT"cd"` | `24 23 22 21 20 19` | `1 1 1 1 1 1` |

So D-EDITLINE's `x.reenter` vs `x.vpoke` split (same glass, opposite answers)
is exactly this table, and **C-BIOS's `CHPUT` maintains it on the zerobas
machine already** (zero on the wrapped row, non-zero on the `VPOKE`d one).
The reference's non-zero values are a countdown (24, 23, …; 175 after a
scroll); zerobas's are 1 — zero/non-zero is the semantics, the value is not.
The "per-row bookkeeping written where the wrap happens, in the output path"
that the 09-07 finding priced as non-zero costs **nothing**: the reader reads
`LINTTB`.

**Scrolls shift the table on both machines** (a wrap at row 21 followed by
three scrolling `PRINT`s: the zero moves to row 18 on the VG-8020 and to row 19
on zerobas, whose screen has one more row). The one case C-BIOS gets wrong is
the wrap that itself scrolls: after `PRINT STRING$(39,"a");"bc";` on the
bottom row the reference reads `3 2 0 175 1` for the last five rows (the
`a` row continues), zerobas reads `1 1 1 1 24` (the mark is dropped). The
reader's echo path writes that one mark when a typed character wraps on the
bottom row; program output wrapping there stays an edge (filed). A first
reading of this case was taken INSIDE a `PRINT` that had scrolled the screen
again and was off by a row — the values are captured into variables first now.

## 2. Two happy-path faces the gate carries

| row | keys | vg8020 | cf3300 | zb before |
|---|---|---|---|---|
| `e.left` | `A=1`, ←, `2`, Enter; then `PRINT A` | **2** | **2** | **12** |
| `e.csr` (first cut) | `A=5` ⏎ `B=1` ⏎ ↑↑ ⏎ then `PRINT A;CSRLIN` | `5 6` | `5 6` | `5 4` |
| `e.up` (miscounted control) | `A=A+1` ⏎ ↑ ⏎ | 1 | 1 | 1 |

🔴 **A CURSOR-UP COUNT FROM THE PROMPT IS NOT MACHINE-NEUTRAL.** zerobas prints
a `ZB` prompt on the row the user types on; the references print an `Ok` line
and the cursor goes to the row after it. So every typed line costs one row
here and two there, and `↑↑` from the prompt lands on `A=5` here and on `B=1`
there — the first cut of `e.csr` measured the layout, not the cursor rule, and
`x.plain` passed on zerobas only because the cursor could not go above row 1.
The gate's re-entry rows therefore build the screen FROM A PROGRAM (identical
glass everywhere) and navigate with HOME + DOWN × n:

| row | program, then keys | all three sides |
|---|---|---|
| `e.csr` | a two-row logical line reading `PRINT"[e.csr";CSRLIN;"]"` (30 blanks then the text, wrapped by `PRINT`); HOME ⏎ | `2` — the cursor was moved below the line's LAST row before it executed |
| `x.plain` | the payload printed on row 6 by `LOCATE 0,5`; HOME, ↓×5, ⏎ | `1` |
| `x.reenter` | a `PRINT`-wrapped `'` row above the payload; same keys | `0` |
| `x.vpoke` | the same fill by `VPOKE`; same keys | `1` |

`e.left` is the everyday case: a typo fixed with the cursor before Enter. The
reference reads the ROW (`A=2`); zerobas appends to a buffer and drops the
cursor byte (`A=12`). `e.csr` shows the cursor after a re-entry lands below the
re-entered line's LAST row on the reference (the line above's `Ok` is
overwritten), where zerobas — which ignored the ↑↑ and executed an empty line —
sits two rows higher. `e.up`'s single ↑ landed on the `Ok` row on every side
(Syntax error, `A` unchanged): a miscount, kept as the negative control it
turned out to be.

## 3. Design

* **`read_line` is a main stub that WAITS inside `CHGET`** (interrupts live,
  so PLAY and the traps keep being served, and the harness's injector latch —
  `latch-check` — still sees the wait it models) and hands the readline tenant
  (sub page 1, `SUBROM_IDX_READLINE`) **one key per call** in `RL_KEY`; the
  tenant never blocks and needs no `EI`. A first cut polled `CHSNS` in main
  instead and `latch-check` went red: the injector's race window is inside
  `CHGET`'s wait, and a machine that never waits there cannot be judged by it. Main records where input began (`RL_ROW0`/`RL_COL0`) at
  entry. The per-keystroke cost is one CALSLT — nothing against typing speed.
  Page 1 went 5 → 11 B: the eviction funded itself.
* **Cursor keys pass through**: `$1C..$1F` (and `$0B` HOME, `$0C` CLS) go to
  `CHPUT` instead of being dropped; C-BIOS moves the cursor (D-EDITSCOUT §4).
* **Enter reads VRAM**: first row = walk up from `CSRY` while `LINTTB[row-1]`
  is zero; rows = until `LINTTB[row]` is non-zero; each row's `LINLEN` bytes
  from the name table (`RDVRM`, stride 40 in SCREEN 0 / 32 in SCREEN 1);
  trailing blanks stripped; into `LINEBUF`, capped at `LINEMAX`.
  **The text window is CENTRED in the name table**: column 1 sits at index
  `(stride + 1 − LINLEN) / 2` — measured 1 at `WIDTH 39` on C-BIOS (the prompt
  row's VRAM reads `| ZB` with `CSRX` = 3; the first cut read `BPRINT 1` into
  `LINEBUF`), and the VG-8020's captures show two blanks at its default 37; 0
  at `WIDTH 40`. `NAMBAS` reads 0 on C-BIOS and is used as the base.
* **Start column**: zerobas prints a `ZB` prompt (the harness keys on it) and
  `INPUT` prints `? `; the reference's reader honours the column where input
  began (`FSTPOS`). Rule: at entry record the start row and column; on Enter,
  if the logical line's first row IS the start row, read from the start
  column, else from column 0 and skip a leading `ZB`. A scroll during typing
  moves the start row up by one (detected as a wrap on the bottom row).
* **After Enter**: line feeds down to the logical line's last row, then CR/LF —
  the `e.csr` placement.
* Out of scope for the happy path (later tiers): `INS` mode, `DEL` mid-row,
  `CTRL`+key, the function-key row, `SELECT`, cursor keys inside `INPUT`
  across rows.

## 4. Gate

`make screditor-acceptance`: `e.left`, `e.csr`, the D-EDITLINE rows
`x.plain`/`x.reenter`/`x.vpoke` (re-entry through the keyboard, the boundary
from `LINTTB`), and an `INPUT` row with a wrapped answer at the bottom row
(§5). Three sides; the two references must agree on every row.

## 5. INPUT with a wrapped answer (measured, see the table filled in below)

| row | program + typed answer | vg8020 | cf3300 | zb today |
|---|---|---|---|---|
| `i.wrap` | 23 blank `PRINT`s, `INPUT A$`, 45 × `x` ⏎; `LEN(A$)` and its ends | `45 xxxx` | `45 xxxx` | `45 xxxx` |
| `i.top` | `CLS`, `INPUT A$`, 45 × `x` ⏎ | `45 xx` | `45 xx` | `45 xx` |
| `i.csrup` | `CLS`, `INPUT A$`, 45 distinct characters, cursor UP into the first row, `Q` ⏎ (D-EDINPUTCSR, 2026-10-06) | `45 01234Q6789hi` | `45 01234Q6789hi` | `45 01234Q6789hi` |

The reference excludes the `? ` prompt from a wrapped answer even when the
answer's first row scrolled off the bottom while it was typed — so the start
column survives a scroll on the reference, and a VRAM reader has to carry the
start row along with the scroll (§3). Both rows agree everywhere today (zerobas
accumulates a buffer) and are the gate's controls that the change must not
move.

## 7. After a graphics program: the line is read in SCREEN 0 (measured; the three rows are in the gate)

| row | program, then keys | vg8020 | cf3300 | zb before |
|---|---|---|---|---|
| `s2.prompt` | `10 SCREEN 2:END`, RUN, then `PRINT PEEK(&HFCAF)` | `0` | `0` | nothing readable |
| `s2.input` | `10 SCREEN 2:INPUT A$:PRINT PEEK(&HFCAF);A$`, RUN, `xy` | `0 xy` | `0 xy` | nothing readable |
| `s2.long` | after the SCREEN 2 program, a 46-char line | `46` | `46` | nothing readable |

Both references return to SCREEN 0 for the prompt after a graphics program AND
for `INPUT` inside one; zerobas stayed in SCREEN 2, where C-BIOS's text rows
are 32 wide while `LINLEN` stays 39, so a wrapping line read back garbled —
graphics-acceptance's phase M lost its second program's third line (the
harness's echo oracle said so: "line 30 never entered") and re-ran that case
alone, without the first program's `S8A1`. `txt_mode` (`INITXT` when `SCRMOD`
≠ 0) runs before the REPL prompt and at `read_line` entry.

## 6. Apparatus, measured on the way

* **A page-1 tenant must not WAIT.** The first cut blocked in `CHGET` under
  `EI` (bload's pattern); `htimi_guard` skips the PLAY/trap seam for every
  frame a page-1 tenant is mapped, so music stopped at the prompt and
  `play-trace-acceptance` went red on every row. The wait now lives in main
  (`CHSNS` polling with interrupts live) and the tenant is called once per
  key, never blocking and needing no `EI`. A CALSLT per keystroke is nothing
  against typing speed — the scout's refuted worry, re-refuted.
* **`sub/readline.asm` was not in `SUB_PARTS`**, so the second and third
  builds shipped the FIRST tenant unchanged (sub page 1 read 144 B both times
  — the size that could not have stayed the same). D-PUDOT's own note
  predicted this; the size line is the tell.
* openMSX's `after` is its own command: `after time <seconds> {…}`. A prologue
  written with Tk's `after <ms>` opens its log and writes nothing.
* A `PEEK` of `LINTTB` inside the `PRINT` that reports it is one scroll late.
* **C-BIOS's scroll shifts `LINTTB` only up to index `bottom−3`** and never
  rewrites the last two entries (write-watchpoint on `$FBC7`/`$FBC8`: after
  the reader's wrap-scroll mark at [22], every later scroll at PC `$13CC`
  copied it into [21] and nothing ever wrote [22] again). So the mark outlived
  its row and, from the first wrapped line typed at the bottom on, every Enter
  spliced the row above the prompt into the read — ten suites went red at
  once, all from their eighth case on (when their typing reached the bottom).
  `rl_botfix` sets the two stale entries after each scroll the reader causes.
* A cursor-UP count from the prompt measures the machine's prompt layout, not
  the editor (§2).
* A race can be GREEN for months on a pending interrupt: `PLAY""` set a
  `MUSICF` bit that only the next tick cleared, and `RUN` happened to leave a
  tick pending at the tenant's `EI`; one more tenant call ahead of it (the
  editor's) and the row went red. The fix is in `PLAY` (an empty string sets
  no bit), measured with a write-watchpoint on `$FB3F` and a `JIFFY` check.
