# Sub-ROM growth: supply/architecture analysis (2026-10-11)

Read-only analysis of the zerobas tree at HEAD `c6b706b4` plus the C-BIOS
checkout at `~/projects/cbios` (BSD, our base) and the openMSX share directory.
No reference ROM was read. Every claim is tagged:

- **[V]** verified in a file named with path:line;
- **[I]** inference from verified facts;
- **[M]** needs measurement (openMSX probe, a build, or a reference-machine PEEK);
- **[R]** needs Joost's ruling.

Wall figures quoted below were read from `build/*.sym` dated 2026-10-11 11:31
and rot; re-run `make basic-reloc` before pricing anything.

---

## 0. What exists today (the baseline every option is priced against)

### 0.1 Machine and slot map [V]

`tools/install-repack-machine.py:135-168` writes both machines: slot 0 = merged
C-BIOS + zerobas main ($0000-$7FFF) + logo ROM ($8000-$BFFF); slot 3 expanded:
3-0 = 64 KB RAM, 3-1 = disk ROM behind a WD2793 (`<mem base="0x4000" size="0x8000"/>`,
empty on `_NODISK`), 3-2 = `build/sub.rom` as a plain `<ROM>` with
`<mem base="0x0000" size="0x8000"/>` (`sub_secondary`, :77-94), 3-3 =
`<secondary slot="3"/>` (empty, :166). Installed copy confirmed at
`~/.openMSX/share/machines/C-BIOS_MSX1_EU_REPACK_DISK.xml`.

### 0.2 The sub ROM image [V]

`sub/sub.asm`: page 0 carries `"CD"` at $0000 (:67), a `jp SUB_INT_RAM` at $0038
(:95), the page-0 jp-table at `SUBROM_ENTRY_BASE_P0 = $0040` (:131, 19 rows
through index 18 `keystr_tenant` :231), `__MEAS_SUB_P0_END` + `$FF` pad to $4000
(:432-433). Page 1 carries `"S1"` at $4000 (:442, deliberately not `"AB"` so the
cartridge scan skips it), the page-1 jp-table at $4010 (:454, 29 rows through
index 28 `seqio_tenant`), `include "basic-resident-abi.inc"` (:720), and
`__MEAS_SUB_P1_END` + pad to $8000 (:896-897). Both bases are mirrored by hand in
`sub/equates.inc:25-26` and `basic/sysvars.inc:4831/4878` — "nothing
cross-checks them" (`sub/equates.inc:22-24`).

Walls on the 11:31 build: sub p0 **137 B** free, sub p1 **94 B**, main low
**19 B**, main page 1 **20 B** (`__MEAS_*` labels; `tools/check_sub_walls.py`
is the gated readout).

### 0.3 Discovery [V]

`basic/subrom-boot.asm:48-63` `try_sub_slot`: RDSLT $0000/$0001 of the scanned
subslot, compare `'C'`,`'D'`, then record `SCAN_SLOT` into `SUBSLOT` ($F106),
**write `EXBRSA` ($FAF8)**, set `SUBSLOT_OK` ($F107). Called from `ier_sloop`
(`basic/islands.asm:123`) for every subslot of every primary after our own,
after `try_init_slot` (the `"AB"` scan).

**Nothing in the tree reads EXBRSA**: the only code reference is the write
(`grep EXBRSA basic sub disk tools tape tests probes` → `subrom-boot.asm:60`,
the equate `sysvars.inc:5166`, prose in two PROVENANCE files). `R4` of
`docs/spec-basic-subrom.md:535-537` already states dispatch never reads it.

**C-BIOS and EXBRSA/"CD"** (C-BIOS source, allowed): `~/projects/cbios/src/main.asm:1315-1387`
is `chkslz`/`chksubpos` — the MSX2 BIOS's "Detect position of subrom": it walks
primaries 0-3 and, for an expanded primary, subslots 0-3 (`sub_subpos`), RDSLTs
$0000/$0001 for `'C'`,`'D'`, and writes **the first hit** into EXBRSA
(`chk_subpos`, :1359-1366; `xor a; ld (EXBRSA),a` when none, :1343-1344). The
whole block is inside `IF VDP != TMS99X8` (:1315), i.e. **absent from the MSX1
build**; `extrom` ($015F, :2927-2950) reads EXBRSA into IYh and CALSLTs. So:
- on our MSX1 machine C-BIOS never touches $FAF8; what it holds at boot without
  our write is whatever RAM init leaves — **[M]** PEEK(&HFAF8) on the VG-8020
  and on the NODISK machine after removing the write (the concept doc already
  files "whether an MSX1 program can tell … has not been measured",
  `docs/concepts/rom-layout.md:177-179`);
