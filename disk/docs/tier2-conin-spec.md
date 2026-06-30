<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 milestone — the missing shared-kernel console-input subsystem (DOS-boot blocker)

**Status: SPEC v3 — ABIs fully pinned (M12d), provenance audit PASSED, awaiting sign-off
to implement. No asm until greenlit** (per [[spec-before-implementation]]). Derived from a
falsify-first differential probe span (2026-06-30, M12) and completed by the M12d black-box
ABI-pin (§3 "Resolved answers"). v1 thought this was a single `$544E` veneer; pinning revealed
the fix is a clean-room reimplementation of the **console line-routine at `$50E0`** (our
`$50B7–$5453` is `$00`). **All blockers cleared:** the M12-span provenance audit is CLEAN
(clean-room-audit run log, `e2a5d5d`); the ABIs are pinned black-box with the guarded harness;
the only remaining gate is the user's go-ahead to write the veneer.

## 0. ABIs (M12) — grounded on ALLOWED sources only
> **Provenance note (M12b correction):** an earlier draft pinned these by reading +
> decoding stock CF-3300 disk-ROM *code* bytes — that is disassembly-class (✗ per
> [`allowed-sources.md`](../../docs/allowed-sources.md) line 119/142) and has been
> quarantined (clean-room-audit run log, 2026-06-30). The facts below DO NOT depend on
> it; each is independently established from a clean source:
- **CONIN console input returns the char in `A`** — the **published CHGET (`$009F`) BIOS
  contract** (MSX Technical Data Book: CHGET waits for and returns a char in A). The disk
  ROM's console-input entry (observed as the call target during BUFIN — black-box) bridges
  to CHGET, so it returns A. *To confirm black-box before coding: inject a key and observe
  the char arrive in A at the BUFIN boundary.*
- **CONOUT reads the char from `E`** — already clean from **M10** (black-box `$7922`-entry
  callseq: E spells the banner/date; the ROM was never read). The `$5454` CONOUT veneer
  already implements this.
- **SCOPE (black-box + our own artifact):** during BUFIN the resident kernel CALLs into a
  disk-ROM console routine in page 1 (execution enters ~`$50E0`, observed via PC trace).
  **Our `build/disk.rom` is `$00` across `$50B7–$5453`** (our own artifact; active code
  ends at the `$50A9` routine's `ret`), so execution NOP-slides the whole region into the
  `$5454` CONOUT veneer → the garbage spin. The internal structure of stock's routine is
  NOT used (and must not be read); we reimplement the documented contract.

## 1. Problem — one missing veneer, mis-read as two bugs

> **Read with §3 "Resolved answers" (v3).** This section is the original M12 framing — it
> correctly explains the *symptom* (the unimplemented `$544E` CONIN primitive falls through
> into the `$5454` CONOUT veneer → garbage spin). The M12d black-box pin then showed the
> kernel delegates the whole line read to a routine entered at the CALL target **`$50E0`**,
> so the FIX replaces the line routine at `$50E0` (not the inner `$544E` primitive). The
> `$544E`-vs-`$50E0` detail is reconciled in §3; §1/§2 stand as the symptom analysis.

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

**The v1 "single `$544E` veneer" is INSUFFICIENT.** Black-box (PC trace): during BUFIN the
kernel enters a disk-ROM console *routine* in page 1 (~`$50E0`) that performs the whole
buffered-line read; on ours that routine is `$00`, so patching only the lowest-level entry
leaves the NOP-slide upstream of it. (We treat the routine as a black box with a documented
func-`$0A` contract — we do NOT read its internals.)

**Option A (recommended) — clean-room buffered-line veneer at the routine ENTRY.** Like
`conout_body`: place `jp conin_line_body` at the kernel's console-input entry —
**CONFIRMED CALL target `$50E0`** (PIN A: entered `ret=$D88A` from kernel `~$D887`, regs
byte-identical ours==stock — a real CALL boundary, not a mid-slide) —
and a free-tail body that reimplements the **documented BDOS func-`$0A` buffer contract**
clean-room: `DE→buf`, `buf[0]=max`, loop { inter-slot CHGET `$009F`; CR→done; BS→edit;
else echo via CHPUT `$00A2` + store }, set `buf[1]=count`. ~50–80 B. Pure contract, no
stock bytes. Smallest correct surface; bypasses the whole `$50xx` subsystem.

**Option B — faithful subsystem reimplementation.** Rebuild the `$50B7–$5453` console
subsystem from its (black-box-characterised) contracts: the buffered-line routine plus its
get-char / echo / state helpers. Larger, closer to "faithful relocation" (fork a), but each
helper's contract must be pinned **black-box** first (entry call-targets + observed
input→output + side-effect cells), never by reading the stock bodies. Defer unless Option A
proves the kernel relies on subsystem side effects we can't reproduce from contract.

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

Open ABI questions — **ALL RESOLVED black-box (M12d, 2026-06-30)** via the guarded
`disk_probe_diff.py callseq` (registers + call-counts + RAM-pointer walks only; the
`trace`/`ctx` clean-room guard ensured NO stock ROM code was decoded; the keystroke was
injected with the new `--keys`). Two probes settled the whole interface:
- **PIN A — `callseq --log 0x50E0`:** at the console-routine entry, regs are **byte-identical
  ours==stock** at the first call: `DE=$DA40 HL=$C924 ret=$D88A` (kernel caller `~$D887`).
  So the **entry is the CALL target `$50E0`** and **`DE` = the func-`$0A` buffer base**. (Ours
  re-enters `$50E0` 4× = the spin; stock once = does the read and proceeds.)
- **PIN B — `callseq --log 0x009F --keys '12-99\r'`:** CHGET now fires **7×** (was 1, blocking).
  Per call `HL` walks `$DA42,$DA43,$DA44,…` (the fill pointer), `D` = running char count
  (`00,01,02,…`), `E=$0A` = max len. So the buffer at `$DA40` is `[+0]=max(=$0A) / [+1]=count
  / [+2…]=chars` — **the published BDOS func-`$0A` layout**, and `DE=$DA40` at entry is its base.

Resolved answers:
- **Entry & register convention:** CALL target **`$50E0`** (in our `$00` dead region — net-zero
  veneer site); on entry **`DE`→buffer**, `[DE]`=max length. (Supersedes the earlier `$544E`/`$5107`
  framing: `$544E` is the stock *inner* per-char primitive; we replace the *line routine* at `$50E0`
  and call the **published** CHGET directly, so stock's inner register convention is irrelevant.)
- **Return register:** NONE — the line routine returns its result in the **buffer** (`buf[1]`=count),
  per func-`$0A`; no char-in-register contract to match. (The inner CHGET returns the char in **A** by
  the published `$009F` contract.)
- **CHSNS/echo:** **bare CHGET per char** — 7 CHGET calls across the line, **no `$009C` CHSNS in the
  input loop** (the 12 earlier `$009C` hits were output-phase break-polls during the banner, `C=09`).
  Echo is done by the routine via CHPUT `$00A2` (the typed chars appear on screen — `screen` confirms
  `Enter new date: 12-25-99`).
- **Interrupts during CHGET:** **PROVEN to work** — keys are received per char (the injected line
  echoed and CHGET fired 7×; `\r` drove stock to a visible `A>`). On ours the A-3/A-5 KEYINT is already
  live, so once the veneer reaches CHGET the same mechanism applies; `pg0_mainrom_in` keeps the main
  ROM mapped for CHGET's duration and the `$0038` handler re-maps page 0 idempotently.

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
