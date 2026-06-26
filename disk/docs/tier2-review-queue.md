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

**[DEFINING FINDING / 2026-06-26, commit TBD — the real blocker is the UNBUILT DOS WORK AREA, not
FOPEN or any single intercept. STRATEGIC CHECKPOINT.]** Followed COMMAND.COM's post-FOPEN branch
to ground: it does `ld a,($F338)` at $C26B; stock ($F338)=00, ours=$FF. Write-watch: stock writes
$F338=00 from PC=$57BE at t=3.80 (BOOT time, not during FOPEN); ours never writes it ($57BE is
`00` padding in ours). So the FOPEN $21 was a RED HERRING — the branch input is a boot-time-init
cell. Forcing $F338=00 alone did NOT fix it (and sent COMMAND.COM down a path that WROTE the disk
— mutated the /tmp copy, restored from canonical, repo clean) because one cell set amid an
uninitialised area is inconsistent. **Decisive probe (disk_probe_dosboot_wadiff.py): the whole DOS
work area $F100-$F3FF at COMMAND.COM entry — 462 of 768 bytes differ, ours almost entirely $FF.**
Stock holds there: executable RAM-resident routines ($F100-$F17C, $F327-$F33F), the DPB+drive
table ($F1A8+), the device-name table ($F21C "PRN LST NUL AUX CON"), the "COMMAND COM" FCB
structure ($F2B8), and the DOS pointer block ($F34D-$F37F). **Ours' disk ROM does NOT construct
the DOS work area during boot; stock's does.** That work area IS the disk-ROM-resident portion of
the shared MSX-DOS-1 kernel ([[msx-diskrom-shared-kernel]]). ∴ reaching A> is neither "fix FOPEN"
(fork A's first step) nor "intercept $0005" (fork B) — BOTH were scoped against a far smaller
problem. The true scope is "reproduce the disk-ROM's DOS-work-area construction" — a large,
multi-milestone sub-system (resident code + structures + pointers). Detail: tier2-workarea-map.md.
**This is a strategic checkpoint: the user should reassess the "reach A>" ambition with this in
hand** (treat the mapping as a documentation deliverable + pause, vs commit to the large build, vs
characterise the construction step-by-step). New probes: fopenoverride, wadiff (+ /tmp helpers).
No production asm written. · undo: n/a.

**[$D858 BLOCKER ROOT-CAUSED + STRATEGIC SCOPE REFRAME / 2026-06-26 — HARD-STOP for a sync.
The $D858 loop is COMMAND.COM's prompt loop spinning because the kernel's FOPEN of AUTOEXEC.BAT
returns the WRONG code; the true scope is "reproduce the shared disk-ROM BDOS kernel", not one
veneer.]** Five anchored differential probes (all new, committed), each ours-vs-stock from the
boot anchor:
- **entry0100seq** — ours runs MSXDOS.SYS at $0100 (b0102=02) THEN COMMAND.COM (b0102=05), SAME
  structure as stock. The standing "ours skips MSXDOS.SYS init" hypothesis is **REFUTED**.
  COMMAND.COM entry (HIT2) is byte-identical to stock (BC=HL=1A00 IX=F195 IY=DC5B SP=DC00). Only
  MSXDOS.SYS-entry (HIT1) differs: IY (ours 0314 vs stock C0AB) + AF flags (0144 vs 0142).
- **conoutstream ($5454)** — ours prints the **full banner byte-identically** (53 chars
  "..MSX-DOS version 1.03..Copyright 1984 by Microsoft..", same ret=$0320/HL=DD0E/DE seq). The
  "blank screen / garbage CONOUT" reading was INCOMPLETE: banner is perfect; garbage ($00/$80,
  ret=$D88A) only starts AFTER COMMAND.COM launches.
- **bdosseq** — first BDOS divergence is call **n=3**: n=1 STROUT + n=2 FOPEN are byte-identical
  on both, then stock→STROUT(ret CBA6) vs ours→SELDSK(ret C30A). Ours then loops
  CONOUT/CURDRV/CONOUT/CONOUT/BUFIN forever (the $D858 loop = COMMAND.COM's prompt loop; BUFIN
  never blocks so it re-prompts endlessly).
- **fopenresult** — the FOPEN (fn $0F) is on **AUTOEXEC.BAT** (FCB at $D62F, identical entry).
  Result: **stock A=$FF (not-found), ours A=$21**. COMMAND.COM tests A==$FF ("no AUTOEXEC → go to
  prompt"); ours' $21 sends it down the wrong branch → spin. (Note: our disk-ROM bdos_open DOES
  return $FF correctly — but COMMAND.COM uses the KERNEL's BDOS via $0005, not our bdos_entry.)
- **fopenromcalls** — brackets that one FOPEN, logs every page-1 ($4000-$7FFF) disk-ROM entry the
  kernel invokes. **Divergence at the FIRST entry, $4462** (both enter with identical
  A=21/BC=0/DE=DA40/HL=C284): stock runs a **144-entry directory search** ($4462→$4411→$5604→
  $425D→$44DE→$4558→DSKCHG $4013→$607B→$434B dir-scan→DSKIO $4010→…) ending A=$FF; **ours bails
  after 1 entry** (A=$21 passes through). Our ROM at $4462 = `ld ($E299),a; ret` (unrelated FDC
  code), NOT a BDOS veneer.

**STRATEGIC FINDING (the reframe).** The MSX-DOS-1 **file-ops BDOS** (FOPEN, directory search,
file read) is implemented **inside the disk ROM** — the shared kernel (~2/3 of every MSX disk
ROM, [[msx-diskrom-shared-kernel]]). MSXDOS.SYS is the thin loader on top; for file ops its
relocated stub pages the disk ROM into page 1 and CALLs canonical addresses ($4462, $4411, $5604,
$425D, $44DE, $607B, $434B, $760E, $764D, …). Our 14 veneers cover only the **COMMAND.COM-LOAD**
subset; genuine DOS operation calls the **rest of the shared BDOS kernel**, which in our ROM is
unrelated FDC/DSKIO code, ds-padding, or bare-`ret` stubs (e.g. k_607B). So reaching `A>` is NOT
a one-veneer fix — it requires reproducing the shared disk-ROM BDOS contracts (dir/file/FAT) at
their canonical page-1 addresses. The 144-entry FOPEN chain is the first concrete map of it.

**HARD-STOP — FORK for the user (a scope surprise that changes the signed-off "fork-a" plan,
sized from the load path only):**
  (A) Continue faithful per-canonical-address reproduction — reproduce the shared BDOS kernel
      contracts ($4462 + its chain) at their fixed addresses (large but mechanical/harness-driven;
      most faithful to the layout-fixed Interface A).
  (B) Intercept higher — route whole BDOS functions (FOPEN…) to our existing bdos_entry/bdos_open
      (which already returns $FF correctly), instead of reproducing each fine-grained address.
      Smaller, but changes the interface model and must not break the kernel's internal BDOS use.
  (C) Characterise more first (e.g. map the full set of canonical BDOS addresses the kernel calls
      across FOPEN/dir/read) to size A precisely before committing.
· No code written (characterise-before-code held). Tier-1 untouched (probes only, no asm/build
change). New probes: entry0100seq, conoutstream, bdosseq, fopenresult, fopenromcalls. · undo: n/a.
  **>> USER CHOSE (C) map-scope-first. DONE 2026-06-26 → disk/docs/tier2-bdos-scope.md.** FOPEN
  (not-found) path = 23 distinct canonical disk-ROM addresses, only 2 covered (DSKIO $4010 /
  DSKCHG $4013), 21 to build (9 collide w/ our FDC-DSKIO code, 7 bare-ret stubs, 5 ds-pad); full
  DOS adds more. $0005=JP $D606 (kernel BDOS dispatch, identical ours/stock). **RECOMMENDATION:
  fork B** (re-point $0005→our bdos_entry at the documented BDOS ABI boundary): cleaner clean-room,
  bounded/finite vs A's open-ended per-address reproduction, reuses our existing disk BDOS (our
  bdos_open already returns the $FF this blocker needs). Next: A-vs-B decision, then (if B)
  tier2-bdos-spec.md before any asm. Risks for B catalogued in the doc §4.
  **>> USER CHOSE FORK B (2026-06-26). Viability gate PASSED** (disk_probe_dosboot_bdoscallers.py:
  every $0005 caller is COMMAND.COM, ZERO in the kernel $D606-$DDFF → redirecting $0005 is safe).
  **Spec drafted: disk/docs/tier2-bdos-spec.md (DRAFT, awaiting sign-off before asm).** Mechanism:
  k_47B2 overwrites $0005→our page-0 RAM trampoline → bdos_entry; extend bdos_entry with the
  startup console fns ($02/$06/$09/$0A/$0E/$19/$2A) on top of the disk fns we have. 5 open sign-off
  items in spec §5 (milestone scope, SDATE stub, BUFIN fidelity, trampoline location, clean-room
  confirm). No asm yet (spec-before-implementation).
  **>> PRE-IMPLEMENTATION VALIDATION OVERTURNED THE FORK-B PREMISE (2026-06-26, commit TBD) —
  HARD-STOP, fork re-opened.** Before writing any asm I cheaply tested the core fork-B assumption
  ("intercept FOPEN → our bdos_open returns $FF → COMMAND.COM unblocks") with register-override
  experiments (disk_probe_dosboot_fopenoverride.py): forced the kernel FOPEN return at $C24E to
  stock's EXACT state — A=$FF (expt2), then AF=$FF45 + HL=$00FF (all other regs already identical
  to stock: BC=0 DE=D64F IX=F195 IY=DC5B SP=D600). **Result: COMMAND.COM STILL mis-branches**
  (next call SELDSK ret=$C30A, not stock's STROUT ret=$CBA6) and still spins. ∴ **COMMAND.COM's
  post-FOPEN branch is NOT register-conveyed — it reads WORK-AREA MEMORY that stock's full 144-
  entry FOPEN populates and our bailed-at-$4462 FOPEN never writes.** A lightweight register-
  contract intercept is therefore INSUFFICIENT; the premise "our bdos_open already returns the $FF
  this blocker needs" was wrong (the value isn't the branch input). Implications: (i) the kernel's
  file machinery must ACTUALLY RUN to build the work area (favours fork A: reproduce the $4462
  chain), or (ii) a fork-B BDOS must additionally populate the exact work-area cells COMMAND.COM
  reads (converges toward A's effort). Recommend ONE more cheap characterisation — identify the
  specific work-area address COMMAND.COM reads between $C24E and its branch (read-watch /
  state-diff) — to decide A-vs-B on evidence before committing. No production asm written
  (validate-before-build held). New probe: fopenoverride. · undo: n/a.

**[$47B2 RETURN CONTRACT DONE / 2026-06-26, commit 9573a4c — COMMAND.COM now runs its real
startup (no longer spins at $050D). New blocker: a kernel loop $D858-$D87F after startup.]**
Implemented the M5.4-deferred fix. Clean same-program comparison (COMMAND.COM `$0100` entry,
ours vs stock) isolated it to 4 registers: stock `BC=HL=$1A00 IX=$F195 IY=$DC5B`, ours
`HL=0 BC=$0014 IX=$F1AA IY=$0314` → COMMAND.COM `jp $0500` then spun at `$050D` (a 5120-byte
LDIR with garbage params). The `$D824→$0100` transfer doesn't touch these regs, so they pass
through from `$47B2`'s return. `k_47B2` now sets, on EOF/success: `HL=BC=FAT_FILESIZE`,
`IX=DRVA_DPB ($F195)`, `IY = entry DE` (saved on the stack; the kernel work ptr `$DC5B`).
**Validated:** `$0100` entry now byte-identical to stock; COMMAND.COM reads `$0007` (TPA top
`$D6`), computes its high-mem target `$C200`, and LDIRs its transient up — genuine MSX-DOS
COMMAND.COM startup. A-3 intact (sp-rompage STUCK); Tier-1 green (unit 18/18,
DSKIO/BLOAD/FILES == CF-3300); net-zero 16384 B. · **NEW BLOCKER (next milestone):** after
startup the boot sits in a kernel loop `$D858-$D87F` ($D87F = the 130-byte LDIR `$D34E→$DA40`
+ a CONOUT call at `$D887`); screen still blank, CONOUT still fed `$00/$80`. Likely a BDOS
function COMMAND.COM calls during startup that our kernel/BDOS path mishandles. Drive it with
the same ours-vs-stock differential, anchored on a shared event. · undo: revert 9573a4c.

**[CHARACTERISATION (corrected) / 2026-06-26 — post-A-5. COMMAND.COM LOADS CORRECTLY; the
blocker is the DOS-env / boot-sequence handoff, NOT a wrong-sector load. RETRACTS the earlier
"+2 clusters" claim below.]**
- **RETRACTION:** I earlier wrote "ours reads COMMAND.COM 2 clusters too late (138 vs 134)".
  That was WRONG — an artifact of snapshotting the MIDDLE of the read. Ground truth from the
  disk: root dir [6] COMMAND.COM = cluster 62 → sectors **134-146** (chain 62-68, contiguous),
  and sector 134's bytes are **`C3 00 05`**. A full from-boot DSKIO capture shows ours reads
  exactly 134,135,…,146 — **CORRECT**. (Lesson, again: don't conclude from a mid-stream
  snapshot; capture from the anchor. [[harness-first-investigation-mo]].)
- **What actually differs:** ours' first `$0100` execution is **COMMAND.COM** (`C3 00 05` =
  sector 134) → `jp $0500` → spins at `$050D`. Stock's first `$0100` is **MSXDOS.SYS** (root
  dir [7] = cluster 69 → sector 148 = `C3 00 02`) → `jp $0200`, which runs the DOS init and
  prints the `MSX-DOS version 1.03 / Copyright 1984 by Microsoft` banner (CONOUT from `$0320`).
  So my "first-divergence at `$0100`" compared DIFFERENT PROGRAMS (ours=COMMAND.COM,
  stock=MSXDOS.SYS) — not a real divergence.
