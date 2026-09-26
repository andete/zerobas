# D-FCBSHAPE — the MSX FCB layout for file channels

Status: **design, not started** (2026-09-26). TODO item D-FCBSHAPE, TIER 4.
Ruled by Joost 2026-09-16: *"I think this means we need to change to the MSX's
FCB shape."* Filed as TIER 4 on 2026-09-26.

## 1. What is measured

All readings are work-area RAM (PEEK), clean-room legal; probes in `scratchpad/`.

| fact | value | source |
|---|---|---|
| `FRE(0)` charge per `MAXFILES` channel, both references | **267** | D-MAXFRE, `docs/chancost-cf3300-characterization.md` §2 |
| channel stride (`VARPTR(#n+1) − VARPTR(#n)`) | **265** | `varptrn_probe.py`, `fcbstride_probe.py` |
| where the other 2 B live | `FILTAB` (`$F860`) → a table of **MAXFILES + 1** FCB pointers, one per channel **including #0**, directly below the FCB array | `filtab_probe.py` |
| geometry, top-down from `$F380` | FCB #MAXFILES … #1, #0, then the pointer table | `filtab_probe.py` |
| FCB header +0 | the file MODE (2 = OUTPUT) | `fcbfields_probe.py` |
| FCB header +1..+2 | disk file: a POINTER into the disk work area (`$DEB5` on the CF-3300) | `fcbfields_probe.py` |
| FCB header +4 | the DEVICE (`$FD` CRT:, `01` drive A:) | `fcbfields_probe.py` |
| FCB header +6 | the BUFFER POSITION (0 → 2 → 3 on a disk file as bytes are written) | `fcbfields_probe.py` |
| FCB +9.. | the RECORD (256 B) | `fcbfields_probe.py` |
| `OPEN` itself | +11 B, and zerobas already pays the same 11 | D-RESERVE |

## 2. What zerobas does today

A channel block is `[state: FCH_STATESZ 50][record: FCH_RECMAX 256]` = **306 B**,
carved out of the pool below the string floor at `MAXFILES` time (D-FCH §3.2).
Its address is derived in ONE place: sub op 18 (`sub/strheap.asm`), reached
through `fch_ctx_addr` (`basic/files.asm`). The 50-byte state is **all disk
engine state**: the FAT cluster iterator (`FAT_CURCLUS`/`FAT_CLUSSEC`), file
meta (`FAT_FIRSTCLUS`/`FAT_FILESIZE`), the read stream (`FREAD_*`) and the
write state (`FWR_*`), saved from and restored to the engine globals
(`fch_save_active` / `fch_load_ctx`). Small per-channel values already live in
fixed tables (`FCH_MODES` `$EA00`, `FCH_RECLENS` `$EA10`, `FCH_RECNOS` `$EA40`).
`VARPTR(#n)` is a Syntax error.

The gap: **306 − 267 = 39 B per channel** (585 B at `MAXFILES=15`), and one
missing `VARPTR` form.

## 3. Target

- **Both builds:** a channel block is **265 B** laid out as the reference's —
  mode +0, device +4, position +6, record +9 — and a **`FILTAB` pointer table**
  of MAXFILES + 1 entries sits below the FCB array, with the published `FILTAB`
  cell pointing at it. `MAXFILES=n` then charges 267 B a channel by
  construction, and `VARPTR(#n)` is the FCB's address (its stride agrees; the
  base is machine-specific and cancels, as `varptr_b` does for arrays).
- **The 50 B of disk-engine state leave the block.** The reference's own answer
  is the +1..+2 pointer into the disk ROM's work area.

## 4. The choice for the disk build — 🙋 Joost's

The diskless build needs no engine state for its devices (CRT:, LPT:, GRP:,
CAS:), so for it the change is a pure gain of 39 B a channel. The disk build
must put up to (15 + 1) × 50 = **800 B** somewhere:

| option | boot `FRE(0)` (disk build) | per channel | per `OPEN` |
|---|---|---|---|
| (a) a FIXED table in the disk work area, reached by the +1 pointer | −800 B (the disk build leads the CF-3300 by ~635 B today, so it would trail by ~165 B) | 267, as the reference | 11, as the reference |
| (b) allocate the 50 B per disk `OPEN`, from the pool | unchanged | 267 | 11 + 50 = 61 — **diverges** from the reference's 11 |
| (c) size the fixed table by `MAXFILES` at `MAXFILES` time | unchanged at the default | 267 + 50 = 317 — **diverges** | 11 |

(a) is the reference's shape. What it costs is boot `FRE(0)` on the disk build
only, and the disk build is measured against the CF-3300, whose own disk work
area makes the same kind of trade.

## 5. Walls — a carve comes first

Clean build 2026-09-26: **sub page 1 was 0 B free**, main page 1 26 B, main
low region 1 B, sub page 0 41 B. The channel layer lives in all of them, so no
slice below starts before a carve has priced its bytes.

## 6. Slices (after §4 is ruled)

1. **S1 — the layout, diskless first.** 265 B blocks, the `FILTAB` table, the
   header fields kept at their offsets, `VARPTR(#n)`. Diskless rows on the
   NODISK target (the ruled rule: any disk-related work adds rows there).
   Probe: `MAXFILES` 0..4 `FRE(0)` steps, the stride, the header after OPEN.
2. **S2 — the disk engine state** in its chosen home, the +1 pointer written on
   a disk OPEN. Gates: `fat-error`, `diskbasic`, `bdos`, the FIELD/LSET rows.
3. **S3 — the channel-I/O carve** (D-FATPAGE1) is the same layer and should be
   priced together: its ~317 B of byte-level FAT I/O would move sub-side only
   with the LOOP, not the byte routine (0.156 ms per inter-slot call).
