<!--
Copyright (c) 2026 Joost Yervante Damad
SPDX-License-Identifier: 0BSD
-->

# Tier-2 M22b — the `$53A7` CONOUT-worker canonical entry (the DIR-corruption root cause; tab-expansion + `$F237` column cell) — CHARACTERISATION + fix-shape spec (no asm)

**Status: CHARACTERISED (2026-07-03). CHARACTERISE + SCOPE ONLY — no asm touched;
`disk/kernel.asm` / `disk/pageenv.asm` / `disk/runtime.asm` left exactly in their
uncommitted M22a state; `build/disk.rom` rebuilt AS-IS only. STOP for sign-off**
(per [[spec-before-implementation]] — this is the SECOND surprise inside the M22
milestone; do not fold it silently into the M22a sign-off). Extends
[tier2-m22-cpmver-spec.md](tier2-m22-cpmver-spec.md) (M22a, implemented but
uncommitted); ground truth [tier2-STATE.md](tier2-STATE.md); fix-shape precedents
[tier2-m8-spec.md](tier2-m8-spec.md) (`$5454` CONOUT veneer),
[tier2-m17-spec.md](tier2-m17-spec.md) (veneer+cell).

## 0. TL;DR

M22a's acceptance suite passed (bdosx2 14-record zero-diff, 27/27 boot callseq,
unit-test, `make probe`) but a broader real-world check — `DIR` at the `A>` prompt —
surfaced screen corruption. Root cause, pinned black-box: **the RAM kernel dispatches
EVERY BDOS `$02` CONOUT character to an eleventh+one canonical page-1 entry, `$53A7`
— un-wired `$00` pad on ours since forever.** Pre-M22a the CALL NOP-slid 173 bytes
into the `$5454` `jp conout_body` veneer, which **accidentally implements the correct
observable contract** (emit E via CHPUT, exit `A:=E`) — that lucky slide is what made
M8→M21 console parity work at all. M22a's new `$543C` CONST veneer now intercepts the
slide, so every func-2 char runs a keyboard poll instead of an emit: the date, the
`A>` prompt, keystroke echo and the whole DIR listing are silently dropped, and
COMMAND.COM's DIR formatting (which consumes the func-2 return) derails from the
second entry (the briefed `$C5BB`→`$C5BE`/`$C649` kernel fork).

- **`$53A7` is a first-class canonical entry** — `ret=$D88A`, `B`=own-low-byte
  fingerprint (`$A7`), `C=$02`, **char in E** — the SAME dispatcher class as the ten
  M22a entries. It needs a byte-exact-position veneer (§6, Q1 = "canonical", not
  "fall-through-only").
- It is the **only** ABI address in `$5300–$5453`: a full boot+DIR session on ours
  enters the region at `$53A7` and nowhere else (400/400). `$53A8` (CONIN echo),
  `$5412/$5415` (per-char poll helper), `$541D-$542A` are stock-internal.
- Stock's routine **returns to the dispatcher before `$543C`** — it does NOT merge
  into `$5454`. `$5454` stays an independent entry (M8 unchanged).
- Functionally it is CONOUT-with-bookkeeping: emit char via CHPUT **+ expand TAB to
  8-column stops + maintain a logical-column byte at `$F237`** (private to page-1
  code; the kernel never reads or writes it). Wrap/scroll live in BIOS CHPUT, not here.
- Fix shape (§6): **slice 1** = a 3-byte `$53A7: jp conout_body` veneer in existing
  pad (net-zero; restores the exact behavior 2 days of green probes ran on).
  **slice 2** = tab expansion + `$F237` column maintenance in the shared
  `conout_body` bottleneck (a REAL pre-existing gap, first exercisable today).

## 1. Reproduction (post-M22a working tree, `build/disk.rom` rebuilt as-is)

