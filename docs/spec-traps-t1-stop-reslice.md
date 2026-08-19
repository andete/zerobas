# spec — interrupt-traps T1 re-slice: STOP (supersedes the INTERVAL first-slice)

Status: **DESIGN — sign-off pending.** Supersedes the INTERVAL choice of
`docs/spec-basic-interrupt-traps.md` §9/§12 for slice T1. The arc spec is otherwise
unchanged; only the *first event source* moves from INTERVAL to STOP.

Repository: all paths under `/Users/joost/projects/zerobas`. Repack-only
(`IF ROM_BASE < $4000`), like the rest of the arc.

---

## 1. Why re-slice — the oracle finding (D-T-5 resolved NEGATIVE)

Arc-spec decision **D-T-5** deferred INTERVAL's token to "oracle-confirm via the crunch
probe against the VG-8020." That confirmation was run (2026-07-24) and **failed**: both
the Philips VG-8020 **and** the National CF-3300 tokenise `interval on` as

```
ff 85 45 52 ff 94 20 95   =  INT(ff 85) + "ER"(45 52) + VAL(ff 94) + ON(95)
```

i.e. **MSX1 BASIC has no `INTERVAL` keyword** — it is an MSX-BASIC 2.0 (MSX2) addition.
On the same ROMs `STOP`(`90`), `KEY`(`cc`), `SPRITE`(`c7`), `STRIG`(`a3`) all tokenise as
real single keywords. For a faithful full-MSX1 BASIC (the charter) we must **not** add an
`INTERVAL` keyword — doing so would break the byte-identical crunch discipline and ship an
out-of-charter MSX2 feature. The MSX1 trap families are **KEY / SPRITE / STOP / STRIG**.

**Chosen first slice: STOP.** It is single-entry and — uniquely — needs **no new event
poll**: the run loop already detects Ctrl-STOP via `BREAKX` at every statement boundary
(`basic/program.asm` `rp_exec`). The STOP trap just diverts that existing detection to a
GOSUB instead of a break. So STOP proves the entire shared skeleton (ZTRAP table +
`check_traps` dispatcher + GOSUB-branch + auto-STOP + RETURN-resume + arming-statement
parse) with the *least* new mechanism — exactly the role INTERVAL was meant to play, and
with a bonus: **no new token, no kwtable row, no crunch-token risk** (STOP=$90, ON=$95,
OFF=$EB, GOSUB=$8D, the LINENO token $0E all already exist).

**Re-slice order:** T1 = STOP → T2 = STRIG (5 entries, PSG/PPI edge, first real
`event_poll` stanza) → T3 = KEY (10 entries, matrix) → T4 = SPRITE (VDP collision,
D-T-4). (Was INTERVAL → STOP+STRIG → KEY → SPRITE.)

**Already-landed skeleton is reused as-is:** the `ZTRAP` sysvars (`sysvars.inc:1109…`),
`trap_init`, and the `htimi_service`/`event_poll` scaffold (commits c355c1d, 83422df) all
stand. Only INTERVAL-specific parts become MSX2-dead: `event_poll`'s INTERVAL tick and
`ZINTVAL`/`ZINTCNT`. **This slice leaves `event_poll` untouched** (it is verified live at
49.8 Hz and is inert for STOP — its INTERVAL stanza reads `ZTRAP+0` state, which STOP never
sets ON). The dead INTERVAL tick is **replaced** (not merely removed) by the first device
stanza when T2/STRIG lands, to avoid churning verified interrupt-path code now.

---

## 2. Scope of this slice

**In:** `ON STOP GOSUB <line>` (arm) · `STOP ON | OFF | STOP` (tri-state) · the resident
`check_traps` dispatcher · the `ex_return` re-enable hook · the `set_state` helper · the
break-path intercept (§6 of the arc spec) · host unit tests · a `stop-trap-acceptance`
VG-8020 differential.

**Out (later slices):** STRIG/KEY/SPRITE event sources and their arming statements;
`event_poll` device stanzas; any INTERVAL surface (dropped entirely).

---

## 3. Data — no new RAM; reuse the ZTRAP entry already allocated

STOP is entry index `ZTI_STOP = 1` (`sysvars.inc`). Its 3 bytes = `[state][handler:2]`.
State encoding unchanged: `00 OFF / 01 ON / 10 STOP(user-suspend) / 11 SERVICING`, bit 7 =
PENDING. `TRAPENA` (count of ON entries), `TRAPPEND` (a PENDING was latched), `TRAPSVC` +
`TRAPSTK` (service stack) all as already defined. No new sysvars.

---

