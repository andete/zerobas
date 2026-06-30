<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 milestone — the missing shared-kernel console-input subsystem (DOS-boot blocker)

**Status: SPEC v2 — awaiting sign-off. No asm until greenlit** (per
[[spec-before-implementation]]). Derived from a falsify-first differential probe span
(2026-06-30, M12). v1 thought this was a single `$544E` veneer; **pinning the ABIs
(below) revealed the fix is LARGER** — the disk-ROM's whole console-I/O subsystem
(`$50B7–$5453`) is unimplemented (`$00`) on ours, so this is a clean-room milestone,
not a one-liner. **Flagged as a scope surprise + clean-room-legitimacy fork → user
sign-off required before any asm.**

## 0. ABIs PINNED (M12, from the CF-3300 oracle bytes + caller decode — contract-level)
- **CONIN `$544E` returns the char in `A`.** Stock body: `CALL $541D / JR Z,$544E / RET`
  (poll a non-blocking get-char `$541D` until NZ — the loop IS the block). Caller `$5107`
  consumes the result with `CPIR` over a table at `$5374` → compares **A**. So conin
  returns A; the block is a poll loop, not a single blocking CHGET.
- **CONOUT `$5454` reads the char from `E`** (stock entry: `LD A,E / CP $FF / JP NZ,$408F`)
  — independently CONFIRMS the M10 E-contract.