- **Open hypotheses (to verify next, fresh):** (a) ours enters COMMAND.COM at `$0100` with the
  wrong environment/entry-registers/SP (ours SP=$DC00, no proper DOS env) so it spins; and/or
  (b) ours' boot SKIPS or mishandles the MSXDOS.SYS-at-`$0100` init step that stock runs (banner
  + DOS setup) before launching COMMAND.COM; and/or (c) a possible off-by-1 in ours' MSXDOS.SYS
  read (ours read sectors 149-152, stock 148-151) — UNCONFIRMED, could be another mid-stream
  snapshot artifact, verify from the anchor before trusting it.
- **NEXT (fresh session, deliberate):** anchor a clean comparison on the SAME program. Either
  (i) compare ours-vs-stock at COMMAND.COM's `$0100` with matched entry state, or (ii) check
  whether ours runs MSXDOS.SYS at `$0100` at all. Understand how our Tier-2 veneer boot
  (k_47B2 et al.) sequences the MSXDOS.SYS-init vs COMMAND.COM-launch relative to stock.
  Connects to M5.4/§8.54 ($47B2 return-register state was explicitly deferred: "does NOT yet
  reproduce $47B2's return AF=0142/HL=1A00/IY=DC5B" — that deferred entry-state may be the env
  bug). · undo: n/a (analysis only).

