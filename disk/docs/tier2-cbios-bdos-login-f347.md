<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# C-BIOS DOS: BDOS `$18` LOGIN returns `0x00FF` — root cause `$F347` (DRVCNT) gated out

**Status:** ✅ FIXED 2026-07-07 (unconditional DRVCNT/CURDRV seed, same shape as the
`$F340` fix). Found by the C-BIOS self-consistency gate
([tier2-cbios-bdos-selfcheck-spec.md](tier2-cbios-bdos-selfcheck-spec.md) §3).
**Method:** 100% black-box — work-area cell reads + our OWN disk-ROM source (never any
stock/kernel code bytes; [[no-reference-rom-disasm]]). The fix lands in `disk/init.asm`.

## 1. Symptom

BDOSX2 record 1 (`$18` LOGIN, get drive login vector) diverges between hosts:

| host | LOGIN return (A / HL) | meaning |
|---|---|---|
| CF-3300 (= stock, bdos-acceptance-proven) | A=`03`, HL=`0003` | drives A:+B: (single-drive → 2 logical) |
| C-BIOS | A=`FF`, HL=`00FF` | 8 phantom drives |

Every other byte of BDOSX2's 112-byte buffer (incl. the console-input records) is
byte-identical, so this is specifically the login vector, not a harness/timing artifact.

## 2. Mechanism (black-box)

Our `login_body` ([runtime.asm:284](../runtime.asm#L284)) builds the bitmap
`A := (1 << DRVCNT) - 1` from **DRVCNT = `$F347`** (the logical-drive count). The comment
notes it "fits one byte for DRVCNT<8"; for any DRVCNT ≥ 8 the low byte of `(1<<n)-1` is
`0xFF`. So a garbage DRVCNT ≥ 8 ⇒ LOGIN `0xFF`.

Decisive measurement — work-area cells read after DOS boot (settle 18 s), both hosts:

| cell | addr | CF-3300 | C-BIOS |
|---|---|---|---|
| RAMAD0-3 | `$F341` | `83 83 83 83` | `C9 C9 C9 C9` |
| CURDRV | `$F247` | `00` | **`FF`** |
| **DRVCNT** | `$F347` | **`02`** | **`C9`** |
| DRVTBL | `$F348…` | `87 93 DF … AA` (built) | `C9 C9 … C9` (untouched) |

On C-BIOS DRVCNT = `C9` → `login_body` low byte = `0xFF`. Confirmed.

## 3. Root cause — the `$F347` seed sits below the RAMAD `$FF` gate

`set_ramad` ([init.asm:389](../init.asm#L389)) clears `$F340` unconditionally (the earlier
fix) and then gates on RAMAD:

```asm
        ld   a,(RAMAD0)     ; $F341
        inc  a
        ret  nz             ; host already set RAMAD -> return early   <-- C-BIOS: C9 != FF
```

Everything after the `ret nz` — the RAMAD fill, `build_wa_table`, `build_drvtbl`,
`build_resident`, AND the `ld (DRVCNT),$02` / `ld (CURDRV_CELL),$00` seeds (was
[init.asm:538](../init.asm#L537)) — is **skipped on C-BIOS**, whose page-3 RAM is
pre-filled with `$C9`. The whole table above confirms it (RAMAD/DRVTBL/CURDRV/DRVCNT all
left at the C-BIOS fill). This is the SAME bug class as `$F340`
([tier2-cbios-dosboot-autoexec-f340.md](tier2-cbios-dosboot-autoexec-f340.md)): the `$FF`
gate mis-classifies C-BIOS's `$C9` garbage as "host already initialised" and skips our
seed.

Why DOS still boots on C-BIOS despite the skipped plumbing: MSX-DOS on C-BIOS provisions
its own RAM paging and does not depend on our CF-3300 `$F348` DRVTBL / resident-routine
build (all `C9` and it boots fine). But **DRVCNT (`$F347`) is a DATA cell the kernel reads
directly** — via `login_body` and the `$50D5` SELDSK entry ([kernel.asm:2263](../kernel.asm#L2168))
— so the garbage leaks straight into LOGIN. `CURDRV` (`$F247`, read by `$50C4`) is the same
class and was likewise left `FF` on C-BIOS (latent).

## 4. Fix — lift the DOS seed cells above the gate (unconditional)

DRVCNT (`$F347`) and CURDRV (`$F247`) are **cold-boot DOS seed cells the kernel reads on
ANY host that boots DOS**, not CF-3300-only plumbing — so, exactly like the `$F340` clear,
they move into the `set_ramad` prologue ABOVE the RAMAD `$FF` gate and run unconditionally.
The RAMAD fill / `build_wa_table` / `build_drvtbl` / `build_resident` stay gated (they are
genuinely the CF-3300 provisioning path; C-BIOS neither needs nor runs them). Minimal
change: two leaf writes relocated up; no plumbing touched.

- CF-3300 unchanged: the gate passes there (RAMAD0=`$FF` at init), so DRVCNT/CURDRV get the
  same `02`/`00`, just seeded a few instructions earlier; `$F348` DRVTBL still built.
- C-BIOS fixed: DRVCNT=`02` → LOGIN `0x03`; CURDRV=`00` (current drive A:).

## 5. Verification

- `make bdos-cbios-selfcheck` → BDOSX2 flips XFAIL→PASS; ALL IDENTIFIED byte-identical.
  Remove `KNOWN_OPEN["BDOSX2"]` in disk_bdos_cbios_selfcheck.py + §3.1 of the selfcheck spec.
- `make bdos-acceptance` 11/11 (CF-3300 differential unchanged).
- `make diskbasic-acceptance`, `make unit-test` green; `disk.rom` still 16384 B.

## 6. Clean-room note

Inputs→outputs only: work-area cell VALUES read at runtime (data, not code) + our own
`disk/*.asm`. No MSXDOS.SYS/COMMAND.COM/stock-ROM code bytes were read or decoded; `$50D5`
/`$50C4`/`login_body` are call/branch targets in our own ROM. Fix is our own `init.asm`.
