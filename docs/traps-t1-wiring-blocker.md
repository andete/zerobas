# Interrupt-traps T1 — resident-poll wiring BLOCKED (2026-07-24)

Status: the T1 **funding carve landed** (build_83_name → fcbname_tenant, committed
f33cae7). Wiring the resident poll (basic/traps.asm) then hit a **consistent, not-yet-
root-caused crash** and was reverted to green. This logs the investigation so the next
span doesn't re-walk it.

## What was wired (all reverted to green in the working tree, with notes)
- `main.asm`: `include "basic/traps.asm"` (event_poll + htimi_service + trap_init).
- `playsvc.asm` `play_install`: H.TIMI seam → `htimi_service` (event_poll then fall into
  play_service).
- `initext.asm` ier_done + `program.asm` run_prog: `call trap_init` (ZTRAP zero-fill).
- Fixed a real latent bug in `event_poll`: its fast-out (`ret z`) was **not register-
  transparent** (leaked the TRAPENA test into A/flags) — violates the H.TIMI contract.
  Now `push af` first, `pop af` on all paths. (Kept in traps.asm; inert while unwired.)

## Symptom
Full wiring → merged C-BIOS machine crashes at BOOT: `diskbasic-acceptance-repack`
34/34 → 3/34, `string-acceptance` fails, FILES/`?1234` print full-screen garbage.
Consistent across repeated runs (verified ×3 each way).

## Bisection — every component is INDIVIDUALLY safe (all verified on the repack machine)
| Config | Result |
|---|---|
| Clean tree (HEAD = carve) | PASS ×3 |
| Clean + 3 `nop`s at ier_done (pure page-1 shift) | PASS |
| traps.asm included + seam ON, **no** trap_init (Config C) | PASS (string + disk 34/34) |
| Zero $E1D1..$E21F **at the prompt** via debug-write, then run a command | PASS (harmless!) |
| **Full wiring (seam + boot/RUN trap_init)** | **FAIL ×3** |

So: the page-1 shift is safe, the seam is safe, and **zeroing the ZTRAP region at
runtime is completely harmless** — yet the full wiring crashes at boot.

## What the crash is NOT (ruled out empirically via openMSX watchpoints)
- **NOT a RAM collision at $E1D1..$E21F.** Spec §3 places ZTRAP in the "freed VARTAB
  window $E1C0..$E240". Read/write watchpoints over the whole range show the ONLY
  accessors are: (a) `event_poll`'s own read (fast-outs when TRAPENA=0), (b) `trap_init`'s
  own `ldir`, and (c) the C-BIOS **boot-time RAM-size detection** (PC 0x0D42, SP=$FFFF,
  pre-stack — writes $E100/$E200 as a probe, not a persistent work area). No BASIC/disk/
  C-BIOS code reads the region during ops or during the post-init boot. Zeroing it at the
  prompt is harmless (proven). So the ZTRAP placement is **not** the cause.
- **NOT the seam / event_poll** (Config C passes; event_poll is register-transparent).
- **NOT the pure page-1 shift** (clean + 3 nops passes).
- **NOT staleness** (clean `make clean` rebuild still fails; sub.rom + disk.rom are
  byte-identical to HEAD — `git diff sub/basic-resident-abi.inc` empty).
- **NOT the merge tool** (build_mainrom splices BASIC over $2812-$7FFF wholesale; no
  hardcoded BASIC page-1 address).

## The remaining paradox / best current hypothesis
Full wiring = Config C (PASS) + the `call trap_init` calls. The zeroing is harmless and
the register clobber is safe (nothing live at either call site). The one thing left is
the **3-byte insertion at ier_done shifting page-1 code, but ONLY when the seam+traps
code is also present** (clean + 3 nops passes; Config C + trap_init fails). That points
to a **fixed-address / alignment dependency in the shifted page-1 region that trips only
at a specific combined shift** — a latent page-1 layout fragility, or possibly an
openMSX RAM-init / boot-timing artifact (initialRam pattern was being investigated).

## Recommended next steps (fresh session)
1. Confirm the localization: Config C **+ 3 nops at ier_done** (seam+include, no
   trap_init, just the shift) — does it fail? If yes, the bug is a page-1 fixed-address
   dependency exposed by shift, independent of trap_init entirely.
2. If so, disassemble our OWN shifted page-1 region (allowed — our code) around the
   routines that move, looking for a hardcoded $4xxx-$7xxx target / self-modifying site /
   jump table with a fixed high byte.
3. Rule out an openMSX artifact: check the repack machine's `initialRam` content; try a
   different RAM-init pattern or a second emulator; the "$FF works / $00 breaks / but
   nothing reads it" signature smells like a masked read-uninitialized bug OR an
   emulator-specific interaction.
