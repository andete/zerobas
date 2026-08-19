# Interrupt-traps T1 — resident-poll wiring BLOCKED (2026-07-24)

## ✅✅ RESOLVED (2026-07-24, commit c355c1d) — H.TIMI page-1-safety guard landed

The blocker is **fixed and committed**. `play_install` now routes H.TIMI through a PAGE-0-resident
`htimi_guard` (basic/subromcall.asm, 13 B) that only falls through to `play_service` when main-ROM
owns page 1, and skips PLAY one frame when a sub-ROM page-1 tenant owns it. Spec (signed off):
[spec-traps-t1-htimi-page1-safety.md](spec-traps-t1-htimi-page1-safety.md). Verified: the whole
crash band (repack-only shift N=0..135) now PASSES; diskbasic 34/34 + string PASS at N=0 and mid-band
N=74; unit-test 51/51; play-trace-acceptance PASS (incl. its di_safety page-1-tenant case). The
sections below are the diagnosis that led here (kept for the trail). **Next: wire `basic/traps.asm`**
(spec §6 follow-on) — the seam is now safe.

## ✅ ROOT CAUSE FOUND (2026-07-24, second span) — it is the H.TIMI→play_service seam, NOT a layout construct

**Everything below the horizontal rule is the original investigation and is now SUPERSEDED**
(the "page-1 layout construct" / "crossing symbols" / ZTRAP theories were all dead ends —
see "Why the earlier framing was wrong" below).

### The mechanism (empirically pinned, decisively proven)

The crash is a genuine **pre-existing architecture flaw** in the PLAY-servicer H.TIMI seam
vs the page-1 sub-ROM tenant model. It has nothing to do with traps and nothing to do with
a byte-alignment-sensitive construct. Chain:

1. Boot: `init` → `show_title` → **`autoexec_run`** (cload.asm) probes for AUTOEXEC.BAS.
2. `autoexec_run` → `fat_mount`/`fat_find` → `subrom_call` **FATPRIM** (`SUBROM_IDX_FATPRIM=12`,
   a **page-1** sub-ROM tenant). While it runs, CALSLT has switched page-1 to the **sub-ROM**;
   main-ROM page-1 is **paged out**.
3. Inside the FATPRIM tenant, `dskio_calslt` (fat-prim-body.inc) does `call CALSLT` to the disk
   ROM's **DSKIO** ($4010) with **no DI guard**. DSKIO enables interrupts.
4. An interrupt fires. The BIOS ISR ($0038, page-0, still mapped) runs the **H.TIMI** hook,
   which `play_install` set to **`jp play_service`** — and `play_service` lives in main-ROM
   **page-1, which is paged out**. The CPU executes whatever sub-ROM bytes sit at
   `play_service`'s address → wild jump → boot crash (garbage screen, then a downstream
   infinite RESUME loop at `res_setptr`/`ev_f`/a DSKIO loop with garbage return addresses —
   all the "landing points" the first span chased are this downstream chaos).
5. `play_service`'s address **shifts with any page-1 growth**. At the shipping size it lands
   on *survivable* sub-ROM bytes (boot is green); a carve/insert that shifts it onto *fatal*
   bytes trips the crash. Hence the **bounded** failure band — see the sweep below.

