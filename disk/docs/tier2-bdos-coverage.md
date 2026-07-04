<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 — MSX-DOS-1 BDOS coverage scoreboard

**What this is:** a living per-function scoreboard of how much of the MSX-DOS-1 BDOS the
zerobas-disk ROM correctly services. The kernel dispatches every BDOS call through a per-function
table (`$D8BE + 3*C` → {segment, handler}, see [tier2-gdate-spec.md](tier2-gdate-spec.md) §3), so
"BDOS function number" is the natural unit.

**How it's maintained (don't hand-guess):** seed each row from `disk_probe_diff.py callseq`/
`capture` output — it reports, per call, whether ours matches stock at the same logical point.
Mark only what a probe has shown; leave the rest `unknown`. Re-run after each slice lands and
update. Repro (boot path): `python3 probes/disk/disk_probe_diff.py callseq --maxhits 40 --diska
~/Documents/msx/msx/disks/test.dsk` (oracle disk = **test.dsk**). Repro (FCB cluster): the
`BDOSX.COM` exerciser, [tier2-bdos-exerciser-spec.md](tier2-bdos-exerciser-spec.md).

**Standing regression gate (2026-07-04):** the BDOSX/2/3/0 exercisers are no longer one-shot —
`make bdos-acceptance` (`probes/disk/disk_bdos_acceptance.py`) replays all four and re-asserts each
converges 0-byte-identical to stock. Green baseline 2026-07-04: **6/6 gated differentials converged**
(BDOSX ×2, BDOSX2 ×1, BDOSX3 ×2 capture-region diffs + BDOSX0 callseq alignment). Run it after any
kernel/BDOS change; a red gate means the surface below regressed. Oracle-dependent (needs
`make machines-oracle` + CF-3300 reference ROMs), so it is NOT in the emulator-free `make unit-test`.

**Status legend:**
- ✅ **converges** — ours matches stock at this call (same params, return, branch, AND observable
  side effect — screen/VRAM or buffer content, not just the call sequence; see the M13 CONOUT
  lesson below). A mature ✅ has **two backings**: the emulator differential (proven once vs the
  oracle) AND a host unit test (`tests/test_<fn>.py`) where one exists — see
  [[host-unit-test-harness]].
- ⚠ **diverges / uncharacterized** — a known, still-open gap or a divergence never chased down.
- 🔲 **not yet exercised** — not reached by any probe so far (untestable with current harness, or
  simply not yet attempted).
- — **n/a** — not part of MSX-DOS 1 / not relevant to this single-drive MSX1 target.

## Scoreboard