```
cp ~/Documents/msx/msx/disks/test.dsk /tmp/zerobas_m22b_test.dsk
python3 probes/disk/disk_probe_diff.py screen --machine both --keys '\rDIR\r' \
    --keys-at 22 --settle 40 --diska /tmp/zerobas_m22b_test.dsk
```
STOCK: full 21-file listing + `41 files` + `375808 bytes free` + `A>`. OURS: only the
func-9 STROUT lines render (sign-on, `COMMAND version 1.08`, `Current date is` —
via our own `res_print`→`conout_body`); the func-2 date `Sun 84-01-01`, the `A>`
prompt, the `DIR` echo and the entire listing are **absent**, with a mangled
`" file bytes free.IR"` remnant — every BDOS `$02` char is dropped. The BDOS
*call* stream stays aligned through the boot (27/27 still passes — the damage is
below callseq granularity), and `callseq --log 0x0005`-level DIR alignment breaks
only when COMMAND.COM's formatting logic consumes the func-2 return (§2.3).

## 2. Falsification pass

### 2.1 "M22a introduced the bug" — REFUTED (M22a only unmasked it)
`callseq --log 0x53A7` (§3) shows the kernel CALLing `$53A7` on OURS and STOCK with
byte-identical entry state — on every build; the call has been arriving since the
DOS-boot track began. Ours' `$53A7..$543B` is `$00` pad (our own artifact,
`build/disk.rom`): pre-M22a the slide ended at `$5454: jp conout_body` (emit E,
`A:=E` — observably correct); post-M22a it ends at `$543C: jp const_body` (CHSNS
poll, no emit). M22a moved the accident, it didn't create the entry. This is §4.4's
"pad-slide luck" class made real — the same latent-bug shape the M22a spec flagged
for DSKRST.

### 2.2 "`$5454` is mid-routine; real code flows from `$53A8` into `$5454`" — REFUTED
Stock's func-2 handler **returns to `$D88A` before reaching `$543C`**: the exit
capture (§5.1) anchors at `$D88A` immediately after the entry call, and the func-2
region walk (§3) never enters `$5416–$5453`. `$5454` remains a clean, self-contained
DIRIO/CONOUT entry; M8's veneer is untouched by this finding.

### 2.3 "wrap/scroll bookkeeping lives here" — REFUTED; it is tab/column bookkeeping
A 44-char line TYPEd on stock wraps at the 29-col screen edge with **no CR/LF
injected into the CHPUT stream** (BIOS CHPUT wraps). What the routine DOES own:
TAB→spaces expansion + a logical-column counter (§5.3) — proven independent of the
BIOS cursor (§5.4). The DIR derail is downstream of the missing emit + wrong return
state, not of any scroll logic ([[tier2-storms-are-downstream]] framing).

## 3. The pinned canonical entry (black-box, stock = oracle)

Method: `callwatch` (region entry-PC sets, both machines) + `callseq --log 0x53A7`
(caller ret + entry regs) + alignment-guarded `capture` at `$D88A` (exit regs).