- on an MSX2 C-BIOS machine a zerobas ROM carrying `"CD"` **would be found by the
  BIOS's own scan**, and if it sits in a lower subslot than the real SUB-ROM,
  EXBRSA would point at us and every EXTROM call would crash. That is the concrete
  collision Joost's 2026-10-11 ruling removes, and it is also a direct case of
  the 2026-10-04 rule "a published BIOS entry point keeps its published contract"
  (`docs/plan-main-rom-space-2026-10.md:192`): EXBRSA is a published MSX2 cell with
  a published meaning (the slot of the MSX2 SUB-ROM), and we are repurposing it.

### 0.4 Dispatch and its cost [V]

`basic/subromcall.asm:61-77` `subrom_call`: `SUBSLOT_OK` test → `push de` →
`IY` from `SUBSLOT` → `pop de` → `di` → `call CALSLT` → `ei` → `or a` → `ret`.
Instruction T-states summed: 13+4+4+5+11+13+4+7+11+14+10+4+17+4+4+10 = **~135 T**
(the header's "~130 cycles", :122, is for the inline stubs `sr_inl*/sc_inl*`,
:133-156, which add roughly the same again). CALSLT itself is C-BIOS's
(`~/projects/cbios/src/slot.asm:125-185`, `select_subslot` :322-363,
`restore_subslot`, `m_clprim` :418-426): for a target in an expanded slot it
runs select_subslot (~240 T), the page-shift loops (~60 T for page 1, ~15 for
page 0), `clprim` in RAM (~70 T) and restore (~100 T). **Estimate ~650-720 T for
a page-1 target, ~600-650 for page 0 [I]** — order of magnitude only;
**[M]** count it with openMSX's cycle counter (or `make kwtime`, the T2/T5 row
type, `Makefile:1192-1202`) before quoting. So one tenant call today is roughly
**0.9-1.0 k T-states ≈ 0.27 ms** including the inline stub; the hot paths
(`ary_engine_call`, `call_strheap`, `str_set_key`) avoid the stub (:122-124).

CALSLT nests: it pushes the previous page config on the stack and restores it
(`slot.asm:164-185`), which is how a page-1 tenant in 3-2 already CALSLTs
DSKIO in 3-1 (`basic/fat-prim-body.inc:80-105`, D-BLDI), and how a page-0
tenant in 3-2 runs while page 1 is still main.

### 0.5 Interrupts during a tenant [V]

- Page-0 tenants: the CPU's $0038 reads sub-ROM bytes, so the sub ROM's $0038
  jumps to the RAM trampoline `sub_int_template` (`subromcall.asm:281-313`):
  maps page 0 back to main using `INT_MAIN_PRIM`, `call $0038`, `di`, maps page 0
  back to the sub ROM using **`INT_SUB_PRIM` and `INT_SUB_SUBSL`** — constants
  captured once at boot from `SUBSLOT` (`subrom-boot.asm:79-93`,
  `sysvars.inc:4489-4491`). **Consequence for any second page-0 island [I]:** a
  page-0 EI tenant in 3-3 would be restored to 3-**2** after every interrupt.
  The stub must save the live `$FFFF` subslot byte at entry and restore it
  (replacing the `INT_SUB_SUBSL` constant), ~+8 B in RAM; the reservation is 64 B
  with 47 used (`subromcall.asm:324-327`).
- Page-1 tenants: the BIOS ISR is visible; `htimi_guard` (:220-241) skips PLAY
  and the trap poll on any frame whose page-1 **primary** field is non-zero, so
  any slot-3 subslot in page 1 is already handled identically. A page-1 tenant
  must not wait (`docs/concepts/rom-layout.md:203-206`, D-SCREDIT).