| `C` | fn | ours | evidence | notes |
|------|--------|------|--------------------|-------|
| `$02` | CONOUT | ✅ | 27/27 boot `callseq`, byte-identical; DIR `screen` byte-identical (M22b) | Fixed M13 (was a `screen`-only-visible render bug — calls matched stock while VRAM showed garbage tile `$80`; root cause was CONIN falling through into CONOUT at `$50E0`, not a CONOUT bug itself). Reads the char from **E**, not A — do not revert (M10 lesson). M22b slice 1 (2026-07-03): the kernel actually CALLs a separate canonical entry, `$53A7`, for every func-2 char — pre-M22a this NOP-slid into the `$5454` veneer by accident (tier2-m22b-conout53a7-spec.md); now wired explicitly (`k_53A7: jp conout_body`). Residual: `$53A7`'s TAB-expansion + `$F237` column bookkeeping (spec §5.3/§5.4) is NOT yet implemented (M22b slice 2, deferred). |
| `$09` | STROUT | ✅ | 27/27 boot `callseq`, byte-identical | Fixed M13 alongside CONOUT (same root cause: CONIN/CONOUT fall-through) |
| `$0A` | BUFIN | ✅ | 27/27 boot `callseq` | headless: reaches BUFIN cleanly at both the date prompt and the `A>` command prompt. Real keyboard input timing untested ([[tier2-storms-are-downstream]]); call/return contract is correct |
| `$0E` | SELDSK | ✅ | 27/27 boot `callseq` | called in the `A>` command loop past BUFIN |
| `$0F` | FOPEN | ✅ | boot-load path (M-series) + M21a full dir-search fix | RC-1 fixed 2026-07-02: `$4462` dir-fill entry now a real veneer (`fopen_fill_body`, fat.asm), fills FCB+14..+31 (record count, size, date/time, devid, cluster chain) from the SFIRST/SNEXT-found dir entry; miss path exits `A=$FF` matching stock |
| `$10` | FCLOSE | ✅ | M21/`BDOSX` run, 0-byte-diff | |
| `$11` | SFIRST | ✅ | M19 — `DIR` lists files | |
| `$12` | SNEXT | ✅ | M19 — `DIR` lists files | |
| `$14` | RDSEQ | ✅ | M21/`BDOSX` run (×2 calls), 0-byte-diff data buffer | |
| `$19` | CURDRV | ✅ | 27/27 boot `callseq` | the `A>` idle loop calls it to print the drive letter |
| `$1A` | SETDTA | ✅ | exercised implicitly by every RDSEQ/RDBLK call in `BDOSX`, 0-byte-diff | no standalone probe of SETDTA in isolation |
| `$1B` | ALLOC (GETALLOC) | ✅ | M20 — `DIR`'s "`nn bytes free`" footer, byte-identical | root cause was the `$F306` dispatcher-flag/`HL`-passthrough rule (see general rule below) |
| `$23` | FSIZE | ⚠ UNVERIFIED (was vacuous ✅) | de-vacuumed gate (2026-07-04): ours returns `A=$03` vs stock `A=0`; but $23 is a KERNEL-internal shared call (no disk-ROM handler) and `A=3` may be a valid CP/M dir code — needs its own $23-contract characterisation | prior "0-byte-diff" was a vacuous-anchor artifact |
| `$24` | SETRND | ✅ | M21/`BDOSX` run | |
| `$26` | WRBLK | ❌ NOT IMPLEMENTED (was vacuous ✅) | de-vacuumed gate (2026-07-04): ours does not persist a random block write (post-run image unchanged); the M21 "0-byte-diff" was a vacuous-anchor artifact | feature gap; tracked follow-on |
| `$27` | RDBLK | ⚠ documented simplification (now well-formed differential, F5) | `k_47B2` streams the whole file from offset 0, ignoring the random-record/count fields (same class as `bdos_rdblk`'s random-record-0 assumption) — NOT a full-contract match. `bdosx.asm` now sets FCB+14..15=128 before the block ops (F5), so the differential is well-formed: BOTH machines transfer a defined 128-B record and the divergence is exactly one record's positional offset (ours streams from 0, stock positions at the random record). Bonus datum: setting FCB+14=128 makes stock read a real block (was 00), confirming stock uses FCB+14..15 as record size = our `driver.asm:578` interpretation. | M21b RC-2 made arbitrary-`.COM` load work; full positional block semantics unverified — green needs the stream-from-0 un-simplification |
| `$2A` | GDATE | ✅ | handler `gdate_handler` @ `$553C` + `$F30D/$F30E` format defaults; backed by `test_gdate.py` | returns 1984-01-01 default |
| `$2B` | SDATE | ✅ | confirmed with a real typed date (`--keys '85-3-27\r'`); screen arbiter matches | no host unit test yet |
| `$01` | CONIN | ✅ | `BDOSX2` record 8, 0-byte-diff; `screen` shows the `x` echo | M22a: canonical entry `$5445` (`conin_body`), CHGET+echo via `conout_body` |
| `$06` | DIRIO | ✅ | `BDOSX2` records 11+13, 0-byte-diff; `screen` shows the `!` output | M22a: extends `$5454` (`conout_body`/`dirio_in_body` branch, discriminated by `ret=$D88A`+`C=$06`+`E=$FF`) |
| `$07` | DIRIN | ✅ | `BDOSX2` record 9, 0-byte-diff | M22a: canonical entry `$5462` (`jp innoe_body` — pinned identical to INNOE at this probe's granularity) |
| `$08` | INNOE | ✅ | `BDOSX2` record 10, 0-byte-diff | M22a: canonical entry `$544E` (`innoe_body`, CHGET no-echo) |
| `$0B` | CONST | ✅ | `BDOSX2` records 7+12 (poll-until-ready + drained), 0-byte-diff | M22a: canonical entry `$543C` (`const_body`, CHSNS poll normalized to `$FF`/`$00`) |
| `$0C` | CPMVER | ✅ | `BDOSX2` record 0, 0-byte-diff | M22a: canonical entry `$41EF` (`cpmver_body`: `A=$22 B=$00`) — kernel-internal constant, but still a real page-1 CALL (tier2-m22-cpmver-spec.md, the milestone's namesake discovery) |
| `$05` | LSTOUT | ⚠ dispatch not wired (root cause fixed) | DIR-parity root cause fixed: `callseq --log 0x0005` 260/260 aligned (was: fork at n=63, 82 spurious calls); BDOSX3 full-block bonus fix 0/896 (was 127/896) | M27 (2026-07-04): root cause was NOT LSTOUT's own dispatch — it was `$F23B` (printer-echo state), never zeroed at DOS boot, causing COMMAND.COM's own DIR line-end + prompt-cycle code to think a list device is attached. Fixed in `dos_handoff` (runtime.asm), same shape as the existing `$F338`/`$F30D` DOS-only defaults. LSTOUT's OWN dispatch (`$5465`) is still un-wired — squatted by `callf_body_body`, currently harmless (nothing calls it for real) — deferred, see tier2-m27-lstout-spec.md §4 |
| `$2C` | GTIME | ✅ | `BDOSX2` record 3, 0-byte-diff (D/E seconds bytes tolerate ±1s clock skew, documented) | M22a: canonical entry `$55DB` (`gtime_body`: all-zero constant, NOT fed by STIME) |
| `$2D` | STIME | ✅ | `BDOSX2` record 2, 0-byte-diff | M22a: canonical entry `$55E6` (`stime_body`: `A:=0 B:=H C:=L`, D/E passthrough; range validation not implemented, residual) |
| `$00` | TERM0 | ✅ | M23 `BDOSX0`: `callseq --log 0x0005` 43/43 aligned incl. the `C=00` call itself (byte-identical `A/B/DE/HL`); `screen` shows both machines back at a live `A>` | never returns — evidence is call-alignment + screen, not a buffer capture (tier2-bdos-remaining-spec.md §5.2); doubles as an M21b generic-COMMAND.COM-reentry regression check |
| `$0D` | DSKRST | ✅ | `BDOSX2` record 6, 0-byte-diff; DTA→`$0080` side effect confirmed | M22a: canonical entry `$509F` (`dskrst_body`, tail-calls the existing `$50A9` continuation stub) |
| `$18` | LOGIN | ✅ | `BDOSX2` record 1, 0-byte-diff | M22a: canonical entry `$504E` (`login_body`: `(1<<DRVCNT)-1` bitmap, `C` preserved) |
| `$2E` | VERIFY | ✅ | `BDOSX2` records 4-5 (on/off), 0-byte-diff | M22a: canonical entry `$55FF` (`verify_body`: `A:=E`); flag-EFFECT on writes deliberately not coupled in (open question, tier2-bdos-remaining-spec.md §5.4) |
| `$16` | FMAKE | ✅ | `BDOSX3` record 0, 0-byte-diff | M24/M25: `$461D` FMAKE worker (`bdos_create_body`, fat.asm) creates/truncates the dir entry |
| `$15` | WRSEQ | ✅ | `BDOSX3` records 1-9 (×9), 0-byte-diff, incl. second-cluster FAT allocation | M24/M25: `$477D` worker (`wrseq_body`) dispatches into `bdos_seqwrite` — shared with RDSEQ's own `$477D` hits, see tier2-m24-fclose-multicluster-spec.md "M25 RESOLVED" |
| `$17` | FREN | ✅ | `BDOSX3` record 14, 0-byte-diff | M26 slice 1 (2026-07-03): real dispatch `$4392` collided with the shared `fdc_read_data` FDC primitive (relocated to `fdc_read_data_body`); `fren_body` (fat.asm) reuses `fat_mount`/`fat_find`/`write_sector` to rename the dir entry in place — tier2-m26-spec.md §6 |
| `$2F` | RDABS | ✅ | `BDOSX3` record 22, 0-byte-diff | M26 slice 2 (2026-07-03): `$46BA` was pure `$00` pad (no relocation needed); `rdabs_body` (fat.asm) reads via `dskio` directly (arbitrary sector count) into the runtime DTA — tier2-m26-spec.md §7 |
| `$30` | WRABS | ✅ | `BDOSX3` record 23, 0-byte-diff | M26 slice 3 (2026-07-03): real dispatch `$4720` was a mid-instruction byte inside `bdos_seqwrite`'s live tail (needed a FREN-class relocation, unlike RDABS's pad-wire); `bdos_seqwrite` relocated to `bdos_seqwrite_body` (kernel.asm), freeing `$4720` for `wrabs_body` (mirrors `rdabs_body`, `dskio` write direction) — tier2-m26-spec.md §8 |
| `$13` | FDEL | ✅ | `BDOSX3` record 15, 0-byte-diff | M26 slice 4 (2026-07-03): real dispatch `$436C` was pure `$00` pad (RDABS-shape, no relocation), but landing FREN moved fresh pad underneath it so the un-wired call was actively corrupting the target dir entry + leaking its FAT chain (not a harmless no-op); `fdel_body` (kernel.asm — NOT fat.asm's own end, which silently broke test_gdate/test_getdpb by starving kernel.asm's pinned-address corridor of slack) reuses `fat_find`, frees the FAT12 chain via `fat_next_cluster`/`fat_write_fat_entry`, then stamps `$E5` — tier2-m26-spec.md §9 |
| `$21` `$22` | RDRND, WRRND | ✅ (fixed 2026-07-04, F1) | disk-artifact round-trip: WRRND r0=1 writes BDOSX.BIN record 1 byte-identical to the CF-3300 | M26 slice 5 built the bodies (`rrnd_position`/`rdrnd_body`/`wrrnd_body`), but the RAM-only gate's "0-byte-diff" was BLIND to a wrong-record P1: `rrnd_recsector`/`rrnd_clussec_tmp` were `db` scratch cells IN THE ROM → runtime stores no-op'd → record-in-sector forced to 0 → wrong record. FIXED (commit c557628): cells moved to RAM `$E760/$E761`; verified on-disk vs oracle (tier2-writepath-remediation-spec.md F1) |
| `$03` `$04` | AUXIN, AUXOUT | — n/a | — | not relevant to a single-drive MSX1 disk target |

## Reading the score
- **The boot-to-`A>` path is 100% ✅ (27/27 parity):** `$02/$09/$0A/$0E/$0F/$19/$2A/$2B` all
  converge, control flow AND rendered output both verified.
- **The FCB read/write/close cluster (M21, 2026-07-02) — CORRECTED 2026-07-04:** `$0F/$10/$14/$1A/
  $24` are solid, but the M21 "100% ✅" for this cluster was inflated by the VACUOUS acceptance
  anchor (fixed 2026-07-04, Phase A). The de-vacuumed gate shows `$26` WRBLK is NOT implemented,
  `$27` RDBLK is a documented stream-from-0 simplification, and `$23` FSIZE returns `A=3`
  (uncharacterised) — see their rows above. `BDOSX`'s own differential is honestly RED in the gate
  for these reasons, not hidden. As of F5 (2026-07-04) `bdosx.asm` sets FCB+14..15=128 before the
  block ops so the comparison is WELL-FORMED (was out-of-contract: no record-size set); the residual
  RED is now diagnostic — the whole-record `$27` positional offset + the `$26` gap + the `$23` nit —
  not garbage. Green requires the `$26` implementation and the `$27` un-simplification (both tracked,
  neither in this pass); the record-size fix alone cannot converge it.
- **The console + misc + termination tier (`$00/$01/$06/$07/$08/$0B/$0C/$0D/$18/$2C/$2D/$2E`)
  is 100% ✅ (M22a+M22b+M23, 2026-07-03):** all proven via `BDOSX2.COM`/`BDOSX0.COM`, 0-byte-diff
  on every record. This is where the milestone's real surprise lived — `$0C` CPMVER and
  `$02` CONOUT's `$53A7` worker both turned out to be genuine un-wired canonical page-1 entries
  that had never been exercised before (tier2-m22-cpmver-spec.md, tier2-m22b-conout53a7-spec.md).
- **`$05` LSTOUT's long-standing DIR oddity is root-caused and fixed (M27, 2026-07-04):** the
  spurious per-file calls were never really about LSTOUT's own dispatch — an uninitialized
  `$F23B` printer-echo cell fooled COMMAND.COM into thinking a list device was attached.
  Fixing it also turned out to fix an unrelated-looking BDOSX3 gap from M26. LSTOUT's own
  dispatch (`$5465`) remains un-wired but currently harmless — see tier2-m27-lstout-spec.md.
- **The mutation + random + absolute-I/O block is 8/8 ✅ (M24/M25/M26, 2026-07-03) — M26 CLOSED,
  full BDOS surface coverage complete:** `$15 WRSEQ`/`$16 FMAKE` (M24/M25, dir-write +
  FAT-allocate machinery), `$17 FREN`/`$2F RDABS`/`$30 WRABS`/`$13 FDEL` (M26 slices 1-4), and
  `$21 RDRND`/`$22 WRRND` (M26 slice 5, the milestone's HIGH-risk closer — a genuinely new
  positioning helper + a new read-modify-write body for WRRND, not just a thin veneer) all
  proven via `BDOSX3.COM`, 0-byte-diff.
- **Historical lesson (M13):** a ✅ needs the OUTPUT verified, not just the call sequence — CONOUT/
  STROUT briefly scored ✅-by-call while `screen` showed VRAM was garbage. Don't repeat that
  shortcut for any future row.
- **General rule (M20):** the RAM kernel's common BDOS-exit path (`$D8AA-$D8BD`) silently
  overwrites a handler's `HL` with `H:=B,L:=A` unless the handler clears dispatcher flag `$F306`
  before `ret`. Any new handler that needs `HL` to survive to the caller must clear `$F306` first.
