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

**[M22a + M22b slice 1 / LANDED (2026-07-03) — second surprise inside M22: the `$53A7`
CONOUT-worker canonical entry; sign-off given, fix implemented and re-verified.]**
Testing `DIR` on the (uncommitted) M22a build surfaced screen corruption; characterised
first (no asm touched), then fixed. Root cause: the RAM kernel dispatches EVERY BDOS
`$02` CONOUT char to page-1 **`$53A7`** (`ret=$D88A`, `B=$A7` fingerprint, char in **E**
— the same canonical class as the M22a eleven), un-wired `$00` pad on ours since forever.
Pre-M22a the CALL NOP-slid into `$5454``jp conout_body` and was **accidentally correct**
(emit E, `A:=E`) — all M8→M21 console parity rode that slide; M22a's new `$543C` CONST
veneer intercepted it, so ours dropped ALL func-2 output (date, `A>`, echo, DIR listing)
while the 27/27 callseq stayed green (why M22a's suite missed it — screen arbiter wasn't
in the loop). Also pinned while at it: stock's routine does TAB→8-col-stop expansion
(do-while, at-least-one-space) tracked in a **logical-column byte `$F237`** (private to
page-1 code, kernel never reads/writes it; CR resets, LF no-op; counter is NOT CSRX —
post-wrap tab proves it), wrap/scroll stay in BIOS CHPUT, and `$5454` is NOT mid-routine
(stock returns to `$D88A` before `$543C`). Full spec + oracle tables:
[tier2-m22b-conout53a7-spec.md](tier2-m22b-conout53a7-spec.md). **Implemented:**
M22a + M22b-slice-1 (3-byte `k_53A7: jp conout_body` veneer, net-zero, restores proven
parity) landed together (kernel.asm). Slice 2 (tab+`$F237` in `conout_body`) deferred as
follow-up, needs a new TYPE-tab-file oracle. **Re-verified:** DIR `screen` byte-identical,
18/18 + 27/27 boot `callseq`, BDOSX2 14-record zero-diff, BDOSX Phase-1 zero-diff, `$F237`
parity, `make unit-test`/`make probe` green, `disk.rom` 16384 B.
· why: M22a alone was a shipping regression; the entry is static ROM-layout fact, same
falsify-first evidence class as M22a §3 · alternative considered: revert M22a's console
veneers instead (rejected — the ten entries are real and pinned; the collision was with
the missing 11th, not with M22a's design) · confidence: high (every claim probe-backed,
repro one-liners in the spec, re-run post-fix) · undo: `git diff disk/kernel.asm` (3-line
veneer + comment block, easy to revert if needed).

**[M21a + M21b / LANDED (2026-07-02) — Tier-2 can now run a typed `.COM` other than
COMMAND.COM; the whole M21 track is closed.]** Implemented against the §0.1-pinned contract.
M21a (`$4462` FOPEN-fill): relocated `fdc_di_save..getdpb` (153 B, driver.asm -> fat.asm's
free tail) to vacate the collision point, wired the new `fopen_fill_body` — plain-boot 27/27
aligned, miss-path `AF=$FF45` exact, FOPEN's FCB byte-identical to stock (only the
already-accepted cosmetic `dirloc` differs). M21b (`$47B2`/`k_47B2`, RC-2): rewrote the
boot-only diagnostic loader into a generic body — trusts FAT_FIRSTCLUS/FAT_FILESIZE already
seeded by the preceding FOPEN, re-primes via `fat_open`, streams to EOF via the existing
`bdos_seqread`. Hit and fixed one real bug beyond the characterisation: our internal
`BDOS_DTA` cell is separate from the kernel's real DTA pointer (`DOS_DTAPTR`, $F23D) — the
kernel's SETDTA only ever writes `DOS_DTAPTR`, so `BDOS_DTA` was stale (boot's leftover
`$1A80`) until `k_47B2` was fixed to reseed it at entry; found via a register capture at
`$47B2`'s own entry, not stock disassembly. Verified regression-first: `make unit-test`
19/19, boot 27/27 aligned, `capture --at 0xC51D` zero register diffs vs stock, full BDOSX
typed-run `callseq` 47/47 aligned, its 384-byte data buffer + FCB/snapshot buffer 0-byte-diff
vs stock, DIR byte-identical, `make probe` green, `disk.rom` == 16384 B. Confidence: high (every
acceptance criterion in [tier2-m21-spec.md](tier2-m21-spec.md) §6 met exactly). Undo: `git
revert` the two commits (M21a docs+code, M21b code) if a later regression surfaces.