**[RETRACTED — see correction above. The "+2 clusters" framing was wrong.]** After A-5 the boot
reaches the COMMAND.COM-load kernel phase but never shows `A>`. Harness findings:
- **Stock** prints the real banner via CONOUT `$5454`: `\r\n MSX-DOS version 1.03 \r\n
  Copyright 1984 by Microsoft \r\n`, called from `$0320` with `HL=$DD0E` (work area), `DE`=
  the banner chars.
- **Ours** feeds `$5454` a repeating `$00 $00 $80 …` garbage stream, called from **`$D88A`**
  (relocated kernel), with junk `DE`/`HL`. The kernel routine `$D87F` LDIRs 130 bytes from
  `$D34E` (garbage) → `$DA40`, maps the disk ROM into page 1 via `$F368`/WA_SEG (now WORKING),
  `ret`s to **`$50E0` — a bogus address inside our ROM's `$00` padding** (real code at `$50A9`
  ends `$50B7`; `$50B8-$520x` is `ds` fill), then NOP-slides. So the kernel is operating on
  corrupt state: garbage buffer, garbage return address, garbage output.
- **These are DOWNSTREAM symptoms** (cf. [[tier2-storms-are-downstream]]); chasing the `$50E0`
  NOP-slide or "missing veneer" would be fixing a symptom. The PRIMARY derail is upstream in
  the shared relocated kernel ($D606-$DD0E, same addresses on ours+stock since both use
  GETWRK=$DD0E) — likely a wrong value our disk ROM returns from one of the `$40xx`/`$50xx`
  kernel-callback contracts during COMMAND.COM load, sending the kernel down a wrong branch
  before it ever reaches the `$0320` banner path.
- **NEXT MILESTONE:** ours-vs-stock FIRST-DIVERGENCE hunt in the shared kernel — compare the
  kernel PC/branch sequences (not time-aligned; ours is slower) from COMMAND.COM entry to the
  first point ours branches away from stock, then identify the disk-ROM callback whose
  contract we get wrong there. Connects to the M5.5 "$544E spin from $D88A" thread (now with a
  clean post-A-5 signal). · undo: n/a (analysis only).

**[A-5 DONE / 2026-06-26 — WA_SEG corruption FIXED, boot now reaches COMMAND.COM]
The post-storm "kernel loop" was a CORRUPTED WA_SEG trampoline; root cause = our OWN
interrupt handler's A-2b private stack overflowing into it. Fix: run the $0038 handler on
the caller's stack (retire A-2b). Implemented + validated; see tier2-a5-spec.md.** After A-3
the real resting state was an infinite loop `$DC03 → call $F368 → jp WA_SEG($E795) → … →
$0000: jp $DC03`: the kernel's `$F368` segment-switch landed on a trampoline whose tail
(`$E7A8+`) was garbage (`ld (#00C0),a … call m,$0000` instead of `ld (SLTTBL3),a; ld
($FFFF),a; … ret`), so the page-1 swap never happened and COMMAND.COM never got control
(stock was already at `$0B9F` by the same time).
- **The corruptor is OUR int handler, not a disk-boot stack (corrected — see HONESTY note).**
  `INT_H_HIRAM` switched to the A-2b 48-byte private stack (`INT_STK_TOP`) before
  `call $0038`; the main-ROM KEYINT (`$0C82` loop + `dec ($F3F6)` JIFFY + the `pop ix/iy/af/
  bc/de/hl` epilogue at `$0D02`) needs ~60 B and overflowed DOWNWARD into `WA_SEG`, laid out
  just below the stack (`INT_STK_TOP = PG_SV_A8+1+48`). The corruption always landed at
  `WA_SEG+19`, regardless of where the band was placed.