4. Only if a real ZTRAP collision is found: re-site ZTRAP (and re-run the runtime-zero
   test at the new address). Current evidence says the placement is fine.

The carve (the real funding work) is solid and committed; this is purely the poll-wiring
step.

## Update — independent static analysis (2026-07-24, agent)

A separate read-only source+binary audit confirmed all the eliminations above and added:

- **openMSX RAM default is the smoking gun.** The repack machine XML
  (`~/.openMSX/share/machines/C-BIOS_MSX1_EU_REPACK_DISK.xml`) has **no `<initialContent>`**
  → power-on RAM is openMSX's default fill (`$FF`). The "`$FF` works / `$00` breaks / but
  no zerobas code reads the region" signature is the exact fingerprint of a
  **read-uninitialized-RAM access masked by `$FF`** — and since it is in NO zerobas source
  and NO absolute load/store in any ROM (grep + opcode binary-scan both clean), the reader
  is **C-BIOS**, through a computed pointer or the stack, during **boot only** (consistent
  with runtime-zero being harmless — C-BIOS is done with the window by the prompt).
- **`$E200` is inside the ZTRAP span** (ZTRAP = `$E1D1..$E207`); C-BIOS provably writes
  `$E100`/`$E200`. Leading theory: a C-BIOS boot work-cell / scratch-stack in `$E1D1..$E21F`
  that C-BIOS reads after `init_ext_roms` returns; `trap_init` (run in `ier_done`) pre-zeroes
  it and corrupts C-BIOS's still-live boot scratch → garbage screen.
- **Disk ROM is clean**: its lowest work cell is `$E299` (`disk/equates.inc`), well above
  the span. Not involved.
- **Verified-free ZTRAP re-home candidates** (agent): the gap between the string temp top
  `$E3E8` and disk `WBUF` `$E560`, or above `FCH_CTX` `$EA00` — but **confirm boot-safety
  with a write-watchpoint over the chosen window across a full disk+string boot** before
  committing (the $E1D1 window looked "free" too).

## CORRECTED DIAGNOSIS (2026-07-24, after further bisection) — it is NOT ZTRAP

The RAM-collision / re-home theory above is **superseded**. Deeper bisection shows the
crash is a **deterministic page-1 CODE-LAYOUT bug**, unrelated to the ZTRAP RAM address:

- **Zeroing `$E1D1..$E21F` is irrelevant.** With the seam reverted to `play_service` (so
  `event_poll`/`trap_init` are assembled but NEVER executed — dead code) and NO `trap_init`
  call, just the `traps.asm` **include** (74 B of page-1 growth) **plus one extra byte** at
  ier_done → the merged machine still crashes at boot. The trap code never runs; it is pure
  page-1 layout.
- **Sharp 1-byte threshold.** Measured with `nop` padding at ier_done on top of the include:
  **+74 B PASS, +75 B FAIL** (each verified ×3–4, deterministic — not flaky; openMSX RAM
  default is a fixed fill). A single byte flips it.
- **Boundary crossing.** A `sym`-diff of the +74 (pass) vs +75 (fail) builds shows exactly
  **4 page-1 symbols cross a 256-byte (`$xx00`) boundary** at the threshold:
  `sgk_empty $48FF→$4900`, `ev_not $4AFF→$4B00`, `rp_lp $7AFF→$7B00`, `flb_no $7BFF→$7C00`.
  That is the fingerprint of a construct (jump/lookup table indexed low-byte-only without a
  high-byte carry, or self-modifying code) that breaks when its bytes straddle a page.
- Symptom is broad (garbage screen on *any* command incl. `?1234`), so the sensitive
  construct is in a hot/boot/console path, not a disk-only site.
- Merge is clean (`build_mainrom` reports only unreferenced C-BIOS overwrites; no clobber).

**This is a PRE-EXISTING latent fragility in the codebase, not a traps bug** — any page-1
addition landing at the wrong size would trip it. It has simply never been hit because prior
page-1 growth happened to land safely. It is invisible to the unit tests and the reloc
byte-identity gate (both pass); only the live merged-machine acceptance catches it.

## The real fix (needs focused disassembly, NOT a RAM re-home)
1. Find the page-boundary-sensitive construct: disassemble our OWN page-1 image around the
   4 crossing addresses (and their preceding tables), looking for a table read/dispatch that
   computes an address by `ld l,idx` / `add a,l` / `jp (hl)` with a **fixed high byte** (no
   `adc h,0`), or a self-modifying `ld (nn),a` whose `nn` low byte is computed. Two known
   `jp (hl)` sites: `bload.asm:130`, `files.asm:1494` (disk-path — likely NOT it since the
   crash is broad; check the console/print and statement-walk paths first).
2. Harden it (carry into the high byte, or `align` the table so it never crosses a page).
3. THEN wire in traps.asm normally (seam + trap_init at ier_done/run_prog). The ZTRAP RAM
   home at `$E1D1` is fine (runtime-zero test proved it); no re-home needed.