**[M21a / §0.1 — DC5B isolation DONE (2026-07-02, stock-only characterisation, no ROM
changes): both hard-stop hypotheses FALSIFIED; prime suspect is now the MISS-path exit.]**
Ran the writewatch isolation the hard-stop demanded ([tier2-m21-spec.md](tier2-m21-spec.md)
§0.1). Stock DOES fill `$DC5B+14..+31` during boot, from the SAME PAGE1 PCs (`$42AA`,
`$4488-$44C8`) with the SAME field semantics as the `DA40` case ⇒ (a) fill-contract-differs
is FALSE; the range is exactly the FCB and stock writes it ⇒ (b) collision is FALSE. New
pinned facts: the `DC5B` call is PRE-`$0100` (MSXDOS.SYS's own COMMAND.COM load); the kernel
(`$D812`) overwrites `+14/+15` to S2=1/RC=0 right after the fill; on a MISS the machinery
writes only `+14:=$00` (`$42AA`, pre-search) and exits `A=$FF`; `$4462` is a TAIL-CALL
(stack-top return addr = `$D88A`), so the body's exit A IS the FOPEN result. The §5.2 fill
list also missed `+20..23` (date/time). Prime suspect for the regression: the generic body's
miss-path exit at boot n=2 (AUTOEXEC.BAT probe) reading as "found" → COMMAND.COM skips the
date prompt → the exact n=3 derail observed (not provable retroactively — the body was
reverted uncommitted). Ready to re-attempt M21a per §0.1's fix shape; run the 27/27 plain-boot
regression FIRST next time. · confidence: high on (a)/(b) falsification (direct observation);
medium on the miss-path attribution (consistent with all facts, body gone). · undo: n/a
(docs only).

**[M21a / HARD-STOP — implementation attempted, a THIRD $4462 calling convention broke the
core boot-to-`A>` chain; reverted]** With the spec's §5 characterisation believed
implementation-ready, built M21a for real: relocated `fdc_di_save..getdpb` (153 B) to the
`$4C77` free tail (net-zero, `disk.rom` stayed 16384 B, Tier-1 `make unit-test`/`make probe` all
green) and wrote `fopen_fill_body` behind a new `$4462` veneer.
· **First falsify-first check (per spec §6) passed cleanly:** `capture --at 0xC4A1 --mem
0xD403:0x25` on the BDOSX exerciser's typed-command call showed the FCB byte-identical to stock
except one field (`+25 dirloc`, the already-flagged known limitation) — RC, size, devid, both
cluster fields, relloc all matched exactly.
· **Then the MANDATORY regression re-check (M18's `callseq --at 0x0100 --log 0x0005 --keys '\r'
--keys-at 22`, no typed command at all — previously rock-solid 27/27 aligned) FAILED**: ours
diverged at n=3, skipping straight to the `A>` redraw loop instead of the date-prompt sequence.
Falsified two hypotheses in turn: (1) *stack imbalance* — ruled out, the code never left an
unbalanced push. (2) *hardcoded `$DA40` buffer instead of the caller's own DE* — CONFIRMED a
real bug (a plain-boot call reaches `$4462` with `DE=$DC5B`, name "COMMAND COM", which my first
cut never read, searching zero-bytes instead and wrongly returning not-found for a file that
demonstrably exists) — but fixing it (read/write via the caller's own DE uniformly) did NOT fix
the regression. Deeper diagnosis found a THIRD, previously uncharacterised calling instance:
`$4462` is reached with `DE=$DC5B` ("COMMAND COM", a boot-time self-check) and separately with
`DE=$DA40` for an "AUTOEXEC.BAT" existence probe — NEITHER of which the M21 investigation (which
only ever exercised `$4462` via the synthetic BDOSX exerciser's SETDTA/SFIRST/SNEXT/FOPEN path)
had characterised. Even with the DE-fix, the "COMMAND COM" self-check now correctly finds the
file (`FAT_FIRSTCLUS=$003E`, `FAT_FILESIZE=$1980`=6528, matching COMMAND.COM's real size) and
writes stock's own observed field pattern into `$DC5B+14..+31` — yet the boot sequence still
derails downstream, meaning either (a) stock's real fill contract for THIS calling instance
differs from the one instance already validated (the typed-command case), or (b) writing into
`$DC5B+14..+31` collides with something else at that address for this specific caller. Neither
is pinned; both remain open.
· **Why I stopped instead of continuing to iterate solo:** this is the CORE, previously
fully-working M13-M20 boot-to-`A>` achievement regressing — the highest-stakes invariant in the
whole Tier-2 track. Per the hard-stop rule ("a regression I can't get green"), guessing a third
time without a decisive falsify-first isolation of THIS specific caller's real contract risks
shipping something subtly broken. The spec's characterisation, despite passing its OWN written
acceptance criteria, missed a real calling instance because it was only ever validated against
one synthetic exerciser run, not a full plain-boot regression sweep — a process gap worth
noting for any future "believed implementation-ready" spec: run the FULL regression suite
(including the ones with nothing to do with the new feature) BEFORE, not after, declaring done.
· **Undo:** fully reverted (`git checkout -- disk/kernel.asm disk/driver.asm disk/fat.asm
disk/equates.inc`); confirmed back to known-good (`make unit-test` 19/19, `make probe` all pass,
`callseq --at 0x0100 --log 0x0005 --keys '\r' --keys-at 22`: 27/27 ALIGNED, NO DIVERGENCE).
`disk.rom`/kernel.asm/driver.asm/fat.asm/equates.inc are byte-identical to before this span
started. Nothing landed; tier2-m21-spec.md updated with this finding, awaiting the user's
direction on how to characterise the remaining $4462 calling instances.

**[M21 / §5 — all four open characterisation items resolved, doc updated in place]** Follow-up
span (user-authorized characterise-further-only, no asm) resolved every §5 open item in
[tier2-m21-spec.md](tier2-m21-spec.md): (1) kernel↔`$4462` division of labor pinned via a new
`writewatch` harness mode (mirrors `readwatch`, write-side, PC-region-classified + BC/DE/HL) —
kernel LDIRs the search-FCB header (+0..+13) from `$D880`, PAGE1 fill code (spanning `$42AA`
then `$4488-$44C8`, which on OUR rom is `dskio_rd` + `getdpb`'s body) owns +14(high)..+31; (2) a
concrete relocation plan for the colliding 153-byte span (`fdc_di_save..getdpb`,
`$445B-$44F3`) into the `$4C77` free-tail region (468 B available, all symbol-based callers,
no hardcoded-address linkage risk, net-zero ROM size preserved); (3) `$47B2`'s two call
contexts (`DE=$DA40` runtime / `DE=$DC5B` boot) are the same FCB-shaped structure at two
different instances, byte-identical caller-supplied contract ours==stock going INTO `$47B2`,
and — new fact — temporally disjoint call chains (`$C51D` never fires on a plain boot), so
M21b needs no context branch; (4) exact exit contract pinned at `$C51D` (not `$D88A`, which
turned out to be a shared multi-purpose exit trampoline unusable for disambiguation) —
`AF=$0142 HL=$0480`(bytes transferred) on success, clear `$F306`. **Confidence: high on all
four; ONE explicitly flagged residual open item for the implementation pass** (not a
characterisation gap): whether the boot contract (`k47b2_done`, pinned separately at
COMMAND.COM's `$0100` entry) and the runtime contract (`$C51D`) are simultaneously satisfiable
by a SINGLE generic body — both are independently solid, never mutually cross-checked. Spec
believed implementation-ready pending human sign-off. · **Undo:** doc-only + one small harness
addition (`disk_probe_diff.py writewatch`, additive, no existing mode touched); no asm changed.

**[BDOSX tooling / HARD-STOP — ours cannot RUN an arbitrary named `.COM`, even though DIR finds
it]** Building the signed-off [tier2-bdos-exerciser-spec.md](tier2-bdos-exerciser-spec.md) tool
(`BDOSX.COM`), typing `BDOSX` at the `A>` prompt on **ours** never loads it: `capture --at 0x0100
--nth N` shows COMMAND.COM's own signature byte (`$0102`=`$05`) both immediately before AND
immediately after the typed command (`t=8.22` then `t=24.58`) — BDOSX.COM's own signature
(`$0102`=`$01`) never appears at `$0100` at all. `screen` corroborates: ours shows a **silent
return to a fresh `A>` prompt** (`ROW09 A>BDOSX` / `ROW11 A>.`), stock shows the program **still
running** (parked in its self-loop, no new prompt) at the same settle time. **Ruled out by a cheap
falsify-first check:** `DIR` lists `BDOSX BIN`/`BDOSX COM` byte-identically on both machines (dir-
search — M19's mechanism — sees the injected files fine on ours). So this is NOT a `fat12_add`/
dir-search problem; it's specifically **"COMMAND.COM loads and runs a typed, non-self program
name"** — a code path every prior M13-M20 milestone never exercised (they only ever proved
COMMAND.COM loading *itself*, via the `k_47B2` loader). **This is a real, previously-unknown Tier-2
gap, not a tooling bug** — confidence: high (the DIR-vs-load split is decisive, not inferred).
· **Why I stopped instead of fixing it inline:** this is a scope surprise outside the signed-off
exerciser spec (which assumed "type a command name" was already a proven-safe mechanism, per
precedent in `disk_probe_diff.py`'s own docstring). It's also a fork the user should weigh in on:
(a) root-cause and fix the "run a named program" path as a new milestone before the exerciser can
work at all, (b) redesign `BDOSX.COM`'s launch mechanism to reuse an ALREADY-proven load path (e.g.
temporarily standing in for `COMMAND.COM` itself on a throwaway disk, since that exact path is
proven byte-identical), or (c) park the exerciser and prioritize differently.
· **Undo:** nothing landed in `disk.rom` or `kernel.asm` — this is 100% probe/tooling code
(`probes/disk/bdosx.asm`, `probes/disk/build_bdosx_disk.py`) plus one small, backward-compatible
harness extension (`disk_probe_diff.py capture --arm-check-val`, opt-in, default off, every
existing `capture` repro unaffected — verified by re-running the M20 `capture --at 0xC6C5` repro
unchanged). No revert needed; safe to leave in tree pending the user's decision.
· **UPDATE 2026-07-02 — ROOT CAUSE PINNED (Fable-solo dispatch, user chose "root-cause as a new
milestone").** TWO independent broken page-1 entries on the "load a typed .COM" path, either alone
fatal: **RC-1** kernel FOPEN's dir-fill entry `$4462` lands mid our own `fdc_di_save` code (`ld
($E299),a; ret`) — the FCB is never transformed to opened form (also clobbers our IFF-save cell on
every runtime FOPEN, a latent bug in its own right). **RC-2** kernel RDBLK's generic record-read
entry `$47B2` — previously assumed COMMAND.COM-boot-only — is proven the GENERIC read entry (called
identically for any program); our `k_47B2` body hardcodes re-loading "COMMAND COM" via our own
mini-BDOS regardless of the caller's real FCB, so it silently re-loads the resident image instead
of the typed program. A causal poke (stock's exact post-FOPEN FCB image into ours) proves RC-2 is
independently fatal even with a perfect FCB. Full evidence + proposed fix shape (two ordered
milestones, M21a prerequisite for M21b) promoted to
[tier2-m21-spec.md](tier2-m21-spec.md). **WARNING flagged to the user:** unlike every prior
M13-M20 fix, M21a is NOT a free-`$00`-pad veneer — `$4462` sits inside LIVE `fdc_di_save` code, so
it needs 3b-relocation-class treatment (net-zero, no canonical shifts, more surface area than a
3-byte `jp`). Awaiting sign-off before implementation.

**[M20 / bytes-free footer · LANDED — REVISION 3, the `$F306` dispatcher-flag fix]** Following
the second hard-stop below, dispatched a Fable-SOLO investigation (no Opus this time — the user's
explicit follow-up to the earlier dual-dispatch trial, to test whether Fable alone is reliable at
this phase) to find the ACTUAL mechanism, since all three prior hypotheses (trust our `HL` / scan
via `IY` / scan via `DPB+19`) were excluded. **Result: root cause pinned and CAUSALLY PROVEN (not
inferred) in one span.** The RAM kernel's common BDOS-exit path (`$D8AA-$D8BD`, identical ours==
stock) gates `HL` passthrough on dispatcher flag `$F306` (set to `$01` on every BDOS-call entry,
per [tier2-gdate-spec.md](tier2-gdate-spec.md)'s earlier pin): if a handler leaves it set, the exit
path overwrites `HL` with `H:=B,L:=A` (CP/M single-byte-result mirror) instead of passing it
through. Stock's `$505D` clears it; ours never did in either falsified revision — explaining the
EXACT wrong constant (`$0202`=514, a mirror of our own correct `A`/`BC`) observed identically both
times. Proven with a poke test (`$F306:=0` at the exit-path anchor flips the branch; the handler's
real `HL` then survives to `$C6C5`). Corroborated in-tree: `gdate_handler` already clears `$F306`
(previously commented "harmless stock parity" — it is in fact load-bearing).
· **Fix:** Revision 1's original register-only `getalloc_body` (unchanged — it was correct all
along) plus one store: `xor a / ld ($F306),a` before `ret`, loading the final `A := sectors/cluster`
AFTER the clear. No buffer, no `IY`, no `DPB+19` — Revision 2's whole premise was a red herring
(those reads are stock's handler's own INTERNAL scratch, confirmed page-1-only via
`callwatch --machine stock --in-func 0x1b`; nothing downstream of the `ret` ever reads them).
· **Verified, all pass:** `capture --at 0xC6C5` → `A=$02 BC=$0200 DE=$02C9 HL=$016F` byte-identical
to stock (only `IY` differs, confirmed benign); screen arbiter → `375808 bytes free` byte-identical
to stock; `callwatch --in-func 0x1b` → `getalloc_body` runs to its own `ret` (not the stub tail);
27/27 boot BDOS parity, zero divergence; `make unit-test` 19/19; `make probe` → DSKIO byte-identical
to CF-3300, BASIC/tape probes pass; `disk.rom` == 16384 B. `DIR` now matches stock 100%
byte-for-byte. Full detail: [tier2-m20-spec.md](tier2-m20-spec.md) §11.
· **Model-split verdict (this trial's data point):** Fable-solo, with NO Opus cross-check, found in
one dispatch what a prior Opus+Fable DUAL dispatch missed entirely (both agents in that trial
proposed the wrong mechanism). This is the strongest evidence yet for [[opus-vs-sonnet-model-split]]'s
open question — worth weighing heavily when deciding whether Fable becomes the default for
investigation-phase zerobas work.
· **Confidence:** HIGH — causally proven by a poke test, not inferred from correlation; independently
corroborated by pre-existing code (`gdate_handler`) that nobody had connected to this bug before.

**[M20 / bytes-free footer · SECOND HARD-STOP — REVISION 2 (IY + DPB+19 resident-FAT-buffer design)
IS ALSO FALSIFIED; the true mechanism is still unknown]** User signed off (2026-07-02) on a REVISED
design synthesized from a one-time dual-dispatch trial (Opus + Fable, run in parallel on the same
characterisation task per [[opus-vs-sonnet-model-split]]'s trial). Fable's pass was clearly more
thorough — fresh black-box probes pinned a per-drive DPB+19 FAT-pointer field (stock: `DRVA_DPB+19/+20`
= `$E595`) that Opus's pass never surfaced, and its RAM-placement recommendation (`FATBUF equ $E820`)
held up against a direct read of `disk/init.asm`, whereas Opus's own recommended address (`$E760`)
turned out to collide with live scratch cells (`BOOT_SV_A8`/RST-30 saves/`RDBLK_*`/`P1_BLIT`/`DRV_TRAMP`)
that Opus's own memory-map pass had missed — verified directly against source before adopting either.
Built Fable's design exactly: `getalloc_body` now reads all `secPerFAT` FAT sectors into a new resident
`FATBUF` ($E820, 1536 B) via our own `read_sector` (never stock's `$E595`), counts free entries by
scanning the contiguous buffer directly (no straddle case), and sets **both** `IY := FATBUF` and
`(DRVA_DPB+19) := FATBUF` before returning the already-validated A/BC/DE/HL. Build was clean (`disk.rom`
16384 B, `make unit-test` 19/19).
· **Falsified anyway.** `capture --at 0xC6C5` confirmed `IY=$E820` (wired correctly) and `FATBUF` held
real FAT bytes (not stock's zero-filled equivalent) — the wiring itself worked. But the footer still
printed **`526336 bytes free`** (514×2×512), byte-for-byte the SAME wrong value as the ORIGINAL falsified
build that never touched IY or DPB+19 at all. Fable's own R1 risk flagged this exact possibility and
recommended re-running the HL-sentinel falsify test as build step 1 — I ran it (should have run it
*before* the full screen check, not after): forced `HL=$BEEF` right before `getalloc_body`'s `ret`;
`$C6C5` still showed `HL=$0202`, IDENTICAL to the original (pre-IY-wiring) falsified build's sentinel
result. **⇒ the downstream free-count value is not derived from our returned HL, not from IY, and not
from DPB+19 either — every hypothesis both agents proposed is now excluded.** Something else entirely
(an unidentified DPB field, a different BDOS call, or logic that doesn't consult `$1B`'s outputs at all
for this figure) produces the `514` constant, unaffected by anything `getalloc_body` does.
· **Action taken:** reverted the uncommitted asm (`git checkout -- disk/kernel.asm disk/equates.inc`);
rebuilt + `make unit-test` 19/19 confirmed a clean baseline. `disk/docs/tier2-m20-spec.md`'s header now
points at a superseded §11 (Revision 2) — a Revision 3 needs fresh investigation, not another design
tweak on the same premise.
· **Model-split note (this trial's second data point):** neither Opus's nor Fable's investigation — despite
Fable's materially deeper probing that correctly found real bugs in Opus's proposal — correctly diagnosed
the ACTUAL mechanism. Both were confidently wrong about what the kernel reads. Worth weighing when the
user decides on the Fable-solo trial: depth of investigation reduced errors in the DESIGN's internal
consistency (buffer placement, contiguity) but did not catch that the entire premise (IY/DPB+19 are what
downstream reads) was itself wrong — that only surfaced via build + falsify-first, not via more reading.
· **Confidence:** HIGH that the premise is wrong (direct, repeated falsification); ZERO on what the real
mechanism is — this needs a fresh characterisation span (anchor+align from scratch on what actually
determines the `$C6C5`-time HL, not an incremental fix to the current design).

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

