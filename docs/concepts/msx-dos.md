<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->
<!-- example: verify=no reason="no example: MSX-DOS needs a system disk the example checker does not mount; the BDOS gates below cover it" -->

# MSX-DOS — booting DOS, the BDOS, and the way back to BASIC

> **Status (2026-10-09):** zerobas's disk ROM boots MSX-DOS 1 from a system
> disk and services the BDOS functions DOS 1 programs use, compared with the
> CF-3300 by standing gates; `A>BASIC` returns to Disk BASIC (since
> 2026-10-02), and `CALL SYSTEM` goes back to DOS (since 2026-10-09). Not
> there: BDOS calls made from BASIC through `&HF37D` are a small private
> subset that nothing compares with the reference.
> Speed is deliberately left out of these docs until on-par speed is
> established for every keyword.

## Summary

MSX-DOS 1 is the disk operating system of a disk MSX1. It lives on the disk,
not in ROM: `MSXDOS.SYS` is the kernel and `COMMAND.COM` the shell that shows
the `A>` prompt. zerobas does not include either file; it provides the **disk
ROM** they run on. Insert an MSX-DOS 1 system disk and power on, and the
disk ROM loads DOS instead of starting BASIC.

A program running under MSX-DOS asks for services — print a character, open
a file, read a record — by calling address `&H0005` with a function number
in register C: the BDOS, the CP/M-style interface MSX-DOS publishes. Much of
the work behind those calls is done by routines in the disk ROM, at addresses
`MSXDOS.SYS` expects. zerobas implements those routines with its own code,
and checks them by running the same test programs under the stock CF-3300
and under zerobas's disk ROM.

## How it works

### Booting a DOS disk

At power-on the disk ROM's `INIT` reads sector 0 of the disk to `&HC000`. If
its first byte is `&HEB` or `&HE9` (a boot sector), it calls the boot program
at `&HC01E` twice: first with the carry clear, then — after switching RAM
into page 0 and laying out the page-0 environment DOS needs — with the carry
set, which on a system disk loads `MSXDOS.SYS` and never returns. A data disk
returns, and BASIC starts as usual (MSX2 Technical Handbook, chapter 3; the
contracts are in [spec-diskrom-kernel.md](../../disk/docs/spec-diskrom-kernel.md)).