- **HONESTY note (process):** I first misread the `$0C85 push` (KEYINT's pushes) as "the MSX
  disk-boot stack roaming `$E7xx`" and got sign-off for A-4 (relocate the band into `$DDxx`).
  A-4 was IMPLEMENTED, then the corruption *reproduced identically at the new address* — the
  stack and WA_SEG had relocated together — which exposed the real cause. A-4 was reverted
  (uncommitted) and `tier2-a4-spec.md` withdrawn. Lesson: I should have confirmed *what*
  `$0C85` is (trace it = KEYINT) before naming the corruptor; pattern-matching `push`+low-PC
  to "boot stack" skipped the black-box check. (cf. [[dont-prematurely-wall]], harness-MO.)
- **Fix (A-5, signed off):** delete the three stack-switch instructions from
  `int_h_hiram_tmpl`; run KEYINT on the caller's stack like stock/standard MSX. A-2b only
  guarded against a corrupt caller SP (the storm) which A-3 already fixed; every caller stack
  here is healthy + roomy. Removes the unbounded-depth guesswork a fixed private stack imposes.
- **Validated:** WA_SEG byte-identical at t=6 & t=14; boot breaks out of the loop and runs
  COMMAND.COM (`$0BA4`/`$0D0A`/`$120C`) + the working `$F36B→$E79B` switch + CONOUT; A-3
  intact (`sp-rompage` STUCK); Tier-1 green (unit 18/18, DSKIO/BLOAD/FILES == CF-3300);
  net-zero 16384 B. · **NEW downstream blocker (next milestone):** screen still blank at
  t=90, PC churning in the `$54xx` CONOUT band — likely a CONOUT/screen-output issue, looser
  than the loop. · undo: re-insert the 3 stack-switch instructions.

**[A-3 DONE / 2026-06-26, commit 71b1096] Relocated int_h to always-mapped high RAM
($DDAE) — THE COMMAND.COM STORM IS FIXED.** Implemented tier2-a3-spec.md approach B:
`int_h_hiram_tmpl` (the A-2/A-2b handler made relocatable — straight-line, only a
PC-relative `jr` + the fixed `call $0038`, `pg0_mainrom_in/out` inlined with `ret z`→
`jr z`, like `res_print_tmpl`) is LDIR'd into `$DDAE` by `lay_page0_env`, and the
`p0_env_tab` `$0038` entry now targets `INT_H_HIRAM` instead of the page-1 `int_h`.
**Validated with the harness + regression:** handler installed (`$DDAE = ED 73 E2 E7…`),
`$0038` chain → `jp $DDAE`, `int-vec hits=0`, SP stable `$DBFA-DC00`; `disk_derail_locate
--preset sp-rompage` = STUCK (no SP corruption — storm gone); Tier-1 green (unit 18/18,
DSKIO/FILES == CF-3300, BLOAD ok); net-zero (16384 B). · **New downstream blocker
revealed** (the storm was masking it): a bounded kernel loop, triage `loop-top $E7B1,
period 23`, healthy stack, in the `$D7xx`/wa_seg band — likely the M5.7/§8.60 "$DA23
wrong-path loop" / work-area thread, now visible with a CLEAN signal (no storm). This is
the next milestone; drive it with the harness (`bisect_locate` on a loop-specific
predicate, ours-vs-stock at the first divergence in the `$D7xx` kernel). · the old
page-1 `int_h`/`int_h_body` are dead-but-kept (net-zero); remove in a follow-up. · undo:
revert 71b1096.

**[FIX DIRECTION / 2026-06-26] Stock comparison (via the new harness) names the fix:
move our interrupt handler to ALWAYS-MAPPED high RAM, like stock's `$DDAE`.** Used the
new `omsx_session.py` `irq_chain` primitive on both machines (one call each) to dump the
`$0038` jp-chain + page-1 mapping at the COMMAND.COM phase:
- **Stock:** `$0038 → jp $DDAE`, and `$DDAE` is in **high RAM (page 3, always mapped)**
  (`push ix` = the real handler). The int entry is NOT in the swappable page-1 ROM.
- **Ours:** `$0038 → jp $4251 → jp $792B` — BOTH in **page-1 disk ROM** (`$792B` =
  int_h_body, the A-2b `ld ($e7e2),sp`). When `wa_seg_ram` swaps page 1 to RAM for
  COMMAND.COM, the whole vector path (`$4251` trampoline AND `$792B` body) is unmapped →
  the first IRQ storms on `$FF`. (This is also exactly why A-2b never ran — it lives in
  the wrong memory.)
- **The fix (Interface-B rework, fork (a)):** install `$0038 → jp <our high-RAM handler>`
  (our own address in the `$D7xx-$DFxx` kernel band, clean-room — mirror stock's structure,
  not its bytes), and relocate the int handler body there so it survives the page-1 swap.
  It can page the disk ROM back in via CALSLT if it needs disk-ROM routines, but the ENTRY
  must be always-mapped. This connects to §8.69 Interface-B / A-2..A-5 and supersedes the
  A-2b placement.
- **HARNESS NOTE:** the negative case validated too — `disk_derail_locate.py --preset
  sp-rompage --stock` = STUCK ("no failure in window"), i.e. stock never corrupts SP.
  · confidence: high (direct ours-vs-stock measurement) · this is a DESIGN sign-off point
  (the deferred Interface-B rework), not yet implemented · undo: n/a (analysis + new probe).

**[ROOT CAUSE FOUND / 2026-06-25] The primary derail is a SLOT-PAGING bug in the
COMMAND.COM handoff — NOT a control-flow slide. Located + confirmed end-to-end with
the new reverse/probe toolbox.** Method: `reverse` binary-search in emulated time for
the corruption instant (SP enters the ROM page is a clean predicate), then a forward
per-instruction trace from a `reverse goto` point. Findings, all from one boot:
- The "storm" is `rst 38h` recursion: RAM `$0038 = C3 51 42 = jp $4251`, but at the
  failure `$4251` reads **$FF** (`rst 38h`) — the **disk ROM is paged OUT of page 1**.
  So `$0038 → jp $4251 → $FF=rst38 → $0038 → …` loops forever, each `rst` pushing
  `$4252` (stack is all `4252`), marching SP down. Fully explains the SP march.
- **The unmap is deliberate, in our own RAM-resident handoff code.** Trace at the
  boundary (t≈8.186s): kernel `$D827 call $F36B → jp $E79B` (RAM trampoline). $E79B
  does `ld a,#00; di; ld a,(FCC8); and $F3; or b; ld (FCC8),a; ld ($FFFF),a`. SLTTBL[3]
  (`$FCC8`) was `$04` → page-1 subslot **1 = the disk ROM**; `and $F3` clears page-1's
  bits, `or b` (B=0) forces page-1 subslot to **0**; the `ld ($FFFF),a` write unmaps the
  disk ROM → page 1 = slot3-sub0 = **empty ($FF)**. Then `$D82A ei; jp $0100`.
- **COMMAND.COM then actually RUNS** (trace: $0100→$0500→ self-relocating `ldir`,
  bc=$1400). It dies at the **first interrupt**: confirmed via `z80.acceptIRQ` —
  ACCEPT#1 interrupts COMMAND.COM at $050D with `m4251=FF`, `$0038=jp $4251` → storm.
- **So:** the handoff unmaps the disk ROM from page 1 while the live interrupt vector
  `$0038 → $4251` still points there. Works only while the disk ROM is mapped; the
  moment COMMAND.COM is given control (page 1 = empty) the first IRQ storms. This is
  why "COMMAND.COM is not sustained" (M5.5).
- **This is the proximate trigger; relationship to the M5.7 "stale work-area" thread
  is unclear** (may be separate/earlier, or the wrong B/subslot value originates
  upstream). The slot bug is the confirmed storm cause regardless.
- **The fix is a DESIGN decision (clean-room, our own code) — HARD-STOP for sign-off,
  not yet implemented.** Candidate directions: (a) re-point the interrupt vector
  (RAM `$0038` / H.KEYI) to a handler that survives the disk-ROM unmap before the
  handoff; (b) keep page 1 mapped to a valid subslot so `$4251` stays a real `jp`;
  (c) follow whatever the real MSX-DOS / stock CF-3300 handoff does at this exact
  point (compare with stock = the obvious next experiment, same reverse method).
  · confidence: very high on the diagnosis (located + confirmed); the fix is open. ·
  undo: n/a (analysis only).

**[tooling / 2026-06-25] Built the dead-zone NOP tripwire — then a fast experiment
FALSIFIED its premise; pivoted to a full openMSX-probing-toolbox sweep instead.**
Added `probes/disk/disk_probe_dosboot_tripwire.py` (kept, per user) on the idea that
the derail is a NOP-slide into `$00` absorption pads, catchable by one watchpoint
(range + opcode==0). Mechanism validated and excellent. **But the decisive negative:
NO `$00` opcode executes anywhere in `$0000-$FFFF` across the entire 30-emulated-second
boot+derail** (ROM page, all RAM, page-0 storm ring — all zero; cross-checked by
trapping a known `$31` which fired instantly). So the triage oracle's **SLIDE** verdict
(`PC==prev+1`) means *consecutive single-byte instructions*, NOT a NOP-pad slide — the
absorption pads are never entered. The "dead zone = `$00` pad" frame (strategy ①) is
dead for this bug; the derail is control running forward through **real, valid-opcode
code at the wrong place**. · **Why this is progress, not a detour:** it cost one cheap
experiment (not a reframe spiral) and forced a systematic sweep of openMSX's debug
surface, which surfaced three capabilities we were not using — now validated and
documented in `disk/docs/openmsx-probing-toolbox.md`: (1) **`z80.acceptIRQ` hardware
probe** = direct interrupt-acceptance catcher, no per-instruction cost; (2) **`reverse`
rewind/replay** = `reverse goto <T>` before a caught failure then single-step forward
to recover the **faulty transfer** (this is the engine the derail hunt was missing);
(3) **`{CPU regs}` byte 27** = real IFF1/IFF2 + "can-accept-IRQ" bit (corrects the old
"reg IFF1 doesn't exist" dead-end). Also added `tools/sym_to_openmsx.py` (pasmo `.sym`
→ openMSX `generic` so traces show symbol names; 352 syms load). · **Recommended next
frame (strategy ③, the memory's "method that works"):** the disk-ROM PCs aren't
comparable to stock (relocated/own-design), but main BIOS (`$0000-$3FFF`) and the
DOS RAM image (MSXDOS.SYS/COMMAND.COM, fixed addresses) ARE byte-identical on both —
so find the first executed-PC divergence ours-vs-stock *restricted to those comparable
regions*, built on the validated `acceptIRQ`+`reverse` engine. This reconnects with the
M5.7 work-area-init diagnosis ($D7CE / $DC80-$DCB2 / $F1A8+ stale). · confidence: high
on the negative result + the toolbox; the next frame is a proposal, not yet greenlit. ·
undo: n/a (new probe + doc + tool, no ROM change).

**[A-2b / §8.76] Implemented the storm-proof int_h (private interrupt stack) — CORRECT
and green, but it does NOT change the boot outcome; the storm bypasses it. Kept as
defensive hardening (user call), then pivoting to the primary derail.** int_h_body now
saves the caller SP, runs on a private 48-byte page-3 stack ($E7B2-$E7E1, save at
$E7E2), and restores — proven by a first-interrupt pctrace (SP $8FEE→$E7E2, KEYINT
$0C3C runs on $E7xx, clean return). Net-zero ($4251=jp $792B unchanged), unit 18/18,
DSKIO/basic/tape regression green. · **The negative result:** the steady-state is
unchanged (triage still SLIDE, SP=$4250) and the storm ring is PURE $4251⇄$0038 with
int_h_body ($792B) NEVER appearing — the interrupt is accepted AT the $4251 trampoline
before the body runs, so A-2b's hardening is never reached during the storm. The SP
march is the hardware accept-push on an already-corrupt SP, not int_h_body. · **So the
"storm masks the bug" hypothesis was WRONG:** the storm is a pure downstream consequence
of the primary derail (IFF=1 while PC is already runaway → interrupts accepted at the
trampoline). No handler-level change can prevent that; fix the primary derail and there
is no runaway to storm. · **Disposition (user: "keep, commit, pivot"):** A-2b kept as a
standalone correctness fix (a handler that marches a corrupt caller stack is a real
latent bug; net-zero, green) but explicitly NOT the blocker. Next = hunt the primary
derail (first divergence from stock), reconnecting with the pre-compaction kernel/
COMMAND.COM-sustain track. · confidence: HIGH (storm ring + first-int trace are
unambiguous). · undo: revert init.asm INT_STK_TOP/INT_SP_SAVE equates + the 3 added
lines in runtime.asm int_h_body (net-zero, trivial).

**[M5.x / §8.72-8.74] RE-BASELINED the hang: the post-compaction "$4251/$0052
storm / SP=$0000 onset" was a RED HERRING; the real hang is an int_h→KEYINT
VDP-ACK FAILURE (interrupt storm).** After /compact I resumed the "find the SP=0
runaway onset" task from the summary and chased it to a tight page-0 loop at
$02E0-$0339 running with SP=$0000. **Judgment call:** I discarded that lead after
proving (PSP+prologue dump + a 30000-instr aligned pctrace, ours vs stock, both
from $02E0) it is **byte-and-register IDENTICAL on the stock CF-3300** — it is the
normal MSX-DOS RAM/slot-sizing scan, which legitimately abuses SP as scratch
(`ld sp,hl`) with interrupts off. Not a bug. · Then re-found the TRUE steady state
with `disk_probe_dosboot_hang.py --settle 24`: **ours** = a runaway sweeping
linearly through high RAM/ROM (`disk_probe_dosboot_derail.py`), **stock** = the A>
idle keyboard loop at $0D87 (SP=$DBE0, regs static). The derail ring pinned the
core: `$0038 (=C3 51 42 = jp $4251) ⇄ $4251 (int_h = C3 2B 79 = jp $792B =
int_h_body)`, **SP descending -2 per cycle**, int_h_body ($792B) NEVER executing →
the VDP interrupt is never acked → storm → SP marches from $8FEE down through our
ROM → derail/NOP-slide. · **Why it matters for you:** this moves the active front
OFF the kernel work-area / $D7xx grind (M5.6-5.9) and BACK onto Interface-B: A-2
(int_h chaining to KEYINT) is *present but not acking*. The fix locus is
`int_h_body` in disk/runtime.asm (the `call $0038` / EI-DI ordering, or KEYINT not
clearing the source under our paging). pg0_mainrom_in itself looks sound (CONOUT
uses it and works). · **My plan (PAUSING for sign-off — this is asm on the
interrupt path):** next milestone = observe whether int_h_body's `call $0038`
actually reaches main-ROM KEYINT ($0C3C) and acks S#0, then spec the fix before
touching asm. · confidence: HIGH on the re-baseline + storm mechanism; MEDIUM on
the precise ack-failure cause (one more probe needed). · undo: n/a (analysis +
6 new read-only probes, no production change).

**[M5.x / §8.75 — CORRECTION to the entry above] The int_h handler is NOT the
primary bug; the $4251 storm is a SECONDARY symptom masking a later control-flow
derail.** A pctrace armed on the first $4251 (the first interrupt) shows the
handler path works END-TO-END: $4251→$792B int_h_body→pg0_mainrom_in (paging
ok)→call $0038→$0C3C the real main-ROM KEYINT (H.KEYI $FD9A + H.TIMI $FD9F +
keyboard scan)→clean return through int_h_body cleanup→RET back to the interrupted
boot code at $0320 with SP recovering to $8FF8. ~700 steps stay healthy (multiple
interrupts + boot code, stack fine). So A-2 was a genuine improvement and the
handler acks correctly. · The collapse happens LATER: a primary derail (fingerprint
AF=C28C BC=C51C↓ DE=C5E4 HL=09E4 IX=F1AA IY=0314, SP frozen $4250) sends PC into a
runaway sweep; interrupts firing into int_h DURING the runaway are the "storm" we
kept catching. The triage oracle's SLIDE-with-SP-at-int_h-1 verdict is exactly this
aftermath. · **Why it matters for you:** the boot fix is NOT the interrupt handler —
it's the primary derail (reconnects with the pre-compaction M5.x kernel/COMMAND.COM-
sustain track). The storm-proof handler (Lever 2) is still worth doing but as
DIAGNOSTIC HARDENING (a non-destructive int_h makes a derail show as a clean SLIDE
pointing at the root, instead of a stack-marching storm that corrupts state and
hides it). · confidence: HIGH (the first-interrupt trace is unambiguous). · undo: n/a.

**[A-2 / LANDED — partial: advances the boot, downstream blocker remains] int_h now chains to the main-BIOS
KEYINT.** Greenlit + implemented per tier2-a2-spec.md. `int_h` ($4251) is now a net-zero trampoline
(`jp int_h_body` + `ds 3`; dskio unmoved); `int_h_body` (free tail) pages the main ROM into page 0 via the new
shared `pg0_mainrom_in/out` helper (factored out of CONOUT — `conout_set_sub` merged in, `CONOUT_A8`→shared
`PG_SV_A8`), `call $0038` (main-ROM KEYINT: VDP ack + H.KEYI/H.TIMI/keyboard/JIFFY), `di`, restore, ret.
Portable (EXPTBL[0]). **RESULT:** regression GREEN (unit 18/18); pctrace `--arm 0x0100` distinct PCs **199→283**,
interrupt path ($0038/$FDA4) now serviced, COMMAND.COM runs broader ($07xx/$0Bxx/$19xx) with stable SP in the
window — a real advance. **BUT** settle-24 still ends in the `$D7B0-DC00`/`SP=$4250` runaway; stackwatch shows
the same `$4251`/`$0052` storm = AFTERMATH, so a downstream blocker remains (the runaway's true onset is upstream
of the storm). · NEXT: find the new first-divergence / runaway ONSET (the `$4251` storm is the symptom, not the
cause) — but FIRST the disk.asm source split (user-approved). · undo: int_h/CONOUT revert is one tail block.

**[A-1 / DONE — A-2 spec ready, AWAITING SIGN-OFF] Architecture-rework analysis complete (10am span).**
Resolved O-1/O-2/O-3 from spec + CF-3300 oracle (§8.70); wrote `disk/docs/tier2-a2-spec.md`; **landed NO rework
asm** (held per the deferral). Results:
- **O-1:** the DISK ROM installs the whole page-0 vector band + `$0038` (write-watch: `$5A31`/`$5A89`/`$5A8C`/
  `$5A8E`/`$5AB9`/`$5ABC`, all disk-ROM) → `lay_page0_env` is correct to exist; the bug is the handler BODIES are
  mapped-memory shortcuts, not the install.
- **O-2:** stock's `$0038` handler inter-slot-CALSLTs to the main-ROM KEYINT (`$0038`→`$0C3C`), which runs H.KEYI
  (`$FD9A`) + H.TIMI (`$FD9F`) = the full service. Our `int_h` does only a partial VDP ack → starves COMMAND.COM's
  timer/keyboard loop → the runaway.
- **O-3:** Interface-B surface = CHPUT (done M8b), KEYINT (A-2), RDSLT/WRSLT/CALSLT/ENASLT (A-3), CALLF (real).
- **A-2 (proposed):** rework `int_h` to inter-slot-call the main-ROM KEYINT via `EXPTBL[0]` (CONOUT pattern),
  drop the partial ack. Expected to clear the residual runaway. BIOS-agnostic (MSX1 standard → ports to C-BIOS).
**DECISION NEEDED (sign-off):** greenlight implementing A-2 per the spec? It's a focused change (rework `int_h`
+ factor a shared `EXPTBL[0]` page-0-switch helper with CONOUT); A-3 (the other inter-slot handlers) stays
separate. · confidence: high that A-2 is the right + likely runaway-clearing fix · undo: trivial (int_h is small).

