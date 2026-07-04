<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Remediation spec — write-path residuals (RDRND/WRRND P1 + follow-ons)  (AWAITING SIGN-OFF)

Status: **DRAFT for sign-off. No source/gate/probe changes until approved.** Written per the
spec-before-implementation rule after the FDC-window P0 fix (commit 2047822) + the de-vacuumed
gate's write-path root-cause (Fable, 2026-07-04) surfaced a NEW confirmed P1 plus smaller items.
User chose "spec + fix the P1 now" + follow-ons {gate allowlist, harness landmines, $23 nit}
(NOT $26 WRBLK implementation — held as a separate feature).

## 1. What we know (evidence grade)

**P1 — RDRND/WRRND position to the WRONG record. VERIFIED (own source read + Fable disk-artifact).**
`rrnd_recsector` and `rrnd_clussec_tmp` are `db 0` scratch cells that live INSIDE the ROM
(`fresh .sym`: `rrnd_recsector`=$7C83, `rrnd_clussec_tmp`=$7CAD; both in page-1 ROM $4000–$7FFF).
They are written at runtime:
- `ld (rrnd_recsector), a` [kernel.asm:1655](../../disk/kernel.asm:1655) — stashes `r0 & 3`
  (record-in-sector) across the sector-seek loop, reloaded at :1692 → `BDOS_RECIDX`.
- `ld (rrnd_clussec_tmp), a` [kernel.asm:1709](../../disk/kernel.asm:1709) — stashes
  `FAT_CLUSSEC-1` across the cluster→sector multiply loop, reloaded at :1723.

A store to a ROM address silently no-ops (the page is read-only when mapped), so BOTH reloads
always return the assembled `0`. Consequence: `BDOS_RECIDX ≡ 0` (record-in-sector forced to 0)
and the absolute-sector math in `rrnd_sector` uses clussec 0 — so random-record file I/O
($21 RDRND / $22 WRRND, and any block op that routes through `rrnd_position`) addresses record
`(r0>>2)*4` instead of `r0`. Fable's disk-artifact proof: our WRRND(r0=1) wrote the pattern to
BDOSX.BIN **record 0** (image offset cluster-336+0); the CF-3300 wrote it to **record 1**.
**Same CLASS as the FDC-window P0** (a silent store into ROM address space), different instance,
NOT in the FDC window; latent since M26. **Invisible to the RAM-capture acceptance gate** — the
readback is self-consistently mis-positioned, so ours-vs-ours looks fine; only cross-machine
disk-artifact inspection caught it. An audit found these are the ONLY two runtime-written `db`
cells in the ROM sources (no third instance).

**$23 FSIZE return-code nit. SYMPTOM-verified (Fable), mechanism to be pinned.** Ours returns
`A=$03` where the map.grauw.nl DOS-1 contract is `A=0` on success. Small but real.

**Gate + harness gaps (Fable; to be corrected so the gate is trustworthy):**
- The acceptance gate has NO allowlist for DOCUMENTED/intentional divergences, so it will stay
  red forever on: the file DATE we intentionally don't stamp (ours=0 vs the DOS-1 default 0x0821;
  [fat.asm:16](../../disk/fat.asm:16)) and the already-accepted cosmetic devid/dirloc bytes.
- `disk_probe_diff.py` `mode_capture` copies `--diska` ONCE and runs OURS then STOCK on that same
  image ([disk_probe_diff.py:324](../../probes/disk/disk_probe_diff.py:324), :1246) → for a
  WRITE exerciser, stock boots an ours-mutated disk. It didn't drive today's diffs (arming +
  fresh rebuilds masked it) but it is a latent soundness landmine.
- The `disk_probe_diff.py` BDOS name table mislabels $25/$26/$27 ($26=WRBLK, $27=RDBLK per the
  published list).

**Out of scope (tracked, not this pass):** $26 WRBLK implementation (a feature, not a
regression); the $27 RDBLK stream-from-0 simplification (documented, same class as bdos_rdblk's
random-record-0 assumption); the register-scratch leaks at rec 14/16 (documented byte A matches;
cosmetic). The exerciser fixture ramp period-256 aliasing + BDOSX's out-of-contract block-op
records (no FCB record-size set) — noted for a future exerciser cleanup, not gated on here.

## 2. Fix design

### F1 — RDRND/WRRND scratch cells: ROM → RAM (net-zero)
- Add two dedicated page-3 RAM bytes in the disk scratch region, immediately after `WBUF`
  (WBUF = $E560..$E75F, the current top of disk scratch; $E760+ is free):
  `RRND_RECSEC equ $E760` (byte), `RRND_CLUSSEC equ $E761` (byte). Same free-RAM discipline as
  the existing cells (clear of SECTOR_BUF / FAT_* / WBUF / basic-core; PROVENANCE §Scratch RAM).
  Both are transient-within-a-single-call (no cross-call lifetime), so no init needed.
