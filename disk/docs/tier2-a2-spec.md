<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 milestone A-2 — make `int_h` chain to the main-BIOS KEYINT

**Status: SPEC — awaiting sign-off (rework deferred to a signed-off effort per the
architecture audit). No asm until greenlit.** Derived from spec + CF-3300 oracle
traces (A-1 analysis, §8.70); the fix is BIOS-agnostic and is the `EXPTBL[0]`/CONOUT
(M8b) pattern applied to the interrupt vector.

## 1. Problem (why the boot runs away)

During DOS, page 0 is RAM, so the disk ROM installs a RAM `$0038` interrupt vector
(`lay_page0_env`; confirmed the disk-ROM's job — O-1). Our `int_h` only does a partial
VDP ack and returns:
```
int_h:  push af / in a,($99) / pop af / ei / ret
```
It runs **none** of the standard interrupt service — no H.KEYI, H.TIMI, keyboard scan,
or JIFFY tick. COMMAND.COM's command/idle loop depends on those (timer + keyboard), so
it derails → the `$D7B0-DC00` / `SP=$4250` runaway (the residual M9 blocker, now
explained: it is downstream of a starved interrupt service, BIOS-agnostic in nature).

## 2. Contract (from the CF-3300 oracle — A-1/O-2, `pctrace --arm 0xDDAE --stock`)

Stock's DOS `$0038` handler (`$DDAE`):
1. saves registers and switches to a private stack;
2. does an **inter-slot CALSLT to the main-ROM KEYINT** — target `$0038` in the main-ROM
   slot, whose body on the CF-3300 is at `$0C3C`;
3. that KEYINT body calls the standard **H.KEYI (`$FD9A`)** then **H.TIMI (`$FD9F`)**
   hooks, i.e. the full service (VDP ack, keyboard, JIFFY, timer), and returns.

So the **standard, BIOS-agnostic contract** is: *the DOS `$0038` RAM handler must
inter-slot-call the main-BIOS KEYINT (`$0038` entry of the main-ROM slot) so the
documented interrupt processing runs.* Every compliant main ROM (CF-3300, **C-BIOS**,
any vendor) has KEYINT at `$0038` and honours the `$FD9A`/`$FD9F` hooks — this is the
MSX1 standard, so it ports by construction (Interface B).

## 3. Design (the CONOUT/`EXPTBL[0]` pattern, applied to `$0038`)

`int_h` becomes a real inter-slot call to the main-ROM KEYINT — **not** via our
simplified `calslt_h` (which doesn't switch slots), but with its own `EXPTBL[0]`-driven
page-0 switch, exactly like `conout_body` (M8b). Sketch:
```
int_h:                      ; maskable interrupt, IFF=0, page 0 = RAM
        ; (no pre-ack: KEYINT does the VDP ack itself — remove the in a,($99))
        push af / push bc / push de / push hl   ; KEYINT preserves regs, but be safe
        in   a,($A8)
        ld   (..save..), a
        <select main-ROM slot in page 0 from EXPTBL[0]  ; reuse the conout_body
         primary switch + (if expanded) the conout_set_sub secondary path>
        call $0038          ; main-ROM KEYINT: ack + H.KEYI + H.TIMI + keyboard + JIFFY
        di                  ; close KEYINT's internal EI window before un-mapping
        ld   a,(..save..) / out ($A8), a         ; restore page 0 = RAM
        pop hl / pop de / pop bc / pop af
        ei
        ret
```
Notes / details to finalise against the stock `$DDAE` return path when implementing:
- **IFF window.** KEYINT ends with its own `ei`; the `di` immediately after the `call`
  closes the re-enable window before we un-map the main ROM. (Stock uses a private
  stack + ordered restore for the same reason; verify the exact safe ordering.)
- **Shared helper.** Factor the `EXPTBL[0]` page-0 main-ROM switch/restore out of
  `conout_body` into a small shared routine used by both CONOUT and `int_h` (avoids two
  copies of the expanded-slot logic). Net-zero/byte-ledger handled as usual.
- **Stack.** Our interrupt arrives with SP in page-2 RAM (banner phase) — the `call`
  to KEYINT and its pushes are safe (page 2 stays mapped). If any phase runs the
  interrupt with SP in a page we switch, add a private-stack switch like stock; confirm.
- **`int_h` stays in page-1 ROM** (slot 3-1, always mapped) — location is irrelevant to
  correctness, only the real inter-slot behaviour matters. `lay_page0_env` keeps
  installing `$0038→int_h` (O-1: correct).

## 4. Validation

1. `make unit-test` (18/18) + DSKIO/FILES == CF-3300 + BLOAD — Tier-1 must stay green
   (the interrupt path is DOS-only; Tier-1 disk-BASIC runs under the main BIOS's own
   `$0038`).
2. `pctrace --arm 0x0100` / `_hang.py`: the runaway should clear or advance materially;
   look for COMMAND.COM reaching the `A>` idle/input loop (`$0B90-$0D8F`).
3. `stackwatch`: the `$4251`/`int_h` storm should be gone (SP stays healthy).
4. **Interface-B regression guard:** because KEYINT is the MSX1 standard, a green result
   on the CF-3300 environment should port to C-BIOS by construction (A-4 confirms).

## 5. Scope note

A-2 is one focused change (rework `int_h` + factor the shared slot helper). It does
**not** touch the simplified `calslt_h/rdslt_h/wrslt_h/enaslt_h` — those are A-3, gated
on O-3 (which page-0 inter-slot vectors the loaded DOS actually exercises). A-2 is
expected to be the change that clears the residual runaway, since the interrupt service
is what COMMAND.COM's loop starves on.