**[ARCH / §8.69] TARGET REFRAME + ARCHITECTURE AUDIT (user-directed, in-loop) — CF-3300 = oracle, C-BIOS =
prime target.** User clarified: we validate inside the CF-3300 *proprietary main BIOS*, but that is the oracle's
environment; the prime target for our disk ROM is **C-BIOS**, and the goal is any standards-compliant MSX. M9
debugging had begun over-fitting our ROM to the CF-3300 BIOS's instruction-level behaviour (wrong success
criterion). Per user: **reason from spec + oracle (no C-BIOS experiments yet), document the corrected
architecture, and DEFER the rework** to a separate signed-off effort. Wrote `disk/docs/tier2-architecture-audit.md`.
Core finding — **two interfaces**: (A) disk-ROM↔MSXDOS.SYS/COMMAND.COM is BIOS-INDEPENDENT and layout-fixed by
the loaded DOS (so all M1–M8 kernel-veneer/work-area work is correct, not BIOS-specific); (B) disk-ROM↔main-BIOS
must be BIOS-AGNOSTIC (EXPTBL/CHPUT/KEYINT/slot work area). **All current bugs are on Interface B** and only
"work" on CF-3300 by that BIOS's tolerance: `int_h` is ack-only (doesn't chain to KEYINT — likely the M9
runaway's real cause), and the lay_page0_env inter-slot handlers are "mapped-memory" shortcuts (CONOUT already
had to bypass `calslt_h`). CONOUT/EXPTBL[0] (M8b) is the correct Interface-B template. Migration plan A-1..A-5 +
open items O-1 (who owns the page-0 DOS env → fate of lay_page0_env) / O-2 (KEYINT chaining contract) / O-3
(enumerate Interface-B surface) in the audit doc. NO code changed; Tier-1 green; M1–M8 NOT invalidated.
· DECISION: documented + deferred per user. Awaiting greenlight to start the rework (A-1).

