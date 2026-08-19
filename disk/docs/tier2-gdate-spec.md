<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 — `_GDATE` slice spec (option B: the date-path canonical reproduction)

**Status:** DRAFT for sign-off, 2026-06-27. Spec-before-code ([[spec-before-implementation]]).
The first concrete slice of the "reproduce the disk-ROM-resident DOS BDOS at canonical
addresses" sub-track ([tier2-workarea-map.md](tier2-workarea-map.md),
[tier2-bdos-scope.md](tier2-bdos-scope.md)). Resume board: [tier2-STATE.md](tier2-STATE.md).

## 1. Goal of this slice
Get ours **past the MSX-DOS date prompt** (currently an infinite garbage-CONOUT loop) to the
same point stock reaches: the date-input **BUFIN** wait (n=18 in the BDOS call sequence). This
is the proven milestone — falsify-first (`callseq --poke`) showed that a correct date value
converges ours byte-for-byte with stock through to BUFIN. Reaching the `A>` prompt *past* BUFIN
(key input + possibly `_SDATE`) is the **next** slice, explicitly out of scope here (§7).

## 2. Why the date is the gate (proven, do not re-litigate)
- COMMAND.COM calls `_GDATE` ($2A) at BDOS-seq n=4 to display the boot date. Ours' `_GDATE`
  returns garbage (return regs at `$CC04`: ours HL=`0000` DE=`0003` vs stock HL=`07C0` DE=`0101`).
- Poking ours' date regs to stock's at `$CDA7` makes ours' BDOS sequence match stock n=9..18
  (date print → STROUT → BUFIN). Repro:
  `python3 probes/disk/disk_probe_diff.py callseq --maxhits 20 --poke-at 0xCDA7 --poke-nth 1
   --poke-reg BC:0x0101 --poke-reg DE:0x1354 --poke-reg HL:0x0054 --poke 0xF30E:0x00
   --diska ~/Documents/msx/msx/disks/test.dsk` (oracle disk = **test.dsk**).

## 3. The dispatch contract (observed, black-box; the design constraint)
The disk-loaded MSXDOS.SYS kernel BDOS dispatcher (identical ours/stock — it's MSXDOS.SYS code,
not ours) routes a BDOS call as follows (observed via PC-trace + watchpoints; no code
bytes decoded): `$0005`→`$D606`→`$D831` reaches the kernel dispatcher, which reads the
function number from C and indexes a 3-byte-per-entry table based at `$D8BE`
(entry = `$D8BE + 3×C`; `$D93C` for `$2A`) whose slots hold {segment byte, 2-byte
handler address}; at `$D885` it calls `$F368` to page the handler's segment (disk ROM)
into page 1, then returns into the handler.
For `_GDATE` the entry = **{segment = disk ROM, addr = `$553C`}**. **The table is in MSXDOS.SYS's
own relocated image (`$D8xx`), loaded from disk → ours cannot change it.** Therefore ours MUST
host a working `_GDATE` handler at the canonical page-1 disk-ROM address **`$553C`** (ROM offset
`$153C`). The handler runs with our disk ROM paged into page 1; it computes the date in registers
and `ret`s to the kernel continuation `$D88A` (which pages RAM back and returns to COMMAND.COM).

## 4. The `_GDATE` return contract (what ours' `$553C` must produce)
Observed at the GDATE return `$CC04` on stock (the values ours must match):

| reg | value | meaning |
|-----|-------|---------|
| HL  | `$07C0` | year = 1984 |
| D   | `$01` | month = January |
| E   | `$01` | day = 1 |
| BC  | `$0000` | (cleared) |
| A   | `$00` | day-of-week = Sunday (1984-01-01 was a Sunday) |
| F   | `$44` | Z=1, P/V=1 (the flags `xor a` leaves) |

This is the **MSX-DOS 1 clock-less default date**. CF-3300 and C-BIOS are clock-less MSX1, so the
default is correct on every target host — **no RTC / inter-slot clock read is needed** (this
refutes the earlier "clock-path" framing). Ours' handler is therefore a constant-return routine,
NOT a reproduction of stock's day-count→Y/M/D math (stock's `$553C` calls `$54C0`/`$4179`/`$492F`
to convert a stored day count in `$F33B`; ours skips all of that).

## 5. Proposed implementation
### 5a. The handler (clean-room, ~13 bytes)
```asm
; canonical $553C — MSX-DOS _GDATE ($2A): return the clock-less default date.
; Clean-room: derived from the documented BDOS _GDATE contract + the observed
; clock-less MSX1 default (1984-01-01 Sun); NO stock bytes copied.
gdate_handler:          ; MUST assemble at $553C
        ld      hl,$07C0        ; year 1984
        ld      de,$0101        ; D=month 01, E=day 01
        ld      bc,$0000
        xor     a               ; A=0 (Sunday); leaves F=$44 (Z,P/V) = stock's flags
        ld      ($F306),a       ; clear the dispatcher re-entrancy flag (stock does this; VERIFY §6)
        ret
```
### 5b. The collision and net-zero relocation
`$553C` currently sits **inside `bdos_create_body`** (`$54B5`–`~$5585`), a Tier-1 BDOS
file-create body that ours parked in the "`$5456-$5FE4` relocated-bodies gap" (`kernel.asm:319`).
That gap is free in *ours'* layout but the DOS kernel calls into it (`$553C`), so it was never
truly free for DOS boot. The implementation must **vacate `$553C`** for `gdate_handler` and
**re-place the displaced `bdos_create_body`** elsewhere using the project's established net-zero
displaced-body primitive (displaced body → free tail, chain preserved with `jp <next-label>`,
sized exactly so no canonical address shifts). Acceptance: `disk.rom` stays 16384 B; no symbol's
canonical address moves except the intentional `$553C` content swap.