| fact | value | evidence |
|---|---|---|
| entry | **`$53A7`** | only entered PC in `$5300:$5453` on ours — 400/400 ungated over boot+DIR (`callwatch --no-gate --machine ours --range 0x5300:0x5453`) |
| caller | kernel dispatcher, `ret=$D88A` | `callseq --log 0x53A7`: 18/18 boot calls, ours==stock byte-identical (`A=00 B=A7 C=02 ret=D88A`) |
| fingerprint | `B` = entry low byte `$A7` | every call; same dispatcher rule as the M22a eleven |
| inputs | **E = the character**; `C=$02`; `A=$00` observed | E walks `Sun 84-01-01`, CR/LF, `A`, `>` … char-for-char |
| gating func | `$02` CONOUT only | all 400 region entries logged with `C=02`; funcs `$01/$06/$07/$08/$0B` dispatch to their own M22a entries |
| stock-internal (NOT our ABI) | `$53A8` (CONIN-echo entry, `ret=$544C`; also stock's resident func-9/`$F1C9` output call, `B=$C9` there — no dispatcher fingerprint), `$5412/$5415` (per-char helper), `$541D-$542A` (INNOE), writers `$53D3`/`$53EA` | M22a spec §3 helper columns + this pass's func-9 writewatch (§5.5); provider-oracle-scope.md:1450 (the `$F1C9` body's `CALL $53A8`) |
| dead-or-internal, unobserved | `$53F0–$5411`, `$542B–$543B` | never entered in any window; either straight-line interior or filler — irrelevant to ours (we implement contracts, not layouts) |

Repro:
```
python3 probes/disk/disk_probe_diff.py callwatch --range 0x5300:0x5453 --in-func 0x02 \
    --machine both --keys '\r' --keys-at 22 --settle 35 --diska /tmp/zerobas_m22b_test.dsk
python3 probes/disk/disk_probe_diff.py callseq --log 0x53A7 --maxhits 20 \
    --keys '\r' --keys-at 22 --settle 35 --diska /tmp/zerobas_m22b_test.dsk
```

## 4. What ours does today (and did yesterday)

All byte checks: `build/disk.rom`, our own artifact. `$53A7..$543B` = `$00`.
- **Post-M22a:** CALL `$53A7` → 149-byte NOP-slide → `$543C: jp const_body` →
  CHSNS keyboard poll → `A=$00/$FF`, no char emitted, staged keys not consumed
  correctly by the CONOUT caller's logic → every func-2 char dropped + COMMAND.COM's
  DIR formatting fork (`$C5BB`: stock→`$C5BE`, ours→`$C649`; content divergence at
  DIR call n=32, the size right-justify loop).
- **Pre-M22a:** same CALL → 173-byte slide → `$5454: jp conout_body` → emit E via
  CHPUT, exit `A:=E` — the pinned contract, by accident. **This resolves the old M14
  oddity** ("`--log 0x5454` ours 12 / stock 0"): ours' 12 date chars *passed through*
  `$5454` mid-slide; stock's handler returns before ever reaching it. Nothing ever
  legitimately called `$5454` for func-2 on either machine.

## 5. Pinned contracts (what the fix must reproduce)

### 5.1 Register contract
Exit captured at `$D88A` immediately after the entry call
(`capture --at 0xD88A --nth 1 --arm-addr 0x53A7 --arm-cond 1 --machine stock`):

| char (E) | entry (callseq) | exit at `$D88A` | reading |
|---|---|---|---|
| `$53` 'S' | `A=00 B=A7 C=02 DE=0153 HL=D31A` | `AF=5344 BC=A702 DE=0153 HL=D31A IX=F195 IY=DC5B` | **`A:=E`**, `F=$44`, B/C/DE/HL preserved |
| `$75` 'u' | `DE=0175 HL=D31B` | `AF=7544 BC=A702 DE=0175 HL=D31B` | same |
| `$0D` CR | `DE=D30D HL=000D` | `AF=0D44 BC=A702 DE=D30D HL=000D` | control chars too: `A:=E` |

`F=$44` is constant across samples but NOT established as load-bearing: pre-M22a
parity ran on `conout_body`'s entry-F-passthrough and every probed surface matched.
**`$F306` stays SET** (the M22a §5.2 mirror rule): what reaches the BDOS caller is
`HL:=H(B),L(A)` — pre-M22a behavior (conout_body never touches `$F306`) matched
stock at all 27/27 + DIR + BDOSX surfaces. IX/IY: ambient values unchanged at exit
(consistent-with-preserved; `conout_body` push/pops them regardless).

### 5.2 Emit
One CHPUT per printable char, char in A at `$00A2` — ours' existing
`conout_body` path (M8/M10) is the proven implementation of exactly this.

### 5.3 TAB expansion — INSIDE this handler, not in the kernel, not in CHPUT
`TYPE` of an injected tab file (`fat12_add`, `/tmp` disk copies) on stock:
`$53A7` receives **raw `E=$09` exactly once**; the CHPUT stream shows spaces:

| tab context (logical col at tab) | spaces emitted | resulting col |
|---|---|---|
| col 1 (`A\tB`) | 7 | 8 |
| col 2 (`AB\tC`) | 6 | 8 |
| **col 8 exactly** (`ABCDEFGH\tX`) | **8** | 16 |
| col 34, after a BIOS wrap at 29 (`CDE…9\tZ`) | **6** | 40 |

Rule: `do { emit ' '; col++ } while (col & 7)` — at-least-one-space, 8-column
stops, computed from the **logical column, not the screen cursor** (§5.4: col 34
gave 6, a CSRX-based routine would have given 3 post-wrap).

### 5.4 The column cell: `$F237` (one byte)
Work-area diff across a single `$53A7` call (`capture --mem 0xF100:0x300` at entry
vs exit): exactly two cells change — `$F237` `$10→$11` (col 16→17, the 'S' printed
at column 16) and `$F3DD` (=CSRX, BIOS CHPUT's own). Across the TAB call:
`$F237` `$01→$08`. Semantics observed: printable → `col++` (writer `$53D3`);
CR → `col:=0` (writer `$53EA`); LF → untouched. `$F237` is the byte immediately
after the resident-code block `$F1C9–$F236`
([tier2-workarea-map.md](tier2-workarea-map.md) row 2).

### 5.5 `$F237` is PRIVATE to page-1 console code — but shared across ALL of stock's output paths
- readers, ungated across boot + DIR + a backspace edit: **only `$53D3`** (the
  routine itself). The RAM kernel never reads it.
- writers gated per func: func-2 → `$53D3/$53EA`; func-9 STROUT → **also
  `$53D3/$53EA`** (stock's resident `$F1C9` path bottoms into the same page-1 body,
  with `B=$C9`, no dispatcher fingerprint); BUFIN echo CR → `$53EA`. All PAGE1.
- ⇒ our implementation may maintain the cell in OUR shared bottleneck
  (`conout_body`) and every output path (func-2/`$53A7`, func-9/`res_print`, BUFIN
  echo/`conin_line_body`, DIRIO-out/`$5454`) gets a consistent column for free —
  the same shared-body shape stock uses, without copying its call graph. Using the
  SAME address `$F237` (not a private cell) keeps future `--mem 0xF100:0x300`
  capture diffs byte-clean.

## 6. Proposed fix shape (M22b; for sign-off — do NOT build yet)

Class: M8 (`$5454`) veneer + a small shared-body extension. No relocation needed —
the whole span is our own `$00` pad. Net-zero; 3-pass object stays 16384 B.

**Slice 1 — the veneer (restores M19/M20/M21-era parity):**
`ds $53A7-$` + `k_53A7: jp conout_body` in kernel.asm's existing pad before the
`$543C` block (the veneer bytes `$53A7-$53A9` overlap stock-internal `$53A8`, which
is never called on ours — 400/400 evidence, §3). This is byte-for-byte the behavior
the pre-M22a slide produced, on which 27/27 + DIR-100% + BDOSX 47/47 were green.

**Slice 2 — tab + column (closes the REAL pre-existing gap):**
in `conout_body` (runtime.asm free tail): on `E=$09` emit spaces per §5.3's
do-while; on printable emit+`col++`; on CR `col:=0`; on LF passthrough; cell =
`$F237`, seeded `$00` at work-area build (verify our WA init already zeroes it, else
add the seed). Exit `A` for the TAB call itself: pin stock's value during the build
(`capture --at 0xD88A --arm-cond '[reg E]==0x09'` — §8.1) before choosing `$09` vs
`$20`.

Build order falsify-first: land slice 1, rerun the FULL regression set (§7.1-7.3)
— that alone must restore DIR/date/A>; then slice 2 with the new tab acceptance.

## 7. Acceptance criteria
1. **Screen arbiter (the check M22a's suite lacked):** `screen --machine both` for
   (a) plain boot `--keys '\r'` (date `Sun 84-01-01` + `A>` render), (b) `'\rDIR\r'`
   (listing + footer + `A>`), both byte-identical frames ours==stock.
2. **No regression:** 27/27 boot callseq; M22a's bdosx2 14-record capture stays
   zero-diff (keys2 echo `x` now also VISIBLE on both screens); BDOSX 47/47;
   `make unit-test`; `make probe`; `disk.rom` == 16384 B.
3. **New differential oracle (slice 2):** inject `TABTEST.TXT`/`TABTEST2.TXT`
   (scratchpad `make_tabtest*_disk.py` recipe: `fat12_add` into a `/tmp` copy) and
   `TYPE` them: CHPUT stream (`callseq --log 0x00A2`) and `screen` byte-identical
   ours==stock — covers cols 1/2/8/34 incl. the at-stop and post-wrap cases.
4. **`$F237` parity:** `capture --mem 0xF237:0x1` at a late anchor, ours==stock.
5. **Docs:** [tier2-bdos-coverage.md](tier2-bdos-coverage.md) `$02` row gains the
   `$53A7` entry; [tier2-m22-cpmver-spec.md](tier2-m22-cpmver-spec.md) §8.1's
   "`$53A8` helper — pin it then" residual is resolved→superseded by this spec;
   STATE.md M14-oddity note (§4) corrected at the next overwrite.

## 8. Residuals / open questions (none block sign-off)
1. Exit `A` after a TAB (`$09` vs last space) — unpinned; one capture during build.
2. BS `$08` / BEL / other control chars through func-2: column behavior unobserved
   (BS may need `col--`; pin if a probe scenario ever exercises it).
3. Ctrl-S pause / Ctrl-P printer echo (published `_CONOUT` behaviors; presumably the
   `$5412/$5415` helper's job): unprobed, invisible to every current oracle surface
   — do NOT implement speculatively.
4. The `ESC x 5` + CR prefix seen once in TYPE's CHPUT stream arrives via a
   non-func-2 path (COMMAND.COM/kernel-owned) — out of scope.
5. Boot-time n=13/14 entry-`HL` mismatch (stock `$000D` vs ours `$0000`, resyncs by
   n=15) — pre-existing, outside this contract (entry HL is caller scratch).
6. Harness note: `writewatch`/`readwatch` cap ranges at 64 B; the §5.4 cell was
   found with a full-WA `capture --mem` diff instead (cheaper than 12 windows).

## 9. Clean-room status
- **No stock ROM / MSXDOS.SYS / COMMAND.COM code bytes read or decoded.** Stock-side
  evidence: entry PCs + counts (`callwatch`), caller ret + registers
  (`callseq`/`capture`), DATA cells (`$F237`, the WA block, CHPUT char stream =
  values in A at a published BIOS entry), screen renders. The §3 "returns before
  `$543C`" statement is an entered-PC-set observation, not a decode.
- Tab/column semantics derived from OUR OWN injected test files' observable output
  (spaces at CHPUT, cell values) + the published `_CONOUT` contract (map.grauw.nl:
  tab expansion; MSX2 TH BDOS §func $02) — the classic BDOSX-style black-box method.
- `$53A7` is a de-facto page-1 kernel-ABI address (class of `$4010`/`$5454`/the
  M22a eleven; spec-diskrom-kernel.md §1.3), pinned by call-target observation only;
  it lies inside the cross-vendor shared block `$4768–$576F`.
- Proposed bodies reuse OUR primitives (`conout_body`, CHPUT inter-slot path) — no
  stock algorithm reproduced; the do-while tab rule is re-derived from four
  observed input/output pairs.
- Test-disk hygiene: all probing on `/tmp` copies; committed images untouched
  (`git status` clean apart from the pre-existing M22a working tree).

## 10. Impact on the M22 recommendation (headline for sign-off)
**M22a cannot ship as-is** — it turns a load-bearing accident into a user-visible
regression (all console output via func-2 lost). Recommendation: **proceed with
M22a + M22b slice 1 together as one commit-series** (slice 1 is 3 bytes in existing
pad and restores the proven-parity behavior; M22a alone is a regression, slice 1
alone is already true today via the slide), then M22b slice 2 (tab/column) as the
follow-up slice with the new TYPE-oracle acceptance. The M22a screen-arbiter gap
(§7.1) should be added to M22a's own acceptance list before its sign-off.
STOP: awaiting sign-off; no asm has been touched.