- Re-entrancy today: nothing sub-side calls `subrom_call` (grep of `sub/` and
  `basic/*-body.inc` finds only comments), and the resident-ABI surface
  (`sub/basic-resident-abi.inc:13-29`) does not reach it, so no tenant has ever
  been entered while another was live. The closure gates do not check this;
  it holds by inspection only.

### 0.6 Gates and tooling that know the sub ROM [V]

`Makefile`: `$(SUB_ROM)` rule (:274-279, `pasmo -I sub`, pad to 32768),
`sub/basic-resident-abi.inc` generation (:312-313), `subrom-abi-check` (:354),
`subrom-closure-check` (:374-377, three modes of `tools/check_tenant_closure.py`),
`basic-reloc` (:388-401: walls, kwtable identity, resident ABI, closure, dead
code), `repack-machine` (:886-890, both machines), `subrom-acceptance` (:988),
`subrom-inttest` (:998), `graphics-floor-teeth` (:1135-1141, rebuilds a variant
sub ROM). `tools/check_sub_walls.py:59-74` hard-codes two pages and the anchors
`"CD"`@$0000 / `"S1"`@$4000 as its positive control. `tools/check_tenant_closure.py`
classifies by `PAGE1 = 0x4000` / `LOWREGION = 0x2765` (:66-67) and by "is the
label sub-local" (:547-620). `tools/check_knife_rom_guard.py:52` `IMAGE_HINTS`
names `sub.rom`. `tests/msxtest.py:192-282` is the host bridge: it slices
`sub.rom` by IX (`< 0x4000` → bare machine with the page-0 half; else overlay
$4000-$7FFF on a copy of the caller). `tools/check_patch_freshness.py` does not
mention `sub.rom` (it covers the main IPS/BPS pair only).

---

## 1. Options

### Option 1 — a second plain 32 KB ROM in slot 3-3, own signature

**Shape.** `build/sub2.rom`, same two-island layout as `sub.rom`: page-0 table
at $0040 (above a $0038 `jp SUB_INT_RAM`), page-1 table at $4010, own markers at
$0000 and $4000, its own `__MEAS_*` labels, its own `include "basic-resident-abi.inc"`.
Installed as a second `<ROM>` block in `<secondary slot="3">` on BOTH machines.
openMSX precedent for several ROM devices in one internal subslot:
`share/machines/Boosted_MSXturboR_with_IDE.xml:134-149` (a sub ROM at $0000 and
another ROM at $4000 in secondary 1).