## 6. Open items (resolve during implementation, before commit)
1. **`ld ($F306),a` necessity.** `$D833` sets `$F306=01` on dispatch entry and stock's `$553C`
   clears it (`xor a; ld (f306),a`). Determine whether COMMAND.COM / the kernel reads `$F306`
   after `_GDATE` (re-entrancy guard). Keep the clear (matches stock, cheap) unless it harms
   Tier-1; verify it is harmless.
2. **Full return-reg sufficiency.** Confirm COMMAND.COM consumes only HL/DE/A (and the F flags)
   from `_GDATE` — i.e. nothing else read between `$CC04` and `$CDA7` that ours must also set.
   (Capture at `$CC04` shows IX/IY/SP already identical; BC=0 on both.)
3. **Exact placement / which displaced body moves.** `$553C` is mid-`bdos_create_body`; decide
   split-vs-relocate-whole and the free-tail destination, net-zero.
4. **Both-host validation.** `$553C` is OUR disk-ROM address (Interface A, BIOS-independent), so
   no host `$F1xx` layout concern — but still run acceptance on **both** C-BIOS_MSX1 and CF-3300.

## 9. IMPLEMENTED 2026-06-27 (validated, green)
- **gdate_handler at `$553C`** (kernel.asm): the ~13-byte constant-return handler of §5a, placed
  with `ds $553C - $`. The colliding body was **`fac_loop_body`** (the FAT-cluster-allocate loop),
  NOT `bdos_create_body` as §5b guessed — `$553C` fell inside `fac_loop_body` ($550B). It is
  label-referenced (fat.asm `jp fac_loop_body`) and relocated net-zero (+63 B, tail-`ds`-absorbed).
- **Second cell needed — date-FORMAT config `$F30D`/`$F30E`** (runtime.asm `dos_handoff`): with the
  value fixed, ours still printed a 2-char-longer date and missed BUFIN. Root: COMMAND.COM reads
  `$F30E` at `$CDA7` for the date format; ours left `$F30D`/`$F30E` = `$FF` (uninit). Defaulted them
  to stock's `$F30D=01 / $F30E=00` in `dos_handoff` (DOS-only, same save/restore as `$F338`). This
  is the "date cells" §5b anticipated — the `_GDATE` value handler alone was NOT sufficient.
- **Open items resolved:** #1 `ld ($F306),a` kept (harmless, matches stock); #2 only HL/DE/A+flags
  consumed (confirmed — `$CDA7` regs now byte-match stock); #3 relocate-whole `fac_loop_body`; #4
  both-host — the date path is BIOS-independent (Interface A: `$553C` is our ROM, dispatch is
  MSXDOS.SYS); Tier-1 unharmed on BOTH hosts (FILES==CF-3300 on C-BIOS; DSKIO/APPEND==CF-3300).
- **Acceptance:** `$CC04` diff NONE; `callseq` converges to **BUFIN n=18**; test_gdate.py PASS
  (suite 19/19); net-zero 16384 B, no canonical shift; DSKIO/FILES/APPEND == CF-3300.

## 7. Out of scope (the NEXT slice, after sign-off of this one)
- Reaching `A>` *past* BUFIN: needs a key (CR) fed to the date prompt, then COMMAND.COM likely
  calls `_SDATE` ($2B) to set the accepted date — `$2B` has its own dispatch-table entry → its
  own canonical handler in ours (probably also a collision; possibly a no-op `ret` suffices).
  Characterize after this slice lands and ours reaches BUFIN.

## 8. Acceptance tests
Two layers — the emulator differential proves convergence against the oracle ONCE; the host unit
test locks the contract in on every build ([[host-unit-test-harness]] "locks in what probes prove").
1. **Emulator differential** (correctness vs stock): `callseq` (no poke) ours-vs-stock advances to
   **BUFIN (n=18)** identically (the un-poked run becomes the poked run's result).
   `python3 probes/disk/disk_probe_diff.py callseq --maxhits 20 --diska
   ~/Documents/msx/msx/disks/test.dsk`. And `capture --at 0xCC04 --nth 1` → reg diff = NONE.
2. **Host unit test** (new — `tests/test_gdate.py`, emulator-free, the `test_getdpb` template):
   `call("gdate_handler")` then assert HL=`$07C0`, D=`$01`, E=`$01`, BC=`$0000`, A=`$00`, F=`$44`
   (§4). Follow the house **"Oracle basis"** docstring convention (cf. test_tape/test_getdpb):
   the PRIMARY basis is the **documented** MSX-DOS-1 clock-less default date 1984-01-01 (public
   spec — like test_tape's documented-FSK basis, not a copied listing), CORROBORATED by the
   black-box `$CC04` capture (like test_getdpb's CF-3300 oracle). Clean-room: no stock disassembly.
   First entry of the per-function BDOS unit-test layer ([tier2-bdos-coverage.md](tier2-bdos-coverage.md));
   add one per implemented slice.
3. **Relocation guard:** the relocated `bdos_create_body` still behaves identically — Tier-1 file
   create/write == CF-3300 (probe), and (if feasible) a `call("bdos_create_body", …)` host test.
4. **Tier-1 invariants:** `make unit-test` 18/18 (→ 19/19 with test_gdate); `disk.rom` 16384 B;
   no canonical-address shift; FILES green on C-BIOS_MSX1_EU_BASIC_DISK and CF-3300.
