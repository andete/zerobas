<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 M26 spec — the mutation/random/absolute-I/O block (`$13 FDEL` / `$17 FREN` /
`$21 RDRND` / `$22 WRRND` / `$2F RDABS` / `$30 WRABS`)

**Status: FREN (`$17`) LANDED 2026-07-03 (§6). FDEL/RDRND/WRRND/RDABS/WRABS
still CHARACTERISED ONLY, not implemented — same stop-for-sign-off posture
as before for those five.** Per [[spec-before-implementation]] this is a
**new-routine-class** milestone (like [tier2-m19-spec.md](tier2-m19-spec.md)),
not a self-approvable veneer-class fix: six BDOS functions, none wired at
the start, one pair (RDRND/WRRND) showing a risk shape not seen in any prior
milestone. Resume board: [tier2-STATE.md](tier2-STATE.md). This picks up the
M26 candidate first logged in
[tier2-m24-fclose-multicluster-spec.md](tier2-m24-fclose-multicluster-spec.md)
("M25 RESOLVED" §, pre-existing divergences) and characterised further in
that doc's "M26 CHARACTERISATION" section (FREN only); this spec extends
that characterisation to all six functions and proposes fix shapes.

## 1. Goal

Wire the six BDOS functions [tier2-bdos-remaining-spec.md](disk/docs/tier2-bdos-remaining-spec.md)
§5.3 groups as the "mutation + random + absolute-I/O block", exercised end to
end by `BDOSX3.COM` (`probes/disk/bdosx3.asm`) records 14-23:

| record | func | what it does |
|---|---|---|
| 14 | `$17` FREN | old `BDOSXW  TMP` at FCB+1 → new `BDOSXR  TMP` at FCB+17 (CP/M rename convention) |
| 15 | `$13` FDEL | delete the freshly-renamed `BDOSXR  TMP` |
| 16-17 | `$0F` FOPEN | reopen `BDOSX   BIN` (already working, M21a/M25) |
| 18 | `$21` RDRND | random field r0=2 (FCB+33..35, direct poke, no BDOS call) → record 2 to `rdbuf2` |
| 19 | `$22` WRRND | r0=1 → overwrite record 1 from `wrpat` |
| 20 | `$21` RDRND | r0=1 → read back what WRRND wrote (round trip) |
| 21 | `$10` FCLOSE | (already working, M24) |
| 22 | `$2F` RDABS | L=0 (drive A:) H=1 (1 sector) DE=0 (sector 0) → `absbuf`, 512 B |
| 23 | `$30` WRABS | same regs, writes `absbuf` back — deterministic, disk unchanged |

Success = BDOSX3 records 14-23 zero-diff against stock (status registers +
the renamed/deleted directory state + `rdbuf2`/`wrpat` content + `absbuf`
content), same acceptance bar as M19/M21/M24/M25.

## 2. Characterisation (falsify-first, no kernel code decoded — black-box
`callwatch --in-func <C>` per function, all runs on `/tmp/zerobas_bdosx3.dsk`,
correctly anchored `--arm-check-addr 0x0102 --arm-check-val 0x03` — BDOSX3's
own compiled-`.com` fingerprint byte, NOT reused from any other exerciser)

`grep -rn "fren\|fdel\|rdrnd\|wrrnd\|rdabs\|wrabs" disk/*.asm` → **zero hits**
for all six. No hand-written body exists for any of them; every landing
described below is either a coincidental slide into unrelated code or a
partial walk into a REAL routine written for a different function.

### 2.1 `$17` FREN — confirmed simple NOP-slide (LOW risk, straightforward fix)
`callwatch --in-func 0x17` → **one** page-1 hit, `$4392`. That address falls
mid-body inside `fdc_rd_n1`/`fdc_rd_n2` (disk/driver.asm:206-219, the
low-level FDC read-status error decoder — `fdc_rd_n1 EQU $438C` / `fdc_rd_n2
EQU $4395`), entirely unrelated to directory rename. Same signature as
M13/M19/M21/M22b's un-wired entries: the kernel's real `$17` dispatch target
in page-1 is unmapped, the CALL lands wherever that byte offset happens to
decode from our unrelated FDC code, and falls back into the kernel having
touched nothing real. **Explains BDOSX3 record 14's `A=$FC`** (a stray
status byte from the FDC decoder, not a real FREN result).

