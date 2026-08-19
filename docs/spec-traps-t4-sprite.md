# spec — interrupt-traps T4: the SPRITE collision trap (`ON SPRITE GOSUB` + `SPRITE ON/OFF/STOP`)

Status: **✅ LANDED + VERIFIED 2026-07-25** — lean ROM byte-identical, walls low 5 B /
page 1 22 B free. Graphics D-G7-4 is closed. **The gate is `make
sprite-trap-acceptance` — 26 cases, 123/123** after the 2026-07-26 **cadence
rebuild** (§1.2.1: the old `F_cadence` measured the main loop, and the 1.5
jiffies/fire it exposed turned out to be the *handler's* cost, not a divergence —
no ROM change). The arc was declared complete at T4 and was not: T5 INTERVAL
followed, see [`spec-basic-interrupt-traps.md`](spec-basic-interrupt-traps.md).

Signed off 2026-07-25. D-T4-2 decided **against** the recommendation —
the poll goes in the **low region off `htimi_guard`**, not page-1 `event_poll`
(§3), so T4 needs a small promotion after all. D-T4-3 as recommended: the T1
divergence is fixed **first, in its own commit**. D-T4-1/4/5 as written.

Fourth and last slice of the interrupt-trap
arc ([`spec-basic-interrupt-traps.md`](spec-basic-interrupt-traps.md), D-T-6 order
T1→T2→T3→T4). Follows [`spec-traps-t3-key.md`](spec-traps-t3-key.md). Closes the
graphics arc's **D-G7-4** handoff, which left `SPRITE ON/OFF/STOP` as an accepted
no-op and `ON SPRITE GOSUB` unimplemented.

**T4 is the smallest slice in the arc, and the only one whose event the program
produces entirely by itself** — two overlapping sprites, no keyboard matrix, no PSG
injection, no C-BIOS patch. The apparatus reduces to "inject the program, RUN, poll
the done sentinel", and the gate is fully deterministic.

---

## 1. Oracle characterization (Philips VG-8020, 2026-07-25)

All readings below are **`done`-gated** (§8): the capture fires the moment the
program sets `$D003`, and a program that errored out or was still running at the
deadline is captured with `done==0` and is a FAILURE, never a zero. Every case in
this section returned `done=1`. Sentinels: `$D000` fire count (saturating at 250 —
`POKE 256` would raise ERR 5 and disguise a "fires every frame" answer as an error
case), `$D002` trapped `ERR`, `$D003` done, `$D004`/`$D005` auxiliaries.

The collision is produced by `SPRITE$(0)=STRING$(8,255)` (a solid 8×8) plus two
`PUT SPRITE` planes at `(100,100)` and `(104,100)`; the **miss** control puts them
at `(40,40)` and `(160,140)`.

### 1.1 The event: a LEVEL, sampled once per frame — not an edge

| case | cnt | reading |
|---|---|---|
| `A_hit` — overlapping, armed + `SPRITE ON`, 400-iteration loop | **56** | fires repeatedly, not once |
| `A2_miss` — same program, sprites apart | **0** | the discriminating control |
| `F_cadence` — as `A_hit`, fires and frames counted **by the emulator** | **299 fires / 300 frames, on BOTH machines** | **exactly one fire per frame** |

`F_cadence` is the load-bearing measurement. ⚠️ **Its 2026-07-25 form — the fire
count over a `JIFFY` delta the BASIC program computed itself — measured the main
loop's progress rather than the trap's rate, and was rebuilt on 2026-07-26; see
§1.2.** The reading above is the rebuilt one. **The SPRITE trap is not an
edge trap.** While two sprites overlap it fires every frame, indefinitely. This is
the opposite of T2's STRIG (a level that is edge-detected against a shadow) and
unlike T3's KEY (a delivery event) — and it makes T4 *cheaper* than both, because
**there is no edge shadow to keep and no seed decision to make** (contrast the long
seed rationale at [`program.asm:470`](../basic/program.asm)).

### 1.2 The cadence is bounded by the STATEMENT-BOUNDARY rate, not only by frames

| loop body | fires | frames | fires/frame |
|---|---|---|---|
| tight `FOR I=1 TO 200:NEXT` | 31 | 30 | **1.03** |
| `X=I*1.5` ×100 | 62 | 60 | **1.03** |
| `X=SIN(I)` ×60 | 105 | ≥250 | boundary-limited |

A trap dispatches at a statement boundary and PENDING is a single latch, so when a
program spends several frames inside one statement those frames collapse into one
fire. Above ~50 boundaries/s the fire rate tracks the frame rate; below it, it
tracks the boundary rate.