## 4. `set_state` — the shared arming-state helper (resident, repack-only)

```
; set_state: set a ZTRAP entry's tri-state, maintaining the TRAPENA (# ON) count.
;   IN: HL -> entry state byte;  A = new state (ZTS_OFF/ZTS_ON/ZTS_STOP)
;   OFF additionally clears PENDING (a disabled trap forgets its latched event).
;   Adjusts TRAPENA: +1 on (old!=ON -> new==ON), -1 on (old==ON -> new!=ON).
;   Clobbers A, B. Preserves HL, DE.
```
Logic: read old `(HL)&STATE_MASK`; compute the TRAPENA delta; write new state (preserving
PENDING unless OFF, which also clears bit 7); apply the delta to `TRAPENA`. Used by both
`STOP ON/OFF/STOP` here and every later arming statement.

---

## 5. Parsing

### 5.1 `ON STOP GOSUB <line>` — arm (sibling peek in `ex_on`)

`ex_on` (`program.asm:977`) already peeks `ERROR_TOKEN` after `ON`. Add a sibling:
```
                cp      STOP_TOKEN
                jp      z,ex_on_stop
```
`ex_on_stop`: consume STOP; `skip_spaces`; expect `GOSUB_TOKEN` (else `stmt_error`);
read the `$0E,<lineno>` (else `stmt_error`); `find_line_bc` (nc → `ex_goto_undef`); store
the resolved LINK into the STOP entry's `handler:2` field. **State untouched** (arm ≠
enable; a bare `ON STOP GOSUB` leaves it OFF until `STOP ON`). One handler line (not a
list — that is KEY/STRIG).

### 5.2 `STOP ON | OFF | STOP` vs bare `STOP` (the break) — extend `ex_stop`

`ex_stop` (`program.asm:387`) is currently `inc hl / jp do_break`. New:
```
ex_stop:        inc     hl                  ; past STOP token
                call    skip_spaces
                ld      a,(hl)
                cp      ON_TOKEN            ; STOP ON   -> enable
                jr      z,es_on
                cp      OFF_TOKEN           ; STOP OFF  -> disable (+clear PENDING)
                jr      z,es_off
                cp      STOP_TOKEN          ; STOP STOP -> suspend
                jr      z,es_stop
                jp      do_break            ; bare STOP (EOL/':'/expr) -> halt the RUN
```
`es_on/es_off/es_stop`: `inc hl` past the sub-keyword, load `A=ZTS_*`,
`ld hl,ZTRAP+ZTI_STOP*ZTRAP_ENTSZ`, `call set_state`, `ret`. Malformed trailing tokens
after a valid `STOP ON` fall to the next statement / `:` like every other statement.

**Lean build:** `ex_stop` stays `inc hl / jp do_break` byte-identically (the sub-parse is
`IF ROM_BASE < $4000`); the whole trap surface is repack-only.

*(No dispatch-table / kwtable / token changes at all — STOP already dispatches to
`ex_stop` in `exec`, `program.asm:435`.)*

---

## 6. The break-path intercept (arc spec §6)

At `rp_break` (`program.asm`, reached when `BREAKX` sets CF): if the STOP entry is exactly
`ON`, latch it and dispatch instead of breaking; otherwise (OFF/STOP/SERVICING) break
normally. HL here = the statement pointer `BREAKX` guarded (the resume point).
```
rp_break:
                ld      a,(ZTRAP+ZTI_STOP*ZTRAP_ENTSZ)
                and     ZTS_STATE_MASK
                cp      ZTS_ON
                jr      nz,rp_real_break        ; OFF/STOP/SERVICING -> the classic break
                push    hl
                ld      hl,ZTRAP+ZTI_STOP*ZTRAP_ENTSZ
                set     7,(hl)                  ; STOP PENDING
                ld      a,1
                ld      (TRAPPEND),a            ; wake check_traps
                pop     hl                      ; HL = resume stmt ptr
                jr      rp_trapchk              ; dispatch now (§7) with HL intact
rp_real_break:  call    do_break
                ret
```
A **held** Ctrl-STOP inside the handler still breaks: on dispatch the STOP entry
auto-STOPs (→SERVICING), so the next boundary's `BREAKX` finds state≠ON → `rp_real_break`
— matching the reference ("a second Ctrl-STOP while servicing aborts"). Bare `STOP` and
OFF/suspended both break (§6: "When OFF/STOP, the normal break happens"). This is a
deliberate STOP-family trait: its event *is* the break, so suspend does not latch (unlike
the event_poll traps), documented in PROVENANCE.md alongside the encoding.

---