`MSXDOS.SYS` then loads `COMMAND.COM`, which prints, in order,
`MSX-DOS version 1.03`, `Copyright 1984 by Microsoft`,
`COMMAND version 1.08` (on the gates' DOS disk), `Current date is Sun 84-01-01` and
`Enter new date:`, and after the date the `A>` prompt. With an
`AUTOEXEC.BAT` on the disk it runs that file instead of asking for the date.

DOS reads a work area at `&HF100`–`&HF3FF` (drive parameter blocks, the
drive table, small resident routines) that the disk ROM lays out, and calls
the disk ROM at fixed addresses; the full list is in
[spec-diskrom-kernel.md](../../disk/docs/spec-diskrom-kernel.md) §1–§7. One
example: `&H4030` returns the work-area pointer, `&HDD0E` as on the CF-3300,
and that value decides where DOS puts its kernel in RAM (`&HD606`).

### The BDOS: functions through `&H0005`

C holds the function number; DE points at a file control block (FCB), a
buffer or a string; the answer comes back in A (and HL, BC for some). These
are the MSX-DOS 1 functions; zerobas implements all of them except the two
in the last row, and each was compared with the CF-3300, by the exercisers
below or by the boot and `DIR` themselves.

| group | functions (`C`) |
|---|---|
| console | `&H00` end program, `&H01` read a key with echo, `&H02` print a character (in E), `&H06` direct console I/O, `&H07` / `&H08` read a key without echo, `&H09` print a `$`-terminated string, `&H0A` read a line, `&H0B` is a key waiting, `&H0C` version (`A=&H22`) |
| printer | `&H05` print a character on the printer (through the BIOS printer routine) |
| drives | `&H0D` reset (the transfer address back to `&H0080`), `&H0E` select a drive, `&H18` logged-in drives, `&H19` current drive, `&H1A` set the transfer address, `&H1B` free space, `&H2E` verify flag |
| files | `&H0F` open, `&H10` close, `&H11` / `&H12` search the directory, `&H13` delete, `&H14` / `&H15` read / write the next record, `&H16` create, `&H17` rename, `&H21` / `&H22` read / write a random record, `&H23` file size, `&H24` set the random record, `&H26` / `&H27` write / read a block of records |
| sectors | `&H2F` / `&H30` read / write absolute sectors |
| date and time | `&H2A` / `&H2B` get / set the date, `&H2C` / `&H2D` get / set the time |
| not on this machine | `&H03` / `&H04` auxiliary in and out (no serial device) |

Some details a program can see:

- **The date** is kept as a day count since 1980-01-01 at `&HF33B`: 1461
  (1984-01-01) from power-on, as on the CF-3300. `&H2B` checks the date (an
  impossible one returns `A=&HFF` and changes nothing; years 1980–2099 are
  accepted); `&H2A` also returns the day of the week; every file written
  under DOS is stamped with it, and `&H10` re-dates a file that was written
  while open.
- **The time**: `&H2C` returns a time of zero and `&H2D` does not change it.
  This matched the CF-3300 in the `BDOSX2` exerciser, whose comparison lets
  the seconds differ by one.
- **The verify flag** is stored and has no effect on writes — on the CF-3300
  neither.
- **The free space** of `&H1B` is what `DIR` prints at the end of a listing,
  identical on both machines.

### MSX-DOS from BASIC: `&HF37D`

On a disk MSX the work-area cell `&HF37D` holds a jump to the disk system's
BDOS entry, so machine code called from Disk BASIC can make BDOS calls too.
zerobas puts a jump to its own small dispatcher there. It answers only open,
close, read and write the next record, create, set the transfer address and
read a block (`&H0F`, `&H10`, `&H14`, `&H15`, `&H16`, `&H1A`, `&H27`), and
returns `A=&HFF` for anything else. It was written for zerobas's own early
`BLOAD` path, and no gate compares it with the CF-3300 (see *Differences*).

### From BASIC to DOS and back

- **`CALL SYSTEM`** (or `_SYSTEM`) leaves Disk BASIC for MSX-DOS, as on the
  CF-3300 (since 2026-10-09, D-CALLSYSTEM). It works only when the machine
  booted into MSX-DOS first; after a boot from a data disk it is `Illegal
  function call`. It closes every open file, removes the function-key row,
  and starts DOS again *warm*: straight to `A>`, with no banner, no date
  question and no `AUTOEXEC.BAT`, and the screen as it was. `MSXDOS.SYS` and
  `COMMAND.COM` are read from the disk again, so the system disk must be in
  the drive; a disk that does not boot gives `Syntax error`, and without
  `COMMAND.COM` DOS asks for the DOS disk. It takes nothing after the name:
  `CALL SYSTEM("DIR")` is a `Syntax error`.
- **`A>BASIC`** (COMMAND.COM's `BASIC` command) calls the disk ROM's standard
  entry at `&H4022`, "start BASIC". zerobas has it since 2026-10-02
  (D-DOSBASIC): Disk BASIC starts as at power-on, but without booting DOS
  again and keeping the DOS date, so a program `SAVE`d there carries the date
  typed in DOS — `&H279F` = 1999-12-31 in the test, as on the CF-3300.
  Whether `AUTOEXEC.BAS` runs after `A>BASIC` has not been measured.

### `AUTOEXEC.BAT` and `AUTOEXEC.BAS`

- **`AUTOEXEC.BAT`** is run by `COMMAND.COM` itself when DOS starts cold. The
  disk ROM's part is to clear the cell DOS reads to tell a cold start from a
  warm one (`&HF340`). The standing BDOS gates start every test program this
  way, with no keys typed.
- **`AUTOEXEC.BAS`** is run by Disk BASIC when it starts and MSX-DOS does not
  (MSX2 Technical Handbook, chapter 3). Measured on the CF-3300 and matched
  since 2026-07-05: exactly that name, anywhere in the directory; loaded and
  run after the banner, before the first prompt; nothing at all if it is
  absent or empty. On a system disk DOS boots, and `AUTOEXEC.BAS` is not
  run (the Handbook's rule; `AUTOEXEC.BAT` is DOS's counterpart).

### Out of scope

- **MSX-DOS 2** and its functions: MSX-DOS 1 is the target.
- **A second physical drive.** DOS sees drives A: and B: on the one drive,
  as on the CF-3300; how zerobas behaves when DOS addresses B: has not been
  measured, and the swap prompt is still to be built
  ([disk](disk.md), D-DSKIB).
- **Formatting from DOS.** The disk ROM's format entry (`DSKFMT`, `&H401C`)
  reports failure and its geometry menu (`CHOICE`) offers nothing; what
  `COMMAND.COM`'s `FORMAT` then does has not been measured. `CALL FORMAT` in
  BASIC formats with its own code ([disk](disk.md)).
- **Memory mappers.** The CF-3300 is a plain 64 KB machine; the DOS hooks for
  switching memory segments are empty, as on the reference.

## Differences from the reference

- **`CALL SYSTEM` with `MSXDOS.SYS` deleted**: the CF-3300 repeats `Boot
  error` / `Press any key for retry`; zerobas restarts Disk BASIC with its
  banner (TODO.md D-SYSBOOTERR).
- **`CALL SYSTEM` after a data-disk start with the DOS disk put in later**: the
  CF-3300 restarts Disk BASIC; zerobas answers `Illegal function call`
  (D-SYSLATE).
- **BDOS from BASIC (`&HF37D`)** answers seven functions only and is not
  measured against the CF-3300. It also uses the sector buffers BASIC's open
  files use, without saving them: the buffer audit of 2026-09-24 (TODO.md)
  names it as the one crossing that cannot be guarded, because the caller is
  the user's machine code.
- **A block write of zero records before the end of a file** (`&H26` with
  HL=0, which shrinks it): zerobas sets the new size and frees the rest of
  the chain, so the following close succeeds; the CF-3300 leaves the chain
  allocated and its close fails. A deliberate, signed-off difference.
- **Set random record** (`&H24`): zerobas computes the CP/M record position
  from the FCB; the CF-3300 sets the field to 1. Deliberate; the gate excuses
  those bytes.
- **After `A>BASIC`** the CF-3300 shows its BASIC banner, 23430 bytes free and
  `Disk BASIC version 1.0`; zerobas shows its own banner and its `ZB` prompt.

## What we found, and how

- **The character to print is in register E, not A** (2026-06-30). Reading A
  worked for the first lines of the boot and printed garbage for everything
  after.
- **A value returned in HL is overwritten** by DOS's common exit unless the
  handler clears a flag cell first (`&HF306`, 2026-07-02). Found on `DIR`'s
  `bytes free` footer; every handler that returns HL now clears it.
- **On zerobas's C-BIOS machine, cells set "only if empty" were never set.**
  The disk ROM builds the DOS work area only when RAM reads `&HFF`, as on the
  CF-3300; C-BIOS fills that RAM with `&HC9`. Three times this hid a fault the
  CF-3300 test machine could not show: DOS warm-started with no banner and no
  `AUTOEXEC.BAT` (`&HF340`, 2026-07-07), function `&H18` reported eight drives
  (2026-07-07), and `&H09` printed nothing (D-STROUT, 2026-10-02). Such cells
  are now set before the check, and `make bdos-cbios-selfcheck` runs the
  exercisers on the C-BIOS machine.
- **`MODE 40` and `MODE 32` at `A>` did not change the screen** (fixed
  2026-10-10, D-DOSMODE40). `COMMAND.COM` stores the new width and then asks
  the BIOS to set the screen up again (`INITXT` / `INIT32`) through the
  standard inter-slot call. While DOS runs, page 0 is RAM, and zerobas's
  inter-slot call jumped to the BIOS address in that RAM instead of switching
  the BIOS in, so only the width cell changed and the following lines came out
  at odd columns. It now pages the BIOS in for the call; the console cells and
  the screen after `MODE 40`, `DIR` and `MODE 32` match the CF-3300.
- **`CALL SYSTEM` was a `Syntax error`** (fixed 2026-10-09, D-CALLSYSTEM).
  Measured first, with and without a system disk and with disks swapped
  mid-session: the CF-3300 refuses with `Illegal function call` unless DOS
  was booted, and returns warm. The cell DOS reads for warm or cold
  (`&HF340`) turned out to hold the same value after both kinds of boot, so it
  cannot be the mark; zerobas keeps its own.
- **`A>BASIC` returned to `A>`** (fixed 2026-10-02, D-DOSBASIC): zerobas had
  put its own banner routine at `&H4022`, the standard "start BASIC" entry.
- **Set-date did nothing** (fixed 2026-10-01, D-DOSDATE): `&H2B` ran into the
  get-time routine and returned 0 by luck; the CF-3300 keeps the day count,
  and every stamp now reads it.
- **The first BDOS gate passed for the wrong reason** (2026-07-04): its
  comparison anchors were not armed, so it compared nothing. The same review
  found random-record reads and writes using the wrong record — their work
  cells were in ROM, so writes to them were lost — which no memory comparison
  could see; reading the disk image back did.

## How zerobas does it

The DOS boot is `boot_disk` in [disk/init.asm](../../disk/init.asm), with
`set_ramad` and `build_resident` laying out the work area and `dos_handoff`
in [disk/runtime.asm](../../disk/runtime.asm) setting the cells DOS reads at
its start. The BDOS handlers sit at the fixed addresses `MSXDOS.SYS` calls,
in [disk/kernel.asm](../../disk/kernel.asm),
[disk/fat.asm](../../disk/fat.asm) and
[disk/runtime.asm](../../disk/runtime.asm); `basent_body` is the
`A>BASIC` entry and `hk_system` in [disk/kernel.asm](../../disk/kernel.asm) is
`CALL SYSTEM`, reached from `ex_call` in [basic/format.asm](../../basic/format.asm)
through the hook cell `&HFDF4`. Because those addresses are fixed, the ROM's free space is in
pads between them ([disk-rom-layout.md](../disk-rom-layout.md)). The
`&HF37D` dispatcher is `bdos_entry` in [disk/driver.asm](../../disk/driver.asm).

The design follows two rules from
[spec-diskrom-kernel.md](../../disk/docs/spec-diskrom-kernel.md) §8: toward
DOS, match the addresses and register contracts exactly; toward the BIOS,
use only documented entries and the slot work area, so the same ROM works on
C-BIOS and on the CF-3300's own BIOS. Everything was found black-box —
registers, memory and screens of the running machines; `MSXDOS.SYS`,
`COMMAND.COM` and the CF-3300's disk ROM are never disassembled. The history
is in [tier2-STATE.md](../../disk/docs/tier2-STATE.md) and the per-function
evidence in [tier2-bdos-coverage.md](../../disk/docs/tier2-bdos-coverage.md).

## Related pages

[Disk](disk.md), [files and devices](files-and-devices.md),
[ROM layout](rom-layout.md), [memory map](memory-map.md),
[errors](errors.md); keyword pages [`FILES`](../keywords/FILES.md),
[`SAVE`](../keywords/SAVE.md), [`DSKF`](../keywords/DSKF.md).

## Tests that cover it

- `make bdos-acceptance` — the exercisers `BDOSX`, `BDOSX0` and `BDOSX2` to
  `BDOSX8` (our own `.COM` programs, started from `AUTOEXEC.BAT`) on the stock
  CF-3300 and on the CF-3300 with zerobas's disk ROM; the memory they leave
  and the BDOS calls they make must match.
- `make bdos-cbios-selfcheck` — the same exercisers on zerobas's C-BIOS
  machine.
- `make dosbasic-acceptance` — `A>BASIC`, then `SAVE`, with the DOS date.
- `make dosmode-acceptance` — `MODE 40`, `DIR`, `MODE 32` at `A>`: the
  console cells and the screen after each, against the CF-3300.
- `make callsystem-acceptance` — `CALL SYSTEM` after a data-disk boot and
  after a DOS boot: the error, the warm return, a file left open, and a
  missing `COMMAND.COM`.
- `make dosdate-acceptance`, `make strout-acceptance` — dates and stamps;
  function `&H09`.
- `make wrblkalt-acceptance` — block reads and writes with two files open.
- `make diskbasic-acceptance` — its `AUTOEXEC` cell runs `AUTOEXEC.BAS`.
- `make unit-test` — host tests of the FAT and date routines.
