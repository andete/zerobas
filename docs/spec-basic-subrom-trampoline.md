# Spec — zerobas-sub interrupt trampoline (page-0 EI enabler)

**Status: SIGNED OFF + IMPLEMENTED (2026-07-12).** Q1–Q4 all confirmed as
recommended ("all good go"). Landed: sub-ROM `$0038` `jp SUB_INT_RAM`
([`sub/sub.asm`](../sub/sub.asm)); the RAM trampoline template + boot install
([`basic/subromcall.asm`](../basic/subromcall.asm) `sub_int_template` /
`sub_int_install`, wired from [`basic/initext.asm`](../basic/initext.asm)); the
RAM cells + `JIFFY` ([`basic/sysvars.inc`](../basic/sysvars.inc)); the self-test
tenant index 3 + the `subrom-inttest` gate. **Gate result: JIFFY delta = 28 ticks
serviced through the trampoline (PASS).** Full gate set below (§4.1).

Slice spec of the sub-ROM arc
([spec-basic-subrom.md](spec-basic-subrom.md)); on sign-off it lands as the
arc-level infrastructure deferred from wave 2
([spec-basic-subrom-wave2-tokeniser.md](spec-basic-subrom-wave2-tokeniser.md)
§R-W2-1 option (b)) and answers main-spec **R3** (the DI-span of a stream/long
page-0 tenant). It is **not** a wave-N eviction — it evicts nothing; it makes the
page-0 island *interrupt-live*.

**One-line goal:** give `zerobas-sub`'s page-0 island its **own `$0038`
interrupt handler** so a long page-0 tenant can run `EI`, collapsing the DI span
from *whole-tenant* to *transition-only* — exactly how a real MSX2 sub-ROM stays
interrupt-live while paged in.

---

## 0. Why this exists (the problem, verified)

A page-0 sub-ROM tenant is entered under `DI`, and today `subrom_call`
([basic/subromcall.asm:54](../basic/subromcall.asm)) holds `DI` for the tenant's
**whole duration**. It must: while a page-0 tenant runs, `CALSLT` has switched
slot-0 page 0 **out** and mapped the sub-ROM in, so the CPU's `$0038` maskable-
interrupt vector now reads **sub-ROM bytes, not the BIOS ISR**. An interrupt
accepted there would execute tenant code as an ISR → crash. Hence the standing
rule "page-0 tenants run under DI" ([sub/sub.asm](../sub/sub.asm) header;
[arc memory] page-0 tenant interrupt rule, MSX2 TH Ch.5 + grauw).

That is fine for the shipped tenants: the tokeniser/detokeniser DI spans are
**cosmetic** (post-Enter, no keystroke/audio pending; worst case ~10 JIFFYs). It
is **not** fine for the roadmap's long page-0 tenants:

- the **math pack** (`^`/`SQR`/`SIN`/`COS` — a Taylor/CORDIC loop can run many
  JIFFYs) as a page-0 native tenant;
- any future **stream** tenant (main-spec R3).

For those we need the tenant to `EI` during its loop. That is only safe if the
sub-ROM carries **its own valid `$0038` entry** that services the real interrupt
in the paged-out BIOS and returns. This slice builds that entry.

---

## 1. The mechanism (own-design, firewall-clean)

### 1.1 The two hard constraints

1. **The BIOS ISR is paged out.** At interrupt time page 0 = sub-ROM. To service
   the interrupt we must map the **main page-0 slot** (BIOS + real `$0038 → JP
   int_h`) back in, run it, and map the sub-ROM back.
2. **The switch code cannot page out its own next instruction.** The `$0038`
   handler starts executing *in* sub-ROM page 0. The instant it writes the slot
   register to map main into page 0, the next opcode fetch comes from *main* at
   the same address — a different byte stream. So the switch sequence **must not
   live in page 0**.

### 1.2 The resolution — a RAM-resident stub

Page 3 (program RAM, `$C000–$FFFF`) stays mapped through **any** page-0 slot
switch (it is a different page register). So we place the switch/service/switch
sequence in a **small RAM stub**, installed at boot. The sub-ROM's `$0038` holds
only a single `jp SUB_INT_RAM` — one instruction, executed before any switch,
that transfers control to the always-mapped stub. From there every slot write
executes from RAM and never pages itself out. **This is the entire "switch stub
placed so it doesn't page out its own next instruction" answer.**

This is not a novel trick — it is **the canonical BIOS mechanism**. The MSX BIOS
itself installs its inter-slot primitives in RAM at boot: `RDPRIM $F380` /
`WRPRIM $F385` / `CLPRIM $F38C` (C-BIOS copies `m_rdprim..m_prim_end` there,
[`slot.asm`](../../cbios/src/slot.asm), [`main.asm`](../../cbios/src/main.asm)),
for exactly the self-paging reason above. `CLPRIM` is the RAM-resident inter-slot
*call* primitive. So the stub is `CLPRIM`-shaped by necessity, not by accident —
see §1.4a for why we adapt it rather than call it.