## 7. The dispatcher — `check_traps` (resident page-1, EI run loop)

Insert a dispatch point in `rp_exec` after the `BREAKX` poll, gated by `TRAPPEND`:
```
rp_exec:        push    hl
                call    BREAKX
                pop     hl
                jr      c,rp_break
rp_trapchk:                                     ; (rp_break re-enters here)
    IF ROM_BASE < $4000
                ld      a,(TRAPPEND)
                or      a
                call    nz,check_traps          ; IN HL=stmt ptr; CF=1 -> a trap fired
                jr      c,rp_lp                  ; fired: run the handler line fresh
    ENDIF
                call    exec
                ...                             ; (unchanged tail)
```
`check_traps` (in `basic/traps.asm`, resident — 155 B page-1 free makes this affordable
without a tenant):
```
; check_traps: fire the highest-priority armed+pending trap, if any.
;   IN:  HL = the statement pointer about to run (the RETURN resume point).
;   OUT: CF=1 -> fired: a GOSUB frame was pushed, the entry is SERVICING, and
;                CURLINE now points at the handler line's LINK (rp_lp runs it fresh).
;        CF=0 -> nothing fired (HL/CURLINE unchanged); the run loop proceeds to exec.
```
Steps on the first entry with `state==ON && PENDING && handler!=0` (scan index 0..17 in
priority order — INTERVAL@0 is permanently OFF so it is skipped for free):
1. clear that entry's PENDING; `set_state`-style `state := SERVICING`; `dec (TRAPENA)`.
2. `call gosub_push` (resume = HL, CURLINE = current) — reuses the golfed helper. CF set
   (stack full) → `gosub_stk_over` (ERR 7), as GOSUB does.
3. push a service record `[GSP:2][idx:1]` onto `TRAPSTK` at `TRAPSTK+TRAPSVC*3`;
   `inc (TRAPSVC)`.
4. `ld (CURLINE), handler_link`.
5. re-scan for any remaining `ON&&PENDING&&handler` → set `TRAPPEND` to 1/0 accordingly
   (the "one trap per inter-statement gap" rule; for STOP-only there is never a second).
6. `scf` / `ret`.