**Supply.** +16 KB page-0 island and +16 KB page-1 island, each with the same
visibility rules as today (the closure checker's model applies unchanged).

**Per-call cost.** Identical to today: one CALSLT into slot $8F instead of $8B.
Zero extra T-states beyond the slot-select branch (~20-45 T, see below).

**Dispatch/ABI change (main side).**
- Discovery: generalise `try_sub_slot` to recognise the second marker and record
  `SUBSLOT2` (new 1 B page-3 cell; `tools/ram_map.py` / `make ram-map-check`
  must be told). ~12-18 B of boot-time code. It is boot-only, so it may be
  promoted into the C-BIOS padding islands (`basic/islands.asm`, where
  `init_ext_roms` already lives, `basic/initext.asm:35-38`) — **[M]** island
  free bytes are not in the five-wall readout; read `tools/build_mainrom.py`'s
  `ISLAND_RANGES` fill from a build.
- Dispatch: `subrom_call` must pick the slot by ROM. Cheapest sketch (own
  design, must be priced by a build): fold `SUBSLOT_OK` into `SUBSLOT` (a slot
  id is never 0, so `ld a,(SUBSLOT) / or a / scf / ret z` replaces the two-cell
  test and saves 3 B), add `subrom2_call: ld a,(SUBSLOT2) / jr sc_slot` (5 B),
  and give the inline stubs a ROM-2 mode (`sr_inl2`/`sc_inl2`, 4 B each, plus a
  second `jr c` target, ~4 B). **Net ~+12-15 B of the low region against 19 B
  free [I]** — feasible but it empties the low wall; the alternative that keeps
  HL/DE pass-through and chooses by IX's high byte inside `subrom_call` costs
  ~15 B and ~45 T per call, so prefer separate entries.
- Table-base encoding: the inline stubs encode the table's high byte as A =
  high/2 and assert `high & $81 == 0` (`subromcall.asm:125-132`), so ROM 2's
  bases must have an even high byte with bit 7 clear — $0040/$4010 again is
  fine because the ROM is selected by the stub entry, not the address.
- **Zero-main-byte variant ("gateway") [I]:** reach ROM 2 only through a 3-2
  page-1 tenant that CALSLTs into 3-3 (exactly the fatprim → DSKIO shape). Costs
  a second CALSLT (~+700 T) and ~20 B of sub p1, 0 B of main. Only for cold
  tenants; worth it only if main cannot be carved first.
- Hot paths stay on ROM 1 untouched (`ary_engine_call`, `call_strheap`,
  `str_set_key`, `evmc_dispatch` in `basic/expr.asm:2241-2246`).

**Re-entrancy.** A ROM-2 tenant calling main's low region which calls a ROM-1
tenant is a nested CALSLT: C-BIOS restores the outer page config on return
(`slot.asm:173-185`), so it is safe in principle; the page-0 trampoline
constant is the one real hazard (§0.5) and is fixed in the RAM stub. A page-1
tenant in 3-3 that nests into a page-0 tenant in 3-2 would run that page-0
tenant with page 1 = 3-3, not main; the `--page0` closure rule already refuses
main page-1 callees (lever A, `check_tenant_closure.py:22-26`), so it holds by
construction — add the case to the checker's selftest anyway.

**Tooling.** Makefile: `SUB2_SRC/PARTS/ROM/SYM`, `all`, `basic-reloc` lines ×2,
`subrom-closure-check` modes take the ROM as an argument (today `sub/sub.asm`
is the seed file — `check_tenant_closure.py:329-359` reads `sub_p0_table`/
`sub_p1_table` by label, so a second file with the same labels works with no
code change if the tool is just pointed at it); `check_sub_walls.py` takes a
ROM/sym pair and hard-codes the anchors (:67) — parameterise the anchors or
run it twice with a second anchor set; `check_kwtable_identity.py` is ROM-1
only (kwtable lives there); `gen_resident_abi.py` unchanged (same .inc,
included by both); `check_knife_rom_guard.py` `IMAGE_HINTS` + the knife runners
that hash images must hash `sub2.rom` too (the D-KNIFEROM class, TODO.md:3807 (T-169379)-
8041, bit exactly this way when the keyword table moved); `install-repack-
machine.py` gains `--sub2-rom` and the NODISK machine must get it too
(`diskless-is-an-official-target`); `probes/basic/basic_probe_subrom_boot.py`
grows two pings (tags $C2/$C3); `tests/msxtest.py` bridge gains "IX came from
which ROM" (the bridge decides by IX page only, :239-282 — with two ROMs sharing
the address space it must know the ROM from the stub that was called, e.g. by
trapping `subrom2_call` separately: small); `docs/concepts/rom-layout.md:40-50`
table, `docs/spec-basic-subrom.md` amendment, the playbook §1.

**MSX2 future [I].** C-BIOS MSX2 lays slot 3 as 3-0 = C-BIOS sub ROM (16 KB,
page 0, `"CD"`), 3-2 = 512 KB MemoryMapper (`share/machines/C-BIOS_MSX2.xml`).
A zerobas-MSX2 needs in slot 3: RAM mapper (all pages), the MSX2 SUB-ROM (page
0), disk (page 1), zerobas p0 island (page 0), zerobas p1 island (page 1), plus
any growth. Because openMSX allows different devices in different pages of ONE
subslot (turboR precedent above), the four subslots can be: A = RAM mapper;
B = MSX2 SUB-ROM (p0) + zerobas p1 island (p1); C = zerobas p0 island (p0) +
disk ROM (p1); D = free for growth. **Option 1 spends D.** The own-ID ruling is
what makes B/C legal at all: with `"CD"` at the zerobas p0 island, `chkslz`
would find the wrong ROM depending on subslot order. The trampoline's "main
slot unexpanded" assumption (`subromcall.asm:284-285`) also needs revisiting
if main ever moves to an expanded slot 0 (C-BIOS MSX2 keeps it unexpanded, so
not yet).