**[M8b / §8.68] PORTABILITY FIX (user-flagged, in-loop) — CONOUT now reads EXPTBL[0] instead of hardcoding
slot 0.** First cut switched page 0 with `and $FC` (= "main ROM is primary slot 0, unexpanded") — a CF-3300-
specific bake-in, not faithful. Rewrote `conout_body` to read `EXPTBL[0]` ($FCC1) at runtime for the main-ROM
slot id, set page-0 primary from it, and (if expanded) program the page-0 subslot via the standard $FFFF/SLTTBL
protocol (`conout_set_sub`). User chose "Full ENASLT." Re-validated on CF-3300: unit 18/18, pctrace 207 distinct
PCs (≈ M8's 199 — identical banner-escape, behaviour unchanged where primary=0). **CAVEAT TO REVIEW: the
expanded-main-ROM sub-path (`conout_set_sub`) is NOT exercisable on the CF-3300 (EXPTBL[0]=$00, unexpanded), so
it is spec-derived (MSX2 TH §2.4) and unvalidated by probe.** Pages 1 (our code) & 2 (stack) are provably
untouched by it (only page-0/page-3 $A8 fields move). · confidence: high on the primary path; the expanded path
is correct-by-construction but unproven · undo: one-block revert of conout_body.

**[M8 / §8.68] REAL CONOUT IMPLEMENTED — banner loop escaped (56→199 PCs), a new later blocker exposed.**
Implemented `conout_body`: emit `A` via main-ROM CHPUT (`$00A2`) through a genuine inter-slot call (slot 0
unexpanded per measured `EXPTBL`, so a plain `$A8` page-0 switch). `$5454` → `jp conout_body`, NET-ZERO (the +2
is absorbed by the `ds $5FE5 - $` pad; `$5FE5` still `jp k_5FE5`). Regression GREEN (unit 18/18). Ours now
escapes the banner loop and runs COMMAND.COM's code broadly with a stable `SP≈$8FE0` (the §8.60-8.66
stack-runaway was banner-spin aftermath, now gone in this phase). BUT it still eventually reaches the old
`$D7B0-DC00`/`SP=$4250` end-state — a NEW downstream blocker past the banner. · DECISION: committing M8 as a
validated incremental advance (strictly further than before) and proceeding to M9 = characterise the new
divergence under span mode. · spec `disk/docs/tier2-m8-spec.md`. · confidence: high that CONOUT is correct &
necessary; the new blocker is open. · undo: `$5454` back to `ret` + drop `conout_body` (one-block revert).

