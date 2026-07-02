<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 review queue — decisions taken without per-step sign-off

Running log for the **autonomous-span** working mode (2026-06-25). During a span I
chain `characterise → spec → implement → validate → commit` across milestones
without bouncing back; every judgment call I'd normally have asked about lands here.
When the user is back we do **one batched review** of the open entries, then I
archive them (move the resolved block under "Archived").

**Hard-stops (I pause the span and wait):** a design fork that hinges on user taste;
a clean-room legitimacy call I'm unsure of; anything irreversible/outward-facing;
a regression I can't get green or a blocker I can't crack; a scope surprise that
changes a signed-off plan.

Entry format: **[Mx.y / §8.zz]** what I decided · why · alternative · confidence ·
undo. Newest first.

---

## Open (awaiting next sync)

**[M20 / bytes-free footer · HARD-STOP after user go-ahead — the §2.4 exit-contract hypothesis is
FALSIFIED, scope surprise, reporting rather than improvising]** User signed off on the spec below and I
built it (veneer + `getalloc_body` computing A/BC/DE/HL exactly per spec §4.2). Host unit-harness
(`tests/msxtest.py` Z80, no emulator) confirms the SCAN ALGORITHM is byte-correct: fed the REAL test.dsk
FAT bytes it returns `HL=$016F`(367) — exactly right. In openMSX, register-captured immediately before
`getalloc_body`'s own `ret` (`capture --at 0x7A8E`, the exact `ret` opcode address) ALSO shows the correct
`A=02 BC=0200 DE=02C9 HL=016F`. **But by the BDOS exit point `$C6C5` it has become `HL=$0202`(514), and a
falsify-first sentinel swap (forced `HL=$BEEF` right before `ret`) changed NOTHING at `$C6C5` — still
`0202`.** ⇒ the kernel/COMMAND.COM code between our `ret` and `$C6C5` does NOT use our returned HL at
all; something else independently supplies the free-cluster count. Screen-arbiter confirms the real
effect: footer prints `526336 bytes free` (514×2×512) instead of `375808` — WORSE-looking than the
pre-fix `0`, though actually just as broken.
· **Root cause of the false spec (public-doc reconciliation):** map.grauw.nl's MSX-DOS `_ALLOC`
($1B) spec (fetched this span) documents THREE more exit fields I hadn't accounted for: `IX` = pointer
to DPB (already fine — we never touch IX, and it's the pre-existing `$F195`), and **`IY` = pointer to the
first FAT sector**, with an explicit MSX-DOS-1-specific note: *"unlike MSX-DOS 1, only the first sector
of the FAT may be accessed from the address in IY [in DOS 2]"* — implying DOS-1's IY exposes MORE than
one sector, i.e. the FULL resident FAT (matches the M20 spec §2.3 finding that stock's `$1B` window reads
its resident `$E595` FAT buffer 81 times via PCs `$4209`/`$420B` — that IS the downstream free-space
PRINT logic scanning the buffer FROM IY, not our handler's own internal count). **Our `getalloc_body`
never sets IY at all** (leaves it at whatever stale value COMMAND.COM last had, `$DC5B` in this run);
downstream code scans garbage from there and gets a garbage-but-plausible 514. The HL="free clusters"
register IS documented, but empirically this COMMAND.COM build ignores it in favour of its own IY-buffer
scan for the DIR footer specifically (confirmed by the sentinel test, not a guess).
· **Scope surprise (why this is a hard-stop, not an improvisation):** the signed-off design was "compute
the count, return it in 4 registers" — no buffer/pointer semantics. The ACTUAL fix additionally needs a
CONTIGUOUS resident-FAT buffer sized to the volume's real FAT (`secPerFAT` sectors — 3 on test.dsk =
1536 B, but volume-dependent, so potentially larger on other media) that `getalloc_body` populates AND
that stays valid for the caller's scan, plus `IY` wired to point at it. That's a new small buffer-
management concern (size, RAM budget, lifetime) beyond "one self-contained register-only call" —
exactly the kind of scope change [[spec-before-implementation]] says needs a fresh look, not a
solo expansion mid-span.
· **Action taken:** reverted the uncommitted asm (`git checkout -- disk/kernel.asm`) back to the
spec-only commit `959725b`; rebuilt + re-ran `make unit-test` (19/19 green) to confirm a clean baseline.
Nothing broken is left in the tree. Reporting to the user for a revised design decision before continuing.
· **Confidence:** HIGH that IY/buffer is the missing piece (direct falsification test, not inference);
NOT yet pinned exactly how large the buffer must be or whether IY must point at a NEW buffer we own vs.
some existing one repurposable for this.

**[M20 / bytes-free footer · CHARACTERISATION+DESIGN, ORIGINAL SPEC — see hard-stop entry above for what
changed after user go-ahead]** Pinned
black-box (no stock code decoded): `DIR`'s free-space footer is the documented BDOS `$1B` GETALLOC,
dispatched by the kernel to page-1 entry `$505D`; on ours that's `$00` NOP-pad sliding into the existing
`$50A9` stub (identical shape to M13/M17/M18/M19's un-wired `$50xx` entries). Exit contract pinned at
`ret=$C6C5`: `A`=sectors/cluster, `BC`=bytes/sector, `DE`=total data clusters, `HL`=free clusters
(stock `02/0200/02C9/016F` → COMMAND.COM computes `367×2×512=375808`; ours gets stub garbage → `0`).
· **Design:** new `getalloc_body` (free tail) wired via a 3-byte `jp` veneer at `$505D` (existing `$00`
pad, net-zero), reusing `fat_total_clusters` + a SIBLING of `fat_alloc_cluster`'s `$000`-entry scan
(count-all instead of stop-at-first) — must leave the write-path `fat_alloc_cluster` byte-unchanged.
Must read the FAT itself rather than depend on stock's resident `$E595` buffer (ours never populates it).
· **Confidence:** HIGH on the entry point + contract (byte-identical `$1B` entry regs ours==stock;
independent FAT-buffer decode cross-checks 367 free clusters = 375808). Exact exit-register load order
is flagged as the first falsify-first build step (spec §8.1), not yet built.
· **Out of scope, deliberately not folded in:** the 82 spurious per-file `C=05 LSTOUT` calls / `$75A5`
divergence (BDOS n=63 fork) — confirmed a separate, cosmetically-absorbed COMMAND.COM branch difference
that does NOT block `$1B`/`$505D`. Left for later characterisation.
· **Sign-off needed:** per [[spec-before-implementation]], new-routine class (like M19) — implementation
gated on explicit user go-ahead on [tier2-m20-spec.md](tier2-m20-spec.md). Nothing committed by the
characterisation span except the spec doc itself.

**[M19 / runtime dir-search (BDOS SFIRST $11 / SNEXT $12) · USER-SIGNED-OFF SPEC, not self-approved]**
Landed the fix for MSX-DOS `DIR` (was: hung forever on a blank screen — the un-wired `$4FB8`/`$5006`
dir-search entries NOP-slid into the `$50A9` stub, phantom "found" forever). Wired `$4FB8`→`sfirst_body`,
`$5006`→`snext_body`, `$5058`→`setdta_cache_body` (net-zero veneers in the descending ds-anchor chain,
free-tail bodies); new work cell `BDOS_SRCHIDX` ($E55E); reuse `fat_mount`/`fat_find` root-dir walk +
`name_cmp_wild` (the `?` wildcard). **RESULT: DIR lists every file + `41 files` + fresh `A>`,
byte-identical to stock, no hang.** Commits `45fd9be` (specs), `5225a29` (impl), docs-update follows.
· **Sign-off:** the user explicitly signed off the M19 spec ([tier2-m19-spec.md](tier2-m19-spec.md)) —
this was NOT self-approved-by-veneer-precedent (it is a substantial new routine, OI-3-class effort).
· **Judgment calls made this span (all pinned black-box, no stock CODE decoded — the falsify-first path
the spec §2.4/§4.1 deferred to build):**
  (i) **Runtime DTA source = `($F23D)`.** The spec flagged this open. Pinned: `$F23D` is a disk-work-area
  DTA cache stock's SETDTA-time entry `$5058` writes and stock's SFIRST reads (PCs `$4FCC`/`$4FEF`); on
  ours it was never written (found entry went to a garbage DTA → "File not found"). Wired the ALSO-un-wired
  `$5058` entry (found via `callwatch --in-func 0x1A` → ours slid into the `$50AD` stub; entry `DE=$D403`
  = DTA) to `setdta_cache_body` = `ld ($F23D),de`. This is a 4th same-class entry beyond the specced
  `$4FB8`/`$5006` — a scope addition I took because it is the mechanically-required companion (SFIRST is
  useless without the DTA). Confidence HIGH (DIR renders byte-perfect). Undo: revert `5225a29`.
  (ii) **Found-entry DTA layout = the MSX-DOS "found FCB"** (drive@0, name@1..11, attr@13, time/date/
  clus/size@23..32), NOT a verbatim 32-byte dir-entry copy. Pinned by a `readwatch` of the DIR formatter's
  DTA reads (attr@+13, size@+29..32) + a byte-diff vs stock's DTA. My first cut (raw copy, attr@+12)
  mis-set COMMAND.COM's label filter → alternating-garbage rows + wrong count; the +13 layout fixed both.
  (iii) **NO attribute filter** in the scan (return volume-label/subdir entries too) — pinned: stock's
  SFIRST returned the `SandStone` volume label (attr $28) as match #1; COMMAND.COM does the `nn files`
  filtering. (iv) **Exit A=$00 found/$FF exhausted** (published contract) — confirmed by the listing
  terminating + rendering. (v) **DIR issues an all-`?` FCB** — verified (`$005C` = `80 3F×11`).
· **HARD-STOP I hit, reporting rather than improvising — the `nn bytes free` footer.** Ours prints
`0 bytes free`, stock `375808`. This is NOT the dir-search and NOT a regression: it is a SEPARATE
free-cluster FAT-scan routine the M19 design (spec §4-§6) never characterised. Evidence: stock issues
10 `$4010` DSKIO during DIR (ours 0 — the ~3 extra are the free scan); ours' COMMAND.COM diverges at
BDOS n=63 (stock SETDTA-to-next-file; ours a spurious `C=05 LSTOUT`) and mis-routes to the `$75A5`
`ret`-stub (stock never hits `$75A5` during DIR) — a value ours supplies as `0` (free-cluster count)
cascades the wrong branch. The spec's acceptance §7.1 lists `375808 bytes free`, so the spec conflated
"DIR lists files" with "DIR's free-space line" — the latter needs its own routine (entry point NOT yet
pinned; `$75A5` is a divergence symptom, not the entry). Per the guardrails I did NOT improvise a whole
new free-scan + dispatch-RE mechanism; **flagged for its own spec + sign-off** (Next action item 1). We
own the primitives (`fat_alloc_cluster`/`fat_total_clusters`) so it should be a small routine once the
entry/contract is pinned. · **Confidence:** dir-search HIGH (5/6 acceptance criteria fully green; the
6th — screen — matches stock in every line except the free-space footer). · **Undo:** revert `5225a29`
(+ its docs) restores the pre-M19 hang; `BDOS_SRCHIDX`/`$F23D` writes are DOS-phase-only, no Tier-1 reach.

**[OI-3 / screen-clear · USER-SIGNED-OFF, not self-approved]** Landed `dos_clear_screen` (runtime.asm
free tail, first action in `dos_handoff`): FILVRM `$0056` fills the SCREEN-1 name table (`$1800`, 768)
with spaces via the `pg0_mainrom_in`/`out` inter-slot path (same as `conout_body`'s CHPUT), then homes
the cursor (`$F3DC`/`$F3DD`:=1) — reproduces stock's characterised direct name-table fill + cursor-home
so ours' `A>` lands at ROW09 on a cleared screen, byte-for-byte matching stock.
· **Sign-off:** this was NOT self-approved-by-precedent — it is a different-shaped fix from the M13–M18
`$50xx`-veneer / work-area-cell class, so per [[spec-before-implementation]] it got its own spec
([tier2-oi3-spec.md](tier2-oi3-spec.md)) and **explicit user go-ahead** before implementation, with BOTH
open items resolved by the user as the spec's own recommendation: (i) **STAY-DI** inside the clear (no
`ei`; caller owns IFF across the page-0-RAM handoff, matching the init.asm invariant); (ii) **accept the
data-disk pre-clear side effect** (a bootable data disk like test720.dsk gets its screen blanked before
`BOOT_ENTRY`; Tier-1 checks DSKIO/BLOAD/FILES correctness, not screen content — no extra gate).
· **Alternatives rejected in the spec:** INITXT `$006C` (mode-switches to SCREEN 0), INIT32 `$006F`
(full SCREEN-1 re-init — colour/pattern side effects); raw VDP fill kept only as a fallback. FILVRM is
the surgical AND BIOS-agnostic choice (does only what stock does).
· **Confidence:** HIGH — all 7 spec §6 acceptance criteria pass with concrete numbers (screen
ours==stock; CSRY/CSRX `01 01` was `0F 01`; BDOS 27/27 aligned zero divergence; IX=`$F195` at `$0200`;
steady-state stable no storm; unit-test 19/19; `disk.rom` 16384 B, 3-pass object verified).
· **Undo:** revert commit `dc2ac8d` (single self-contained 35-line addition in the free tail; no
canonical-address shifts, so a clean revert). **This entry CLOSES the Tier-2 DOS-boot-to-`A>` goal.**

---

## Archived

Reviewed & re-levelled entries (M5–M10 history) have been split into
[tier2-review-archive.md](tier2-review-archive.md) to keep this live board lean.
Only **Open** (awaiting next sync) lives here.

