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
| `$23` | FSIZE | ✅ | M21/`BDOSX` run, 0-byte-diff | |
| `$24` | SETRND | ✅ | M21/`BDOSX` run | |
| `$26` | WRBLK | ✅ | M21/`BDOSX` run | |
| `$27` | RDBLK | ✅ | M21b — RC-2 fix (2026-07-02): `$47B2`'s body (`k_47B2`) rewritten from a COMMAND.COM-only diagnostic loader into a generic body streaming via `bdos_seqread`; also fixed a real bug found along the way — our internal `BDOS_DTA` cell is separate from the kernel's real `DOS_DTAPTR` and must be reseeded at entry | this is the fix that made loading/running an arbitrary named `.COM` work at all |
| `$2A` | GDATE | ✅ | handler `gdate_handler` @ `$553C` + `$F30D/$F30E` format defaults; backed by `test_gdate.py` | returns 1984-01-01 default |
| `$2B` | SDATE | ✅ | confirmed with a real typed date (`--keys '85-3-27\r'`); screen arbiter matches | no host unit test yet |
| `$01` | CONIN | 🔲 untestable-here | — | expected to ride the already-proven CHGET primitive (shared kernel dispatch); unverified by direct probe. Reachable now via a `BDOSX.COM` Phase-2 extension (harness can only inject one keystroke burst, not timed mid-program input — see [tier2-bdos-exerciser-spec.md](tier2-bdos-exerciser-spec.md) §"OUT of scope") |
| `$06` | DIRIO | 🔲 untestable-here | — | same expectation/blocker as CONIN |
| `$07` | DIRIN | 🔲 untestable-here | — | same |
| `$08` | INNOE | 🔲 untestable-here | — | same |
| `$0B` | CONST | 🔲 untestable-here | — | expected to ride the already-proven CHSNS primitive |
| `$0C` | CPMVER | 🔲 untestable-here | — | returns a kernel-internal constant with NO disk-ROM code involved at all — lowest risk of the console tier |
| `$05` | LSTOUT | ⚠ open, uncharacterized | 82 spurious per-file `C=05` calls observed during `DIR` (BDOS n=63 fork, first noticed M19/M20) | confirmed OUT OF SCOPE for `DIR`'s own correctness; never root-caused. Pick up if a future milestone touches this area |
| `$2C` | GTIME | 🔲 not yet exercised | — | clock-group; may be called like GDATE, unconfirmed |
| `$2D` | STIME | 🔲 not yet exercised | — | clock-group |
| `$00` `$0D` `$13` `$15` `$16` `$17` `$18` `$21` `$22` `$2E` `$2F` `$30` | TERM0, DSKRST, FDEL, WRSEQ, FMAKE, FREN, LOGIN, RDRND, WRRND, VERIFY, RDABS, WRABS | 🔲 not yet exercised | — | not seen on the boot path or by `BDOSX`; needs a shell/user-program path or a further `BDOSX` extension |
| `$03` `$04` | AUXIN, AUXOUT | — n/a | — | not relevant to a single-drive MSX1 disk target |

## Reading the score
- **The boot-to-`A>` path is 100% ✅ (27/27 parity):** `$02/$09/$0A/$0E/$0F/$19/$2A/$2B` all
  converge, control flow AND rendered output both verified.
- **The FCB read/write/close cluster is 100% ✅ (M21, 2026-07-02):** `$0F/$10/$14/$1A/$23/$24/
  $26/$27` all proven via the `BDOSX.COM` exerciser — byte-identical registers across 47 shared
  calls, 0-byte-diff on both the 384-byte data buffer and the FCB/register-snapshot buffer.
- **The console tier (`$01/$06/$07/$08/$0B/$0C`) is the next open item** — architecturally
  expected to work (rides CHGET/CHSNS, no page-1 disk-ROM code involved) but genuinely unverified;
  `BDOSX.COM` is the tool that would unblock probing it (Phase 2, not yet written).
- **`$05` LSTOUT** has a known, still-uncharacterized oddity (spurious per-file calls during
  `DIR`) — harmless to `DIR` itself but nobody has explained it yet.
- **Historical lesson (M13):** a ✅ needs the OUTPUT verified, not just the call sequence — CONOUT/
  STROUT briefly scored ✅-by-call while `screen` showed VRAM was garbage. Don't repeat that
  shortcut for any future row.
- **General rule (M20):** the RAM kernel's common BDOS-exit path (`$D8AA-$D8BD`) silently
  overwrites a handler's `HL` with `H:=B,L:=A` unless the handler clears dispatcher flag `$F306`
  before `ret`. Any new handler that needs `HL` to survive to the caller must clear `$F306` first.
