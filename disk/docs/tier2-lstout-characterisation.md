<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 — BDOS `$05` LSTOUT fully characterised (M27 follow-up)

_2026-07-04. Resolves the M27-deferred "printer-pluggable angle" (see
[tier2-m27-lstout-spec.md](tier2-m27-lstout-spec.md) §4) that was left
**inconclusive** because it relied on PC snapshots instead of I/O-port tracing.
This pass settles it with a real func-5 trigger + I/O-port-level observation._

## 1. What was open

M27 landed the real DIR fix (`$F23B` printer-echo cell) but deliberately did
**not** wire LSTOUT's own dispatch (`$5465`, un-wired / harmless squat), and
left two questions unanswered:

1. **Is stock's LSTOUT poll hang-safe with no printer attached?** (M19/M20/M27
   all declined to trigger a real LSTOUT for fear of an unbounded "wait for
   printer ready" hang.)
2. **What is LSTOUT's real contract** — which port(s), what register in, what
   does it delegate to — so `$5465`/`lstout_body` could be wired later?

## 2. Method (clean-room: black-box side-effects only)

- **Real trigger**, not a poked stub: [`probes/disk/lstoutx.asm`](../../probes/disk/lstoutx.asm)
  → `LSTOUTX.COM`, 100% own code, issues five REAL `BDOS $05` calls
  (`E`='L','P','!',CR,LF) then spins at `done:` ($0123). Injected into a
  throwaway `test.dsk` copy via the existing FAT12 injector.
- **New probe capability** in the sanctioned differential probe
  `probes/disk/disk_probe_diff.py` (NOT a new probe — a mode + a flag):
  - `ioport` mode — traces `read_io` **and** `write_io` on a set of ports
    (a status poll is a tight *read* loop; data output is a *write* stream).
  - `--plug-printer` / `--printer-device` / `--printer-log` — plug an openMSX
    printerport pluggable at init so the list device presents READY and a stock
    poll can complete. (`simpl` is a Covox DAC, NOT a printer — use
    `msx-printer` / `epson-printer` / `logger`; all three present ready and
    behave identically here.)
- Only PC / port / direction / value / call-counts recorded — the allowed
  black-box kind ([[no-reference-rom-disasm]]). No stock code bytes decoded.

## 3. Findings — the complete LSTOUT contract

### 3.1 It is NOT hang-safe without a printer (Q1: answered)
With **no** ready-presenting device on the printerport, a single `$05` call
**never returns**: stock tight-polls printer-status port **`$90`** forever
(300 reads, capped, all from reader-PC `$0887`; zero writes). `LSTOUTX.COM`
reaches only call n=1 on stock, then hangs. This is **authentic CF-3300
hardware behaviour**, not a bug — the M19/M20/M27 caution was correct.
(Ours' un-wired `$5465` squat returns instantly, so ours races through all 5
calls with garbage `A=B0` — the signature of the harmless NOP-slide.)

### 3.2 The on-the-wire protocol (Q2, mechanism)
With a ready printer plugged, each char is exactly:

| step | port | op | value | issuing PC |
|------|------|----|-------|-----------|
| status poll | `$90` | READ | (ready) | `$0887` |
| data | `$91` | WRITE | the char | `$086D` |
| strobe assert | `$90` | WRITE | `$00` | `$0870` |
| strobe release | `$90` | WRITE | `$FF` | `$0873` |

Matches the published MSX printer-port hardware spec (`$90` bit-in = /BUSY
status, bit-out = /STROBE; `$91` = data) — an independent cross-check that the
observation is faithful. End-to-end verified: the raw `logger` output file
contained `4C 50 21 0D 0A` = `"LP!\r\n"`, exactly the bytes sent.

### 3.3 It delegates to main-BIOS LPTOUT `$00A5` (the architecturally key fact)
All the port I/O happens in **page 0 = main BIOS ROM**. Stock's func-5 path
calls the standard BIOS **`LPTOUT` (`$00A5`)** vector **once per char, with the
char in `A`** (`callseq --log 0x00A5` → stock 5 hits, `A`=4C/50/21/0D/0A;
ours **0** hits). The kernel's page-1 func-5 worker at `$5465` is reached with
**`E` = char** (`callseq --log 0x5465` → both machines `E`=char, `A=00`,
return to dispatcher exit `$D88A`) — the **same entry contract as CONOUT
`$5454`** (M10). So the whole path is:

```
BDOS $05  →  kernel func-5 worker $5465 (E=char)  →  main-BIOS LPTOUT $00A5 (A=char)
                                                        →  poll $90 / write $91 / strobe $90
```