### 2.2 `$13` FDEL — walks a REAL routine fully, purpose unconfirmed (MEDIUM
risk — needs a `trace` pass before assuming NOP-slide)
`callwatch --in-func 0x13` → **12** page-1 hits, `$435E`-`$438A`, each
entered exactly once, in address order. `$435E` is `fdc_rd_wait`'s real,
intended entry point (disk/driver.asm:174-219) — not a mid-body landing.
The PC sequence walks the ENTIRE wait/read/status-decode chain
(`fdc_rd_wait → fdc_rd_byte → ... → fdc_rd_drain → fdc_rd_status → fdc_rd_n1`)
exactly once, consistent with one real, successfully-completing low-level
sector read — this could be (a) a genuine sector read our kernel's own
SFIRST/SNEXT-style directory scan performs while searching for the FDEL
target name (SFIRST/SNEXT, M19, already legitimately calls `read_sector`),
in which case FDEL rides an existing wired primitive for its search half and
only its final "mark deleted" step is un-wired and un-observed by this probe
(a single directory-scan pass may find zero matches if FDEL's search FCB
isn't threaded through correctly, silently no-op'ing); or (b) a coincidental
full walk through the SAME code region if the un-wired `$13` dispatch target
happens to numerically land exactly on `fdc_rd_wait`'s entry byte and the
polling loop's own exit conditions happen to terminate it after one pass
regardless of real FDC state. **Not enough to tell apart from `callwatch`
alone** — the two hypotheses have different fix shapes (a real primitive
riding correctly vs. another coincidental slide) and only differ in whether
directory state changed. First implementation step for this function must
be a `capture --mem <root-dir-sector-buffer>` diff (does the target dir
entry's first byte become `$E5`, the CP/M delete marker, or not) before
writing any code — do not assume either hypothesis.

### 2.3 `$21` RDRND / `$22` WRRND — IDENTICAL shared landing, partial walk
into REAL M25 routines (HIGH risk — flagged for careful sequencing)
`callwatch --in-func 0x21` and `--in-func 0x22` produce **byte-identical**
PC lists: `$5495,$549C,$549F,$54A1,$54A4,$54DD(×2),$54E0,$54E4,$54E8,$54EB,
$54F0` then `$7832,$7836,$7839,$783C,$783F,$7842,$7845(×4),$7849,$784C`.
Symbol brackets:
- `$5495-$54F0` falls between `bdos_seqread_body` (`$548E`) and
  `bdos_create_body` (`$54B1`) — i.e. mid `bdos_seqread_body`'s own code —
  and touches `frs_mul_body` (`$54DD`, entered twice; presumably a
  record→sector multiply helper used by the M25 read path).
- `$7832-$784C` is `k_47B2`'s body and its `k47b2_rdloop` (the M21b RDBLK
  veneer, disk/kernel.asm:527+) — a DIFFERENT, unrelated canonical entry's
  real body.

Two things stand out and BOTH need resolving before implementation:
1. **RDRND and WRRND land at the exact same PC trace** — strong evidence
   they, too, share ONE currently-unmapped page-1 dispatch address (the
   `$477D`-shared-WRSEQ/RDSEQ pattern from M25 repeating for the random-access
   pair), rather than being two independently broken entries that coincidentally
   agree.
2. **The landing partially executes REAL, non-garbage routines** — unlike
   FREN's clean NOP-slide into an unrelated decoder, this walks through
   actual read/write machinery (`bdos_seqread_body`, `frs_mul_body`) AND a
   completely different veneer's body (`k_47B2`/`k47b2_rdloop`). This is
   NOT simply "does nothing" — it may perform a real (but wrongly-addressed,
   since nothing computed the random-field-to-record conversion first)
   sequential read/advance, silently mutating `BDOS_RECIDX`/`FAT_CURCLUS`/
   the DTA content in a way a later, correctly-implemented RDRND/WRRND could
   inherit as corrupted starting state. **Do not implement a fix for RDRND/
   WRRND without a `trace --regdump` pass confirming exactly what shared
   state this un-wired landing mutates** — this is the same class of
   silent-corruption risk M24/M25 spent real effort distinguishing from a
   true fix (the two reverted M25 attempts).

