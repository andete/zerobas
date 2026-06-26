<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 BDOS spec (fork B) — intercept $0005 with our own BDOS

**Status:** DRAFT for sign-off, 2026-06-26. No asm until signed off (spec-before-implementation).
**Chosen fork:** B (user, 2026-06-26), sized in `tier2-bdos-scope.md`.
**Goal of this milestone:** make genuine MSX-DOS 1 reach the `A>` prompt by routing COMMAND.COM's
BDOS calls to our own implementation, instead of reproducing the proprietary kernel's internal
disk-ROM address layout (fork A).

## 1. Why this is safe (the viability gate — PASSED)

Probe `disk_probe_dosboot_bdoscallers.py` (stock, whole boot to prompt): **every** caller of the
page-0 `$0005` vector is COMMAND.COM (6 from its `$C2xx` body, 12 from `$D085`, which is inside
COMMAND.COM's transient `$C200-$D5FF`). **Zero** callers are in the kernel range `$D606-$DDFF`.
The relocated kernel dispatches its own BDOS internally via `$D606`/`$D831`, never through `$0005`.
∴ Re-pointing `$0005` catches exactly application calls (COMMAND.COM + future user programs) and
does not disturb the kernel. (`$0005 = JP $D606` today, set by MSXDOS.SYS; identical ours/stock.)

## 2. Mechanism — the $0005 redirect

### 2.1 Where/when installed
In `k_47B2` (our COMMAND.COM-loader veneer), AFTER the file is loaded and BEFORE the `ret` to
`$D824 → jp $0100`. At that instant MSXDOS.SYS init is complete (so `$0005 = JP $D606` is already
in place), and COMMAND.COM has not yet run. k_47B2 overwrites the three page-0 RAM bytes:

```
$0005 = C3 <lo> <hi>      ; JP BDOS_TRAMP   (was JP $D606)
```

`BDOS_TRAMP` is a small page-0 RAM trampoline, LDIR-installed from a ROM template in the free tail
during init (like the existing `wa_seg`/`int_h_hiram`/`res_print` templates), so **ROM stays
16384 B, no canonical address shifts** (net-zero discipline). Page-0 location: TBD in a free
page-0 RAM cell in our reserved band (sign-off item — must not collide with COMMAND.COM's page-0
use; the FCBs/DTA/command-tail at `$005C/$0080` and the RST vectors are reserved, but there is
room, e.g. just above `$0008`).

### 2.2 The trampoline
```
BDOS_TRAMP:  ; entry: C=function, DE/etc per BDOS ABI; called from page-0/3 with TPA in page 1
        di                       ; no interrupt while page 1 is swapped
        <page the disk ROM into page 1>     ; the proven $F368/wa_seg segment switch
        call bdos_entry          ; our BDOS dispatch (page 1)
        <restore page 1 = TPA RAM>          ; $F36B/wa_seg
        ei
        ret
```
Precedent: identical paging window to `conout_body` (which pages the MAIN ROM into page 0) and to
the stock kernel's own "page disk ROM into page 1 for file ops". bdos_entry reads only the FCB
(DE, in page 3) and our private work area (`$E4xx`), never page-1 TPA, so hiding the TPA during
the call is safe. **Open item:** confirm COMMAND.COM does not pass a BDOS buffer pointer that
lives in page 1 (the DTA default is `$0080` page 0; STROUT/BUFIN buffers seen so far are page 3).

## 3. Function table — COMMAND.COM startup set

Measured (probe `bdosseq`) BDOS calls during COMMAND.COM startup, in order: `$09 $0F $0E $02 $06
$19 $0A $2A`. Target = reach `A>` and accept a line. Coverage plan:

| fn | name | contract (MSX2 TH / CP/M ABI, public) | status |
|----|------|----------------------------------------|--------|
| `$0F` | FOPEN | DE=FCB → A=$00 found / $FF not-found | **HAVE** (`bdos_open`, returns $FF — fixes this blocker) |
| `$14` | RDSEQ | read 128-byte record → A=$00 / $01 EOF | HAVE (`bdos_seqread`) |
| `$10` | FCLOSE | DE=FCB → A=$00 | HAVE (`bdos_close`) |
| `$1A` | SETDTA | DE=new DTA | HAVE (`bdos_setdta`) |
| `$02` | CONOUT | E=char → emit via CHPUT `$00A2`; A=char | NEW (reuse `conout_body`'s CHPUT path) |
| `$09` | STROUT | DE→string, '$'-terminated → emit each via CONOUT | NEW (loop on CONOUT) |
| `$06` | DIRIO | E=$FF: console in (no echo), A=char/0; else emit E | NEW (CHPUT + CHSNS/CHGET) |
| `$0A` | BUFIN | DE→{max,len,buf}: edited line input until CR | NEW (BIOS keyboard; minimal editor) |
| `$0E` | SELDSK | E=drive → set current drive; A=#drives (1) | NEW (drive cell; single-drive) |
| `$19` | CURDRV | → A=current drive (0=A) | NEW (read drive cell) |
| `$2A` | SDATE | set date → A=$00 ok | NEW (**stub** — MSX1 has no RTC; see open items) |

bdos_entry (driver.asm `$626`) is extended with the NEW dispatch cases. Console functions delegate
to the main BIOS (CHPUT `$00A2`, CHSNS `$009C`/CHGET `$009F`) via the same page-0 main-ROM switch
`conout_body` already uses — BIOS-agnostic (EXPTBL[0]), clean-room (documented BIOS ABI).

## 4. Shared DOS state

- **DTA:** our `BDOS_DTA` (`$E4C0`); COMMAND.COM sets it via `$1A` (seen at startup). OK.
- **Current drive:** new 1-byte cell (single-drive A → 0). `$0E`/`$19` read/write it.
- **FCB:** caller-owned (DE). We already keep drive(+0)/name(+1..11) byte-identical to MSX-DOS;
  the documented intentional divergence in FCB bookkeeping fields (PROVENANCE.md §BDOS) is
  unchanged and unread by COMMAND.COM's startup path (to re-verify).
- We do **not** share the kernel's `$F1xx/$F2xx` work area — our BDOS is self-contained (reads the
  disk fresh via DSKIO), which is the point of B. (To watch: anything COMMAND.COM set up *expecting*
  the kernel BDOS to have cached — none seen in the startup trace.)

## 5. Open items for sign-off

1. **Scope of this milestone:** stop at "reach `A>` + accept one line" (startup set only), then
   iterate per command? (Recommended — validate the mechanism before the long tail of functions.)
2. **SDATE `$2A`:** stub to A=$00 (no RTC) acceptable for now? (COMMAND.COM's date prompt: confirm
   it proceeds on a stub.)
3. **BUFIN `$0A` fidelity:** minimal (CR-terminated, backspace) vs full CP/M line editor? Minimal
   first, recommended.
4. **Trampoline page-0 location** (§2.1) — pick a free cell that cannot collide with COMMAND.COM.
5. **Clean-room confirm:** all contracts cited to MSX2 TH / CP/M public ABI; no oracle disassembly.
   The function *behaviours* are documented; the only oracle use is observing return *values* to
   pick the right documented variant (e.g. FOPEN $FF). OK to proceed on that basis?

## 6. Validation plan (before commit)

- `fopenresult` (ours): FOPEN of AUTOEXEC.BAT returns **A=$FF** (was $21).
- `bdosseq` (ours): startup sequence matches stock's *shape* (STROUT→FOPEN→… no prompt-spin);
  the `$D858` CONOUT-garbage loop is gone.
- Screen: the `A>` prompt appears (VRAM check) — the milestone's visible success.
- A-3 intact (`disk_derail_locate --preset sp-rompage` STUCK); Tier-1 green (`make unit-test`
  18/18; DSKIO/BLOAD/FILES == CF-3300); net-zero `disk.rom` == 16384 B; test disk md5 unchanged.

## 7. Provenance

Mechanism + contracts from public sources (MSX2 Technical Handbook BDOS call table, CP/M FCB/
console conventions, MSX BIOS ABI for CHPUT/CHGET/CHSNS, EXPTBL slot protocol). Oracle use is
black-box only (observe `$0005` callers and return values; never disassemble the kernel,
MSXDOS.SYS, or COMMAND.COM). Probes: `disk_probe_dosboot_{bdoscallers,bdosseq,fopenresult}.py`.
