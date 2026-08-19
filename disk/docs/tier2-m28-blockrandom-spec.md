<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# M28 — block/random completion: real $23 FSIZE + $26 WRBLK  (APPROVED — 2026-07-04)

Status: **APPROVED, implementation authorized (Sonnet 5).** Written per the spec-before-implementation
rule after the user chose "bundle $23 + $26 as a block/random pass" (2026-07-04), following the
$23-FSIZE characterisation (confirmed BUG: found-blind stub) and the F5 well-formed-BDOSX groundwork.
Both agent-fed sections — the [LANDED-A] oracle contract and the [LANDED-B] dispatch entries — landed
and are folded in. **Sign-off decisions (§6): Q1 defer $27 · Q2 full past-EOF extend · Q3 sane shrink
(diverge from stock's bug, document + allowlist) · Q4 resolved ($DA40 kernel copy) · Q5 Sonnet 5.**

## 1. Goal & scope

Complete the two remaining random/block FCB functions to a faithful contract match with the
CF-3300 oracle:

- **$23 FSIZE** — currently a found-blind stub (constant `A=L=$03`, random-record field never set).
  Make it a real GET FILE SIZE: locate the file, set fcb+33..35 = ceil(size/128), return
  `A=L=0` found / `A=L=$FF` not-found.
- **$26 WRBLK** — currently accepts the call but does not persist (no disk write). Make it a real
  RANDOM BLOCK WRITE: position at the random record (r0..r2), write HL records of `record-size`
  bytes from the DTA into the file, extending it (cluster alloc + dirent size + FAT) as needed.

**Explicitly IN scope:** the two functions above + their dispatch wiring + acceptance-gate
allowlist/greening + disk-artifact verification + host unit tests where they add value.

**Considered, decision at sign-off (§6 Q3):** the **$27 RDBLK stream-from-0 un-simplification**
(make RDBLK honour r0..r2 like the new WRBLK). It shares the positioning helper this pass builds,
so it may be cheap to fold in — but it is a behaviour change to a working path and can regress the
COMMAND.COM-load fast path (k_47B2). Default: **defer** unless the incremental cost is trivial.

**Out of scope:** $24 SETRND already works for our purposes (rrnd_position reads r0 straight from
the FCB); multi-byte r1/r2 record numbers beyond what the oracle exercises; any FCB field the
oracle does not diff.

## 2. Evidence (what we know, graded)

**$23 FSIZE — CONFIRMED BUG (black-box, independently re-verified).** Ours returns constant
`A=L=$03` for found, **not-found** (absent BDOSX.BIN → stock `A=$FF`, ours `$03`), any dir slot
(44 mod 4 = 0 still 3), any size (5-record file still 3). Never writes fcb+33..35. Stock returns
`A=L=0` + r0=ceil(size/128) on found and `A=L=$FF` on not-found (map.grauw.nl `_FSIZE`; seasip:
dir codes belong to F_OPEN/CLOSE/SFIRST/SNEXT, never F_SIZE). See
[tier2-bdos-coverage.md](tier2-bdos-coverage.md:54).

**$26 WRBLK — NOT IMPLEMENTED (black-box).** Post-run image unchanged after a WRBLK; no persisted
random block write. See [tier2-bdos-coverage.md](tier2-bdos-coverage.md:56).

**Infrastructure that already exists (code map, our source):**
- **Dispatch pattern** — the RAM BDOS dispatcher (`$D831`; table `$D8BE + 3*C`) routes certain FCB
  functions to page-1 ROM canonical entries. `$21`→`$4788`, `$22`→`$4793` are `jp <body>` pad-wires
  in the `fat_find` corridor ([fat.asm:133](../fat.asm:133)/:137), pinned in M26 via black-box
  `trace --resync`. Entry contract (M26 §): kernel passes a 37-byte FCB **copy** at `$DA40`
  (copy+33..35 = r0/r1/r2, copy+32 = CR); the USER FCB is a separate address; exit `A=H=L=0`; CR
  (user fcb+32) := r0 as the one random-op side effect.
- **Random positioning helper** — `rrnd_position` ([kernel.asm:3107](../kernel.asm:3107)) seeds the
  file iterator to record r0 (target sector r0>>2, record-in-sector r0&3 → `RRND_RECSEC $E760`),
  `rrnd_sector` ([kernel.asm:3170](../kernel.asm:3170)) recovers the absolute sector. `wrrnd_body`
  ([kernel.asm:3214](../kernel.asm:3214)) already does the read-modify-write overlay + `write_sector`
  that WRBLK needs per-record. **$26 WRBLK ≈ loop `wrrnd_body`'s core HL times, advancing r0.**
- **Dir search** — `fat_mount` + `fat_find`/`dsm_found` ([fat.asm](../fat.asm)) locate an entry by
  exact 8.3 name and expose size via `FAT_FILESIZE` (entry+28..31). **$23 FSIZE ≈ fat_mount +
  fat_find(fcb+1..11) → r0 = (FAT_FILESIZE+127)/128 → store fcb+33..35 → A=0/$FF.**
- **Cluster allocation / file extend** — `fat_alloc_cluster`, `fat_dir_update` (updates dirent
  first-cluster + size) exist from the WRSEQ path; WRBLK's file-extension reuses them.

**ROM space — SOLVED.** Fresh-build dead-pad scan: **5305 B free at `$60EC-$75A4`** (kernel free
region before the `k_75A5` pin), + 2531 B at `$5602-$5FE4`, + 708 B at `$50E3-$53A6`, others. Two
bodies (~200-400 B) insert into the `$60EC` corridor via ds-anchored placement; `k_75A5` and all
downstream canonical addresses stay fixed (net-zero, ROM stays 16384 B). The FDC window
`$7F80-$7FBF` stays dead pad (unusable for code — registers alias it).

**[LANDED-A] Oracle contract for $26 WRBLK / $27 RDBLK** (Fable black-box, 2026-07-04; markers
[O]=observed, [C]=contract-derived). **Shared:** start byte-offset = **RR × RS**, RR = fcb+33..35
little-endian **24-bit** (r0,r1,r2 — r1 weight proven: r1=1 ⇒ record 256), RS = fcb+14..15
(0→128); transfer bytes = **(HL × RS) & 0xFFFF** (16-bit mod-64K truncation, silent); **CR
(fcb+32) and EX (fcb+12) are NEVER read/altered** by block ops (unlike $21/$22, which set CR:=r0 —
do NOT copy that here); fcb+26..27 untouched; fcb+28..31 track the last cluster accessed.
- **$27 RDBLK:** delivers min(request, ceil(size/RS)−RR) records; a partial tail record is a whole
  record, **zero-padded** in the DTA; HL_out = records actually read; **A = 0 iff HL_out==HL_in
  else 1**; **RR += HL_out (actual)**; start at/past EOF → A=1, HL=0, RR unchanged, DTA untouched;
  >64K request not rejected (transfers mod-64K).
- **$26 WRBLK:** A=0 success (disk-full A=1 is [C]-only, not provoked); **HL return = HL requested
  (preserved, carries no result)**; **RR += HL_requested** (read/write ADVANCE ASYMMETRY — RDBLK
  actual vs WRBLK requested — matches published wording); writing past EOF grows the file with a
  **contiguously-allocated FAT chain through the gap** (not sparse), gap bytes uninitialised (do NOT
  spec the garbage); **size = max(old, RR×RS + bytes-written)**; HL=0 & RR-beyond-EOF sets size to
  RR×RS with no data (A=0); **HL=0 & RR-below-EOF (shrink) is BROKEN on stock** (sets size but
  leaves the FAT inconsistent → the next FCLOSE returns A=$FF) — see §6 Q5.
- **Not pinned (out of black-box bounds):** RS<64 four-byte-RR rule; disk-full A=1 path; exact
  shrink-path FCLOSE-$FF mechanism. Reference exercisers + run images kept under /tmp + scratchpad.

**[LANDED-B] $23 / $26 canonical dispatch entries** (ours-only black-box, 2026-07-04 — gated
first-page-1-fetch watchpoint + live dump of OUR RAM dispatch table at `$D8BE + 3*fn` as a DATA
read; `trace` avoided so no stock code is decoded; ROM bytes read are OUR ROM only). Both functions
**ARE page-1-delegated** (dispatcher jumps into `$4000-$7FFF`) — neither is RAM-kernel-resident, so
the fix stays page-1-wired. Live table dump (self-checks against M26's `$21`/`$22`):

| fn | table @ | bytes | page-1 target | site |
|---|---|---|---|---|
| $21 RDRND | $D921 | `24 88 47` | $4788 | ✓ M26 cross-check |
| $22 WRRND | $D924 | `24 93 47` | $4793 | ✓ M26 cross-check |
| **$23 FSIZE** | **$D927** | **`24 1E 50`** | **$501E** | **dead-$00 pad** — wire in place (3a-style) |
| **$26 WRBLK** | **$D930** | **`25 BE 47`** | **$47BE** | **⚠ LIVE CODE** (mid-`ff_secloop`) — **3b-relocate** |

- **$23 → `$501E`: editable dead-$00 pad.** Sits in the `$50xx` kernel-entry corridor between
  `snext` (`jp snext_body` at `$5006`, ends `$5008`) and `k_504E`; `$5009-$504D` is
  `ds $504E-$,$00` pad ([kernel.asm:40](../kernel.asm:40)). A 3-byte `jp fsize_body` wires directly,
  RDABS/M26-style, no relocation. Entry regs: `A=$25, B=$00, C=$00` (NOT the fn number), `DE=$DA40`
  (kernel 37-byte FCB copy, name pre-filled), `SP=$DBFE`, `ret=$D88A`. Same dispatcher class as
  `$4788`/`$4793`. The current `A=L=$03` is our stub's own output, not a kernel-supplied constant
  (at entry `HL=$012D`=301, the kernel's pre-jump value, unrelated to the answer — the handler is
  expected to compute the record count itself).
- **$26 → `$47BE`: LIVE CODE — 3b-relocate `ff_secloop`, do NOT "repoint".** `$47BE` is
  `jr z, ff_notfound` **5 bytes inside** `ff_secloop` (the fat_find scan loop anchored at `$47B9`:
  `$47B9 ld hl,(FAT_DIRREM)` [3B] → `$47BC ld a,h` → `$47BD or l` → `$47BE jr z,ff_notfound`,
  [fat.asm:141](../fat.asm:141)). The unimplemented WRBLK currently nop-slides into that loop and
  returns **harmless-by-luck** — a latent accidental target, never exercised because COMMAND.COM
  does not call WRBLK during boot. **ARCHITECTURE CORRECTION (Opus verification pass, folded in):**
  the source agent's "repoint the `$D930` table entry" is WRONG for our design. **The `$D8BE` table
  is the relocated MSX-DOS-1 kernel's — the FIXED shared-kernel ABI ([kernel.asm:561-532](../kernel.asm:561)),
  not ours to edit.** We do not own the dispatch table; we expose `jp k_XXXX` **veneers at the
  kernel's fixed canonical addresses**, and when a canonical address **collides with our active
  code** the established fix is the **3b relocation pass** — relocate OUR colliding code out to the
  free tail (same technique as the FDC-window fix and M26's collision entries,
  [kernel.asm:568-529](../kernel.asm:568)), freeing the canonical address for a `jp wrblk_body`
  veneer. `$26`→`$47BE` is exactly such a collision. So: **relocate `ff_secloop` (position-free —
  reached only by label; internal `jr`s are all local) to the `$60EC` corridor, then pad `$47B9-$47BD`
  and place `jp wrblk_body` at `$47BE`** (see §3.1). Entry regs: `A=$26, B=$00, C=$00, DE=$DA40`
  (kernel FCB copy), `HL=$0001` (= requested record count, passed straight through), `SP=$DBFE`,
  `ret=$D88A`.
- **FCB pointer carrying r0..r2 (resolves §6 Q4): `DE=$DA40`, the kernel 37-byte FCB COPY** for BOTH
  functions (copy+33..35 = r0..r1..r2, copy+14..15 = RS). FSIZE writes the record count back into
  copy+33..35 (the kernel propagates the copy → user FCB on exit, per M26). WRBLK reads r0..r2 + RS
  from the copy and advances copy+33..35 by HL on exit. The USER FCB is at `$0300` (= DE at the
  `$0005` call). Which of {copy, user} stock actually leaves the count in is confirmed by the
  acceptance diff during impl, but the copy is the write target.

## 3. Fix design

### 3.1 Dispatch wiring  — the two functions differ (see [LANDED-B])

**$23 FSIZE — wire in place at `$501E`.** A 3-byte `jp fsize_body` replaces 3 bytes of the dead
`$00` pad at `$501E` (RDABS/M26-style, no relocation); the trailing `ds $504E-$,$00` shrinks by 3
and every canonical address past it stays fixed (net-zero). The `$23` table entry (`$D927 =
`24 1E 50``) already routes to `$501E` — no table change.

**$26 WRBLK — 3b-relocate `ff_secloop`, expose `$47BE` as a veneer.** `$47BE` is the kernel's FIXED
canonical WRBLK entry ([LANDED-B]); it collides with live `ff_secloop` code, so we free it the same
way M26 and the FDC-window fix free colliding canonical addresses — relocate OUR code, NOT the
kernel's table (which we do not own). Steps ([fat.asm:141-199](../fat.asm:141) is the block):
1. **Relocate the `ff_secloop`…(end of the fat_find scan block) body** out of the `$47xx` corridor
   into the `$60EC-$75A4` free tail, exactly like `fdc_entloop_body` ([kernel.asm:594](../kernel.asm:594)):
   move the label + body verbatim; it is position-free (entered only via the `ff_secloop` label from
   `fat_find_body` and the `jr ff_secloop` back-edge, and every internal target — `ff_entloop`,
   `ff_skip`, `ff_endmark`, `ff_notfound`, `ff_found` — is a local label the assembler recomputes).
   Confirm during impl that no fixed address other than `$47BE` points into the block (grep the
   `$47B9-$47FF` span for canonical `k_47xx` labels; expected: none between `k_47B2` and the next).
2. In the vacated corridor, `ds $47BE - $, $00` (pads `$47B9-$47BD`), then `k_47BE: jp wrblk_body`,
   then `ds <next-canonical> - $, $00` to re-anchor whatever label followed the old block — net-zero.
3. **Do NOT modify the `$D8BE` RAM table or `$47BE`'s kernel routing** — the kernel already jumps to
   `$47BE`; we are only changing what OUR ROM places there (loop code → `jp wrblk_body`).
Build assert: post-build `$47BE` = `jp wrblk_body` (`C3 <body>`); `ff_secloop` relocated verbatim
(old-vs-new ROM diff = only the moved bytes + the veneer, à la the FDC-window byte-purity proof);
no canonical address past the block moved.

Both bodies (plus the relocated `ff_secloop`) live in the `$60EC-$75A4` corridor (§2 / §4).

### 3.2 $23 FSIZE body  (`fsize_body`)
Entry per [LANDED-B]: `DE=$DA40` (kernel 37-byte FCB copy, name pre-filled at copy+1..11, receives
r0..r2 at copy+33..35), user FCB at `$0300`, `ret=$D88A`, `A=$25/B=$00/C=$00`. Logic:
1. `fat_mount` the volume (as bdos_open does). On mount error → `A=L=$FF`, ret.
2. `fat_find` the 11-byte name (fcb+1..11) via the existing dir-walk. Not found → `A=L=$FF`, ret.
3. On found: `FAT_FILESIZE` = size in bytes. Compute r0..r2 = ceil(size / 128) as a 24-bit count:
   `(size + 127) >> 7` (size is 4-byte; result fits 3 bytes). Store into fcb+33..35 (the field the
   trace confirms the caller reads back — user FCB and/or the `$DA40` copy; write whichever stock
   updates, verified by the acceptance diff).
4. `A=L=0`. Preserve any register the entry contract pins (§ from trace).
Reuses the dir-search wholesale; the only new code is the ceil-divide + field store (~30-50 B).

### 3.3 $26 WRBLK body  (`wrblk_body`)  — contract per [LANDED-A]
Inputs: RS = fcb+14..15 (0→128); count = HL; start = 24-bit RR = fcb+33..35. Byte budget =
(HL × RS) & 0xFFFF (mod-64K). **New shared helper needed: 24-bit positioning** — `rrnd_position`
today reads ONLY r0 ([kernel.asm:3112](../kernel.asm:3112)); WRBLK/RDBLK need the full RR. Extend it
(or add `rrnd_position24`) to take a 24-bit record number: target sector = RR>>2, record-in-sector
= RR&3, walk the FAT chain to that sector — same shape, wider arithmetic (~+20-30 B). Loop over the
byte budget, RS bytes per record, rec = RR, RR+1, …:
1. Position at `rec` via the 24-bit helper.
2. `rec` at/before EOF → read-modify-write overlay (reuse `wrrnd_body`'s core: `fat_read_file_sector`,
   overlay RS DTA bytes at `(rec&3)*128` into `SECTOR_BUF`, `write_sector`).
3. `rec` past EOF → **file extension**: allocate cluster(s) with `fat_alloc_cluster`, append
   **contiguously through any gap** (per [LANDED-A]: chain is NOT sparse — allocate every cluster
   from old-EOF to `rec`), write the record; gap bytes left uninitialised (matches stock; do not
   zero-fill). Disk-full → stop, A=1 (contract-only path — see §6 Q5).
4. Advance DTA by RS.
After the loop: **size := max(old size, RR_start×RS + bytes-written)**; update dirent size +
first-cluster + FAT via `fat_dir_update`; **RR (fcb+33..35) += HL_requested** (NOT actual — the
write-side asymmetry); **do NOT touch CR/EX** (stock leaves them). Return **A=0, HL preserved =
requested**.
New code: 24-bit positioning extension (~+25 B) + the extend-aware per-record loop with contiguous
gap alloc (~120-160 B). Overlay + alloc + dir-update are reused.

**Design risk (real, flagged for sign-off):** the past-EOF contiguous-extend logic is the genuinely
new, higher-risk piece. §6 Q2 offers a smaller first cut (within-EOF-only WRBLK) if we want to land
the safe half first. The **shrink path (HL=0, RR<EOF) is BROKEN on stock** — §6 Q5 decides whether
to reproduce the bug, do the sane thing, or reject it.

### 3.4 $27 RDBLK positioning (optional, §6 Q1)
If folded in: replace bdos_rdblk's `fat_open`-to-0 with the 24-bit positioning helper (start at RR
instead of 0), deliver min(request, available) records with partial-tail zero-pad, HL_out = actual,
A = 0-iff-all, **RR += HL_out (actual)**. Must NOT disturb the k_47B2 COMMAND.COM-load fast path
(which relies on the stream-from-0 behaviour) — that is the reason to default-defer.

## 4. ROM space plan (net-zero)
- Both bodies inserted into the `$60EC-$75A4` dead-pad corridor via the ds-anchored pattern (insert
  before the `ds $75A5 - $, $00` pin; the pin shrinks, `k_75A5` fixed). No canonical address moves.
- **$23**: `jp fsize_body` replaces 3 dead-`$00` bytes at `$501E`; the trailing `ds` absorbs it.
- **$26**: `ff_secloop` is **relocated verbatim** out of `$47xx` into the `$60EC` corridor (3b
  pattern); `$47BE` then holds `jp wrblk_body`. A table-value repoint was REJECTED — the `$D8BE`
  dispatch table is the fixed shared-kernel ABI, not ours (§3.1 / [LANDED-B]).
- Three bodies land in the `$60EC-$75A4` corridor: `fsize_body`, `wrblk_body`, and the relocated
  `ff_secloop` (+ the 24-bit positioning helper). ~5305 B available; comfortably fits.
- Post-build asserts: `disk.rom == 16384`; sym diff shows ONLY the new labels + `ff_secloop`'s move
  + the intended pad shrinkage — no unintended canonical-address move; `$47BE` = `jp wrblk_body`;
  old-vs-new ROM diff for the `ff_secloop` move is byte-pure (moved bytes + veneer only); FDC window
  `$7F80-$7FBF` still 0/64 nonzero.

## 5. Verification (each independently gated)
- **$23 FSIZE:** de-vacuumed BDOSX record 0 → ours `A=L=0` + fcb+33..35 = ceil(size/128) matching
  stock; the not-found variant (build_fsize_variant.py `--no-bin`) → ours `A=L=$FF` matching stock;
  the slot-shift + bigger-file variants → A tracks nothing spurious (all 0). Host unit test for the
  ceil-divide.
- **$26 WRBLK (RAM-gate BLIND — disk-artifact round-trip mandatory):** on a /tmp fixture, WRBLK a
  known non-period-256 pattern with cases: (i) record N within EOF (N non-multiple of 4); (ii) record
  N PAST EOF (extend — assert contiguous FAT chain through the gap, dirent size = max rule); (iii) a
  **24-bit RR** (r1≠0, e.g. record 256) to prove multi-byte positioning; (iv) HL×RS crossing 64K to
  prove the mod-64K truncation; (v) HL=0 RR-beyond-EOF (size-set-only). For each, black-box scan the
  post-run image and assert bytes/size/FAT match the CF-3300 oracle byte-for-byte, and that
  **RR += HL_requested** post-call. Then RDBLK the record back and confirm ours==stock. The shrink
  path (§6 Q3) verified per the chosen option.
- **Acceptance gate:** the well-formed BDOSX differential (F5) goes GREEN on records 0/5/6 (or with
  an exact-address allowlist for any residual documented cosmetic); a deliberately-injected diff
  still FAILS. BDOSX2/3/0 stay green.
- **Tier-1 throughout:** disk.rom == 16384; net-zero canonical (sym diff = intended only);
  DSKIO/BLOAD/FILES/DOS-boot == CF-3300; `make unit-test` green.

## 6. Sign-off decisions  (RESOLVED 2026-07-04)
1. **$27 RDBLK un-simplification (§3.4)** — **DEFER.** Land $23+$26 clean first; do $27 as a fast
   follow with its own COMMAND.COM-boot regression check. `bdos_rdblk` stays stream-from-0 this pass.
2. **WRBLK file-extension depth (§3.3)** — **FULL past-EOF contiguous extend now.** The oracle
   contract is pinned, so the higher-risk new logic ships in this pass (no within-EOF-only cut).
3. **WRBLK shrink path (HL=0, RR<EOF)** — **DO THE SANE THING** (option (a)): set size + free the
   tail chain + EOF-mark so the next FCLOSE SUCCEEDS. This is an **intentional divergence from
   stock's known-broken behaviour** (stock corrupts the FAT → FCLOSE `A=$FF`). Document it in the
   coverage doc + code comment, and add the one documented shrink-path difference to the acceptance
   allowlist. Verification asserts ours' FCLOSE succeeds where stock's fails (the divergence is the
   correctness win, not a regression).
4. **FCB pointer for FSIZE r0..r2** — **RESOLVED ([LANDED-B]): the `$DA40` kernel FCB copy**
   (copy+33..35); kernel propagates copy → user FCB (`$0300`) on exit. Confirm-during-diff checkpoint.
5. **Model for implementation** — **Sonnet 5** implements the signed-off spec (per the model-split);
   Opus drives verification.

## 7. Invariants & clean-room
- ROM stays 16384 B; canonical addresses net-zero (ds-anchored inserts). Derive from DPB / published
  BDOS contracts (map.grauw.nl, seasip) / our own code only; stock stays a black box — dispatch
  entries pinned by call-target **trace** (allowed), never by decoding stock ROM code. Test disks
  are /tmp copies (WRBLK mutates the image; `git status` clean after every run).