### 2.4 `$2F` RDABS — NOP-slide into an existing net-zero stub (LOW risk)
`callwatch --in-func 0x2f` → two hits: `$46BA` (61 bytes into `bdos_create`'s
body, `$467D`) then `$7831`, which is exactly `k_46C8` — an existing,
already-in-tree net-zero stub (`k_46C8: ret`, disk/kernel.asm:504) reserved
for a canonical address with no current use. The slide walks a few bytes of
`bdos_create`'s unrelated body, then falls into `k_46C8`'s bare `ret`,
ending the call having done nothing. Simple shape, same fix pattern as FREN.

### 2.5 `$30` WRABS — NOP-slide into the TAIL of a real routine, false
success status (LOW-MEDIUM risk — check the exit contract carefully)
`callwatch --in-func 0x30` → three hits, `$4720,$4724,$4727`, landing inside
`bdos_seqwrite`'s body (`$46EE`) and running straight into `bsw_ok`
(`$4727`, disk/kernel.asm:1218 area) — `bdos_seqwrite`'s own SUCCESS exit
path. This means WRABS currently returns a **false success status** (`A=$00`,
not an error) while writing nothing to the target absolute sector — a
correctness bug that could pass a status-only check while corrupting no
disk state (the write to `absbuf`'s target sector 0 never happens on ours),
but must be understood exactly before wiring a real body, since the fix
must ensure the real veneer's own exit does NOT fall through into
`bsw_ok`'s cell-clearing side effects (`bsw_ok` mutates write-side state
cells meant for WRSEQ/WRRND — falling through it from an unrelated
dispatch is itself a second small bug worth confirming is harmless or not
during implementation).

## 3. Risk ranking + proposed implementation order

1. **FREN** (`$17`) — simplest, fully localised NOP-slide, no shared-state
   risk. Fix shape: a `fren_body` veneer wired at the kernel's real `$17`
   dispatch address (not yet located precisely — `callwatch` only proves
   the LANDING point, not the dispatch instruction's own address; that
   needs a `trace --window` immediately before `$4392` to find the actual
   `call`/`jp` site, same technique used for M19/M21/M22b). Reuses M19's
   `fat_find`/name-match machinery to locate the old name, mirrors 8.3 name
   fields, does not need FAT/allocation changes (rename, not resize).