**Gate consequence (the same shape as T3's repeat-count finding, §8):** the raw fire
COUNT is *not* an equality-differential — it is a function of how many frames elapse
in a window whose duration differs ~7× between the two machines.

#### 1.2.1 🔴 REBUILT 2026-07-26 — the ratio measured the MAIN LOOP, and the handler is part of the boundary rate

The 2026-07-25 gate turned the paragraph above into `0.75 <= cnt/aux <= 1.35`, where
`cnt` is the fire counter (which **saturates at 250**) and `aux` a `JIFFY` delta the
**main program** computed by polling. It went RED at 95/96 when `TIME` landed —
a commit that does not touch the trap. Both halves were unsound:

* **the numerator saturates.** Post-`TIME`: `cnt=250 aux=172`, asserted as 1.45 when
  the counter had simply run out of range. Pre-`TIME`, the same program: `cnt=170
  aux=163` = 1.04, PASS. `TIME`'s only contribution was a small interpreter
  slowdown that pushed a saturating counter over its cliff.
* **the ratio tracks the main loop, not the trap.** Three measurements of the same
  quantity returned **1.00, ≥1.43 and 0.67** fires/jiffy, differing only in how long
  the *handler* was — because §1.2's own insight cuts deeper than it was applied:
  the handler runs at a statement boundary, so **the handler is itself part of the
  boundary rate.** A denominator computed by main-loop statements is competing with
  the numerator for the interpreter.

**And the underlying quantity is not 1.0 on zerobas.** Measured between fires (the
T5 technique: the handler stamps `JIFFY` at fire #1 and fire #1+100, so the main
loop is out of the measurement) the period is **1.500 jiffies/fire on the repack
build against 1.000 on the VG-8020** — identically on a control built from the
pre-`TIME` commit `e3a2135`, which is what cleared `TIME`.

**1.5 IS THE HANDLER'S OWN COST, NOT A LOST FIRE.** Emulator-level counting settled
it in one run — watchpoints on `JIFFY` and on the handler's own `POKE`, plus
breakpoints on `htimi_guard`, `sprtrap-body.inc`'s `set 7,(hl)` latch and
`check_traps`' fire exit (`$5C32`):

| handler in the loop | ref fires/frame | zb fires/frame | zb latch / ISR entries |
|---|---|---|---|
| `POKE` + `RETURN` (lean) | 0.997 | **0.997** | **300 / 300** |
| the T4-era counting + stamping | 0.997 | 0.62 | 300 / 300 |
| one extra float statement | 0.24 | 0.727 | 251 / 300 |

The source **offers** a fire on every frame (300 latches in 300 ISR entries) and the
dispatcher **delivers** every one it can (299 dispatches). With a lean handler
zerobas fires on 299 of 300 frames — the reference's figure, to the frame. What
differs is only that the T4-era handler costs ~1.6 frames of zerobas interpreter
time and ~0.7 of the VG-8020's. **No divergence, and nothing to fix in
`event_poll` / `check_traps` / the `htimi_guard` seam.**

So the invariant to gate is the general law, verified on both machines across a 30×
range of handler lengths (all six cells above):

> **trap-driven rate == min(1 fire/frame, the same handler's synchronous rate)**

Both sides are measured in **one boot**, so there is no per-machine constant and no
tolerance band standing in for a denominator: if a future slowdown stops the
handler fitting in a frame, the ceiling moves with it and a correct implementation
stays green. Gate on that, never on a count and never on a ratio whose denominator
the interpreter can starve.

#### 1.2.2 A handler that outlasts a frame STARVES THE MAIN PROGRAM COMPLETELY

Measured while rebuilding the case, and it is a property of the design rather than a
bug: a fresh collision has always re-latched by the time a >1-frame handler
`RETURN`s, so the pending trap fires at the *same* statement boundary again and the
interrupted statement never runs. With the T4-era handler on the repack build the
program sat at one poll line for **400 emulated seconds** without advancing (the
emulator's window-close cell written, the program's acknowledgement never). Hence
the rebuilt case's window boundaries are the emulator's too, and its synchronous
window runs **first** — the T5 rule (*when the feature can starve the main program,
the main program cannot be the instrument*) extended from the readings to the
window boundaries. The reference is subject to the same starvation; its own float
handler costs ~4 frames.

### 1.3 Arm, enable, suspend

| case | cnt | conclusion |
|---|---|---|
| `B_armed_not_on` — `ON SPRITE GOSUB` with no `SPRITE ON` | 0 | **arm ≠ enable**, as T1/T2/T3 |
| `C_off` — armed, then `SPRITE OFF` | 0 | — |
| `G_stop_latch` — collide under `SPRITE STOP`, *separate the sprites*, then `SPRITE ON` | **0** (aux 0, aux2 0) | **STOP does NOT latch** |
| `H_off_latch` — identical with `SPRITE OFF` | **0** | control agrees |
| `E_no_handler` — `SPRITE ON`, no handler line at all | 0, err 0 | harmless, no error |

`G`/`H` are built to be decisive: the sprites are moved **apart** before the enable
and given time for the flag to clear, so a latched pending event would show as
`cnt>0` with nothing currently colliding. It reads 0. **`SPRITE STOP` ≡ `SPRITE
OFF`** — the fourth independent confirmation of that in this arc (T1 STOP, T2 STRIG,
T3 KEY, now T4 SPRITE).

**No enable-time seed.** In `A_hit` the sprites are already overlapping when
`SPRITE ON` runs, and it fires immediately. A collision that predates the enable is
therefore *not* suppressed — the STRIG seed question (T2 cases E/F) simply does not
arise for SPRITE.

### 1.4 Arming is independent of state — and a bare `ON SPRITE GOSUB` DISARMS

| case | readings | conclusion |
|---|---|---|
| `R_bare_disarms` — fire, then bare `ON SPRITE GOSUB`, keep colliding | aux **21** → aux2 **22** = cnt **22** | the bare form **clears the handler slot**; firing stops |
| `S_rearm` — as above, then `ON SPRITE GOSUB 800` again | 21 → 22 → cnt **45** | firing **resumes**; the `SPRITE ON` state survived |

This is a direct confirmation of the arc's `ZTRAP` model (§3 of the arc spec): the
**state byte and the handler link are independent**. Disarming does not disable, and
re-arming does not re-enable — nothing needs to be re-issued.

### 1.5 🔴 The parse surface — and a SHIPPED DIVERGENCE in T1 that this round found

| case | ERR | |
|---|---|---|
| `J_syn_on_goto` — `ON SPRITE GOTO 800` | **2** | Syntax error |
| `K_syn_bare` — bare `SPRITE` | **2** | matches the graphics arc's existing `gfx_syntax` |
| `P_syn_junk` — `SPRITE FOO` | **2** | |
| `M_undef_line` — `ON SPRITE GOSUB 777`, no line 777 | **8** | Undefined line number, exactly as `GOTO` |
| `I_screen0` — `SCREEN 0`, armed + `SPRITE ON` | **0**, cnt 0 | arming in SCREEN 0 is **legal** and simply never fires |
| **`L_syn_noline` — `ON SPRITE GOSUB` with no line at all** | **0** | **accepted silently** |

`L_syn_noline` did not match what zerobas ships for the sibling statement, so the
whole family was swept:

| `ON <event> GOSUB` with no line | reference | zerobas (repack) | |
|---|---|---|---|
| `ON STOP GOSUB` | err **0** | err **2** | 🔴 **DIVERGENCE** |
| `ON STRIG GOSUB` | err 0 | err 0 | ✅ |
| `ON KEY GOSUB` | err 0 | err 0 | ✅ |
| `ON SPRITE GOSUB` | err 0 | *(unimplemented)* | — |

and `Q5`/`Q6` (`ON SPRITE GOSUB:POKE&HD004,77` / `ON STOP GOSUB:POKE&HD004,77`)
both wrote **77**, proving the reference's parser stops cleanly at the missing line
reference rather than swallowing the rest of the statement.

**T1 ships `ON STOP GOSUB` (no line) → ERR 2.** [`program.asm:1341`](../basic/program.asm)
does `jp nc,trap_syntax` where the reference accepts the form and **clears the
handler slot** (§1.4). T2 and T3 already get this right — `ex_on_strig`
([`program.asm:1424`](../basic/program.asm)) and `ex_on_key`
([`program.asm:1557`](../basic/program.asm)) both do `jr c,…store` / `ld de,0` — so
this is T1-only, and it was measured, not inferred from the source. Fix: give
`ex_on_stop` the same shape (≈ +2 B, §7). **In scope for T4** — the parse surface
T4 adds is the same routine, and shipping T4 correct while its identical sibling
stays wrong would be worse than either.

*This is the arc pattern recurring for the ~19th time and the third time a later
slice's gate work has found an earlier slice's bug (T3's gate found T2's empty-slot
tokeniser bug). It is also why §1's family sweep exists at all: the SPRITE reading
looked like a T4 question and was actually a T1 defect.*

### 1.6 The collision bit is NOT consumed by the trap

| case | `VDP(8)` | `PEEK(&HF3E7)` |
|---|---|---|
| `N_statfl_on` — colliding, trap enabled | **191** = `$BF` | **191** |
| `N2_statfl_off` — colliding, trap disabled | **191** | **191** |

`$BF` = `1011 1111`: bit 7 VBLANK, bit 6 (5S) clear, **bit 5 (C) set**, bits 4–0 the
fifth-sprite number field. Two things follow, and both constrain the implementation:
`VDP(8)` **is** `STATFL` on the reference (identical readings), and an enabled
SPRITE trap **does not change what a program reads there**. zerobas must not consume
the bit either.

---

## 2. D-T-4 — the collision source. RESOLVED: read `STATFL`, option (a)

The arc spec left this as the one fork with a real oracle question. It is now
answered, and the answer is forced.

**Option (b) — a direct `in a,($99)` in `event_poll` — is impossible by
construction on this target.** C-BIOS's `$0038` handler
([`cbios/src/main.asm:2634-2636`](https://github.com/cbios/cbios), pinned tag)
reads the status register and latches it *before* dispatching the hook:

```
                call    H_KEYI
                in      a,(VDP_STAT)
                or      a
                ld      (STATFL),a      ; save status
                jp      p,int_end
                call    H_TIMI          ; <- event_poll runs HERE
```

S#0 is read-to-clear. `event_poll` runs at the `H_TIMI` seam, i.e. **after** that
read, every frame — so a second port read there can never see the collision bit.
There is no race to characterize: the BIOS wins, always.

That same ordering is what makes option (a) exact rather than merely workable:
`STATFL` is written **before** `H_TIMI`, so the poll reads the **current** frame's
sample with no one-frame lag.

**Measured, on both machines** (200-iteration loop counting iterations that saw
`STATFL & $20`):

| | hits / 200 | final |
|---|---|---|
| VG-8020, colliding | **198** | `$BF` bit 5 SET |
| VG-8020, apart | **0** | `$9F` clear |
| repack build, colliding | **199** | `$BF` bit 5 SET |
| repack build, apart | **0** | `$9F` clear |

The miss row is the control: hit and miss disagreeing is what makes the reading
worth anything.

**Provenance:** `STATFL` `$F3E7` is a **published MSX work-area address** (already
declared at [`sysvars.inc:685`](../basic/sysvars.inc) and already what zerobas's
`VDP(8)` returns), *not* a C-BIOS internal. The arc spec's worry that option (a)
"depends on a BIOS internal — weak provenance" does not survive contact: reading a
documented system variable that the interrupt handler is *specified* to maintain is
the same class of dependency as `NEWKEY` or `TRGFLG`. No reference-ROM disassembly
is involved; the C-BIOS excerpt above is **build-input source**, not a stock
reference ROM ([[no-reference-rom-disasm]] is untouched).

⇒ **Recommend adopting option (a).** Option (c) (defer T4) is moot.

---

## 3. Where the poll lives — page 1, and why the T3 argument does NOT carry over

`event_poll` is main **page-1** resident (`$5ADA`), reached through `htimi_guard`
([`subromcall.asm:97`](../basic/subromcall.asm)), which **skips the frame entirely**
when a sub-ROM page-1 tenant owns page 1. T3 could not accept that and put
`keytrap.asm` in the low region, because a skipped frame **leaks an undiverted
keystroke into `KEYBUF`** — a correctness divergence, not a deferral.

**For SPRITE the skipped frame costs nothing semantic, for a structural reason:**
the collision condition is a function of sprite positions in VRAM, and those change
only when the program executes `PUT SPRITE` / `SPRITE$=` — which it cannot do while
it is *blocked inside* a page-1 tenant call. The collision state is therefore
**constant across the whole tenant window**. If sprites overlap during it they still
overlap after it, and the next unskipped frame sets PENDING; if they do not, there
was nothing to lose. What is lost is only *repeat* fires — and repeats are already
collapsed by the single PENDING latch (§1.2) and are already not an
equality-differential across machines.

*Recommended: put the SPRITE stanza in `event_poll` (page 1), costing no low-region
byte and no promotion, with §8's `T_tenant` gating the argument.*

### 3.1 ✅ D-T4-2 DECIDED (2026-07-25) — **LOW REGION, off `htimi_guard`**

**Signed off against that recommendation.** The stanza goes in the low region,
called from `htimi_guard` **ahead of its slot test**, so it is always mapped and no
frame is ever skipped. Cost: ~23 B of low region against **14 B free** ⇒ **T4 needs
a promotion** (low → freed page 1), the T3 technique, but a far smaller one than
T3's 74 B.

**Why this is the better call, and my §3 argument was the weaker case:** it rests on
"sprites cannot move during a tenant window", which is an *argument about the rest
of the system* — and §3 already had to carve out `bload_tenant`/`title_tenant` as
VRAM writers. That premise is exactly the kind that a later slice quietly
invalidates: every new page-1 tenant becomes a fresh obligation to re-audit, with
nothing in the build to catch it. The low-region stanza needs no premise at all —
page 0 is untouched during a page-1 tenant, so it is correct *by construction*, the
same reasoning that put `htimi_guard` itself and `keytrap.asm` in page 0. Paying ~23
B once beats carrying a standing audit obligation.

`T_tenant` **stays in the gate** regardless: it now asserts that the low-region poll
really does keep firing through a tenant window, rather than excusing a design that
does not.

⚠️ **The one caveat, recorded honestly:** the argument assumes no page-1 tenant
itself rewrites sprite VRAM. `bload_tenant` and `title_tenant` do write VRAM, so a
`BLOAD` into the sprite attribute table could in principle change the collision
state mid-window. Even then the *resulting* state persists after the tenant
returns, so the event is not lost — only its first frame or two. Noted as a bounded,
documented deviation rather than pretended away.

---

## 4. The model

Nothing new. T4 uses the arc's existing `ZTRAP` machinery unchanged:

- **entry `ZTI_SPRITE` = 2**, already allocated in [`sysvars.inc:1125`](../basic/sysvars.inc);
- **priority falls out for free.** `check_traps` scans ascending and `ZTI_SPRITE`
  (2) sits between STOP (1) and STRIG 0 (3) — exactly the arc spec's §5 enum order.
  No priority work, no scan-direction change (contrast T3's reversed KEY band);
- **state byte / PENDING / SERVICING / RETURN-re-enable**: shared, untouched;
- **no edge shadow** (§1.1) and **no enable-time seed** (§1.3) — bit 6 of the entry
  stays unused for SPRITE.

### 4.1 The poll stanza

Per §3.1 this is **low-region** code, reached from `htimi_guard` **before** its
page-1 slot test — so it must save its own registers (`htimi_guard`'s contract is
AF-only transparency, and this stanza needs HL too). It touches only RAM, so it has
no page-1 dependency to give up:

```
                push    hl
                ld      hl,ZTRAP+ZTI_SPRITE*ZTRAP_ENTSZ
                bit     0,(hl)              ; ON (01) or SERVICING (11) — as T2
                jr      z,ep_spr_done
                ld      a,(STATFL)
                and     $20                 ; S#0 bit 5 = sprite collision (§2)
                jr      z,ep_spr_done
                set     7,(hl)              ; PENDING
                ld      a,1
                ld      (TRAPPEND),a        ; wake the run-loop dispatcher
ep_spr_done:
                pop     hl
```

`bit 0` covers ON *and* SERVICING for the same reason T2 documents: a collision
during the handler must latch and fire after `RETURN`. Reading `STATFL` is a plain
RAM load — it does not clear the bit, satisfying §1.6.

⚠️ **`htimi_guard` currently saves only AF and is entered DI from the `$0038` ISR.**
Inserting the stanza ahead of its slot test must not disturb that contract: the
`push hl`/`pop hl` above is not optional, and the whole stanza must stay
register-transparent on **every** path, including the not-armed fast-out — the same
discipline `event_poll`'s own `push af` fast-out documents.

### 4.2 Parse

- **`ON SPRITE GOSUB <line>`** — a new sibling peek in `ex_on` (`cp SPRITE_TOKEN`,
  `$C7`, a single-byte token like KEY, so no `$FF` prefix to put back) plus a body
  that is, after the §1.5 fix, **byte-identical to `ex_on_stop` except for the entry
  index**. ⇒ share one routine parameterised by index (`ld a,ZTI_STOP` /
  `ld a,ZTI_SPRITE` → common tail via `ztrap_entry`).
  ⚠️ Per [[generalisation-not-free-at-two-callers]], **build both and measure** —
  the last time this arc assumed sharing was cheaper it was wrong by 11 B in the
  other direction, and the *duplicated* variant shipped.
- **`SPRITE ON|OFF|STOP`** — promote `spr_noop`
  ([`graphics.asm:690`](../basic/graphics.asm)) from the D-G7-4 no-op. The token
  discrimination **already exists** there (it tests `ON_TOKEN`/`OFF_TOKEN`/
  `STOP_TOKEN` and branches to a shared `inc hl` / `jp exec_stmt`); the promotion
  replaces those three branch targets with the `ex_stop` shape —
  `ld a,ZTS_ON|ZTS_OFF|ZTS_STOP` → `ld hl,ZTRAP+ZTI_SPRITE*ZTRAP_ENTSZ` →
  `call set_state`, **no seed block** (§1.3). Bare `SPRITE` keeps its existing
  `gfx_syntax` ERR 2, which §1.5 `K_syn_bare` confirms is right.
- **`ON SPRITE GOSUB` with no line** clears the slot (§1.4), via `trap_line_link`'s
  existing CF=0 path — the same `ld de,0` that `ex_on_strig`/`ex_on_key` use.

---

## 5. Byte budget

**Measured walls now: page-1 free = 78 B, page-0 low region = 14 B**
(`make basic-reloc`; page 1 gained +16 B from T1's STOPGRACE retirement, `746b075`).

| item | region | estimate |
|---|---|---|
| SPRITE poll stanza + the `htimi_guard` call (§3.1, §4.1) | **low** | **~23 B** |
| `SPRITE ON/OFF/STOP` promotion (§4.2) | page 1 | ~22 B |
| `ex_on` peek + `ex_on_sprite` (shared with `ex_on_stop`) | page 1 | ~10–25 B |
| §1.5 `ON STOP GOSUB` divergence fix | page 1 | ~+2 B |
| **total** | **page 1** | **~34–49 B** (78 free) |
| | **low region** | **~23 B** (14 free ⇒ **~9 B short**) |

Under D-T4-2 the slice is **split across both walls**, as T3 was. The page-1 half
looks comfortable; the **low-region half is ~9 B short and needs a promotion**
(low → page 1, [[promotion-funds-low-region]]) — the same lever T3 used, at roughly
an eighth of the size. Note the walls are **coupled**: page 1 pays exactly what low
is relieved of, so the promotion spends part of the page-1 headroom above.

### 5.1 ✅ AS BUILT — measured, and the estimate held

**Measured with the low-region tripwire lifted: low 27 B, page 1 34 B — 61 B total**,
against a 57–72 B estimate. **This is the first slice in the arc whose estimate was
not a serious underestimate** (T2 ran 70 B low, T3 ran 106 B / 1.8× low). The
difference is not virtue: T4 reuses `ZTRAP`, `set_state`, `check_traps`,
`trap_line_link` and `ztrap_entry` wholesale and invents nothing.

⚠️ **Reading a wall while the other one overruns needs care.** Low and page 1 are one
contiguous image in the relocated build, so a low-region overrun of K bytes shifts
every page-1 address up by K, and `__MEAS_PAGE1_END` reads K too high. Page-1 free is
`$8000 - (__MEAS_PAGE1_END - K)`, not `$8000 - __MEAS_PAGE1_END`. Taking the raw
number made page 1 look 13 B tighter than it was.

**Golfed to 21 B of low region before spending any funding**, which is most of what
the promotion had to cover:
- **inlined the stanza into `htimi_guard`** instead of `call`/`ret` — 4 B, and there
  can only ever be one call site (§3.1), so the routine boundary bought nothing;
- **dropped `ld a,1` before `ld (TRAPPEND),a`** — 2 B. `A` still holds the `$20` the
  collision mask left, and every reader of `TRAPPEND` tests it with `or a` / `jr nz`.

**Funded by promoting `zkey_install` (12 B) to `basic/subrom-boot.asm`** — T3's own
boot-time-half file, on identical grounds: it runs once, from `init_ext_roms`, under
the boot DI, before any tenant exists, so neither pinning caller can reach it *by
construction*. It writes only RAM and touches no `$A8`/`CALSLT`, so
`promote_scout.py`'s known blind spot does not apply. `zkey_hook` stays low — it *is*
the `$0038` keyboard-scan path.

**Final walls: low 5 B free, page 1 22 B free.** Lean 16 KB ROM **verified
byte-identical** (`e22d8c5f80ca1df8d20cf35d812de112` with T4 in and out of the tree),
not merely argued from the `IF ROM_BASE < $4000` guards.

🔴 **It should not be believed.** The standing arc rule is that **every byte estimate
here is a LOWER BOUND**: T3's §7 estimate ran 106 B low (1.8×) *while describing
itself as deliberately pessimistic*, and T2's ran 70 B low. A 1.8× multiple on 70 B
is 126 B against a 78 B wall.

**Therefore the implementation order is measure-first** (§7): write the slice behind
`TRAPS_T4`, lift the tripwire, read the real number, and only then decide funding.
If it overruns, note that the T3 lever is **not** available in this direction — a
low→page-1 promotion makes page 1 *worse*, and low has only 14 B to give. The lever
would be another **carve** (a page-1 cluster evicted to the sub-ROM, as `bload`
was) or golf. Flagged as the one real risk in the slice.

---

## 6. Tokens

**None.** `SPRITE` (`$C7`), `ON` (`$95`), `GOSUB` (`$8D`), `OFF` (`$EB`), `STOP`
(`$90`) and the `$0E` line reference all exist. T4 adds no keyword and no token
byte — unlike T1's stillborn `INTERVAL` (MSX2, out of charter,
[[interval-is-msx2-not-msx1]]).

---

## 7. Implementation order

1. Land the §1.5 `ON STOP GOSUB` fix **first and separately**, with a case added to
   `stop-trap-acceptance` — it is a shipped divergence, independent of T4, and
   keeping it separate keeps its ~2 B out of T4's measurement.
2. Write the slice behind a `TRAPS_T4` gate that is **`ROM_BASE`-conditional, not a
   bare `equ`** — T3 lost a round to exactly that (its parse surface is repack-only
   while its call sites are always-assembled, so the lean build died on an undefined
   symbol).
3. **Measure** against **both** walls with the tripwire lifted, per §5. The
   low-region half is expected ~9 B short ⇒ fund it by **promotion**
   (`tools/promote_scout.py`), remembering that tool's known blind spot: it calls
   `subrom_call` promotable because a call-graph walk cannot see that the pin is on
   the code *performing* the slot switch. Never promote anything touching
   `$A8`/`CALSLT` on a bare verdict.
4. Low-region poll stanza + the `htimi_guard` insertion (§4.1); `set_state` wiring;
   `ex_on_sprite` (both variants, measured); `spr_noop` promotion.
5. `make sprite-trap-acceptance` — and **run it**. The standing trap in this arc is
   "builds green but was NEVER RUN".
6. Full standing-gate sweep, including `graphics-acceptance` (T4 edits
   `graphics.asm`) and the reloc/lean byte-identity gate.

---

## 8. Gate — `make sprite-trap-acceptance`

VG-8020 differential, one boot per case, repack machine on the zerobas side.
**T4's gate is the cleanest in the arc**: no `keymatrixdown`, no PSG port-A
injection, no C-BIOS hook — the program collides its own sprites, so every case is
`-machine <name>` and nothing else.

**Apparatus requirements are inherited verbatim and are not optional:** RAM
sentinels (never screen text — the REPL echoes every typed line); **every reading
gated on the `done` sentinel**, with `done==0` a FAILURE and never a zero; program
entry by **KEYBUF injection** (`probes/lib/omsx_repl.py`), never openMSX `type`; no
string building; **no `TIME`** (not implemented on zerobas — it parses as the
variable `TI` and reads 0 forever, so a `TIME`-bounded loop never terminates);
windows sized by iteration count; the fire counter **saturates** below 256.

⚠️ **The three cadence cases (§1.2.1) deliberately step outside two of those, and
the reasons matter.** Their fires and frames are counted by **openMSX watchpoints**
(on `JIFFY` and on the handler's own `POKE`), so nothing saturates and no BASIC
arithmetic is in the reading; and they are gated on an **apparatus check** — both
windows ran their full length, the program did not error — rather than on `done`,
because a handler that outlasts a frame starves the program so completely that it
can never reach an `END` (§1.2.2). `done==0` remains a failure everywhere it is the
gate; these cases replace it with a stronger one rather than dropping it. Both
watchpoint anchors are plain RAM on **both** machines, so the apparatus needs no
symbol table and stays a true differential. Note also that `TIME` **has** landed
(`docs/spec-basic-time.md`, 2026-07-26), so the "no `TIME`" rule is now a matter of
not rewriting green cases rather than a limitation.

Cases, from §1 — every one already has its reference reading recorded above, so the
gate is written against measured values, not expectations:

| case | asserts |
|---|---|
| `A_hit` / `A2_miss` | the discriminating pair — fires vs the control. **If these agree the run is void.** |
| `F_cadence` | **one fire per frame**, fires and frames counted by the emulator, plus the precondition that the handler fits in a frame (§1.2.1) |
| `F_cadence_period` | the same law with a handler that does *not* fit: the between-fires period equals that handler's own measured cost — no fire lost beyond what the handler pays for |
| `F_cadence_off` | the cadence apparatus' own discriminating control, **inside one boot**: armed-but-not-enabled counts ZERO while the same handler, called by the program, counts thousands |
| `B_armed_not_on`, `C_off` | arm ≠ enable |
| `G_stop_latch`, `H_off_latch` | `SPRITE STOP` ≡ `SPRITE OFF`, no latch |
| `E_no_handler` | enabled with no handler is harmless |
| `R_bare_disarms`, `S_rearm` | bare `ON SPRITE GOSUB` clears the slot; state survives |
| `J`,`K`,`P` / `M` / `I_screen0` | ERR 2 / ERR 8 / legal-and-silent |
| `L_syn_noline` + the `Q1..Q3` family sweep | the §1.5 divergence stays fixed across **all four** events |
| `N_statfl_on` / `N2_off` | `VDP(8)` unchanged by an enabled trap (§1.6) |
| **`T_tenant`** | **the §3 argument, measured**: collide while the loop runs `SIN` (a `fp_sin` page-1 tenant, so `htimi_guard` is skipping frames) and assert the trap still fires |
| `U_servicing` | a collision during the handler latches and fires after `RETURN` |

`T_tenant` is the case that exists because §3 reasons rather than measures. It is
the one most likely to fail, and it is the reason §3's recommendation is safe to
make.

### 8.1 ✅ AS BUILT — `make sprite-trap-acceptance`, **123 assertions, ALL PASS**

26 cases, one boot per case per machine. `T_tenant` on zerobas reads **174 fires
over 173 frames — a ratio of 1.006 while the loop sits inside `fp_sin` page-1 tenants
for most of every frame.** That is D-T4-2 paying off directly: with the poll in
page-1 `event_poll`, `htimi_guard` would have skipped exactly those frames.
(`T_tenant` keeps its `JIFFY`-polled window because it asserts `cnt>0` and **does not
divide by it** — §1.2.1's defect is in the ratio, not in the window.)

**2026-07-26 — the cadence trio (§1.2.1), 96 → 123 assertions.** The old
`F_cadence` (1.007 ref / 1.043 zb, and 95/96 RED once `TIME` landed) is replaced by
`F_cadence` + `F_cadence_period` + `F_cadence_off`, all three emulator-counted:

| | ref | zb |
|---|---|---|
| `F_cadence` trap / sync | 299/300 = 0.997 · 4.53 | **299/300 = 0.997** · 2.95 |
| `F_cadence_period` trap / sync / period | 300/300 = 1.0 · 1.20 · 1.00 | 186/300 = 0.62 · 0.573 · **1.60** |
| `F_cadence_off` trap / sync | **0**/300 · 4.53 | **0**/300 · 2.95 |

The predicates were additionally checked against synthetic readings for teeth: every
one of *every other frame*, *twice per frame*, *two frames in three (the 1.5)*, a
*truncated window* and an *errored program* is caught, and a handler too fat for the
claim fails the **precondition** line first, so the diagnosis is legible instead of
being a mystery ratio.

🔴 **THE APPARATUS WAS WRONG FOUR TIMES BEFORE THE IMPLEMENTATION WAS WRONG ONCE —
and every one of them looked like a dispatcher firing several times per frame.**
The implementation was correct from the first run; all four were in the measurement:

1. **A torn JIFFY read.** Composing lo-then-hi tears when the low byte wraps
   (~1 frame in 256), giving a value 256 low; the "restart the window" guard then
   reset the FRAME count while the fire counter kept accumulating. Fixed by
   re-reading the high byte and retrying.
2. **The two counters covered different spans.** The fire counter ran from
   `SPRITE ON` to capture — including frames after `END`, since the capture polls at
   1-emulated-second granularity — while the JIFFY delta covered only the loop. On
   the reference the loop dominates and this hides; on zerobas, ~7× slower, it *was*
   the reading.
3. **`RETURN` without `GOSUB` (ERR 3).** A subroutine placed after the `END` line in
   the *text* still sorts before it by LINE NUMBER, so execution fell straight into
   it. Renumbering the text achieved nothing; the line numbers had to move.
4. **A wait that counted iterations, not frames.** "30 iterations of a
   change-detector" is ~30 frames on the reference and **~387 on zerobas**, which
   saturated every counter at 250.

**What ended it was measuring at the emulator level rather than reasoning harder**:
breakpoints on `htimi_guard`, on the `set 7,(hl)` latch site and on `check_traps`
gave **htimi = latch-path = JIFFY delta = 200/200/200**, and 387 latches across the
armed span — a clean once-per-frame source with every fire paid for by a latch. Two
of the four bugs had already produced *self-consistent* wrong answers across repeated
runs before that. **The apparatus is part of the measurement** —
[[traps-t3-key-slice]] recorded the same lesson for the capture window; here it was
the window's *definition*.

Design consequence now baked into the gate: fire counts are asserted **per machine**
(`EXPECT[...][PER]`), and only the error surface and the STATFL readings are
cross-machine equalities (`EXPECT[...][EQ]`).

---

## 9. Sign-off items

- **D-T4-1 — the collision source (§2).** Read `STATFL` bit 5 (option (a)). Option
  (b) is impossible by construction; `STATFL` is a published work-area address, so
  the arc spec's provenance worry does not apply. *Recommend as written.*
- **D-T4-2 — where the poll lives (§3). ✅ DECIDED: LOW REGION, off `htimi_guard`
  (§3.1)** — correct by construction rather than by an argument about which page-1
  tenants touch sprite VRAM. Costs ~23 B low against 14 free ⇒ a small promotion.
  *(Decided against the original page-1 recommendation.)*
- **D-T4-3 — the T1 `ON STOP GOSUB` divergence (§1.5). ✅ DECIDED as recommended:**
  fixed **first, in its own commit**, with a `stop-trap-acceptance` case, so its
  ~2 B stay out of T4's measurement.
- **D-T4-4 — share or duplicate `ex_on_stop`/`ex_on_sprite` (§4.2).** Build both,
  measure, keep the smaller — and prefer the variant that costs nothing when
  `TRAPS_T4` is off. *Recommend measuring rather than deciding here.*
- **D-T4-5 — scope of the fire-cadence assertion (§1.2/§8).** Gate the
  `fires/frames` ratio per machine, never a cross-machine count. *Recommend as
  written.* → ⚠️ **SUPERSEDED 2026-07-26 by §1.2.1.** "Per machine, never a count"
  was right and not enough: the ratio's *denominator* was computed by the main
  program, which the handler competes with, so the ratio moved with the handler's
  length and passed at T4 by luck. The replacement gates
  `rate == min(1/frame, the same handler's synchronous rate)` with **both** sides
  counted by the emulator in one boot.

---

*Characterization rounds 1–6 were run 2026-07-25 against `Philips_VG_8020` and
`C-BIOS_MSX1_EU_REPACK_DISK`; all cases `done`-gated, all controls discriminating.
Clean-room: observed I/O only, plus C-BIOS **source** (a build input) for the ISR
ordering in §2.*