- **SCOPE: the kernel delegates the WHOLE buffered-line read (BDOS func `$0A`) to a
  disk-ROM console routine entered ~`$50E0`.** That routine + its helpers
  (`$50B7`,`$50C4`,`$50C8`,`$50D5`,`$50E0`,`$541D`,`$544E`,`$5448`,…) are ALL `$00` on
  ours; ours NOP-slides the whole block down into the `$5454` CONOUT veneer (→ the garbage
  spin). Our active code ends at `$50B7` (the `$50A9` routine's `ret`).

## 1. Problem — one missing veneer, mis-read as two bugs

The relocated MSX-DOS-1 kernel has TWO console primitives at adjacent fixed entries in
the shared ASCII-kernel block:

| entry   | role   | stock call-chain                                   | ours |
|---------|--------|----------------------------------------------------|------|
| `$5454` | CONOUT | `$5454→$408F→CALSLT→kernel→$F398→$00A2` (CHPUT)     | `jp conout_body` veneer → inter-slot CHPUT ✅ (M8/M10) |
| `$544E` | CONIN  | `$544E→…→$009F` (CHGET, **blocks for a key**)       | **NO veneer — `$00` padding, falls through into `$5454`** ❌ |

`$544E` is only **6 bytes below `$5454`**. Our `kernel.asm` positions CONOUT with
`ds $5454 - $, $00`, so `$544E–$5453` are `$00` (NOP) padding. When COMMAND.COM's
BUFIN (BDOS func `$0A`) makes the kernel call **`CALL $544E`** to read a console line,
ours executes 6 NOPs and **falls straight through into `$5454` = `jp conout_body`** —
i.e. a console-INPUT request is serviced by the console-OUTPUT veneer. The result:

1. `conout_body` emits one char (`ld a,e`, E = the stale low byte of whatever DE held —
   a string/buffer pointer) and **RETURNS immediately**. It never calls CHGET, never
   blocks.
2. COMMAND.COM sees "input complete," loops its date/`A>` prompt, calls `$544E` again,
   gets another garbage char + immediate return → an **infinite spin** that scrolls the
   sign-on off and fills the screen with the 5-byte cycle `D8 19 3E 40 0A` (= the DE-low
   values of the spin's CONOUT calls).

This single fault produced BOTH symptoms the M11 board mis-split:
- **"Bug A — func-9 STROUT renders garbage":** the garbage IS `conout_body` being
  wrongly invoked by the CONIN fall-through. func-9 output itself works (its chars do
  reach CHPUT; verified). "func-9 emits zero chars / `$F398` vector unset" is REFUTED.
- **"Bug B — BUFIN returns instead of blocking":** because `$544E` falls into CONOUT
  and returns, never reaching CHGET. **Proof: CHGET (`$009F`) is called 1× on stock
  (it blocks there), 0× on ours** (`callseq --log 0x009F`, M12).

## 2. Evidence (M12, all on test.dsk, direct ground-truth — `disk_probe_diff.py`)

- `capture --at 0xC238 --mem 0xF390:0x10` → regs + `$F390` sysvars **byte-identical**
  ours==stock at func-9 entry. (Refutes "`$F398` CONOUT vector unset on ours.")
- `callseq --log 0x009F` (CHGET) → **stock 1 call, ours 0 calls.** The decisive proof
  that ours' BUFIN never reaches console input.
- `trace --anchor 0x0005 --nth 18 --resync` (from BUFIN) → fork 10 = stock
  `CALL $544E`, ours takes a 789-instr detour and never calls CHGET; the `$0038`
  interrupt fork ($0C3C vs our $DDAE int_h) **re-converges = benign** (A-3/A-5 already
  chains KEYINT correctly — interrupt service is NOT the blocker).
- `screen --machine both --settle 16` → stock = full boot blocked at `Enter new date:`;
  ours = `D8 3E 40` scrolling diagonally forever. (The arbiter.)
- `grep -i '544E\|conin\|CHGET\|009F'` over `disk/*.asm` → **nothing.** We never
  implemented console input.

## 3. Design — TWO options (decide at sign-off)

**The v1 "single `$544E` veneer" is INSUFFICIENT.** The kernel does not call `$544E`
directly per char from its own line editor — it calls a disk-ROM console *routine*
(~`$50E0`) that itself runs the line loop (CR-check at `$50FF`, `CALL $F2AC`, work cells
`$F237/8/9`, `IX=$F459`) and calls `$544E` per char. On ours that routine is `$00`, so
patching only `$544E` leaves the NOP-slide upstream of it.

**Option A (recommended) — clean-room buffered-line veneer at the routine ENTRY.** Like
`conout_body`: place `jp conin_line_body` at the kernel's console-input entry (pin the
exact address — execution enters ~`$50E0`; confirm it's the CALL target, not mid-slide),
and a free-tail body that reimplements the **documented BDOS func-`$0A` buffer contract**
clean-room: `DE→buf`, `buf[0]=max`, loop { inter-slot CHGET `$009F`; CR→done; BS→edit;
else echo via CHPUT `$00A2` + store }, set `buf[1]=count`. ~50–80 B. Pure contract, no
stock bytes. Smallest correct surface; bypasses the whole `$50xx` subsystem.

**Option B — faithful subsystem reimplementation.** Rebuild the `$50B7–$5453` helper
cluster (`$541D` non-blocking get-char, `$544E` poll-wrapper, `$5448` echo, the `$50xx`
line loop, the `$F2xx`/`$FDxx` work cells) from contract. Larger, closer to "faithful
relocation" (fork a), but needs each helper's contract pinned first. Defer unless Option
A proves the kernel relies on subsystem side effects we can't fake.

### Reference shape (Option A inner CHGET bridge, parallel of CONOUT M8/M10)

Add `$544E: jp conin_body`, consuming the existing 6-byte `$00` pad (3 bytes `jp` +
3 bytes pad, then `$5454` CONOUT as today — **net-zero, no address shift**). The body
`conin_body` lives in the free tail beside `conout_body` and mirrors it exactly, but
calls the BIOS **CHGET (`$009F`)** instead of CHPUT (`$00A2`):

```
; in:  -            ; out: A = char read (CHGET blocks until a key); BC/DE/HL/IX/IY preserved
conin_body:
        push    bc
        push    de
        push    hl
        di                          ; no interrupt while the BIOS is half-mapped
        call    pg0_mainrom_in      ; main BIOS ROM -> page 0 (EXPTBL[0]; shared helper)
        call    $009F               ; CHGET - wait for + return a char in A
        ld      (CONIN_CHAR), a     ; stash before the un-map clobbers A
        call    pg0_mainrom_out     ; restore page 0 = RAM
        ei
        pop     hl
        pop     de
        pop     bc
        ld      a, (CONIN_CHAR)     ; return A = the char
        ret
```

Open ABI questions to PIN before coding (cheap probes, falsify-first):
- **What register(s) does the kernel's `$544E` expect the char back in?** CHGET returns
  A; confirm the kernel reads A (not E/C) by capturing the kernel's use of the return at
  the `$544E` call site (`$5107` per the M12 trace). Mirror whatever CONOUT's caller
  contract turned out to be (the M10 E-vs-A lesson — do NOT assume).
- **Does `$544E` need CHSNS/echo, or is bare CHGET enough?** Stock's single `$009F`
  call (no `$009C` CHSNS in the log) suggests bare blocking CHGET is the primitive;
  the kernel's BUFIN does its own line editing/echo on top. Confirm no CHSNS is needed.
- **Interrupts during CHGET:** CHGET blocks with EI so the keyboard-scan interrupt
  (A-3/A-5 KEYINT, already live) fills the buffer. Verify `pg0_mainrom_in` left the
  main ROM mapped for the *duration* of CHGET (it does — CHGET runs to completion
  inside the mapped window), and that re-entrancy with our `$0038` handler is safe
  (the handler pages the main ROM into page 0 itself, idempotently).

## 4. Expected result & how we'll know

After the fix, ours' BUFIN calls CHGET and **blocks at `Enter new date:`** — a stable
screen byte-matching stock (no more garbage spin). Verify:
- `callseq --log 0x009F` → ours now 1 call (was 0).
- `screen --machine ours --settle 16` → `COMMAND version 1.08 / Current date is
  Sun 84-01-01 / Enter new date: .` (matches stock), no garbage.
- Then **inject a keystroke** (Enter, then a command) to drive past BUFIN to a visible
  `A>` accepting input — the GOAL's final step. The keyboard interrupt service
  (A-3/A-5) is already in place, so injected keys should be received.

## 5. Invariants
- Tier-1 green: `make unit-test` 19/19; DSKIO/BLOAD/FILES == CF-3300.
- Net-zero: `disk.rom` == 16384 B; `$544E` veneer uses existing pad (no canonical
  shift); `conin_body` added to the free tail (confirm space).
- Clean-room: `$544E`/`$009F` are the cross-vendor CONIN/CHGET ABI; our own code,
  no stock bytes (same basis as the `$5454`/`$00A2` CONOUT veneer).
- BIOS-agnostic: CHGET via `pg0_mainrom_in`'s `EXPTBL[0]` switch (CF-3300, C-BIOS, any).
