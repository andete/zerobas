<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# C-BIOS DOS boot: `AUTOEXEC.BAT` (+ banner + date) skipped — root cause `$F340` seed

**Status:** CHARACTERISATION COMPLETE, fix AWAITING SIGN-OFF. No code changed.
**Method:** 100% black-box — PC/register/memory/I-O-port observation + poke causality
tests. MSXDOS.SYS / COMMAND.COM are never disassembled (their code bytes were not
read/decoded; only call-targets, register/memory side-effects, and screen output were
observed — [[no-reference-rom-disasm]]). The fix lands in **our own disk ROM**.
Repro artifacts: `scratchpad/autobat/` (throwaway; not committed).

## 1. Symptom (the reported finding)

On the **C-BIOS target** (`C-BIOS_MSX1_EU_BASIC_DISK` = C-BIOS + zerobas-tape +
zerobas-disk), booting MSX-DOS 1 from a disk with `AUTOEXEC.BAT` does **not** run it;
on the **CF-3300 oracle** (`National_CF-3300_ZEROBASDISK`, same COMMAND.COM) it does.

Truth table (each machine × `AUTOEXEC.BAT` present/absent; screen at settle):

| machine | AUTOEXEC.BAT | screen | behaviour |
|---|---|---|---|
| CF-3300 | present | `MSX-DOS 1.03` / `COMMAND 1.08` banners, then `A>LSTOUTX` | **cold** — runs it |
| CF-3300 | absent | banners, then `Current date is Sun 84-01-01` / `Enter new date:` | **cold** — date prompt |
| C-BIOS | present | *(no banners)* `@>` | **warm** — nothing runs |
| C-BIOS | absent | *(no banners)* `@>` | **warm** — identical |

On C-BIOS, COMMAND.COM takes its **warm-start** path (no MSX-DOS banner, no
`COMMAND` banner, no `$2A` GET DATE, no date prompt, no `AUTOEXEC.BAT` search — just
a bare prompt). Note the prompt drive letter is `@` (0x40), one below `A` (0x41).

## 2. Mechanism (black-box trace)

- **BDOS `$0005` call sequence diverges from the first call.** CF-3300:
  `$09`(STROUT banner) `$0F` `$09` `$2A`(GET DATE) `$02`×12 `$09` `$0A` = cold.
  C-BIOS: `$0E`(SELDSK) `$02`×2 `$19`(CURDRV) `$02`×2 `$0A` = warm.
- **The cold/warm branch is a single byte.** COMMAND.COM's resident code runs
  identically on both machines up to `$C228`, where `LD A,(nnnn)` loads a byte;
  `$C22C` tests it: `0` → fall through to cold (`$C22F`…`$C238` = `$09` STROUT);
  non-zero → `JP $C300` warm (`$0E` SELDSK). CF-3300 reads `00`, C-BIOS reads `C9`.
