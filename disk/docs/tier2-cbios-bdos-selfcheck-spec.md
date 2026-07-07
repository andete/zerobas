<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# C-BIOS-target BDOS self-consistency gate (`make bdos-cbios-selfcheck`)

**Status:** gate BUILT + wired 2026-07-07 (`make bdos-cbios-selfcheck`, exit 0 = green).
First run caught a real, confirmed BIOS-dependent divergence — **BDOS `$18` LOGIN**
(§3) — briefly carried as a tracked XFAIL, then **ROOT-CAUSED + FIXED same day**
(tier2-cbios-bdos-login-f347.md): `KNOWN_OPEN` is now empty and the gate is **10/10
byte-identical** across both hosts (ALL IDENTICAL). The XFAIL machinery (§3.1) stays in the
gate for the next finding.

## 1. Why this gate exists (the coverage gap)

`make bdos-acceptance` (disk_bdos_acceptance.py) proves the disk ROM's whole MSX-DOS-1
BDOS surface is 0-byte-identical to the stock oracle — but it is a **differential**, so it
can only run on the **CF-3300** host (`National_CF-3300_ZEROBASDISK`): that is the only
machine carrying a genuine stock disk ROM + MSX-DOS to diff against. C-BIOS has no such
reference. So the disk ROM's MSX-DOS boot + BDOS behaviour on the **actual shipped C-BIOS
target** (`C-BIOS_MSX1_EU_BASIC_DISK`) was never exercised. The two-interface rule ASSUMED
disk-ROM↔main-BIOS is BIOS-agnostic, so CF-3300-only was deemed enough for the DOS layer.