**Real hardware.** Internal expanded slots holding several ROMs by page are
standard MSX2 practice; a 32 KB ROM decoded at $0000-$7FFF in an internal
subslot is plausible (the turboR config shows a page-0 ROM beside a page-1 ROM
in one subslot).

**Risks and gates.** (a) Discovery picks the wrong ROM → both pings per ROM in
`subrom-acceptance`, tags distinct. (b) Trampoline restores 3-2 under a 3-3
page-0 EI tenant → an `inttest` twin in ROM 2 (spin EI, assert JIFFY moved AND
the tenant returned); a knife that leaves `INT_SUB_SUBSL` as is must turn that
gate red. (c) A stub `db` names the wrong ROM → `make stubinl-check`
(`tools/check_stub_inline.py`) must learn the new entries. (d) Stale `sub2.rom`
under a knife → image hashing. (e) Closure: ROM-2 tenants reaching ROM-1 code
by absolute address (same address space!) — the label-based classifier treats
"sub-local" as "defined in the image being walked", so a cross-ROM `call` to a
label only the other image defines shows up as an undefined symbol at assembly
time, not a silent escape — but shared `*-body.inc` files assembled into both
ROMs would make the same label exist in both; the checker needs a per-ROM
walk and a "no label from the other ROM" rule.

### Option 2 — an 8 KB-bank mapper ROM in 3-3 (the hybrid)

**What the standard mappers do (public knowledge, as I believe it; every line
is [M] in openMSX before relying on it):**

| | ASCII8 | Konami (non-SCC, "Konami4") | Konami SCC | ASCII16 |
|---|---|---|---|---|
| windows | $4000,$6000,$8000,$A000 (8 KB each, all switchable) | $4000 **fixed** = bank 0; $6000,$8000,$A000 switchable | $4000..$A000 all switchable | $4000 and $8000 (16 KB each) |
| bank registers (write-only) | $6000-$67FF→$4000, $6800-$6FFF→$6000, $7000-$77FF→$8000, $7800-$7FFF→$A000 | $6000-$7FFF→$6000, $8000-$9FFF→$8000, $A000-$BFFF→$A000 | $5000,$7000,$9000,$B000 (+$x800 ranges); bank $3F at $9000 maps the SCC | $6000-$67FF→$4000, $7000-$77FF→$8000 |
| reset state (openMSX) | all banks 0 (I believe) | banks 0,1,2,3 (I believe) | 0,1,2,3 | 0,0 |
| pages 0 and 3 | unmapped, read $FF | same | same | same |