**[M7 / §8.67] ROOT CRACKED, MILESTONE UN-BANKED — the blocker is our own no-op CONOUT veneer at `$5454`.**
You said "continue; we're still making genuine progress," so I resumed on the §8.66 stack-write-watch angle and
it paid off decisively. New probe `disk_probe_dosboot_stackwatch.py` ruled out the interrupt-storm/bad-`LD SP`
theories (both machines set `SP≈$9000` by design — §8.66's "stack too low" was a red herring). A properly
aligned PC-trace from `$0100` (regs near-identical there) is byte-identical for 20 steps then diverges at ONE
instruction: stock's `$5454` runs the real disk-ROM CONOUT (inter-slot call to BIOS CHPUT `$00A2`), ours' is a
bare `ret` — our deliberately-stubbed `conout` "first cut" (disk.asm §8.38). COMMAND.COM's banner loop branches
on CONOUT's return flags, so ours spins forever (56 distinct PCs, never escapes) while stock proceeds (482).
**The entire §8.60-8.66 chase (`$DA23`/`$607B`/`int_h` storm) was downstream aftermath of this one stub.**
Alignment is rock-solid — far stronger than the superseded `$607B` reading. · DECISION: proceeding to implement
a real CONOUT (M8) under span mode — emit `A` via CHPUT through a genuine inter-slot call, preserving regs;
clean-room-legit (documented BIOS ABI, no oracle disassembly). It's the deepest Tier-2 code yet (our `calslt_h`
is a simplified `jp (ix)`, so CONOUT must do its own slot switch). · confidence: very high on the root;
implementation effort unknown · undo: n/a (analysis + new probe).