LSTOUT is a **BIOS-delegating** function — exactly the BIOS-agnostic disk-ROM↔
main-BIOS interface the two-interface rule ([[cbios-target-cf3300-oracle]])
wants. The disk ROM must NOT poke `$90`/`$91` itself; it must call BIOS
`$00A5` and inherit whatever the host BIOS does.

## 4. `$5465` / `lstout_body` — WIRED (2026-07-04, signed off)

Implemented exactly as the fix shape below (`disk/kernel.asm`): `k_5465: jp
lstout_body` lands naturally at `$5465` (= `k_5462` + 3 bytes), body in the
`$5456-$5FE4` gap section so the `ds $5FE5 - $` pad absorbs it **net-zero**
(`k_5FE5` unmoved at `$787E`, `p0_env_tab` unmoved at `$7FB7` ≤ the FDC-window
guard `$7FB8`; ROM still 16384 B). **Verified:** ours now calls BIOS `$00A5`
**5× (was 0×)** with `A`=char matching stock; on-the-wire byte-identical to
stock (READ `$90` / WRITE `$91` / strobe `$90` `$00`/`$FF`, same BIOS PCs
`$0887`/`$086D`); raw log = `"LP!\r\n"`; boot+DIR BDOS parity 260/260 aligned;
unit-test 19/19; probe smoke (DSKIO/BASIC/tape) green.

> ### ⚠ FOLLOW-UP — C-BIOS needs a real LPTOUT (`$00A5`)
> LSTOUT is deliberately BIOS-delegating, so on the **C-BIOS target** it only
> does something once **C-BIOS's own `$00A5` LPTOUT** is a real implementation.
> C-BIOS today stubs it → on C-BIOS our LSTOUT **safely no-ops** (correct, no
> hang), but nothing prints. **To make list output actually work on C-BIOS,
> C-BIOS must gain a working LPTOUT** (poll printer-status port `$90`, write
> data `$91`, pulse strobe — the protocol pinned in §3.2). That is a change to
> C-BIOS, NOT to this disk ROM: once C-BIOS's `$00A5` works, LSTOUT here starts
> printing with zero change to zerobas-disk. Tracked as a standing cross-
> component follow-up ([[cbios-lptout-followup]]).

The fix shape (as landed):

- **Entry:** `E` = char (confirmed, = CONOUT contract). `$5465` is CALLed by the
  kernel dispatcher; return to `$D88A`.
- **Body:** `ld a,e` → call main-BIOS `LPTOUT $00A5` via the inter-slot
  main-ROM path (the `pg0_mainrom_in`/`pg0_mainrom_out` pattern `conout_body`
  and `dos_clear_screen` already use for CHPUT/FILVRM) → `ret`. **No direct
  `$90`/`$91` I/O.**
- **Return/epilogue:** mirror `conout_body`'s proven epilogue (LSTOUT returns
  nothing in `HL`, so the `$F306` HL-mirror rule is not a concern, but copy the
  known-good shape rather than re-derive it).
- **Placement:** `$5465: jp lstout_body` + shift `callf_body_body` down within
  the M22a section's slack (net-zero, verify at build) — per M27 §4's tentative
  plan. **Watch the FDC-window guard** ([[disk-hardware-target-variants]]): the
  new body goes in a free-tail region, and the guard now errors if it crosses
  `$7FB8`.
- **BIOS-agnostic payoff:** on real CF-3300 hardware this drives the printer
  (and, faithfully, hangs if none is attached — matching stock); on C-BIOS it
  inherits C-BIOS's own `$00A5` (a stub/no-op there → LSTOUT safely no-ops, no
  port poll, no hang). We delegate the policy to the BIOS; we don't decide it.

## 5. AUXIN (`$03`) / AUXOUT (`$04`) — same technique applies
Not characterised here, but the `ioport` + `--plug-printer` toolbox and the
`rs232-tester` / `rs232-net` pluggables (on the RS-232/aux side) make the same
black-box approach available if AUX support is ever prioritised. Both are
expected to be BIOS-delegating in the same way (`AUXIN`/`AUXOUT` BIOS calls).

## 6. Status
**Characterisation COMPLETE and `$5465`/`lstout_body` WIRED** (§4). LSTOUT is
fully understood (mechanism, hang-safety, entry/exit contract, BIOS delegation,
all black-box) and now implemented, delegating to main-BIOS LPTOUT `$00A5`.
Verified end-to-end vs stock; net-zero ROM change; all regressions green. Tooling
landed for reuse (`ioport` mode, `--plug-printer`). **One standing follow-up:**
C-BIOS needs a real `$00A5` for list output to actually print on the C-BIOS
target (§4 ⚠; [[cbios-lptout-followup]]) — a C-BIOS change, not a disk-ROM one.