### 1.3 The slot switch — reuse our own template

We already ship a raw, host-adaptive page-0 slot switch that never CALLs the
BIOS: [`page0_ram_in`/`page0_ram_out`](../disk/init.asm:329) (primary via
`OUT ($A8)`, secondary via `$FFFF`, derived from the live registers — never a
hardcoded slot id). The trampoline uses the **same primitive** in both
directions:

- **sub → main:** write the captured *main* page-0 config (`MAIN_A8`/`MAIN_SEC`).
- **main → sub:** write the *sub* page-0 config (`SUB_A8`/`SUB_SEC`), derived
  once at boot from `SUBSLOT` (the slot id we already record,
  [subromcall.asm](../basic/subromcall.asm)).

Firewall: this reads only slot **registers** and our own bytes; **no C-BIOS code
is read, decoded, or relocated** — identical stance to the 163 disk CALSLT sites
and to `page0_ram_in`. (`cbios-repack-provenance.md`, main-spec §3g.)

### 1.4 Reaching the real ISR — `call $0038`, a published contract

Once page 0 = main, `$0038` reads the real `JP int_h`. The stub reaches it with a
plain **`call $0038`** — the same published-entry-point contract the disk ROM
uses for every BIOS call, **not** disassembly (we never read the bytes; we call
the documented maskable-interrupt vector). `ENASLT`/`CALSLT` are *not* usable
here: they live in the BIOS page-0 region that is paged out at entry, and would
re-drive their own DI/slot dance. The manual map + direct `call` is both
necessary and cleaner.

The real `int_h` acks the VDP, bumps `JIFFY`, and runs the `H.TIMI`/`H.KEYI`
hooks — all automatically, because page 0 is now the main slot exactly as during
a normal interrupt. Our trampoline adds nothing to the ISR's job; it only
brackets it with the two switches.

### 1.4a Why not `jp CLPRIM` — the interrupt-safe DI guard