**[M6 / §8.66] TIME-BOXED ATTEMPT DONE → MILESTONE BANKED.** _(SUPERSEDED by §8.67 — the "unresolved late stack/
interrupt corruption" is now fully explained as aftermath of the `$5454` CONOUT no-op; milestone un-banked.)_ You chose "one
time-boxed cleaner attempt." It found the proximate failure (interrupt-storm stack
corruption — `SP` walks into the page-1 ROM) but that too is a late symptom: the
first interrupt is handled cleanly and COMMAND.COM runs 4000+ instructions normally
before the corruption appears. The true root receded under every method. Per the
agreement, I banked and stopped. **Banked milestone:** the clean-room disk ROM loads
real MSX-DOS 1 + COMMAND.COM byte-perfect and begins executing it (interrupts handled
correctly through COMMAND.COM startup). Best untried angle for a future restart: a
stack-write watch to find the first unbalanced push. No code regressions — Tier-1
Disk-BASIC stays fully green. · nothing to action; this is the wrap-up.

**[M6 / §8.65] COURSE CORRECTION — the M6 pre-build spec is INVALIDATED, and the
M5.8/M5.9 "stale work area = root" thesis was a mis-aligned-comparison artifact.**
Read-watch probes show ours reads none of the stale work-area cells before it loops,
and the loaded COMMAND.COM image is byte-identical to stock — both machines do the
same `$0500` self-relocation, so our loader is correct and the work area isn't what
the derail reads. The hang is a kernel BDOS-service loop, reached while COMMAND.COM
runs. **No code was written on the invalidated path** (characterise-before-code held
the line — twice this session: wa_seg-incomplete §8.60 and pre-build §8.65). **Net
positive banked: the clean-room disk ROM loads real MSX-DOS + COMMAND.COM byte-perfect
and starts executing it.** Re-synced with the user on direction (keep drilling with a
cleaner BDOS-level method / bank the milestone / reprioritise). · confidence: high on
the invalidation; the final-hang root is still open.

**[M5.9 / §8.62] ROOT PINNED — the upstream divergence is the stubbed canonical
entry `$607B`.** _(SUPERSEDED by §8.65 — see above; this was a mis-aligned-checkpoint
reading. `$607B` is real and stubbed, but it is not proven to be the hang's cause.)_ Binary-searched the first work-area memory divergence (it's already
stale at `$0100`/`$D824`, i.e. during MSXDOS.SYS-init) and named the responsible
canonical ABI entry: **`$607B`**, a multi-purpose disk-ROM service the kernel calls
15× during init to do inter-slot block copies AND build the `$F2B8` (filename+DPB)
and `$F1A8` work-area structures. **Our `k_607B` is a bare `ret`** — so the work area
is never built → the `$DA23` hang. **Scoped sub-track (M6): characterise + implement
`k_607B`.** Clean-room-feasible (the data it builds is derived from the disk/DPB,
like our GETDPB — no oracle disassembly). · confidence: high · this supersedes the
"build more of the work area" framing below with a concrete single entry point.

**[M5.8 / §8.61] SCOPE FLAG — the COMMAND.COM-load blocker is an upstream
work-area-init gap, not a single hook/veneer.** I disproved two of my own
hypotheses (the `$F368` hook and `$50A9` both rejoin register-identical with stock)
and traced the real divergence to STALE work-area memory at `$D7CE`: ours leaves
`$DC80-$DCB2` and `$F1A8+` uninitialised (`$FF`) and (before the fix below)
clobbered `$F2B8`. These regions are built upstream by MSXDOS.SYS page-0 code and
disk-ROM routines ours apparently skips. **Why it matters for you:** the remaining
fix is "build more of the DOS work area" — a sub-track of unknown size, a shift from
the M5.6-era "fill the `$F368` hooks" framing. **My plan (proceeding unless you
redirect):** M5.9 = binary-search the first upstream divergence (memsnap at earlier
landmarks) to name the exact init step ours skips, THEN scope/spec the build. ·
confidence: high on the diagnosis, unknown on remaining effort · undo: n/a (analysis).

**[M5.8 / commit 6ba6393] Narrowed the `RES_STUBS` `$C9`-fill `$F24E-$F2FD → $F24E-$F2B7`.**
Decided to commit this standalone even though it does NOT clear the hang. · why: it
removes a genuine clobber bug — our fill was destroying the kernel's `07 "MSXDOS  SYS"`
+ DPB block at `$F2B8` (proven by memsnap + write-watch: stock builds it via
`$4354/$5667`, ours' only writer there was our own fill LDIR). Correct regardless of
the hang. · alternative: hold it until the whole work-area fix is ready (rejected —
it's an independent correctness fix and removes a confound). · confidence: high ·
undo: revert `RES_STUBS_END` to `$F2FE` (one line). · regression: unit 18/18,
DSKIO/FILES==CF-3300, BLOAD ok.

**[workflow] Adopted the autonomous-span mode mid-session and ran this whole M5.7→M5.8
investigation under it** (multiple probes + one committed fix without bouncing). This
queue + §8.60/§8.61 are the batch to review. · undo: n/a.

---

## Archived (reviewed & re-levelled)

_(empty)_