2. **RDABS** (`$2F`) — simplest of the remaining, isolated NOP-slide into an
   inert stub, no partial real-code execution to reason about. Straightforward
   `read_sector`-based veneer (LBA sector from DE, count from H, drive from
   L, target the FCB's DTA) — very close in shape to the low-level primitive
   Tier-1 DSKIO already implements.
3. **WRABS** (`$30`) — same shape as RDABS (mirror write), plus verify the
   `bsw_ok` fall-through side effect noted in §2.5 is harmless before or
   after wiring the real veneer.
4. **FDEL** (`$13`) — needs the `capture --mem <dir-sector>` disambiguation
   in §2.2 FIRST; likely rides M19's SFIRST/SNEXT-family search machinery
   (reuse, don't reimplement), with only the delete-marker write (`$E5` at
   the entry's first byte) as new work.
5. **RDRND / WRRND** (`$21`/`$22`) — LAST, and only after a `trace --regdump`
   pass per §2.3 confirms what the current mis-landing mutates. Likely fix
   shape (tentative, NOT signed off): a shared `rdrnd_wrrnd_body` mirroring
   the `wrseq_body` dispatch-on-`BDOS_WRMODE` pattern from M25, PLUS new
   code to convert the FCB's random field (r0/r1/r2, +33..35) into the
   record index `bdos_seqread`/`bdos_seqwrite` expect (`BDOS_RECIDX`) and
   the corresponding cluster/sector position (`FAT_CURCLUS`/`FAT_CLUSSEC`) —
   this conversion does not exist anywhere in the current source (confirmed
   by the same `grep` in §2 sweep) and is the real new-code centre of this
   milestone, comparable in scope to M25's `fopen_fill_body` read-iterator
   seed but for arbitrary mid-file positioning rather than open-time reset
   to record 0.

## 4. Explicit non-goals for this spec

- No FAT allocation/extension logic beyond what FDEL's delete-marker write
  needs (freeing the chain is a CP/M-1-compatible detail to confirm against
  the published FCB contract, not new allocation code — MSX-DOS FDEL does
  not need to walk/free the cluster chain itself for a single-cluster test
  file, per `disk/PROVENANCE.md` §FCB layout; if BDOSX3's scratch file spans
  more than one cluster this assumption needs re-checking before FDEL is
  implemented).
- No change to `bdos_seqread_body`/`bdos_seqwrite_body`/`k_47B2` themselves
  — RDRND/WRRND's fix should REUSE them (matching the M25 precedent of a
  thin dispatch veneer over the existing engine), not duplicate their logic.
- No attempt to fix all six functions in one commit. Per §3's ordering,
  each function should land as its own falsify-first micro-milestone with
  its own re-verification pass (BDOSX3 zero-diff for that record, plus the
  full standing regression suite: BDOSX/BDOSX2/BDOSX0/boot callseq/DIR
  screen/`make unit-test`/`make probe`), same discipline as M19/M21/M24/M25.

## 5. Open questions for sign-off

1. Does the proposed order (FREN → RDABS → WRABS → FDEL → RDRND/WRRND) match
   your risk tolerance, or would you rather front-load the highest-risk
   RDRND/WRRND investigation (§2.3's `trace --regdump` pass) before touching
   anything, on the theory that its answer might also inform FDEL's dir-scan
   question in §2.2?
2. OK to proceed one function at a time without a fresh sign-off per function
   (i.e. treat this spec as covering the whole block), or do you want each
   function's actual implementation to come back for its own review given
   RDRND/WRRND's shared-state risk?
3. FDEL's cluster-chain-freeing assumption (§4, first bullet) — confirm
   BDOSX3's `BDOSXR  TMP` scratch file is single-cluster before treating
   "just write `$E5`" as sufficient, or should this spec wait for that check
   before being considered final?

## 6. FREN (`$17`) — LANDED 2026-07-03

Given repeated "continue" and this being the explicitly offered lowest-risk
default (§3 item 1), proceeded with FREN alone; the other five functions in
this block are UNTOUCHED and still require the sign-off in §5.

**Refined characterisation before implementing:** `trace --resync` (anchored
at BDOSX3's call n=17, the FREN call) found the REAL fork — `$4392: ex
af,af'` diverges (stock jumps to its own real FREN body from this exact
address; ours falls through) — confirming `$4392` is genuinely the fixed
inter-slot dispatch address the kernel calls for `$17`, not merely a
coincidentally-touched address. This upgrades §2.1's risk read slightly:
`$4392` isn't dead/unrelated space, it's byte 56 of the 74-byte
`fdc_read_data` routine (disk/driver.asm) — the shared low-level FDC
sector-read primitive used by EVERY disk read on the whole ROM. Checked
before touching it: `fdc_read_data` has exactly ONE caller
(`call fdc_read_data` in `fdc_rp_attempt`, symbolic) and no external code
jumps into its middle — fully self-contained, so it relocates cleanly with
no manual call-site fixups (matching the M21a `fdc_di_save` precedent).

**Fix:** relocated the 74-byte `fdc_read_data` body verbatim to
`fdc_read_data_body` (disk/kernel.asm free tail, appended after
`wrseq_body` — the file's genuine end, not the tightly-packed
write_sector/GDATE corridor, which turned out to have no slack for a
74-byte insert and produced a real "64KB limit passed" build error on the
first attempt). `disk/driver.asm`'s `fdc_read_data` is now a 3-byte `jp
fdc_read_data_body` thunk, followed by `ds $4392 - $, $00` / `k_4392: jp
fren_body` / `ds $43A4 - $, $00` — net-zero, so `fdc_write_phys`
(the very next real routine) stays at its exact original address.

**`fren_body`** (disk/fat.asm, next to `fopen_fill_body`): reuses
`fat_mount`/`fat_find`/`write_sector` exactly as designed in §3 item 1 —
`fat_find` on the FCB's old name (+1..11) returns the matched directory
entry inside `SECTOR_BUF` with `FAT_DIRSEC` holding its sector number;
`fren_body` overwrites the entry's 11-byte name field in place with the
new name (FCB+17..27) via `ldir` and calls `write_sector` to persist it.
Not-found and I/O-error branches both clear `$F306` per the M20 rule and
return `A=$FF`/`Cy=1`.

**Verification:**
- BDOSX3 record 14's own status byte (`regs+14*8+1` = `$0446`) — the
  originally reported `A=$FC` — now reads `$00` on both stock and ours:
  **zero-diff**, confirmed by `capture --mem 0x3b0:0x125` before/after
  comparison (36 diverging bytes pre-fix → 24 post-fix, all 13 removed
  bytes clustered around `$0446`/`$044E`/`$045E`/`$3B1`/`$3BF-3D0`
  region). One byte (`$03C8` = FCB+24) newly visible in the post-fix diff
  set turned out to be the SAME already-logged FCB-mirror-field gap from
  the M25 doc (FCB+16/17/20/21/24/28/29) — confirmed by offset match, not
  a new regression; it's only visible now because FREN succeeding changes
  which real code path the downstream still-un-wired FDEL/FOPEN/RDRND take.
- Records 15+ (FDEL onward) remain diverging, as expected — those five
  functions are still un-wired per §2, untouched by this fix.
- **Tier-1 regression (critical, since `fdc_read_data` is shared by every
  disk read on the ROM):** `make probe` — DSKIO byte-identical to the
  CF-3300 reference (sectors 0 and 14), BASIC probe green, tape probe
  green. `make unit-test`: 19/19.
- Boot `callseq` (27 shared calls to `A>`): aligned, zero divergence.
- `DIR` `screen` (both machines): byte-identical, including the `41 files`
  / `375808 bytes free` / `A>.` footer and the full VRAM hex dump.
- Phase-1 BDOSX (`--mem 0x400:0x180`, RDSEQ content): 48 diverging bytes
  both before AND after this fix (byte-count identical) — confirmed via
  the git-stash/rebuild-baseline technique that this is the SAME
  already-logged pre-existing RDBLK-content gap from `$500`+ (M25 doc
  "M26 candidate" item (b)), unaffected by the FREN fix.
- BDOSX2: memory zero-diff (0 of 112 bytes); a benign `AF` flag-only
  register difference, consistent with prior BDOSX2 runs.
- BDOSX0: `callseq --log 0x0005` 43/43 shared calls aligned, no divergence.

`disk.rom` stays exactly 16384 B (no wrap warnings after moving the
insertion point to kernel.asm's genuine free tail). Changed:
disk/driver.asm (relocation thunk + veneer), disk/kernel.asm
(`fdc_read_data_body`), disk/fat.asm (`fren_body`).

---

Ground truth: [tier2-STATE.md](tier2-STATE.md). Judgment-call log for this
characterisation pass: [tier2-review-queue.md](tier2-review-queue.md) (M26
entry). Design/fix-shape precedents: [tier2-m19-spec.md](tier2-m19-spec.md)
(SFIRST/SNEXT reuse), [tier2-m21-spec.md](tier2-m21-spec.md) (generic body
trusting prior-call state), [tier2-m24-fclose-multicluster-spec.md](tier2-m24-fclose-multicluster-spec.md)
+ its "M25 RESOLVED" section (shared-dispatch-by-internal-flag pattern this
spec's RDRND/WRRND proposal reuses).
