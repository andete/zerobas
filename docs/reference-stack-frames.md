# How the reference keeps GOSUB / FOR / trap frames — a RAM-only study

Asked by Joost, 2026-09-27: *"About the gosub ram how does reference do it? Study
it in detail for gosub and other stack using commands to understand the
mechanism."*

**Method (clean room).** Only RAM contents and registers were read — no ROM byte,
no breakpoint in ROM code. Each program marks its own moment with
`POKE &HC000,173`; an openMSX *watchpoint on that RAM cell* records SP (a
register), `STKTOP` ($F674, a published work-area cell) and every byte of
`[SP, STKTOP)`. A fresh boot per case; the baseline case (no construct open)
gives what the interpreter keeps below its frames. Probe:
[`scratchpad/stackframe_probe.py`](../scratchpad/stackframe_probe.py), readings:
[`scratchpad/stackframe_run.out`](../scratchpad/stackframe_run.out) (Philips
VG-8020).

## 1. Where the frames live

On the **Z80 machine stack**, growing DOWN from `STKTOP` ($F0A0 in these runs).
There is no separate control area: SP itself is the frame pointer, and a
frame is simply bytes pushed below the previous one. The baseline holds 4 B
below `STKTOP`: a `00 00` word at the very top and one interpreter return word
under it (not interpreted further — it is the interpreter's own state).

## 2. The frames, decoded (lowest address first; words little-endian)

### GOSUB — 7 bytes

| offset | bytes | meaning | evidence |
|---|---|---|---|
| +0 | `8D` | the **GOSUB token** — the frame's type tag | every GOSUB frame |
| +1 | 2 B | **trap entry pointer**: `0000` for a plain GOSUB, the trap table entry for a trap GOSUB | `ON INTERVAL` frame: `$FC7F` |
| +3 | 2 B | **the caller's line number** | `0A 00` = 10; nested: `1E 00` = 30; trap: `14 00` = 20 (the interrupted line) |
| +5 | 2 B | **resume text pointer** — just past `GOSUB n` in the caller's text | `$800A` for `10 GOSUB 30`; `$800E` for `10 A=1:GOSUB 30:B=2` |

Two nested GOSUBs are two such frames, 14 B. **No link to the previous frame is
stored.**

### FOR — 25 bytes, whatever the variable's type

| offset | bytes | meaning | evidence |
|---|---|---|---|
| +0 | `82` | the **FOR token** | every FOR frame |
| +1 | 2 B | **pointer to the loop variable's value** | `$801F` (`I`), `$8020` (`I%`/`I#`) — just past the program text |
| +3 | 1 B | **sign of STEP** (`01` = positive) | all rows here |
| +4 | 1 B | **the loop's numeric kind** | `05` for single and double; `FF` for integer |
| +5 | 8 B | **STEP** | `41 10 00…` = 1; `41 30 00…` = 3 (`STEP 3`) |
| +13 | 8 B | **limit** | `41 20 00…` = 2 |
| +21 | 2 B | **line number** of the FOR | `0A 00` = 10 |
| +23 | 2 B | **text pointer** after the FOR statement | `$800E`, `$8012` with `STEP 3` |

- **Single and double FOR frames are byte-identical.** STEP and limit are held as
  8-byte BCD whatever the variable's own precision.
- **An integer FOR keeps the same 25 B.** Its STEP and limit are 2-byte integers
  in the last bytes of those slots (`01 00`, `02 00`); the rest of the slot is left
  as whatever the stack held before.

### Traps and handlers

- **`ON INTERVAL … GOSUB` enters with an ordinary 7-byte GOSUB frame.** It is
  distinguished only by the trap entry pointer at +1, which is how RETURN knows
  the trap to re-arm.
- **An `ON ERROR` handler adds nothing** (0 B): the handler runs at the depth
  where the error was raised.

### Interleaving

- **FOR inside GOSUB and GOSUB inside FOR simply stack**, 7 + 25 = 32 B, in the
  order they were opened.
- **Nothing links a frame to its neighbours.**

## 3. The mechanism this implies

- **RETURN finds its frame by scanning UP from SP for `8D`.** Everything below
  it, meaning the FOR frames opened inside the subroutine, is discarded by
  setting SP just above the frame. That is D-FORRET's rule, obtained for free
  from the layout.
- **NEXT scans for `82`** with a matching variable pointer (or takes the first
  `82` for a bare NEXT).
- **The type token is what makes the walk possible.** Every frame kind starts
  with one, and each kind has a fixed size (7 or 25).
- **Memory for frames is the free gap below SP.** `FRE(0)` shrinks by exactly the
  frame size, which is what the `fremops` economy rows measured (FOR 25, GOSUB 7).

## 4. Against zerobas

zerobas keeps frames in its control pool (merged with the stack since
D-SPMERGE) and links them instead of tagging them:

- **GOSUB = 7 B** (since 2026-10-17; 8 B before):
  `[CURLINE:2][resume:2][prevFSP:2][gdelta:1]` (`basic/sysvars.inc`
  `GOSUB_FRAME`). The previous GOSUB frame is `prevFSP + gdelta`; the trap
  service record lives separately (`TRAP_FRAME`, 3 B).
- **FOR = 25 B**, the reference's size (D-FORFLOAT):
  `[name1][name0][type][limit: type + 8][step: type + 8][CURLINE:2][resume:2]`.
  Since D-FORFAST a single/double loop whose limit and step are exact int16 keeps
  both slots as int16 (`[2][lo][hi]` + 6 unused bytes, the shape a `%` loop's slots
  always had) so NEXT can take an int16 path; the first NEXT that cannot widens
  them for good to the packed double they used to hold. Same 25 B either way.

This section used to conclude that matching GOSUB's 7 B meant adopting the
reference's tagged, walked shape. It did not: the old frame's two chain words
(`prevGSP`, `prevFSP`) are never more than one trap record (3 B) apart, so one of
them became a one-byte distance from the other, and the linked design stays.