The `$F340` cold/warm-boot bug (tier2-cbios-dosboot-autoexec-f340.md) falsified that
assumption once already: a genuinely BIOS-dependent seam (C-BIOS's `$C9` RAM fill vs the
real BIOS's `$FF`) sat in the DOS-boot path, structurally unreachable by the CF-3300 gate.
This gate closes the general form of that gap.

## 2. What it does (self-consistency, not differential)

There is no stock C-BIOS+DOS oracle, so this is a **self-consistency** gate: it re-captures
the SAME memory regions the BDOSX exercisers already pin (the FCB/data/register-buffer
evidence proven 0-byte-identical to stock on the CF-3300), once on the CF-3300 host and
once on the C-BIOS host, and asserts the two buffers are **byte-identical**. Both runs use
our OWN disk ROM — only the host BIOS differs — so any differing byte is a BIOS-dependent
behaviour of our DOS layer. Identical buffers ⇒ the BDOS surface is BIOS-independent, i.e.
what the CF-3300 gate proved against stock also holds on the shipped C-BIOS target.

Mechanics (disk_bdos_cbios_selfcheck.py):
- Reuses `disk_bdos_acceptance.EXERCISERS` + `build_and_plan` as the single source of truth
  for anchors/regions (the two gates can't drift on coverage).
- For each harvested `capture ... --mem R` command, runs a one-sided `capture --machine
  ours` twice: default env (CF-3300) and `ZEROBAS_OURS_MACHINE=<C-BIOS machine>` (the new
  env hook in omsx_session.py), then compares the printed `memory …:` buffers.
- `callseq`/`screen` probes are skipped — the boot/console call *sequence* legitimately
  differs between BIOS hosts; the capture buffers are the ROM-behaviour evidence.
- Exercisers launch via `AUTOEXEC.BAT` (zero typed keys), which only fires on C-BIOS
  because of the `$F340` fix — so this gate is also that fix's standing regression guard
  (a C-BIOS side that never reaches the anchor is reported as a boot regression).

Clean-room: our own ROM under two host BIOSes; only DATA/register capture, no reference
code decoded — same allowed class as the differential.

## 3. First catch — BDOS `$18` LOGIN returned `0x00FF` on C-BIOS (✅ FIXED)

> **RESOLVED 2026-07-07** — root cause + fix in tier2-cbios-bdos-login-f347.md: DRVCNT
> (`$F347`) was seeded below the RAMAD `$FF` gate, which C-BIOS's `$C9` RAM-fill defeats, so
> `login_body` read garbage ≥8 → bitmap `0xFF`. Fixed by seeding DRVCNT/CURDRV
> unconditionally above the gate (same shape as the `$F340` fix). BDOSX2 now byte-identical
> across both hosts; `KNOWN_OPEN` is empty. Kept below as the worked example of what the gate
> catches.

BDOSX2 record 1 (`$18` LOGIN, get login vector) is the only divergence in the whole suite.
Full 8-byte record `func A B C D E H L`:

| host | record 1 bytes | HL (login vector) | A |
|---|---|---|---|
| CF-3300 (= stock, bdos-acceptance-proven) | `18 03 00 18 00 80 00 03` | **`0003`** (drives A+B) | `03` |
| C-BIOS | `18 FF 00 18 00 80 00 FF` | **`00FF`** (all 8 drives) | `FF` |

Everything else in the 112-byte buffer — including the console-input records
(CONIN='x'/DIRIN='y'/INNOE='z') — is byte-identical, so this is NOT a `--keys2` timing
artifact; it is specifically the login vector. Since `bdos-acceptance` BDOSX2 passes on
CF-3300 with no allowlist, `0x0003` is the **stock-correct** value (single-drive → 2 logical
drives A,B). `0x00FF` on C-BIOS claims 8 drives exist — a genuine wrong-behaviour on the
shipped target (a DOS program enumerating drives via LOGIN would see 8 phantom drives).

Same *flavour* as `$F340`: a value our DOS layer computes/seeds correctly under the real
CF-3300 BIOS but not under C-BIOS. NOT yet root-caused (login vector is built by the DOS
kernel from the disk ROM's drive-count / a work-area seed at init — black-box trace TBD,
same method as the `$F340` hunt: PC/reg/mem/port + poke-causality, no reference disasm).

**This byte is deliberately NOT allowlisted** — allowlisting a real bug would defeat the
gate. Instead it is a tracked **KNOWN_OPEN** entry (§3.1).

### 3.1 How the known-open is carried (xfail, not excused)

`disk_bdos_cbios_selfcheck.py` distinguishes two dicts:
- `ALLOWLIST` — a byte that is *correct* and BIOS-seeded on both hosts (excused). Empty.
- `KNOWN_OPEN` — a *confirmed real bug*, tracked but unfixed. The LOGIN A/L bytes
  (`0x0349`, `0x034F`) live here. Semantics: a region whose diffs land EXACTLY on its
  known-open set → **XFAIL** (loud, exit 0, doesn't red the build); a diff that spreads to
  ANY other byte → **FAIL** (the bug must not grow unnoticed); a known-open byte that STOPS
  diverging → **XPASS** ("update the tracker — the bug may be fixed"). So the gate is
  committable and green today without hiding the finding, and it will notice both
  regression (spread) and resolution (cleared) of the LOGIN bug automatically.

**Follow-on milestone:** ✅ DONE 2026-07-07 — LOGIN `$18` root-caused + fixed
(tier2-cbios-bdos-login-f347.md); `KNOWN_OPEN["BDOSX2"]` removed, gate 10/10 ALL IDENTICAL.
The xfail/known-open machinery above is retained for the next finding.

## 4. Regions covered (9/10 byte-identical on first run)

BDOSX 0x0300 / 0x0400 · BDOSX3 0x03b0 / 0x04d5 · BDOSX4 0x01c5 · BDOSX5 0x019a ·
BDOSX6 0x0207 / 0x0270 · BDOSX7 0x01b8  — all byte-identical CF-3300 vs C-BIOS.
BDOSX0 contributes no capture region (callseq/screen only). BDOSX2 0x0340 — the LOGIN
divergence (§3).

## 5. Usage

```
make bdos-cbios-selfcheck               # full suite (both hosts, heavy)
make bdos-cbios-selfcheck ONLY=BDOSX3   # one exerciser
python3 probes/disk/disk_bdos_cbios_selfcheck.py --list   # plan only, no emulator
```