`RESUMEFLAG` is already 0 at `rp_exec`, so `jr c,rp_lp` runs CURLINE (the handler) fresh —
identical to the `ON ERROR` trap-branch model (`interp.asm` "setting CURLINE IS the
branch").

---

## 8. RETURN re-enable — `ex_return` hook (resident, repack-only)

At `ex_return` entry (`program.asm:636`), before the frame pop:
```
    IF ROM_BASE < $4000
                ld      a,(TRAPSVC)
                or      a
                call    nz,trap_return_check    ; re-enable a trap whose gsp == current GSP
    ENDIF
```
`trap_return_check`: the top `TRAPSTK` record is at `TRAPSTK+(TRAPSVC-1)*3`. Compare its
`gsp` with the current `(GSP)` (before the pop). On **match** this RETURN is the trap
frame's own: `dec (TRAPSVC)` (pop the record) and — iff the entry `idx` is still
`SERVICING` (a handler `STOP OFF/ON/STOP` overrides) — `state := ON` (preserving PENDING)
and `inc (TRAPENA)`. On **no match** (a normal/nested RETURN) do nothing; the frame pop
proceeds. Nested normal GOSUBs push GSP higher and their RETURNs pop back down first, so
the top record only matches when the trap frame is genuinely on top — the match nests
exactly (arc spec §3, the GSP-match service stack).

---

## 9. Gates — host-first, then the empirical differential

### 9.1 Host unit tests — `tests/test_traps.py` (`make unit-test`)

Emulator-free, calling routines by label (the `msxtest.Machine` harness):
- **`set_state`**: every transition adjusts `TRAPENA` correctly (OFF→ON +1, ON→OFF/STOP
  −1, OFF↔STOP 0); OFF clears PENDING; ON/STOP preserve it.
- **`check_traps` fires**: ON+PENDING+handler → CF set, entry SERVICING, PENDING cleared,
  TRAPENA−1, TRAPSVC+1, a `[GSP][idx]` record on TRAPSTK, CURLINE = handler, a GOSUB frame
  at GSP with resume = the passed HL.
- **`check_traps` no-fire**: OFF / STOP(suspended) / PENDING-clear / handler==0 → CF clear,
  no state change.
- **`trap_return_check`**: gsp-match → SERVICING→ON, TRAPENA+1, TRAPSVC−1; gsp-mismatch →
  untouched; handler-changed-state (SERVICING overwritten) → left as the handler set it.
- **End-to-end via `run_prog`** with `BREAKX` trapped to assert CF on the Nth call
  (simulated Ctrl-STOP): `10 ON STOP GOSUB 100 / 20 STOP ON / 30 A=A+1:IF A<50 THEN 30 /
  40 END / 100 B=B+1:RETURN` → the simulated press fires the handler (B increments) and the
  loop resumes (A completes). A `STOP OFF` variant → the simulated press breaks (ENDFLAG,
  B stays 0).

### 9.2 `stop-trap-acceptance` — VG-8020 differential (and **run it**)

A new probe + `make stop-trap-acceptance`, on the repack machine vs the VG-8020, using the
matrix-hold harness (`run_cases(holds=…)` presses the Ctrl-STOP row). **Timing-robust
outcomes**, not fire-counts:
- **Case A (trap fires + diverts):** `10 ON STOP GOSUB 100 / 20 STOP ON / 30 A=A+1:IF
  A<20000 THEN 30 / 40 PRINT"NOTRAP":END / 100 PRINT"TRAPPED":END`, hold Ctrl-STOP during
  the loop → **both** machines print `TRAPPED` (any press in the window diverts; the
  handler ENDs deterministically).
- **Case B (OFF → normal break):** same but no `STOP ON` (or `STOP OFF`), hold Ctrl-STOP →
  **both** print `Break in 30`.
- **Case C (RETURN re-arms):** handler `RETURN`s and the loop continues; a second press
  later re-fires → both reach the same terminal state.
Compare zerobas-repack == VG-8020 for each.

### 9.3 Standing sweep + byte-identity

`make basic-reloc` (lean byte-identity + `--page1`/`--page0` tenant closure), `unit-test`,
`diskbasic-acceptance-repack`, `string`, `play-trace-acceptance` (event_poll untouched but
re-prove no regression), and the reloc/lean gate — then commit.

---

## 10. Byte budget

### 10.0 MEASURED 2026-07-24 — resident-everything does NOT fit (284 B over)

The routines were written resident and measured (`main-reloc` with the ceiling guard
neutralized): the image ends at **$811C = 284 B past the $8000 page-1 ceiling**. HEAD free
was **80 B** (not the 155 B of D-T-8c — the `event_poll`/`htimi_service`/`trap_init` wiring
of 83422df consumed ~75 B of the carve). So the fully-generic (18-entry, reusable) dispatch
is **~364 B** of new page-1 code against **80 B** free — a **~284 B shortfall**. This is a
STOP-and-confirm fork: **D-T-8c's "keep dispatch RESIDENT" premise is falsified** (it rested
on 155 B free + a ~118 B dispatch; both were wrong). Paths under evaluation:
- **A (recommended) — revert to D-T-2a: tenant the dispatch.** Move the generic machinery
  (`check_traps`/`ct_find`/`set_state`/`trap_return_check`) into sub-ROM tenant(s) off the
  page-1 budget; keep thin resident stubs + the parsers + hooks. Resident floor ~110–160 B
  → still a modest cold-cluster carve (~40–80 B), but the skeleton stays generic for T2–T4.
- **B — keep dispatch resident, fund a ~284 B carve** (2–3 `build_83_name`-scale evictions).
  Least trap-code churn (already written + host-testable), largest carve.
- **C — STOP-specialise** the dispatcher (drop the 18-entry scan) → small/no carve now, but
  abandons the reusable skeleton (T2 re-generalises it).

*(The original §10 estimate below said ~190 B — the measured number supersedes it.)*

### 10.0a SCOUT 2026-07-24 — no cheap carve exists (the disk/file region yields 0 B)

A closure scout of the $7000–$7800 cold disk/file/cassette cluster (`lrset_common`,
`do_name`, `do_open`, `input_common`, `dpl_line`, `do_disk_bload`, `skip_hdr`, `ctp_line`,
`bsv_cas_id`, `exf_item`, …) found **zero page-0-evictable bytes.** Every candidate is
either an **eval-bound executor** (`eval`$4A89/`str_eval`$4976 whose closure dips into the
low-region float pack — `fp_sub`$3570, `fac_to_int_strict_reset`$3874, `pu_deref_body`$2877)
or an **I/O driver** (FAT via `subrom_call`$3C94; cassette via `TAPIN`/`TAPION`/`TAPOUT` BIOS;
BLOAD via `WRTVRM`$004D) — all callees <$4000, disqualifying a page-0 tenant. The genuinely
pure, cold, page-1+RAM helpers that once lived here were **already evicted** (`build_83_name`,
tokeniser/detokeniser, `dirverb_tenant`). The only clean leaves left (`fld_add`, `fld_find`,
`cas_put`, `fch_select`, ~30–60 B) are called *by* resident executors, so evicting them
inverts the call direction (resident caller must `subrom_call` out) at a cost exceeding the
saving. **Conclusion: page-1 is byte-starved with no cheap carve** — funding T1 needs either
the page-1 CIRCLE→co-routine reclamation (§10.3 opt 2, ~150 B, high effort/risk, funds T1–T4)
or an aggressive tenant-everything split, and even a *minimal* STOP trap (~150–220 B resident:
the parsers alone are ~90 B) does not fit the **80 B** free. This is the §10 dominant-risk
wall, now fully characterised — a project-direction STOP-and-confirm.