`CLPRIM` ($F38C) already does *map-target-in → call → restore-caller*, so it is
tempting to route the ISR call through it. We don't, and the reason is specific to
an **interrupt** target. `CLPRIM`'s body ([`slot.asm`](../../cbios/src/slot.asm)
`m_clprim`) is `out ($A8),a / ex af,af' / call cl_jp / ex af,af' / pop af / out
($A8),a / ret` — it restores the caller's slot **with interrupts in the caller's
state**. That is correct for an ordinary inter-slot call, whose target does not
touch the interrupt flag. But our target is the real ISR, which ends `EI`/`RETI`;
so on the way out `CLPRIM` would execute its slot-restore `out ($A8)` **interrupts-
live**, and an IRQ landing in that window — just after page 0 flips back to the
sub-ROM — would re-enter `$0038` mid-restore. Our stub instead does an explicit
`di` the moment the ISR returns, *before* the switch-back (§2). So the trampoline
is `CLPRIM` **plus an interrupt-safe DI guard** — the precedent is the BIOS's, the
adaptation is what an interrupt target requires. (This is also why we hand-roll the
switch with `page0_ram_in`'s register math rather than calling the primitive.)

---

## 2. The trampoline sequence (design)

At interrupt time (CPU has pushed PC, cleared IFF, jumped to sub `$0038`):

```
; --- sub-ROM page 0, at $0038 (1 instruction, pre-switch) ---
    jp   SUB_INT_RAM            ; transfer to the always-mapped RAM stub

; --- RAM stub (installed at boot; executes entirely from page 3) ---
SUB_INT_RAM:
    push af                     ; the switch clobbers A/C; the real ISR saves the
    push bc                     ;   rest itself, but we touch A,C before calling it
    ; map main page 0 in (BIOS + real $0038 -> JP int_h)
    ld   a,(MAIN_A8)   : out ($A8),a
    ld   a,(MAIN_SEC)  : ld ($FFFF),a
    call $0038                  ; run the REAL ISR (VDP ack, JIFFY++, H.TIMI/H.KEYI)
    di                          ; guard the switch-back (ISR EI'd on the way out)
    ; map the sub-ROM back into page 0
    ld   a,(SUB_A8)    : out ($A8),a
    ld   a,(SUB_SEC)   : ld ($FFFF),a
    pop  bc
    pop  af
    ei                          ; tenant resumes interrupt-live
    reti                        ; return to the interrupted tenant
```

**Reentrancy is bounded and safe** (analysed, §5 R-T1): the only interrupt-live
windows outside `di` land with page 0 = **main** (the real ISR is reentrant
there) or back in the tenant with page 0 = **sub** (which re-enters this
trampoline correctly). No window executes a stray `$0038`.

### 2.1 Boot-time install (repack-only, `IF ROM_BASE < $4000`)

A new routine `sub_int_install`, called from `init_ext_roms`
([basic/initext.asm](../basic/initext.asm)) **after** `try_sub_slot` records
`SUBSLOT`/`SUBSLOT_OK` and only when `SUBSLOT_OK`:

1. Copy the `SUB_INT_RAM` template (a ~30–40 B blob in the merged main ROM's
   page-0 low region, beside `subrom_call`) into the page-3 RAM stub cell.
2. Capture `MAIN_A8`/`MAIN_SEC` = the **current** page-0 config (`in a,($A8)` +
   `$FFFF`, cpl — exactly `page0_ram_in`'s derivation), i.e. the BIOS slot.
3. Derive `SUB_A8`/`SUB_SEC` from `SUBSLOT` (FxxxSSPP → page-0 primary/secondary
   bit fields).

The sub-ROM's `$0038` `jp SUB_INT_RAM` is a **fixed constant** (`SUB_INT_RAM` is
a fixed RAM address), so it needs no relocation and is byte-identical every
build.

### 2.2 Tenant opt-in contract (no `subrom_call` change)

`subrom_call` is unchanged (`di / call CALSLT / ei`). A tenant that wants to run
interrupt-live simply **`EI` after entry and `DI` before `ret`** — so the
`CALSLT` entry/exit slot transitions stay interrupts-off (the always-DI rule
still holds for the *transition*, the tenant relaxes it only for its own body).
Short tenants (ping/tokeniser/detok) keep running fully-DI and are unaffected —
this slice is purely additive.

---

## 3. RAM & sub-ROM layout

### 3.1 RAM cells (repack-only free window `$F108–$F194`, below `DRVA_DPB $F195`)

The stub + save cells are **permanently resident** (unlike `DB_CUR`, which is
transient), so they take fresh cells above `DB_CUR $F108`:

| cell | size | purpose |
|---|---|---|
| `SUB_INT_RAM` | ~30–40 B | the copied trampoline stub (executes from RAM) |
| `MAIN_A8` / `MAIN_SEC` | 1+1 B | main (BIOS) page-0 primary/secondary select |
| `SUB_A8` / `SUB_SEC` | 1+1 B | sub-ROM page-0 primary/secondary select |

Total ≈ 44 B; the window `$F10A–$F194` has ~138 B free (S2's `__MEAS`). Exact
addresses fixed at implementation; `sysvars.inc` documents them like the rest.

### 3.2 Sub-ROM page-0 header — reserve `$0038`

Today sub-ROM `$0038` falls inside tenant code (the entry table is `$0010`, then
ping + tenants). We must **reserve `$0038`** for `jp SUB_INT_RAM`. The clean lay:
keep the `CD` header + entry table at `$0010`, then `org $0038 : jp SUB_INT_RAM`,
then continue tenant bodies at `$003B`. This displaces nothing an index points at
(entries are `$0010`-relative and unchanged) and costs 3 bytes of page-0 body
space. Lean `basic.rom` is untouched (sub-ROM only). Gate 6 (lean byte-identical)
is trivially preserved.

---

## 4. Gate — a dedicated interrupt self-test tenant

A behavioural, falsifiable gate (the wave-1 lesson: the execute+oracle probe, not
a descriptor unit test, is the arbiter). Add a page-0 tenant **index 3
`SUBROM_IDX_INTTEST`** (append-only, kept shipped like the PING as a standing
self-check):

```
sub_int_selftest:              ; page-0 tenant, run interrupt-live
    ld   hl,(JIFFY)  : push hl  ; JIFFY before
    ei
    ld   bc,0                   ; spin > one 50/60 Hz frame (fixed count)
.spin: dec bc : ld a,b : or c : jr nz,.spin
    di
    ld   hl,(JIFFY)  : pop de   ; JIFFY after / before
    ; return delta in HL (after - before)
    ...
    ret
```

`basic_probe_subrom_inttest.py` (new; sibling of `basic_probe_subrom_boot.py`)
boots the minimal C-BIOS MSX1 with `3-2 = sub.rom`, installs the trampoline,
CALSLTs `$0010 + 3*3`, and asserts:

- **delta ≥ 1** — interrupts were serviced *during* the EI tenant (with the
  trampoline absent or the tenant left DI, delta is **0**: the falsification);
- **no `$0038` storm / no hang** (reuse the storm classifier,
  `openmsx-probing-toolbox`);
- the tenant **returns cleanly** and the machine keeps running.

### 4.1 Full gate set (all must pass)

1. **`subrom-inttest`** (new) — delta ≥ 1, no storm, clean return.
2. **`subrom-acceptance`** — the S2a ping + tokenise/detok dispatch still round-trip.
3. **`string` / `float` / `input` acceptance** — unchanged (short tenants stay DI).
4. **`diskbasic-acceptance-repack` 34/34** — the disk `H.TIMI` hook, if any, still
   fires correctly with the trampoline installed (R-T2).
5. **`unit-test`** — host suite green (the separate-machine bridge is unaffected;
   the trampoline is boot/interrupt infra, not on any host-tested compute path).
6. **Lean `basic.rom` byte-identical** — all trampoline code is `IF ROM_BASE <
   $4000` (repack) or sub-ROM-only.

---

## 5. Risks

- **R-T1 — reentrancy at the EI/RETI seam.** The real ISR ends `EI`/`RET(I)`; on
  return IFF is enabled one instruction later. *Analysis:* every interrupt-live
  instant lands with page 0 = **main** (real ISR reentrant, page-0 correct) or,
  after our `ei`, back in the **tenant** with page 0 = **sub** (re-enters this
  trampoline correctly). The `di` before the switch-back closes the one window
  where page 0 = sub mid-stub. Bounded stack growth only if interrupts fired
  faster than the ~20-instruction tail — not physical at 50/60 Hz. **Mitigation:**
  the self-test spins for multiple frames → forces the nesting the gate would
  otherwise miss.
- **R-T2 — an `H.TIMI`/`H.KEYI` hook inter-slot-calls under a wrong page-0 map.**
  The hooks run *inside* the real ISR while page 0 = main, exactly as in a normal
  interrupt, so any hook (e.g. a disk `H.TIMI`) sees the environment it expects.
  **Investigation task (implementation):** confirm which hooks are live on the
  merged machine and that none assumes page 0 = sub. Gate 4 exercises the disk
  hook end-to-end.
- **R-T3 — `MAIN_*`/`SUB_*` capture wrong on an expanded main slot.** Mitigated
  by reusing `page0_ram_in`'s proven host-adaptive derivation verbatim (it
  already handles the expanded-primary case via `EXPTBL`/`$FFFF`); the self-test
  boots the real expanded-slot-3 machine.
- **R-T4 — firewall.** `call $0038` is a **published contract vector**, not a byte
  read; the slot switch reads registers only. Zero C-BIOS-leak preserved
  trivially. Own-design divergence to log in `sub/PROVENANCE.md`: an own-design
  sub-ROM interrupt trampoline (real MSX2 sub-ROMs carry an equivalent; ours is
  reconstructed from the MSX2 TH Ch.5 mechanism + our own `page0_ram_in`, no
  stock code).
- **R-T5 — `$0038` reservation collides with a tenant body.** The `org $0038`
  reserve is a build-time layout change; an assert (`$ <= $0038` before the org,
  `$ == $0038` at it) catches any future page-0 growth that would overrun it.

---

## 6. Scope boundary

- **In:** the sub-ROM `$0038` `jp`; the RAM stub + its boot install; `MAIN_*`/
  `SUB_*` capture; the tenant opt-in contract (docs only — no `subrom_call`
  change); the self-test tenant + probe; `PROVENANCE.md` + `sysvars.inc` notes.
- **Out:** converting any *existing* tenant to EI (tokeniser/detok stay DI —
  their spans are cosmetic; no reason to touch a green path). The **math pack**
  that *consumes* this (its own later slice, where EI tenancy earns its keep).
  `H.KEYI`-specific fast-interrupt paths beyond what the real ISR already runs.
- **Effort:** arc-level infra, **> wave 2/3** in design care (the reentrancy
  analysis + the boot-time RAM install), **< wave 2/3** in bytes moved (nothing is
  evicted).

---

## 7. Open questions for sign-off

- **Q1. Reach the real ISR via `call $0038`** (manual page-0 map + direct call),
  not `CALSLT` — recommended (§1.4; `CALSLT`/`ENASLT` are paged out and
  redundant). **Confirm.**
- **Q2. Ship the self-test tenant permanently** (index 3, standing self-check
  like the PING) vs build-gate-only. Recommend **ship it** — it is ~20 bytes, and
  a standing "interrupts survive a page-0 tenant" self-check is cheap insurance
  as more tenants land. **Confirm.**
- **Q3. Install the stub unconditionally at boot** whenever `SUBSLOT_OK`, vs
  lazily on first EI-tenant. Recommend **unconditional** — ~44 B RAM, one boot
  copy, no per-call cost, and it means "the trampoline is just there" for every
  tenant. **Confirm.**
- **Q4. `JIFFY` address** — use the published MSX work-area `JIFFY` (`$FC9E`) as
  the "interrupts serviced" witness. Confirm that is the witness you want (vs a
  dedicated `H.TIMI`-driven counter), given it is a published work-area address
  (allowed source), read-only, in the probe. **Confirm.**