- Repoint the four instructions [kernel.asm:1655](../../disk/kernel.asm:1655)/:1692/:1709/:1723
  from the ROM labels to the RAM equates. Each is `ld (nn),a` / `ld a,(nn)` — **same 3-byte
  size**, only the 16-bit operand changes ⇒ ZERO code-size change ⇒ no address shift.
- Retire the two ROM `db 0` cells (:1699–1700, :1729–1730): keep the byte as an anonymous
  `ds 1, $00` pad (drop the now-unused label) so every following address is unshifted.
  Net effect: byte-for-byte identical ROM except the 4 operand words + 2 (now label-less) pad
  bytes ⇒ **net-zero canonical addresses, disk.rom stays 16384 B.**

### F2 — $23 FSIZE return code
- Locate the FSIZE handler (dispatched via the relocated-kernel table to our page-1 entry;
  the $23 record in BDOSX/bdosx.asm), confirm the `A=$03`-on-success path, and set `A:=0` on
  success per the published contract. Verify no register the contract pins is disturbed. If the
  `$03` turns out to be a deliberate/necessary value (re-check against the contract before
  editing), STOP and report instead of forcing it.

### F3 — Gate documented-divergence allowlist
- Add an allowlist to [disk_bdos_acceptance.py](../../probes/disk/disk_bdos_acceptance.py) that
  excuses SPECIFIC, documented byte offsets per exerciser (the FCB/dir date field; the
  devid/dirloc cosmetic bytes) — matched by exact `(region, offset)` with a cited reason, NOT a
  blanket mask. A diff at ANY non-allowlisted byte still FAILS. The allowlist entries carry a
  one-line provenance note (why the divergence is intentional). Goal: the gate goes GREEN on the
  create/write block for the RIGHT reason, and any NEW divergence still trips it.

### F4 — Harness landmine fixes
- `disk_probe_diff.py`: for `mode_capture`, give OURS and STOCK each their OWN fresh copy of
  `--diska` (copy-per-machine, not copy-once) so a write exerciser never boots the other
  machine's mutated image. Keep `--no-copy` semantics for callers that opt out.
- Fix the BDOS name-table labels ($26=WRBLK, $27=RDBLK).

## 3. Verification (each fix independently gated)
- **F1 (the P1):** the RAM-capture gate is BLIND to it, so verify by **disk-artifact round-trip**:
  on a /tmp fixture, WRRND a known pattern to record N (N not a multiple of 4, e.g. 1 and 5),
  then black-box scan the post-run image and assert the pattern lands at the SAME cluster+offset
  as the CF-3300 oracle writes it (Fable's `(i*3+1)&0xFF` ×128 scan, reused). Also RDRND record N
  back and confirm ours==stock. Use a fixture whose record content is NOT period-256-aliased so
  position is unambiguous. Plus: DOS boot stays green (no $E760/$E761 collision) and `make
  unit-test` green.
- **F2:** the $23 record in the de-vacuumed BDOSX capture shows `A=0` matching stock.
- **F3:** `disk_bdos_acceptance.py` reports the create/write block GREEN with the allowlist, and
  a deliberately-injected extra diff still FAILS (anti-vacuity of the allowlist itself).
- **F4:** re-run a write exerciser through the copy-per-machine path and confirm the differential
  is unchanged (no regression) and the name-table labels read correctly.
- **Tier-1 throughout:** disk.rom == 16384 B; net-zero canonical (sym diff shows only the intended
  operand changes, no label moves); DSKIO/BLOAD/FILES == CF-3300.

## 4. Invariants & clean-room
- ROM stays 16384 B; canonical addresses unshifted (F1 is byte-size-neutral by construction);
  derive from DPB / published contracts / our own code only; stock stays a black box (no ROM-code
  decode); test disks are /tmp copies (esp. important now — F1/F4 are WRITE paths that mutate the
  image; `git status` clean after every run).

## 5. Risks / rollback
- **F1 RAM choice:** $E760/$E761 must not collide with anything MSX-DOS uses during our ops. The
  DOS-boot-green + gate-green checks are the collision detector; if either regresses, revert and
  pick a byte inside the already-proven WBUF-adjacent region.
- **F2:** risk of "fixing" a deliberate value — mitigated by the re-check-contract-before-edit gate.
- **F3 allowlist:** the real risk is a TOO-BROAD allowlist re-hiding a bug — mitigated by exact
  (region, offset) matching + the F3 injected-diff-still-fails check.
- Every change is source/probe-level and git-reversible; no irreversible/outward-facing action.

## 6. Open questions for sign-off
1. **RAM address** for the two cells — $E760/$E761 (immediately after WBUF), OK? Or prefer a
   specific already-proven region?
2. **$23 FSIZE:** fix the return code in THIS pass, or (if it turns out entangled with the
   dispatcher-flag/HL-passthrough path) split it out? Default: fix if isolated, report if not.
3. **Allowlist scope (F3):** exact-offset allowlist with provenance notes (my plan), vs a looser
   per-field mask? I recommend exact-offset.
4. **Order:** F1 (the P1) first + fully verified before touching the gate/harness (F3/F4), so the
   P1 fix is proven against the CURRENT harness, then the harness is improved. OK?
