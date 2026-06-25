<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 architecture audit — a BIOS-agnostic disk ROM for C-BIOS

**Status: AUDIT + MIGRATION PLAN (rework DEFERRED to a separate signed-off effort).**
Method per user direction (2026-06-25): reason from the MSX-DOS-1 / disk-ROM ABI and
the already-captured CF-3300 oracle traces (`provider-oracle-scope.md` §8.40–8.68);
**no new C-BIOS experiments here**, and **no code changes** — this document is the
deliverable. Triggered by the clarification that **CF-3300 is the behavioural ORACLE,
C-BIOS is the prime TARGET, and any standards-compliant MSX is the goal**, plus the
observation that recent debugging had begun over-fitting our ROM to the CF-3300's
*proprietary main BIOS* (which is the oracle's environment, not the target's).

## 0. The mistake this corrects

We have been validating Tier-2 only inside `National_CF-3300_ZEROBASDISK` = the
**CF-3300 proprietary main BIOS** (`cf-3300_basic-bios1.rom`) + our `build/disk.rom`.
That environment *tolerates* main-BIOS shortcuts that a genuine disk ROM must not take,
so it both (a) masks BIOS-dependence and (b) tempted instruction-level "make ours match
stock" debugging — which is matching the **CF-3300 BIOS**, the wrong success criterion.
The genuine target is C-BIOS; the genuine criterion is "boots real MSX-DOS to `A>` on
C-BIOS (and any compliant BIOS)."

## 1. The two interfaces (the load-bearing distinction)

A genuine MSX disk ROM sits between **two** interfaces with **opposite** portability
rules. Conflating them is the root of the drift.

### Interface A — disk-ROM ↔ MSXDOS.SYS / COMMAND.COM  (BIOS-INDEPENDENT, layout-fixed)
The DOS we load (`MSXDOS.SYS` + `COMMAND.COM`, from the DOS disk) is proprietary and
**hard-codes specific disk-ROM addresses** — e.g. COMMAND.COM's `CD 54 54` immediate
call to CONOUT (§8.67), the 21-entry de-facto-standard kernel surface at `$41xx–$77xx`
(§8.41/8.49), the `$F365` page-3 jump table the disk ROM builds (§8.57). Per our
established cross-vendor finding ([[msx-diskrom-shared-kernel]]), **~2/3 of every MSX
disk ROM IS this shared MSX-DOS-1 kernel** — the BDOS/kernel lives in the *disk ROM*,
not on disk; `MSXDOS.SYS` is a small disk-resident bootstrap that links to it.
- **Rule:** our ROM must MATCH this layout/contract (this is exactly fork (a),
  §8.47 — "faithful relocation"). It is **the same regardless of main BIOS**, because
  we always load the same DOS image. **So all of M3–M8's kernel-veneer + work-area work
  is correct and not BIOS-specific.** Reimplement *contracts*, never the proprietary
  bytes of MSXDOS.SYS/COMMAND.COM.

### Interface B — disk-ROM ↔ main BIOS  (must be BIOS-AGNOSTIC)
The disk ROM's kernel, to do its job, calls main-BIOS services: CHPUT (`$00A2`), the
interrupt handler KEYINT (`$0038` in the main ROM), the inter-slot primitives
(RDSLT/WRSLT/CALSLT/ENASLT), and reads the slot work area (EXPTBL `$FCC1`, SLTTBL
`$FCC5`, hooks `$FD9A`/`$FD9F`). On the CF-3300 these are CF-3300 BIOS code; on C-BIOS
they are C-BIOS code at the **same documented entry points / work-area cells**.
- **Rule:** reach them ONLY through documented, BIOS-agnostic entries and the slot work
  area — **never** a hardcoded slot, a fixed BIOS address, or an "it's already mapped"
  assumption. The `EXPTBL[0]`-driven CONOUT (M8b) is the correct template for *every*
  Interface-B interaction.