Page-1 free = **80 B** (measured; was 155 B post `build_83_name` carve, D-T-8c, minus ~75 B
consumed by the 83422df poll wiring). Resident additions this
slice: `check_traps` (~55 B), `trap_return_check` (~45 B), `set_state` (~25 B),
`ex_on_stop` (~25 B), `ex_stop` sub-parse (~25 B), the two hook stubs (~15 B) ≈ **~190 B**
— **over 155 B.** Levers before any carve: (a) `set_state`/`check_traps` share the
`idx*3` → `ZTRAP+idx*3` address math as one helper; (b) `ex_on_stop` shares the
`GOSUB`/`$0E`/`find_line_bc` tail with `ex_gosub`; (c) the two hooks are ~7 B each once
`check_traps`/`trap_return_check` own the work. **Measure-first after writing** (the
recurring lesson); if still over, the cheapest carve is another cold page-1 cluster to a
tenant (per D-T-8c precedent) — surfaced as a STOP-and-confirm only if the real measured
number exceeds 155 B after the shared-helper golf.

---

## 11. Decisions for sign-off

- **D-T1S-1 — re-slice STOP-first** (this doc). Recommend as written.
- **D-T1S-2 — STOP suspend == break** (§6): a suspended/OFF STOP trap lets Ctrl-STOP break;
  only ON diverts. Follows arc spec §6 verbatim; documented as a STOP-family trait.
- **D-T1S-3 — leave `event_poll` untouched** this slice (INTERVAL tick inert, replaced when
  STRIG lands). Recommend, to avoid churning verified interrupt-path code.
- **D-T1S-4 — acceptance = timing-robust outcomes** (§9.2), not fire-counts. Recommend.
- **D-T1S-5 — eager handler resolve** (`ON STOP GOSUB` stores the resolved LINK at arm
  time; undefined line → error at the arming statement, like GOSUB). Recommend.

---

## 12. BLOCKER (empirical, 2026-07-24) — the §6 live-BREAKX design cannot run the handler