The design comment at `main.asm:206` ("page-1 tenants run DI so the ISR never fires with
page 1 switched out") states the intended invariant. **FATPRIM violates it** by CALSLTing an
interrupt-enabling DSKIO.

### Proof (all on the clean, guarded repro — see "Clean repro" below)

- **Disable the H.TIMI hook** (comment out `call play_install` in `ier_done`) at the failing
  size → **PASS**. The seam is the cause.
- **Skip `show_title`** (the title tenant, also page-1) at the failing size, seam ON → still
  **FAIL**. So the culprit tenant is **FATPRIM in `autoexec_run`**, not the title banner.
- **CALSLT trace divergence** (bp at $001C, log IX/IYh/ret): both boots make the disk-INIT and
  title-tenant (idx17) CALSLTs identically; then the healthy build calls **FATPRIM (idx12,
  ix=4034 iyh=8B)** and the crash build **skips it** and falls into a DSKIO loop with a garbage
  return ($5926 = mid-instruction, not a real call site). The wild jump is at/just after the
  first FATPRIM tenant call.

### Clean repro (use THIS, not the contaminated one below)

Instrument with a **repack-only** page-1 shift and a bas_tokenise-free oracle:
- In `basic/initext.asm` at `ier_done`, inside the `IF ROM_BASE < $4000` block, add
  `defs N,0` (N bytes of page-1 shift). **It MUST be inside the guard** — an unguarded `defs`
  also grows the byte-full **lean** cart, overflowing $8000, which makes `probes/disk/
  bas_tokenise.py`'s `pasmo --bin basic/main.asm` exit 1 and fails ~5 acceptance cases as a
  pure **build artifact** unrelated to the runtime crash (this artifact is what inflated the
  first span's "34/34 → 3/34").
- Oracle: `make diskbasic-acceptance-repack ONLY=FILES` (a live case, no `bas_tokenise`).
  Exit 0 / "1/1 verbs converged" = clean boot; "0/1" + garbage VRAM = the crash.
- Result: **N=0 → PASS. Band N∈[4,135] → FAIL (garbage boot). N≥136 → PASS again.**
  A ~132-byte-wide bounded window (single-byte edges are fuzzy — downstream landing chaos);
  it recovers because `play_service` clears the fatal sub-ROM byte-range. NOT overflow (guarded,
  page-1 ends at $7FED with room), NOT a RAM collision (no RAM symbol moves with N).

### The fix (design, not yet implemented)

`play_service` must be reachable **whenever the ISR can fire**, including while page-1 is a
sub-ROM tenant. The only home that is *always mapped* is **RAM** (page-0 low region is paged
out during page-0 tenants; page-1 during page-1 tenants). Mirror the existing `sub_int_template`
RAM trampoline (subromcall.asm): make `play_install` point H.TIMI at a **RAM-resident stub** that
either (a) **guards** — read the page-1 primary-slot field, and if it is *not* main-ROM, `ret`
without draining PLAY (a one-frame music skip during a rare tenant window is inaudible); or
(b) **swaps** — map main-ROM page-1 in, `call play_service`, restore the tenant's page-1 mapping,
then RETI. (a) is far simpler and sufficient. Either way it is the same class of fix as the
$0038 trampoline already in the tree. This also makes the future traps `event_poll`/`htimi_service`
seam safe for free (same H.TIMI path). **Spec + sign-off before implementing** (per workflow).

### Why the earlier framing was wrong

- "**Page-1 layout construct straddling a $xx00 boundary**": no such construct exists. Static
  audit found no self-modifying code (impossible in ROM), no unrelocated page-1 literals (reloc
  gate + grep clean), no low-byte-only address arithmetic (every `add a,l`/`ld l,a` site carries
  correctly and indexes RAM), no `inc l` table-walks. The "4 crossing symbols" (and this span's
  2/1) are **innocent labels** that merely happen to sit at $xxFF — every ±1 shift crosses a few;
  they are not the cause.
- "**ZTRAP RAM collision**": irrelevant — the crash reproduces with `traps.asm` fully absent,
  purely from page-1 growth + the (baseline) play seam.
- The "**34/34 → 3/34**" magnitude was **inflated by the lean-cart `bas_tokenise` build artifact**
  above; the genuine repack-only crash is real but was measured through a contaminated oracle.

---

## Original investigation (SUPERSEDED — kept for the audit trail)

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
   `jp (hl)` sites: `bload.asm:130`, `files.asm:1613` (disk-path — likely NOT it since the
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
  (interp.asm:100, between them), i.e. **while loading/running a program at boot** (AUTOEXEC).
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
