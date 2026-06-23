# How MSX1 BASIC is coupled to the BIOS

On a real MSX1, the "BASIC ROM" and the "BIOS ROM" are not two chips that get
wired together — they are the two halves of a single 32 KB ROM in slot 0, with a
small set of well-defined connection points that keep BASIC decoupled enough that
cartridges and disk hardware can extend it. This doc records that mechanism and
checks zerobas against it (zerobas is the clean-room MSX1 BASIC loader in the
this repo).

## One ROM, split by page

The main ROM is 32 KB and fills the bottom half of the Z80 address space:

| Range           | Contents                  |
|-----------------|---------------------------|
| `$0000–$3FFF`   | BIOS (page 0)             |
| `$4000–$7FFF`   | MSX BASIC interpreter (page 1) |

"Hooking" is mostly just *adjacent code in one chip*. The interesting part is the
four connection mechanisms below.

## 1. BASIC → BIOS: the jump table at `$0000`

The bottom of the BIOS is a table of `JP` instructions — the documented BIOS
entry points (`CHKRAM`, `RDSLT`, `CHGET $009F`, `CHPUT $00A2`, `INITXT $006C`,
`CALSLT`, …). BASIC never touches VDP/PSG/keyboard hardware directly; it calls
these fixed addresses. Because they are `JP` stubs, the real routine can move
anywhere in the ROM and the public entry address stays stable across machines.

Plain `CALL` is enough for this even from a cartridge in another slot: page 0
(`$0000–$3FFF`) stays mapped to slot 0 / the BIOS regardless of where the caller
sits, so a same-page `CALL $00A2` reaches the jump table with no slot switching.

## 2. The `"AB"` header — how BASIC is *found* and *started*

At `$4000` (the start of page 1) sits the standard ROM-module header, identical
to the format every cartridge uses:

```
+0,+1  "AB"  ($41 $42)   signature
+2,+3  INIT             cold-start / init entry
+4,+5  STATEMENT        CALL-statement expansion hook
+6,+7  DEVICE           device expansion hook
+8,+9  TEXT             tokenized BASIC program to auto-run
+A..+F reserved
```

On boot the Z80 resets to `$0000` (BIOS), which does RAM/VDP/work-area init, then
**scans all slots and subslots for the `"AB"` signature** at `$4000` and `$8000`,
calling each module's `INIT`. The main BASIC ROM is just one such module — its
`INIT` starts the interpreter and takes over (it does not return to the scanner).
BASIC is launched through exactly the same discovery path a game cartridge uses.

## 3. BIOS → BASIC (and extensions): the RAM hook table

In the system-variable area there is a block of **5-byte hook slots** (`$FD9A`
upward: `H.KEYI`, `H.TIMI`, `H.CHPU`, `H.READ`, …), each initialized to `RET` +
padding. BIOS routines `CALL` into these so ROMs can patch themselves in at
runtime (the disk ROM rewrites several). 5 bytes is deliberately enough room for
an inter-slot call (`CALL CALSLT` + slot byte) so a hook can redirect into a
different slot.

## 4. STATEMENT / DEVICE expansion — extending BASIC syntax

When the interpreter meets something it does not recognize — a `CALL FOO` /
`_FOO`, or an unknown device in `OPEN"…"` — it walks the slot table and calls
every ROM's `STATEMENT` (+4) and `DEVICE` (+6) vectors via inter-slot calls. Each
ROM either claims it or declines. This is how disk BASIC adds `FILES`, `LOAD`,
etc., without the BIOS or main BASIC knowing they exist.

## Summary

- **Same physical 32 KB ROM**, BIOS in page 0, BASIC in page 1.
- **BASIC calls down** through the fixed `JP` jump table at `$0000`.
- **BIOS reaches BASIC** by slot-scanning for the `"AB"` header at boot, calling
  its `INIT`.
- **Runtime patching** goes through the 5-byte RAM hooks.
- **Syntax extension** goes through per-ROM `STATEMENT`/`DEVICE` vectors via
  inter-slot calls.

## How zerobas maps onto this

zerobas is already a well-behaved page-1 module: it uses the two connection
points that matter and deliberately skips the rest.

- **`"AB"` header + INIT (mechanism 2) ✓** — `basic/main.asm` lays the 16-byte
  header at `$4000` with `INIT → init` and the other vectors zeroed; `init`
  (`basic/interp.asm`) never returns, falling into the REPL. Faithful to the real
  main BASIC, whose INIT also takes over.
  - The cartridge form is normal; the *patch* form (`build-patches.sh` in the
    zerobas repo) splices the same image into **slot-0 page 1**, so C-BIOS's own
    cold-boot scan of its slot-0 page-1 finds the header and calls INIT — the
    real-hardware layout reproduced exactly, no boot-vector patch needed.
- **BASIC → BIOS jump table (mechanism 1) ✓** — all I/O goes through fixed
  jump-table addresses, never hardware: `INITXT $006C`, `CHGET $009F`,
  `CHPUT $00A2`, `TAPION/TAPIN/TAPIOF $00E1/E4/E7` (`basic/sysvars.inc`). Plain
  `CALL` suffices because page 0 is always slot 0.
- **No inter-slot calls** — none needed; everything it calls lives in page 0 of
  the same always-visible slot 0. No `CALSLT`/`EXTROM`/`CALBAS $0159`. (MSX1 has
  no sub-ROM anyway.)
- **RAM hooks untouched** — it just does `ei` and leans on C-BIOS's existing
  interrupt handlers for keyboard timing; it is a guest in C-BIOS's work area,
  not a replacement.
- **Real work-area sysvars honored** — `TXTTAB $F676`, `HIMEM $FC4A`,
  `USRTAB $F39A`; own scratch confined to `$E0xx/$E1xx`.

### The one gap

zerobas does **not** honor the expansion mechanism (STATEMENT/DEVICE vectors are
zeroed). That is a scope choice, not a bug — but it is the thing that would
matter the day a disk ROM (or anything else) needs to hook into zerobas's BASIC,
or zerobas needs to coexist with other extension ROMs. The header vectors plus a
slot-walk dispatcher are where that would go. Relevant given disk is the next
target.

## Sources

MSX2 Technical Handbook (cartridge ROM format, work-area appendix, BIOS call
list); MSX Assembly Page (BIOS entry points, hook table); C-BIOS sources
(boot-time slot scan, system variables). All allowed clean-room sources — no
MSX-BASIC / GW-BASIC disassembly.