> **Everything that is currently wrong is on Interface B.** Note these bugs fail on the
> CF-3300 too (the boot doesn't reach `A>` there either) — they are not "CF-3300
> tolerances," they are simply non-standard shortcuts that limp along on paths that
> don't exercise them and break where they're needed (CONOUT, KEYINT).

### Interface B is the STANDARD — so drift across BIOSes is minimal-to-none
Interface B *is* the MSX1 BIOS standard. The CF-3300 main ROM, C-BIOS, and every
compliant vendor ROM all adhere to it, so **correctly-standard BIOS-agnostic disk-ROM
code behaves identically across all of them.** Three consequences:
1. The CF-3300 oracle's Interface-B behaviour (e.g. its `$DDAE`→KEYINT chaining, O-2)
   **is the standard behaviour** — derive the *standard contract* from it and trust it
   ports. (Same "contracts, not bytes" rule: derive the contract, never the CF-3300
   *specifics* — the `$DDAE` address, a byte sequence, a proprietary quirk.)
2. Interface-B fixes validated on the CF-3300 standard environment **port to C-BIOS by
   construction**. So C-BIOS is a *confirmation cross-check*, not a development
   prerequisite — which lowers the urgency (not the value) of A-4.
3. The over-fitting risk therefore narrows to matching CF-3300 *specifics* rather than
   the standard contract — the same discipline, now applied to Interface B.
Residual caveat: C-BIOS is a *faithful but not 100%-complete* reimplementation, so the
confirmation run still earns its keep by distinguishing genuine C-BIOS gaps from our
bugs.

## 2. The disk-ROM ↔ MSXDOS.SYS boundary (what we can settle now)

Best reading from spec + traces (confidence noted):
- **Disk ROM owns** (HIGH confidence): the `$4000–$7FFF` resident (signature, INIT,
  H.PHYD hook, the `$4010` driver table, the shared MSX-DOS-1 kernel surface), and it
  *builds* certain page-3 work-area structures (the drive-A DPB at `$F195`, the `$F365`
  jump table §8.57, the `wa_seg` subslot hooks §8.59).
- **MSXDOS.SYS owns** (MEDIUM confidence): its own ~1.9 KB relocated high-RAM image
  (`$D300–$DC7F`, incl. the `$DDxx/$DExx` inter-slot/interrupt handlers, §8.53) and —
  this is the open question — most likely the **page-0 DOS RAM environment**: the
  `$0038→$DDAE` interrupt vector, the RAM inter-slot routines, and the `$003B–$0054`
  slot-select helper (stock page 0 has all of these; §8.45/8.68).
- **COMMAND.COM owns** (HIGH confidence): the `$0100+` TPA, and at startup it **rebuilds
  page 0 with its own vectors** (`$0038→$0C3C`) — observed byte-identical on ours and
  stock at the banner phase (§8.68), which means our early page-0 vectors are transient
  and overwritten.

**Consequence for `lay_page0_env`:** if the page-0 DOS environment is MSXDOS.SYS's (and
then COMMAND.COM's), then our disk ROM installing `$0038→int_h` + its own `$000C…$0030`
inter-slot vectors is at best a **transient boot-bridge** construct and at worst
**redundant/interfering**. The one thing it must not do is leave a *broken* Interface-B
mechanism in place that the bridge (or an early interrupt) depends on. (Open item O-1.)

## 3. Audit of the current design

| Component | Verdict | Why |
|---|---|---|
| Kernel-veneer surface `$41xx–$77xx`, work-area builders, `k_47B2` loader, CONOUT layout at `$5454` | **KEEP** | Interface A — fixed by the loaded DOS, BIOS-independent. Correct. |
| CONOUT inter-slot CHPUT via `EXPTBL[0]` (M8b) | **KEEP — template** | Interface B done right; the pattern to copy. |
| `int_h` (`$0038`) = `push af / in ($99) / pop af / ei / ret` | **REWORK** | Ack-and-return only; does **not** chain to the main-BIOS KEYINT, so no H.TIMI/H.KEYI/keyboard/JIFFY. Almost certainly the M9 runaway's real cause. Fix is BIOS-agnostic: chain to KEYINT via `EXPTBL[0]` (CONOUT pattern). |
| `rdslt_h/wrslt_h/calslt_h/enaslt_h` (lay_page0_env handlers) | **REWORK or REMOVE** | "Operate on currently-mapped memory, no real inter-slot switch" (§8.4) — a CF-3300-environment shortcut. CONOUT already had to bypass `calslt_h` and switch slots itself: proof the shortcut is wrong, not a one-off. Must be real inter-slot routines, or removed if MSXDOS.SYS owns the page-0 env. |
| `lay_page0_env` existing at all | **RE-EXAMINE (O-1)** | May be doing MSXDOS.SYS's job; possibly only needed as a transient bridge, possibly removable. Decide once O-1 is resolved. |
| Validating only on the CF-3300 BIOS | **CHANGE** | Move the success criterion to C-BIOS; keep CF-3300 stock as the Interface-A/behavioural oracle. |

## 4. Open items to resolve before rework

- **O-1.** Who installs the page-0 DOS RAM environment (`$0038` vector + inter-slot
  routines + `$003B–$0054` helper) — MSXDOS.SYS, the disk-ROM kernel, or COMMAND.COM?
  Settles whether `lay_page0_env` should exist. (Resolve from the MSXDOS.SYS boot
  sequence + a write-attribution trace like §8.57, when rework is greenlit.)
- **O-2.** Exact KEYINT chaining contract: does the DOS `$0038` RAM vector call the main
  ROM's KEYINT by inter-slot (`EXPTBL[0]`, IX=`$0038`), and what register/IFF/stack
  state must our `int_h` present? (Derive black-box from the stock `$DDAE` path.)
- **O-3.** Which Interface-B entries does the disk-ROM kernel actually use, enumerated,
  so each can be made `EXPTBL`-driven. (CHPUT done; KEYINT, and any CALSLT/ENASLT/RDSLT
  the kernel relies on.)

## 5. Migration plan (DEFERRED — each step its own signed-off milestone)

1. **A-1 (analysis).** Resolve O-1/O-2/O-3 from spec + oracle traces. Output: the exact
   Interface-B surface + the page-0-env ownership decision.
2. **A-2 (int_h).** Make `$0038` chain to the main-BIOS KEYINT, BIOS-agnostically
   (`EXPTBL[0]` inter-slot, CONOUT template). Expected to clear the M9 runaway.
3. **A-3 (inter-slot handlers).** Replace the mapped-memory shortcuts with real
   inter-slot routines, **or** remove `lay_page0_env` if O-1 says MSXDOS.SYS owns the
   env. Keep diffs reversible.
4. **A-4 (C-BIOS confirmation).** Stand up a `C-BIOS_MSX1 + build/disk.rom` machine
   config and confirm "boots real MSX-DOS to `A>` on C-BIOS." Per §1, standard-
   conformant Interface-B code ports by construction, so this is a *cross-check* (catch
   genuine C-BIOS gaps vs. our bugs), not a gate that blocks development on CF-3300.
5. **A-5 (resume).** Continue filling the Interface-A kernel-veneer contracts (M9+)
   under the corrected, BIOS-agnostic, C-BIOS-validated regime.

## 6. What is NOT invalidated

The Interface-A work (M1–M8: the veneer scaffold, the work-area builders, the loader,
the CONOUT *layout*, the byte ledger) stands — it is fixed by the loaded DOS and is
BIOS-independent. The CONOUT *implementation* (M8/M8b) is the correct Interface-B
template. Tier-1 Disk-BASIC is unaffected throughout. The rework is scoped to the
Interface-B plumbing (`int_h`, the inter-slot handlers, `lay_page0_env`'s role) plus
moving validation to C-BIOS — not a teardown of the kernel work.