The code was written resident, **fits** (measured: page-1 free = 258 B after the CIRCLE
carve fda9c17 — §10.0/§10.0a's 284 B shortfall is RESOLVED, now stale), and the host
unit tests (`tests/test_traps.py`, 41 checks) all pass: `set_state`, `ct_find`,
`check_traps`, `trap_return_check` are each correct in isolation. But the **end-to-end
empirical test on the repack build caught a design-level bug the green host suite hid**
(the recurring arc lesson, ~15× now).

**Symptom.** A new probe (`probes/basic/basic_probe_stop_trap.py`) arms `ON STOP GOSUB
100 / STOP ON`, runs an infinite `30 GOTO 30`, and holds Ctrl-STOP. Instrumented RAM
after the press: **flag=0** (handler POKE never ran), **state=$03 SERVICING**,
**TRAPENA=0**, **TRAPSVC=1**. So `check_traps` DID fire (state→SERVICING, frame pushed,
CURLINE=handler) — but the handler's body **never executed a single statement.** Verified
across hold widths from 4 s down to a **20 ms tap** — identical (flag=0). Arming itself is
perfect (PEEK $E1D4=1 ON, TRAPENA=1, handler link $804D stored).

**Mechanism.** After `check_traps` returns CF=1, `jr c,rp_lp` sets up the handler line and
falls into `rp_exec` — whose **first act is another `call BREAKX`**. Ctrl-STOP is still
physically held (the fire→handler gap is micro­seconds; no release can be timed into it),
so CF=1 → `rp_break`; the STOP entry is now **SERVICING (≠ON)** → `rp_real_break` →
`do_break`. The handler breaks at its own first statement boundary, **before** running any
statement. Under the §6 "detect Ctrl-STOP with live `BREAKX` in `rp_break`" design this is
unavoidable: a live keyboard scan cannot be *consumed*, so a held key re-triggers every
boundary, including the handler's.

**Why the reference almost certainly differs (UNVERIFIED — needs the VG-8020 oracle).**
Real MSX detects the STOP-trap condition at **interrupt time** (the 60 Hz keyboard ISR /
`INTFLG`-style latch), **cleared on consumption** and only re-set on the next frame. That
hands the freshly-dispatched handler a **full ~16 ms frame** (tens of thousands of Z80
cycles) to run before the held key is seen again — ample for a `POKE:END` handler to
complete. zerobas's `event_poll` (the H.TIMI poll) does **not** check Ctrl-STOP at all
(T1 left it INTERVAL-only), so STOP has **no interrupt-latched detection** — the §6
shortcut ("STOP needs no new event poll — just divert the existing `BREAKX` detection")
is the root of the defect.

**This invalidates D-T1S-2 and the §6 design.** Candidate redesigns (a real fork — each
needs oracle confirmation of the target semantics before coding):

- **R1 — interrupt-latched detection (most faithful).** `event_poll` reads the Ctrl-STOP
  latch each frame and, for an ON STOP entry, sets PENDING + `TRAPPEND` (exactly the
  device-stanza shape T2/STRIG will add anyway). `rp_break` reverts to handling ONLY the
  OFF-state normal break. The handler then runs via the same `check_traps` path, uninter­
  rupted for its frame. Cost: churns the "verified interrupt-path code" D-T1S-3 wanted to
  avoid, and needs a reliable per-frame Ctrl-STOP latch under C-BIOS (INTFLG $FC9B may not
  be C-BIOS-populated — must verify).
- **R2 — edge-detect in `rp_break` (minimal).** Track the previous Ctrl-STOP level; act
  only on a rising edge (was-up→now-down). One press → one fire; the held key produces no
  further edge, so the handler runs to completion; release+re-press = a new edge. Keeps
  live BREAKX, no interrupt-path change. Needs oracle confirmation that real MSX is
  one-fire-per-press (vs re-fire-per-frame).
- **R3 — SERVICING suppresses the break** (handler is Ctrl-STOP-proof for its duration).
  Simplest, but abandons §6's "a 2nd Ctrl-STOP while servicing aborts" — an explicit UX
  change the oracle must arbitrate.

**Prerequisite before choosing: characterize the real VG-8020** (hold vs tap Ctrl-STOP
with `ON STOP GOSUB`: does the handler run once? re-fire per frame? can a 2nd press abort
it?). The T1 code (parsers + arming + dispatch + host tests) is otherwise sound and can be
reused as-is under any of R1–R3; only the *detection seam* is wrong.

### 12.1 CONFIRMED via the VG-8020 oracle (2026-07-25) — R1 is the fix

Oracle characterized (`Philips_VG_8020`, boots cleanly under the probes' openMSX). Two
regimes, both machines POKE-sentinel instrumented:

- **Held Ctrl-STOP during a tight break-poll loop (`30 GOTO 30`), 5 ms → 4 s:**
  zerobas == VG-8020, **both `flag=0`** (both break, handler does not run). This regime is
  *non-discriminating* — the earlier sweep's false "we match" reading came from here.
- **DISCRIMINATING regime — a brief tap DURING a delay (`30 FOR I=1 TO 4000:NEXT`),
  RELEASED, then a poll loop (`40 GOTO 40`):** **VG-8020 `flag=1` (handler RUNS), zerobas
  `flag=0` (handler never runs)** — robust across press@+0.3/+0.5 s, tap 30–100 ms.

**Interpretation.** Real MSX detects Ctrl-STOP at **interrupt time** and LATCHES it
(INTFLG-style, consumed on dispatch); a tap caught by the 60 Hz ISR fires the handler at
the next statement boundary **even after the key is released**. zerobas's live `BREAKX` in
`rp_break` cannot latch: a released tap is either missed (no fire) or, while held, breaks
at the handler's first boundary. **This is a genuine, oracle-confirmed zerobas divergence,
and D-T1S-2 / the §6 "divert the existing BREAKX detection" design is the root cause.**

**Decision: adopt R1.** `event_poll` (already wired into H.TIMI at 60 Hz, `docs/spec-
traps-t1-htimi-page1-safety.md`) grows a Ctrl-STOP stanza: when the STOP entry is ON and
the ISR sees Ctrl-STOP, latch PENDING + raise TRAPPEND (exactly the device-stanza shape
T2/STRIG needs anyway), and *consume* the raw Ctrl-STOP so the handler is not immediately
re-broken. `rp_break` reverts to the pristine `do_break` for the OFF/suspended normal
break only (its STOP-ON intercept is removed). Open sub-questions for the R1 spec, to be
pinned against the oracle while writing it: (a) the exact Ctrl-STOP read available to
`event_poll` under C-BIOS at interrupt time (INTFLG $FC9B populated? else a debounced
matrix read), DI-safe and register-transparent per the H.TIMI contract; (b) held-key /
2nd-press-during-handler semantics (does VG-8020 break out of a running handler?); (c)
RETURN re-arm across a released-then-re-pressed tap. **The dispatch/arming/host-test code
is reused verbatim; only the detection seam moves from `rp_break` to `event_poll`.**

**Acceptance gate (the real one):** the DISCRIMINATING case above — a released tap during a
delay must make the handler run on BOTH machines — is what `stop-trap-acceptance` must
assert (not the non-discriminating held-key case, where both correctly break).

### 12.2 AS-BUILT (2026-07-25) — R1-lite: the grace window [SUPERSEDED BY §12.3]

> ⚠️ **This section is HISTORICAL.** Its oracle claims ("a key still held one frame later
> aborts the handler", and the faithfulness boundary derived from it) came from a capture
> window that closed while the program was still running. STOPGRACE is retired. See §12.3.

Building §12.1 turned up a simpler, smaller fix than the proposed "event_poll latches
Ctrl-STOP → PENDING" scheme. A one-line experiment (rp_break: while `SERVICING`, IGNORE the
Ctrl-STOP instead of breaking) made zerobas fire the handler on the discriminating case,
**3/3**. That proves the premise wrong in a useful way: zerobas's live `BREAKX` **already
catches** the tap (it polls every FOR/NEXT iteration) — the tap is NOT missed. The defect
was ONLY that the freshly-dispatched handler re-broke at its own first boundary while the
triggering key was still (briefly) down. So no interrupt-time latch / NEWKEY read is needed;
just a bounded window in which the just-entered handler is Ctrl-STOP-proof. (NEWKEY $FBE5 IS
populated under C-BIOS — verified — but is unused; INTFLG $FC9B is NOT populated.)

**As-built mechanism (R1-lite):**
- `STOPGRACE` (1 B RAM, `sysvars.inc` $E220). `check_traps` sets it when it fires the STOP
  entry (idx==`ZTI_STOP`); `event_poll` clears it every VBLANK, **before** the `TRAPENA`
  fast-out (a SERVICING handler has `TRAPENA==0`, so gating the clear on `TRAPENA` would
  wedge it set). `trap_init` zeroes it. Live window = `[fire, next VBLANK]`, mirroring
  INTFLG's clear-on-fire / re-set-next-frame without any interrupt-time keyboard read.
- `rp_break`: `ON` → fire (unchanged); `SERVICING` + `STOPGRACE` set → ignore, run the
  handler statement; `SERVICING` + grace expired → **break** (a key still held a frame later
  aborts the handler — VG-8020 does this, oracle-confirmed robustly); `OFF`/suspended →
  the classic break. `event_poll` grows only the two-instruction grace clear; its Ctrl-STOP
  detection stays in the run loop's existing `BREAKX`, so the verified interrupt path and
  the normal-break path (cont.py) are minimally disturbed.

**A second bug the differential caught (unrelated to detection):** the arming sub-parse
`es_set` ended with `ret`, which **swallowed the rest of the line** — `STOP ON:STOP OFF`
left the trap ON (the `STOP OFF` never ran), and `STOP ON:<anything>` dropped `<anything>`.
Fixed to `jp exec_stmt` (statement continuation). The host suite missed it (it calls
`set_state` directly, never through the line executor); the `B2_stop_off` differential
exposed it. Both fixes are the recurring arc lesson (~15×): green host tests + static
reasoning hid two real defects that the empirical VG-8020 differential caught.

**Faithfulness boundary (documented deviation):** the one regime zerobas does NOT match is a
**held** Ctrl-STOP in a **tight** `GOTO` loop with an **instant** (`POKE:END`) handler: VG
gives flag=0 (handler does not complete), zerobas gives flag=1 (handler runs in-grace). This
depends on VG's exact INTFLG-vs-frame accident and is not clean-room replicable; zerobas's
flag=1 is arguably the more correct "the handler ran" outcome. Every meaningful case matches:
tap→fire, armed-off/stop-off→no-fire, held→break, held-breaks-a-running-handler.

**Gate:** `make stop-trap-acceptance` — A (tap fires), B (armed-off no-fire), B2 (stop-off
no-fire) ASSERTED zerobas==VG-8020 (robust across trials); D (interruptible) a straight
differential. Green. Byte budget after R1-lite: page-1 free **232 B**. Standing sweep
(`unit-test` 52/52 incl. `test_traps`, `basic-reloc` lean-identical, `diskbasic-acceptance-
repack` 34/34, `string`, `play-trace`) all green. **D-T1S-2 is superseded by this section.**

### 12.3 AS-BUILT (2026-07-25, supersedes §12.2) — the edge shadow, and STOPGRACE retired

§12.2 is **withdrawn as a description of the reference**. Its two oracle claims — that a key
still held one frame later "aborts the handler — VG-8020 does this, oracle-confirmed
robustly", and the "faithfulness boundary" it derived from that — both came from the `D`
acceptance case read through a **capture window that closed while the program was still
running**. `D`'s handler carries a `FORK=1TO9000:NEXT` delay that takes ~15 s on the
reference; the gate captured 9 s after the last key-up and read `flag==1` on both machines,
which is not "the handler was aborted", it is "the handler has not reached line 108 yet".
Both sides were being read mid-loop, and the agreement was an artifact. Retrofitting the
`done` sentinel to `basic_probe_stop_trap.py` (so every reading is taken only once the
machine is back at command level) made the disagreement visible immediately.

**What the reference actually does** (VG-8020, 2026-07-25, each result 2 trials):

| stimulus | reference | rule |
|---|---|---|
| Ctrl-STOP while entry `ON` | fires, never breaks | `ON STOP GOSUB` + `STOP ON` makes the program **unbreakable from the keyboard** — the point of the statement |
| 100 ms tap during the handler | handler **completes**, +1 fire after `RETURN` | latched, not obeyed |
| 3 s hold during the handler | handler **completes**, +1 fire | **edge**, not level — one hold, one extra fire |
| 11 s hold spanning the handler | handler **completes** | never aborts, at any duration |
| 40-edge tap train during the handler | handler **completes** | ditto |
| handler re-arms itself (`STOP OFF:STOP ON`, one line) under a held key | **122 fires** | a transition into `ON` does **not** seed the shadow |

That is the T2 STRIG model (`spec-traps-t2-strig.md` §4) applied to Ctrl-STOP — with one
measured exception, the last row.

**As-built mechanism:**
- `rp_break` (`basic/program.asm`): `bit 0,(hl)` on the STOP entry — `ON` (01) and
  `SERVICING` (11) are both **sampled and never break**; `OFF` (00) / suspended (10) fall to
  `rp_real_break`. When sampled, a 0→1 edge against `ZTS_SHADOW` (bit 6) sets `PENDING` +
  `TRAPPEND`; shadow already set → ignore the key and run the statement.
- `rp_exec`: the `CF=0` arm of the existing `BREAKX` poll clears the shadow. This is the
  release observation the run-loop seam needs — `rp_break` is only reached when the key IS
  down, so without it the shadow latches forever. (`ep_strig` gets this for free: it polls
  `GTTRIG` every frame regardless of level.)
- `ex_stop`/`es_set`: **deliberately no seed**, unlike `ex_strig_set`, with the reason in a
  comment. The seed was written first and the last table row deleted it. The case a seed
  would protect (key held across the enable) is unreachable for STOP anyway: with the entry
  `OFF` or suspended, a held Ctrl-STOP breaks the program at the line boundary *before*
  `STOP ON` runs.
- `STOPGRACE` is **retired** — the byte ($E220), `check_traps`'s set, `event_poll`'s
  unconditional clear, and the `trap_init` fill length (now `TRAPPEND-ZTRAP`). It was a
  timing proxy for what `check_traps`'s existing `and ZTS_SHADOW` already does: carry the
  shadow into `SERVICING`, so the still-held triggering key is not a fresh edge — with no
  window to expire. **Do not reintroduce a timing proxy here.**

**Byte budget:** page-1 free **62 B → 78 B** (the retired grace machinery outweighs the edge
logic by 16 B); low region unchanged at 14 B.

**Gate:** `make stop-trap-acceptance` — A/B/B2 plus new **C** (handler baseline: exactly one
fire), **C2** (press during the handler → latched → exactly two), and **E** (re-arm under a
held key → re-fires; asserted as a per-machine PROPERTY `flag>=2`, since the count is an
artifact of how many line boundaries fit the run — ref 122, zerobas 6). D now reads `flag=2`
on both. `tests/test_traps.py` grows `t_stop_shadow`, a fence pinning that `ZTI_STOP` is not
special-cased out of the shadow discipline.

**Arc lesson, again:** the host suite was green through all of this and stayed green — it
pins zerobas's own state machine, not the oracle. What was never really measured was the
reference, because the apparatus could not hold still long enough to read it.