Reproduce the failing state: uncomment the `traps.asm` include in `main.asm`, point
`play_install` at `htimi_service`, add one `nop` at `ier_done` — `make string-acceptance`
fails; remove the `nop` — it passes.

## Crash forensics (2026-07-24, openMSX on the +75/failing build)

Traced the actual boot crash of the failing merged machine:
- Boot **reaches `show_title` ($4653) but never `repl` ($465A)** — it dies in `autoexec_run`
  (interp.asm:62, between them), i.e. **while loading/running a program at boot** (AUTOEXEC).
- Machine ends **stuck looping at PC `$4C9D`, inside `ev_f`** (the expression factor
  evaluator, `ev_f`=$4C63). Deterministic (same PC at 11 s and as a breakpoint).
- At the crash: **`IX = $4010`** — the eval token pointer is corrupted to a ROM address
  (`$4010` = the cartridge `init` / `SUBROM_ENTRY_BASE_P1`). `ev_f` does `ld a,(ix+0)` =
  **`$C3`** (a JP opcode read as a bogus "token") → wild dispatch → loop. `HL=DE=$004E`,
  `BC=$00F9`. Return address on the stack is **`$4273`** (inside the `ex_let` region, the
  `ex_*` `inc hl`/`jp do_*` trampolines at $4200+) → call chain is
  **`autoexec run → ex_let → eval → ev_f` with IX already garbage**.
- `event_poll` ($5A8F) is nested on the stack (the seam's ISR fired mid-run) but is NOT
  the cause — the crash also occurs with the seam reverted (event_poll never called), so
  it is pure layout. The ISR nesting is incidental.

**Two hypotheses for the next investigator (start here):**
1. **The disk/AUTOEXEC LOAD is broken by the shift** → a garbage program is loaded, so
   running it feeds `ev_f` a wild IX. Check whether AUTOEXEC.BAS's program text is valid
   in RAM under the shifted build. This would implicate the FAT/`fat_io` load path or the
   subrom_call stubs (incl. the new `fcbname`/`fatprim` marshalling shims) — look for a
   page-boundary-sensitive construct there.
2. **The eval/run path itself corrupts IX** under the shift. Find where `eval`/`ex_let`
   loads `IX` from the token pointer (`HL`) and why it becomes `$4010`; check `ev_not`
   ($4AFF→$4B00) and `rp_lp` ($7AFF→$7B00), the two hot-path boundary-crossers.

The `$4010` value is the strongest clue — it is exactly `SUBROM_ENTRY_BASE_P1` (a
subrom_call stub's `ld ix,SUBROM_ENTRY_BASE_P1+3*idx` with idx=0), OR the merged ROM's
`init`. Tracing what sets `IX=$4010` should pinpoint the construct.

## Lead #1 tested — DISPROVEN; crash is EARLIER (2026-07-24)

Re-traced on a fresh +1 build: `show_title` ($4653) is **entered but never returns**, and
**`autoexec_run` ($6B16) is never reached**. So it is NOT the AUTOEXEC load — the crash is
**in `show_title`, which is a subrom_call stub to the page-1 `title_tenant`** (the boot
banner, the FIRST tenant subrom_call at cold start). Execution then wanders into
error-handling code (`res_setptr`/`check_expr_errors` ~$444C) and hangs.

**The crash LANDING POINT varies by build** (one +1 build hangs in `ev_f`, another right
after `show_title`) — classic downstream chaos from a **wild jump / corrupted return**.
Chasing the landing PC is futile; the root is a **page-boundary-sensitive construct that
produces a wild jump early in boot, around the first tenant subrom_call**.

**Sharper next step (for a dedicated session): divergence analysis.** Boot the passing
(+74) and failing (+75) merged machines to the same point (bp at `show_title` $4653) and
single-step BOTH in lockstep, comparing PC/regs until they first differ — that first
divergence IS the buggy construct. Note: `subrom_call` itself is in the low region ($<4000$,
UNSHIFTED) so it is byte-identical between the two; the divergence must be in the shifted
page-1 caller (`show_title` stub) or a page-1 routine it reaches. Also worth checking: does
`show_title`'s stub compute `IX = SUBROM_ENTRY_BASE_P1 + 3*17` correctly in the +75 build,
and does the CALSLT to `title_tenant` return? (Watch the `$4010`=idx-0 vs `$4043`=idx-17
distinction — a wrong index would call the wrong tenant.)

**Net:** neither ZTRAP re-home nor the AUTOEXEC path is the fix. This is a latent page-1
layout fragility around the boot / subrom_call path, exposed by ~75 B of page-1 growth. It
needs the divergence analysis above, not more landing-point forensics.