- **The tested byte is `$D61A`** (COMMAND.COM's cold/warm flag). **Poke-proven:**
  forcing `($D61A)=0` on C-BIOS at the `$C228` read flips it onto the cold path
  (`Sun 84-01-01` appears).
- **`$D61A` is seeded from `$F340`.** At `$D50F`, `LD A,(HL)` with `HL=$F340`
  (`A ← ($F340)`), then `$D511` `LD ($D61A),A`. `($F340)` = `00` on CF-3300, `C9`
  on C-BIOS at that instant.
- **`$F340` = the MSXDOS.SYS init seed (§8.33).** MSXDOS.SYS reads
  `$0246: LD A,($F340) / AND A / CALL Z,$0317`: `$00` = normal (cold) init path.

**Final causal test:** on C-BIOS, poking `($F340)=0` just before the `$D50F` load
restores **full cold boot** (plain disk → date logic; `AUTOEXEC.BAT` disk → `@>LSTOUTX`
**and the printer logger receives `4C 50 21 0D 0A` = "LP!\r\n"** — `AUTOEXEC.BAT`
runs). So `$F340` being non-zero is the whole cause.

## 3. Root cause — our own `set_ramad` `$FF` gate (an invalidated assumption)

`$F340` = `00` (CF-3300) vs `C9` (C-BIOS) because of **who writes it**:

| | CF-3300 | C-BIOS |
|---|---|---|
| power-on | `$036A` main BIOS → FF | `$0F32` C-BIOS → **`C9`** (C-BIOS fills `$F330…` RAM with `C9`) |
| disk-ROM init | **`$40D5` (our `set_ramad`) → `00`** | *(no write — gate skipped)* |
| result at DOS read | `00` → cold | `C9` → warm |

Our disk ROM already clears `$F340` — in [`set_ramad`](../init.asm) ([init.asm:383](../init.asm#L383)),
added for the CF-3300 DOS boot (§8.33). But the clear sits **after a gate**:

```asm
set_ramad:
        ld   a,(RAMAD0)     ; $F341
        inc  a              ; $FF -> $00 (Z): RAMAD uninitialised?
        ret  nz             ; host already set RAMAD -> leave it alone   <-- early return
        xor  a
        ld   (DOS_F340),a   ; clear the $F340 cold/warm seed  (NEVER REACHED on C-BIOS)
        ... set RAMAD0-3 ...
```

The gate assumes an uninitialised host leaves `RAMAD0 = $FF` (true on the real
CF-3300). **C-BIOS pre-fills `RAMAD0` with `$C9`** (its `$F330…` RAM fill), so
`inc a` = `$CA` ≠ 0, `ret nz` returns early, and **`$F340` is never cleared**. The
routine's own comment states the now-invalidated assumption verbatim
([init.asm:373](../init.asm#L373)): *"the C-BIOS hosts set their own RAMAD (observed
`$C9..`) … and **C-BIOS never boots DOS, so nothing reads RAMAD there**."* That last
clause is false — the `*_BASIC_DISK` machine boots MSX-DOS on C-BIOS (this whole
investigation; and `disk_probe_lstout_cbios.py` depends on it).

**This is a bug in our disk ROM, not in C-BIOS** — our gate mis-classifies C-BIOS's
`$C9` RAMAD-garbage as "host already set RAMAD," and skips the `$F340` clear that DOS
needs. (RAMAD itself is *not* the problem: at DOS-read time `RAMAD0-3` = `83 83 83 83`
on C-BIOS anyway, so RAM paging works and DOS boots; only the uncleared `$F340`
leaks through.)

## 4. Fix proposal (awaiting sign-off — do NOT implement yet)

The `$F340` cold/warm seed must be cleared whenever our disk-ROM cold-init runs,
regardless of what garbage a host left in `RAMAD0`. Two shapes:

- **(A, recommended) Unconditional `$F340` clear — minimal + safest.** Move the
  `xor a / ld (DOS_F340),a` **above** the RAMAD gate, so it always runs; leave the
  RAMAD `$FF` gate exactly as-is for its original regression-safety (don't clobber a
  host's valid RAMAD). Clearing the DOS cold/warm seed to `0` at cold-init is always
  the correct "cold boot" state; `set_ramad` runs only at disk-ROM cold-init, never
  on a warm COMMAND.COM re-entry, so it never wrongly forces a genuine warm boot.
  ~2 instructions moved; RAMAD logic untouched.
- **(B) Broaden the gate to detect garbage RAMAD.** Replace `inc a / ret nz` (tests
  only `$FF`) with a valid-slot-id test: a real MSX slot id is `F000SSPP`, so bits
  6-4 are always `0` — `and $70 / ret z`-style logic treats both `$FF` (`&$70=$70`)
  and `$C9` (`&$70=$40`) as uninitialised, and never misfires on a valid id
  (`$83 & $70 = 0`). This also re-derives RAMAD on C-BIOS (harmless — it already ends
  up `$83`). Larger behavioural change than (A).

**Recommendation: (A).** It fixes the reported bug with the smallest, most obviously
safe change and doesn't touch the RAMAD regression-safety logic.

**Regression tests the fix must pass** (all already have harnesses):
- CF-3300 DOS boot still cold (`make bdos-acceptance` 11/11; the AUTOEXEC.BAT-based
  exercisers still run — they rely on this cold path).
- C-BIOS DOS boot now cold: `disk_probe_lstout_cbios.py` can drop its typed-launch
  fallback and use the zero-typing `AUTOEXEC.BAT` launcher; a new probe should assert
  `AUTOEXEC.BAT` runs on C-BIOS (printer "LP!\r\n" with no keys).
- C-BIOS **BASIC** (non-DOS) boot unaffected (`make diskbasic-acceptance`; the
  `$F340` clear on the BASIC path is new but `$F340` is below RAMAD and not a
  standard sysvar — verify the BASIC banner/`Ok` still appear).
- `disk.rom` size unchanged (16384 B); FDC-window guard intact.

## 5. Clean-room note

Everything above is inputs→outputs: BDOS/BIOS **call targets** and function codes
(`callseq`), **register/memory values** at PCs, **I/O-port** writes to the printer,
and **poke causality** (forcing a byte and observing the branch). No MSXDOS.SYS or
COMMAND.COM code bytes were read or decoded — the `$C228`/`$D50F`/`$D511`/`$0246`
addresses are call/branch **targets** observed black-box, not disassembly (contrast
provider-oracle-scope.md §8.33's warning about a sub-agent that disassembled
MSXDOS.SYS and was reverted). The fix is in our own `disk/init.asm`.
