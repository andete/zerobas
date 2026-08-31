# D-OOMTAIL — the two store-overflow exits share one body, and the probe was wrong four ways before the carve was provable

*2026-08-31. `basic/cload.asm` (`ctp_oom` → `jp dpl_oom`). Probe
`scratchpad/oomtail_probe.py`. **+13 B main page 1** (378 → 391 B free).
ROM hashes change; the `.ips`/`.bps` pair rides this commit.*

## 1. The carve

`ctp_oom`'s seven-instruction tail (cassette store overflow) was byte-for-byte
`dpl_oom`'s whole body (disk store overflow) — its own comment said *"mirrors
dpl_oom"*. Both are page 1 (`$668A` / `$6828`), `$19E` apart, so the mirror
became `jp dpl_oom`: 16 B → 3 B. The D-CASTAIL contract (CF=1, empty program,
`Out of memory`) is unchanged — `dpl_oom` **is** that contract — and the
coupling is deliberate: the two halves are filed as mirrors, so an edit to one
is an edit to both. No fallthrough enters either label; no interior labels in
the span ([`ngram_sweep`] instruction-level check).

## 2. Reaching the exits — the probe was wrong four ways first

The exits had **no row**: [spec-basic-castail.md](spec-basic-castail.md) §"coverage,
stated exactly" records `ctp_oom` as unreachable by any *differential* row
(the references hang on tokenised tape). A functional zerobas row can still
witness both — but four wrong probe drafts stood between here and there, and
each is a recorded class:

1. **The green that was green for the wrong reason.** Draft 1 used
   `CLEAR 200,&H8300` + a 5 KB file. Both loaders bound the store against
   **`TXTMAX`, a fixed `$BB00`** ([sysvars.inc](../basic/sysvars.inc)) — *not*
   the CLEAR ceiling — so 5 KB overflows nothing and `d.oom` printed
   `<nothing>`. Yet `c.oom` printed `Out of memory` — from the **CLEAR
   itself**, which refuses a floor under the disk work area. One row green, on
   the right words, from the wrong mechanism. The check now requires the
   `Found:` line too, so only a tape load can satisfy it.
2. **The capture that fired mid-load.** At truncload's 2.5 s per-line step, a
   17 KB load was still running at capture: `d.oom` read `<nothing>` and
   `d.oom-l` read `<NO ECHO>` — both exactly what "the machine is busy" looks
   like. 25 s.
3. **The prompt that is not `Ok`.** `c.ctl` looked for `Ok`; this machine's
   ready prompt is **`ZB`**. The row failed twice on a word the screen never
   contains.
4. **The boot text that is always there.** The capture's `s1` half (VRAM
   `$1800`) still holds the SCREEN-1 boot banner on *every* capture — "boot
   text present" means nothing, and a named positive word (`Found:SM`) is the
   only honest check.

## 3. What the rows then said

| row | CF-3300 | zerobas | |
|---|---|---|---|
| `ctl.ok` small LOAD + LIST | the line | the line | 🟢 |
| `d.oom` 17 KB LOAD | *loads fine* | `Out of memory` | **ADJ** |
| `d.oom-l` …then LIST | (long listing) | *(empty)* | **ADJ** |
| `c.oom` 17 KB CLOAD | *(no oracle: refs hang)* | `Out of memory` | ✅ |
| `c.ctl` small CLOAD | *(no oracle)* | `Found:` + clean | 🟢 |

**Before/after: the zerobas rows are IDENTICAL on the pre-carve and carved
builds** — measured by building both and diffing the row output, which is the
whole witness a byte-behaviour-preserving carve owes.

## 4. The divergence the fixture exposed is a settled decision

A ~17 KB program loads on the CF-3300 (~29 KB program capacity) and raises
`Out of memory` here, because the repack's text ceiling is `$BB00` — capacity
**14079 B**, chosen by measurement (D-LINEMAX / D-FCH: DETOKBUF is funded out
of program space exactly the way the reference funds its file-channel buffers
out of `FRE(0)`). Not a defect; **adjudicated**. The rows print `ADJ`, do not
fail the run, and are pinned in
[tools/filed-row-known.txt](../tools/filed-row-known.txt) — the D-FILEDROT
convention's first live entry written the same day the convention landed.

## 5. Walls after

`make basic-reloc`: low 127 B · **page 1 391 B** · sub p0 2019 B · sub p1 1623 B.
