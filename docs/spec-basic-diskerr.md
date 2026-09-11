# An empty drive is `ERR 70` — the disk ROM hosts its own error codes (D-DISKERR)

TIER 3 (a common error: the forgotten disk). D-NMFAIL measured it on 2026-09-10;
Joost ruled the same day: *"add ERR 70, maybe add an ERR extension mechanism in
Disk ROM, maybe look if there is a hook for that"*. Shipped 2026-09-11.

## 1. Measured

| row | CF-3300 (no image mounted, `ON ERROR GOTO 900`) | zerobas before |
|---|---|---|
| `NAME`/`KILL`/`FILES`/`LOAD`/`SAVE` | `Disk offline`, ERR 70, ERL 20, trapped, STOPS | prints `load error`, no trap, runs on |
| `DSKI$`/`DSKO$` (D-DSKNODISK) | ERR 70 | ERR 2 / nothing |
| `BLOAD`/`MERGE` (measured 2026-09-11) | ERR 70 | `load error` printed, runs on / ERR 70 |
| `ERROR 68` / `69` / `70` in a program | `Disk write protected in 10` / `Disk I/O error in 10` / `Disk offline in 10` | `Unprintable error` |
| `ERROR 70` on the diskless VG-8020 | `Unprintable error in 10` | (same) |

## 2. The mechanism — three parts, none on main page 1 but a 9 B raiser

* **`dskio_calslt` maps DSKIO's error byte** (published: 0 write protected, 2
  not ready, 4 CRC, 6 seek, 8 record not found, 10 write fault, 12 other) into
  `DISKOP_ERR` ($E098): 2 → 70, 0 → 68, else 69; a successful transfer clears
  it, and every disk tenant clears it at entry, so a stale code can never be
  raised by a later verb. Sub page 1 only — no main copy of the body exists.
* **`disk_error` (main, 9 B)** raises the pending code, else falls to
  `load_error` — the old face for a bad BPB after a good read or an absent
  sub-ROM. The post-tenant DSKIO exits of the disk verbs jump there: `FILES`'s
  status decode, `df_or_loaderr` (LOAD/SAVE), `KILL`, `nm_fail` (NAME),
  `mc_ioerr`, `dsk_core` (DSKI$/DSKO$/COPY). The DISKSLOT checks, the parse
  rejects and every cassette exit keep `load_error` itself
  [[a-shared-tail-is-not-a-decision]].
* **The hook.** The errmsg tenant offers a code it does not host to `H_ERRP`
  ($FEFD, the MSX error-print hook) with A = ERR; the disk ROM claims the cell
  (`hk_errp`) and prints the texts it hosts from a code→string table in its own
  free space, CF=1; unclaimed (diskless), the cell is a bare `ret` and main
  prints `Unprintable error` — the VG-8020's own answer. Every future disk code
  is a table row in `disk/kernel.asm` and costs main nothing: the extension
  mechanism Joost asked for, on a published cell.

* **The driver's write path tests readiness itself.** With no medium the
  emulated FDC accepts a write command's data and completes clean, where a
  read completes NOT READY — `DSKO$ 0,0` on an empty drive said nothing, three
  runs out of three, while the CF-3300 says `Disk offline`. (A first rig with a
  breakpoint inside the driver's poll loop had shown the write failing — the
  breakpoint perturbed the DRQ handshake; the plain runs are the reading.)
  `fdc_write_phys` now reads the seek's type-I status before offering data and
  returns code 2 on the NOT READY bit, like the read path.

* `fat-error-acceptance`'s MOUNT arm pinned zerobas's own `load error` at an
  empty drive while the reference was unmeasured; it is pinned to the
  reference's `Disk offline` now, its purpose (differ from the mounted twin's
  `File not found`) unchanged.

## 3. Gate

`make nodiskerr-acceptance`: ten verbs on an empty drive (`ERR 70 AT 20`,
self-naming fences — these programs `CLS`) and the three message rows with the
image mounted; `--survey` shows the CF-3300 column. Walls: main page 1 11 → 1 B,
sub page 1 115 → 67 B, disk ROM +~110 B.