openMSX config syntax: `<ROM><mem base=... size=.../><mappertype>ASCII8</mappertype>
<rom><filename>…</filename></rom></ROM>`; precedent for **an ASCII8 mapper ROM in
internal slot 3-3**: `share/machines/Al_Alamiah_AX230.xml:104-113` ("Games
ROM", `<mem base="0x0000" size="0x10000"/>`, `<mappertype>ASCII8</mappertype>`) —
a real machine, so the layout is also hardware-plausible. Mapper type names
should be confirmed with `openmsx_info romtype` once the battery is done
**[M]** (that command starts openMSX; do not run it now).

**The shape that fits our constraints [I].** Keep 3-2 exactly as is. Put the
mapper ROM in 3-3 with a **fixed window at $4000-$5FFF** (marker, jp-table,
bank dispatcher, shared helpers, resident-ABI import) and a **swapped window at
$6000-$7FFF** (one cold tenant cluster per 8 KB bank). Never map the slot in
page 2 (it would hide program text and DETOKBUF at $BE00 —
`docs/spec-basic-subrom.md` page-2 rule and memory `basic-rom-space-and-growth`).
Konami is the natural fit (bank 0 at $4000 is fixed by the hardware; one
register at $6000-$7FFF); ASCII8 works too if the dispatcher simply never writes
$6000-$67FF (bank 0 stays at $4000 from reset — **[M]** verify the reset value,
and verify that nothing in a cold boot writes it). Reject Konami SCC (a sound
device appears on bank $3F; needless side effect).

**Why the bank write works from inside a CALSLT'd tenant [I, M].** A Z80 write
to $6000-$7FFF reaches whichever device is selected in page 1 at that instant.
During a tenant call page 1 = 3-3, so the write hits the mapper; from main
(page 1 = slot 0) the same write hits ROM and is ignored — so **every bank write
must be issued by code in the fixed window of 3-3**, which is exactly where the
dispatcher lives. openMSX routes writes through the slot layout, so this should
hold; **[M]** a probe that writes the register from main and asserts no bank
change, then from the fixed window and asserts the change.

**Dispatch inside 3-3 [I].** CALSLT lands on a jp-table row at $4010+3n in bank
0 (fixed). Row → per-tenant 8 B stub in the fixed window: `ld a,BANK / ld
hl,TENANT / jp bank_go`. `bank_go` (once, ~25-30 B): save `BANK_CUR` (1 B page-3
shadow — the registers are write-only) on the stack, write the new bank to the
shadow and the register, `call` the tenant via `jp (hl)`, then restore shadow
and register from the stack and `ret`, preserving A/HL/DE/CF-less as today's
tenants do (A is the result; use the stack, not registers). Cost ≈ **+120-160 T
per mapper-tenant call [I]**, i.e. ~+15 % on a ~1 k T call; cold tenants only.
Returning with the register restored (not just "bank 0") is what makes nesting
correct: tenant in bank 1 → main low region → `sc_call` → tenant in bank 2 →
back in bank 1. The ASCII16 variant needs a per-bank "landing pad" (identical
bytes at the same address in every bank, the classic MegaROM trick) because the
instruction after the write is fetched from the new bank; with the hybrid's
fixed window that trick is unnecessary.

**Visibility rules for a bank tenant [I]:** may call the fixed window, its own
bank, main low region/BIOS (< $4000), RAM; may NOT call main page 1 (switched
out), another bank (not mapped), 3-2's page 1 (not mapped), nor any page-0
sub island. These are the `--page1` rules plus "same bank or fixed window" —
a per-bank walk with `(bank, address)` as the identity, which
`check_tenant_closure.py` does not have (it keys by address alone,
:547-620). The `.sym` from pasmo gives addresses only; the per-bank source
layout must be the checker's input (one `org $6000` block per bank in
separate files, or a bank tag per include).

**Interrupts.** Page 0 is untouched, so the ISR is the BIOS's; `htimi_guard`
skips the frame as for any slot-3 page-1 tenant. Hooks claimed by disk.rom are
RST 30h inter-slot calls that switch page 1 to 3-1 and back; the mapper's
registers are internal state and survive. EI tenants are therefore fine; but
**[M]** that no hook path writes $6000-$7FFF while page 1 = 3-3 (none should).

**Main-ROM cost.** Same as Option 1 for page 1 (it is "a second slot with a
page-1 table"): `SUBSLOT2` + `subrom2_call` + inline-stub mode, ~12-15 B low.
The bank machinery costs main **0 B**. The page-0 island does not grow at all
under this option (the mapper has no page 0).

**Tooling.** Everything in Option 1 plus: a bank-aware wall readout (one
`__MEAS_B<n>_END` per bank), a bank-aware closure checker (new identity
model), a bank-aware host bridge (`msxtest.py` must overlay $6000-$7FFF with
the right bank's bytes — it needs the bank per entry, derivable from the stub
table), and the ROM build itself (pasmo emits one linear image; banks are
`org $6000` blocks concatenated by a small `tools/` step, or assembled as
separate files and stitched). `graphics-floor-teeth`-style variant builds must
stitch too. This is the largest tooling delta of the four options.

**MSX2 future.** Spends subslot D like Option 1, but its capacity is open-ended
(8 KB × N) and it never needs a page-0 presence, so it coexists with an MSX2
SUB-ROM trivially. An MSX2 machine with a tighter subslot budget would benefit
from the mapper's "one subslot, unbounded page-1 space".

**Risks and gates.** (a) Bank register reset state ≠ assumed → a cold-boot
ping that returns the bank number from the swapped window before any switch.
(b) Bank not restored after a nested call → a ping-in-ping gate (bank 1 tenant
→ main → bank 2 tenant → back; assert both tags). (c) A tenant straddles the
$8000 end of its bank or calls another bank → assembler asserts per bank +
the per-bank closure walk. (d) Shadow cell corrupted by a user program → same
class as SUBSLOT (R4); accept, document. (e) openMSX's ROM-type auto-detection
must never be relied on: always `<mappertype>` explicit. (f) The register
write from the wrong page silently does nothing → gate (b) catches it.

### Option 3 — 16 KB-bank mapper (ASCII16-style) for comparison

Window is all of page 1, so there is no fixed dispatch window: the dispatcher
and shared helpers must be duplicated in every bank, or a RAM-resident switch
stub (like the trampoline) must do the write and the jump. Nesting needs the
shadow as in Option 2. Fewer, bigger banks mean fewer boundary problems for a
large tenant (a 10 KB tenant fits one 16 KB bank but not one 8 KB bank), and
more duplication for shared helpers. **[I]** Strictly worse than Option 2 for
our tenant sizes (the largest page-1 tenants are a few KB) and no cheaper in
tooling. Only worth it if an 8 KB bank proves too small for a specific
cluster — which the demand side should say.

### Option 4 — do nothing / carve

The carve routes on main are measured shut repeatedly (`carve-routes-measured-
shut`, `jrslice-slice`), and main is at 19/20 B; the sub walls (137/94 B) are
still above zero and D-CPY18 showed a sub-side carve can be large (sub p1 1 →
699 B, commit `673271c4`). Doing nothing is viable **only while the demand side
finds sub-side carves ≥ the next slice's price**; it does not change the MSX2
story and it leaves EXBRSA/`"CD"` as they are (which Joost has ruled out).

### Variant worth noting, not recommended first: a page-2 island in a 3-3 ROM

A plain ROM in 3-3 could be 48 KB and present a page-2 island ($8000-$BFFF).
A page-2 tenant sees BIOS + main page 1 + page 3, i.e. FAC/ARG/sysvars, but
hides program text, variables, strings that spill below $C000, and DETOKBUF
($BE00). The closure checker reasons about code, not data, so the hazard is
invisible to the gates; R4 of the space plan already lists "a page-2 island …
hides it during the call" as the cost. **[R]** only if the demand side needs
a third island shape; otherwise leave closed.

---

## 2. Ranking

1. **Option 1 (second plain ROM in 3-3)** — same ABI, same gates with
   parameters, same per-call cost, +16 KB on BOTH islands, smallest tooling
   delta; the only real new hazard (trampoline subslot constant) is a known
   8 B fix. Spends the last subslot.
2. **Option 2 (hybrid 8 KB mapper in 3-3)** — unbounded page-1 supply, 0 main
   bytes for the bank machinery, real-hardware precedent in openMSX (AX230),
   coexists best with an MSX2 SUB-ROM; but the largest tooling change (bank-
   aware closure, walls, host bridge, stitching), a new reentrancy invariant
   (the shadow), +15 % per call, and no page-0 growth. Choose it over Option 1
   only if the demand side says page 1 is the wall that binds **and** 16 KB is
   not enough for the foreseeable queue.
3. **Option 4 (carve)** — necessary anyway for the first slice (main is at
   19/20 B), not a growth strategy.
4. **Option 3 (16 KB banks)** — dominated by Option 2.

Options 1 and 2 are not exclusive in design, but they ARE exclusive in
hardware: both want subslot 3-3. A later move to an MSX2-shaped slot 3 (§1,
Option 1, "MSX2 future") can recover a subslot by pairing page-0 and page-1
devices, so choosing Option 1 now does not foreclose a mapper later.

---

## 3. Recommended staged plan

### Stage 0 — measure before anything (no code)

- Walls from a clean build (`make basic-reloc`), island fill
  (`tools/build_mainrom.py` ranges) **[M]**.
- `PEEK(&HFAF8)` on the VG-8020 and on both zerobas machines **[M]**.
- A cycle count of one tenant call (`kwtime` or openMSX cycle counter) so the
  ±15 % of Option 2 is against a measured number **[M]**.
- The demand side's answer: which wall binds over the next N items, and the
  size of the largest single cold tenant.

### Stage 1 — own signature, drop the EXBRSA write (safe, useful alone)

Scope: `sub/sub.asm:67` `"CD"` → an own pair (e.g. `"Z0"`; keep `"S1"` or
rename to `"Z1"` for symmetry); `basic/subrom-boot.asm:51,55` compare the new
bytes; delete `subrom-boot.asm:60` (−3 B page 1); `tools/check_sub_walls.py:67`
anchors; `probes/basic/basic_probe_subrom_boot.py:31` (reads the markers);
prose in `sub/sub.asm:28-39,64-67`, `basic/subromcall.asm:18-25`,
`docs/spec-basic-subrom.md` (D-3, D-6, §3c, §3g, R4), `docs/concepts/rom-
layout.md:74-76,177-179`, `docs/subrom-tenant-playbook.md`, both PROVENANCE
files, `sysvars.inc:4466-4470`. Main-ROM delta: ≤ 0 B. Behaviour delta: none
on MSX1 except $FAF8 (Stage 0 says what the reference holds; if the VG-8020
shows a value other than "untouched", match it — that is the faithful answer).
Gates: `subrom-acceptance`, `subrom-inttest`, `nodisk-acceptance`, the walls
(`check 2` must go RED on an all-$FF image with the NEW anchors — run its K4
knife), full battery. This also removes the only MSX2-collision path (§0.3).
**[R]** the exact marker bytes.

### Stage 2 — the space change: a second plain ROM in 3-3 (Option 1)

Order: (2a) trampoline fix in the RAM stub (save/restore the live `$FFFF`
subslot; retire `INT_SUB_SUBSL`), gated by `subrom-inttest` still green —
0 B main (the stub is copied into RAM), lands alone. (2b) `sub2.rom` skeleton:
markers, both tables with pings, `__MEAS_*` labels, Makefile targets, both
machine configs, `check_sub_walls.py` parameterised, closure checker pointed
at the second file, knife image hints; gate = ping both islands of both ROMs by
injection (the S2a pattern, zero main bytes) **before** any main change.
(2c) main dispatch: `SUBSLOT2`, `subrom2_call`, inline-stub mode, discovery —
priced by a build against the low/page-1/island walls; if it does not fit,
use the gateway variant for the first tenant and carve the native entry later.
(2d) first tenant: a cold page-1 leaf (the playbook's shape A) with a
nested-call gate (ROM-2 tenant → main → ROM-1 tenant) and an EI gate in ROM-2's
page 0. Every step re-measures the five (then seven) walls.

### Stage 3 (conditional) — the mapper

Only if Stage 0's demand numbers say page 1 is the binding wall and the queue
exceeds ~16 KB: build the hybrid in 3-3 **instead of** Option 1, starting with
the four verification probes ([M] rows in §1 Option 2: pages 0/3 read $FF,
reset bank, write-from-main ignored, write-from-fixed-window honoured) run by
injection against an openMSX machine with an empty-bank test image, before
any dispatcher is written.

---

## 4. Open questions

Rulings [R]:
1. The marker bytes for the two islands (Stage 1).
2. Whether `$FAF8` should be left untouched or matched to the measured VG-8020
   value (Stage 0 decides what "faithful" is).
3. Option 1 vs Option 2 for 3-3 (after the demand numbers).
4. Whether a page-2 island is on the table at all (R4 still open).

Measurements [M]:
- Wall and island fill from a clean build; `PEEK(&HFAF8)` on three machines;
  tenant-call cycle count.
- openMSX mapper facts (reset banks; pages 0/3 contents; writes from
  the wrong page ignored; `mappertype` names via `openmsx_info romtype`).
- Island free bytes for the boot-time discovery code.

Facts verified, for the record: EXBRSA has no reader in the tree; C-BIOS MSX1
does not scan for `"CD"` nor touch EXBRSA; C-BIOS MSX2 scans every subslot for
`"CD"` and takes the first; openMSX accepts an ASCII8 mapper ROM in an internal
subslot 3-3 and several ROM devices by page in one subslot; the trampoline
restores a boot-time constant subslot; nothing sub-side re-enters
`subrom_call` today.
