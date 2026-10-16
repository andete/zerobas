# D-WSZERO S14g — the refused-S13 set minus SH_*, homed by "what the reference does" (read-only design, 2026-10-16)

Scope: the 17 names / 15 window bytes that `python3 tools/ram_map.py --floor-top F380` lists
besides SH_* (designed separately). After S14g the listing holds only the 13 SH_* names (18 B).
Rule applied, in order (Joost, S13 refusal): (1) the reference's published cell FOR THE SAME JOB;
(2) registers / the Z80 stack, as the reference passes arguments; (3) an exclusive idle byte.
Every path below is repo-relative; nothing in the repo was written or built. 🔍 = verified by
reading the code/sources named; 🔮 = prediction; ⚠️ UNVERIFIED = not checked, says what would check it.

---------------------------------------------------------------------------------------------------

## 0. Verdict in one screen

| cell(s) | B | home | rule tier | ROM cost | slice |
|---|---|---|---|---|---|
| FCH_RDMODE | 1 | **FLKINP $F6A6** ("a READ or INPUT statement is being executed") | 1 same job | 0 | S14g-a |
| GFX_MODE / ASPMAJ / ARCF / SNEG / ENEG | 5 | **BUFTX+10..+14 ($F571-$F575)** — CIRCLE/LINE are statement-exclusive with DRAW/FOR/PU/TSV; the S14f "DRAW drives GFX_MODE" hazard is REFUTED (§2.2) | BUF (S14d's host, same proof as CIRCLE's 72 B S12 guests) | 0 | S14g-a |
| AUDIO_VMASK | (alias) | **PRSCNT $FB35** ("status about the parsing of a PLAY string") | 1 same job | 0 | S14g-a |
| DISKOP_OP (+FOPEN_SEL, +LE_OP for now) | 1 | **KANAST $FCAC** (kana / EU dead-key state; C-BIOS has neither) — must stay RAM: an ARMED selector (§2.4) | 3 idle byte | 0 | S14g-a |
| ERRMARK | 1 | **KANAMD $FCAD** (Japanese-only typeset) — a persistent landmark the tests read | 3 idle byte | 0 | S14g-a |
| WSRC_TYP | 2 | **register B, then F on the stack** (the type is read once, from FACTYP / LHS_FACTYP) | 2 register | seg B **−17 B** (−21 with an optional dead reload), faster | S14g-b |
| INDLR_N | 1 | **the Z80 stack** (pushed after the count's eval; a nested INPUT$ keeps its own) | 2 stack | seg C **−2** | S14g-c |
| PRDEST | 1 | **PTRFIL $F864** (C-BIOS ISFLIO reads exactly this byte as "I/O to a device is taking place") | 1 same job | (with PRDEV) | S14g-c |
| PRDEV | 1 | **BUF $F5FD** (the free gap TSV_CNT..DB_WIN; statement-only; never read unless PRDEST≠0, and every PRDEST:=1 site sets it first) | BUF | seg C **+2** (save.asm loses its one-store pair) | S14g-c |
| GFX_PTX / GFX_PTY | 2 | **registers E / D** through gfx_tenant → subrom_call → CALSLT | 2 register | seg C **−6**, sub p0 **−24** | S14g-d |
| LE_OP (optional) | 0 (alias) | **register C** through sc_inl1 → CALSLT; LIST pushes the verb | 2 register | seg C −4, seg F −5, sub p1 −2 | S14g-d (opt.) |

* **S14g-c is seg-C neutral by construction** (−2 +2): no refill. **S14g-d needs a 6-B (10-B with
  LE_OP) refill in seg C** — `tools/pin_plan.py`'s exact fill, as S14d refilled pl_exit; if none
  fits, the fallback is S14_plan's leaf host for GFX_PTX/PTY (0 ROM, §2.7).
* Window bytes freed: a 8, b 2, c 3, d 2 = **15**. Names: a 11 (incl. 3 aliases), b 1, c 3, d 2.
* 🔴 **s14_plan.md §6's "refused" table is stale on two rows**: ERRMARK → FLKINP collides with the
  rule's FCH_RDMODE → FLKINP (same job wins), and DISKOP_OP → NLONLY collides with S14f's
  VARTYPE → NLONLY. The four S11 spare singles (NLONLY, FLBMEM, FLKINP, PTRFLG) are ALL taken now
  (VARTYPE, DISKOP_STATUS, FCH_RDMODE, RDV_MODE) — hence KANAST / KANAMD (§2.4, §2.5).

---------------------------------------------------------------------------------------------------

## 1. Census of the hosts (re-done today, read-only)

Method 🔍: every published name in `cbios/src/systemvars.asm` in $F380-$FFFF, minus any address
carrying a value in the four syms (`build/basic-reloc.sym`, `sub.sym`, `sub2.sym`, `disk.sym`),
then for each candidate: references by NAME in C-BIOS outside systemvars.asm, literal `$xxxx`
references in basic/ sub/ sub2/ disk/ tape/ cbios-repack/, and pointer loads (`ld rr,NAME`).
Script: [`wszero_s14g_pubidle.py`](wszero_s14g_pubidle.py) (needs the C-BIOS sources beside the repo, or `CBIOS_SRC`).

| host | C-BIOS description (systemvars.asm, brief) | zerobas today | C-BIOS use | verdict |
|---|---|---|---|---|
| FLKINP $F6A6 | "switch indicating if currently a READ or INPUT statement is being executed" | no sym, no literal (DATASTATE $F6A5 / BL_PTR $F6A7 are 1 / 2 B) | none | FCH_RDMODE |
| PRSCNT $FB35 | "status about the parsing of a PLAY string; bit 7 one time parsed; bits 1-0 number of parsed strings" | no sym, no literal; zerobas already uses the neighbours VOICEN $FB38 / MCLPTR / QUEUEN / MUSICF for their own jobs | none | AUDIO_VMASK |
| PTRFIL $F864-$F865 | "during file I/O the start address of the active file-buffer" | no sym in any image (disk.rom crosses with A/C/FN_RESUME, disk/kernel.asm:1628) | **READ by ISFLIO** ($014A, main.asm:2252: `ld a,(PTRFIL) / and a`) — "tests if I/O to device is taking place"; no writer | PRDEST (low byte only) |
| KANAST $FCAC | "in non-japanese models: dead key status 0..4; in japanese models charset" | none | none (C-BIOS drops dead keys: main.asm:2862 stores nothing) | DISKOP_OP |
| KANAMD $FCAD | "only used in japanese MSX models; the used typeset" | none | none | ERRMARK |
| BUF $F5FD-$F5FF | inside BUF | free: TSV_CNT $F5FC (1 B) .. DB_WIN $F600 | — | PRDEV ($F5FD) |
| BUFTX $F567-$F59F | inside BUF | S14d's statement-exclusive host (FOR / PRINT USING / DRAW / TSV_NAME share it) | — | the 5 CIRCLE/LINE cells |

C-BIOS `init_ram` zero-fills $F380-$FFFD at boot (main.asm:1086-1094) 🔍, so every new high home
starts at 0 — DISKOP_OP's "idle" value, and better than $EE38's random boot content.
Rejected on the way: PADX/PADY ($FC9C/D: zerobas's tape firmware uses them, tape/tape.asm:72-73),
PRTFLG $F416 (PRDEV must be PRDEST+1 for save.asm's one-store; $F417 is GFX_SPATN), CLMLST /
ENSTOP / CAPST (BASIC- or user-visible settings), FILTAB/NULBUF (D-FCBSHAPE), LOGOPR $FB02 (RS2IQ
tail, S11 stopped short of it), CASPRV / SAVENT (kept for their own future same-job re-homes:
CAS: pushback, BSAVE exec address), NOFUNS / CONSAV / RTPROG / MAXDEL..SKPCNT (inside wider zerobas
cells: FN_PAREA, H9, STRPTR, S7's SUB_INT_RAM). Noted: the reference's own CIRCLE cells CLINEF
$F935 (spoke flag = GFX_SNEG/ENEG's job) and CSCLXY $F941 (= GFX_ASPMAJ's job) sit inside S7's
SUB_INT_RAM trampoline ($F92D-$F950) — the same-job homes exist but are occupied.

---------------------------------------------------------------------------------------------------

## 2. Per cell: users, lifetime, the reference, the design

### 2.1 FCH_RDMODE ($EF66) → FLKINP $F6A6 (same job, equates)
Users 🔍: writers [basic/files.asm:1283](basic/files.asm) (`input_common`: 0 = INPUT, 1 = LINE
INPUT, both console and `#` forms), [basic/strvar.asm:543](basic/strvar.asm) (INPUT$ on a disk
channel: 2 = raw). Readers: [basic/files.asm:1447](basic/files.asm) (`read_into_strscr`),
[basic/input.asm:66,75,81,418](basic/input.asm) (console prompt / the CAS: arm),
[disk/fat.asm:479](disk/fat.asm) (disk.rom's H_CHIN; the address comes from the GENERATED
disk/basic-resident-abi.inc — tools/gen_resident_abi.py:269 lists it). Host tests poke it by sym
(tests/test_seqin.py, tests/test_input.py) — unaffected.
Lifetime: set at the head of an INPUT / LINE INPUT statement, read through that statement; INPUT$
writes it inside an expression (disk channel only). Job: the reference's FLKINP distinguishes the
two users of its shared READ/INPUT reader; zerobas's FCH_RDMODE distinguishes the modes of its
shared INPUT reader — the same switch on the same machinery. Value encoding differs (S8 accepted
that for DRWFLG/DRWSCL; the PEEK row in §4 measures it).
Edit: `FCH_RDMODE equ $F6A6 ; D-WSZERO S14g: FLKINP, the reference's "a READ or INPUT statement is
being executed" -- the same switch (was $EF66)` at [basic/sysvars.inc:3172](basic/sysvars.inc).
0 ROM bytes (main/sub/sub2); disk.rom re-assembles with the regenerated ABI (same sizes).

### 2.2 GFX_MODE / ASPMAJ / ARCF / SNEG / ENEG → BUFTX+10..+14 (equates)
Users 🔍:
* GFX_MODE: writers [basic/graphics.asm:256](basic/graphics.asm) (LINE default 0, BEFORE the
  colour expression), [:299](basic/graphics.asm) (`,B`/`,BF`), [sub/graphics.asm:1416](sub/graphics.asm)
  (`gco_spoke`, CIRCLE's radius spokes, then `jp gfx_line_op`); the ONLY reader is
  [sub/graphics.asm:623](sub/graphics.asm) (`gfx_line_op`, entered by the GFX_OP=3 dispatch :82 and
  gco_spoke's tail).
* ASPMAJ: [sub/circleparse.asm:234,248,320](sub/circleparse.asm) → [sub/graphics.asm:1654,1803](sub/graphics.asm).
* ARCF: [sub/circleparse.asm:324,371](sub/circleparse.asm) → [sub/graphics.asm:1335,1914](sub/graphics.asm).
* SNEG / ENEG: [sub/circleparse.asm:325,326](sub/circleparse.asm) + through the pointer
  `ld bc,GFX_SNEG/ENEG` (:170, :196) → `cpt_angle_from_arga` → [sub/graphics.asm:1367,1370,1564,1572](sub/graphics.asm).
* Host tests poke ARCF/SNEG/ASPMAJ by name (tests/test_graphics.py:218-295) — unaffected.
Lifetime: one LINE or CIRCLE statement, and **live across expression evaluation**: LINE's colour
expression runs between :256 and the tenant; CIRCLE's parse is a co-routine (`GFX_DREQ = 3` →
the resident evaluates the next angle / aspect → re-entry), with `cpt_defaults` (:316-329) writing
all four defaults first.
Why BUFTX is safe: (a) S14d's invariant — no expression writes BUF past STRSCR+8 (inherited, not
re-proved here; its witnesses `ovbuftx` / K-WS69 stand); (b) CIRCLE already keeps 72 B in BUF
$F5A0-$F5E7 across the very same evaluations (S12 §3.1: SVX..WRAPF, TX1..YSTEP), so this adds no new
hazard class; (c) every other BUFTX tenant (FOR / NEXT's working copy, PRINT USING, DRAW, the tape
SAVE name) is a different STATEMENT, and traps run only at statement boundaries; the ISR (C-BIOS
KEYINT, htimi_guard → PLAY / traps) writes no BUF.
🔍 **The S14f hazard "DRAW may drive the line engine through GFX_MODE" is REFUTED**: DRAW's only
line call is `call gfx_draw_seg` [sub/graphics.asm:3531](sub/graphics.asm), which reads no
GFX_MODE; GFX_MODE has exactly the four sites above. DRAW never co-lives with LINE/CIRCLE, so
overlapping DRAW's 57 B is legitimate; +10..+14 is chosen only to keep the CIRCLE cells off PRINT
USING's +0..+9 and make knives readable.
Edit (literal addresses, because GFX_MODE's equ at sysvars.inc:723 precedes BUFTX's at :1960 —
⚠️ UNVERIFIED whether pasmo AND tools/ram_map.py / ws_shift.py resolve a forward `BUFTX + 10`;
S14d/S14f only ever wrote BUFTX-relative equs AFTER :1960):
```
GFX_MODE   equ $F571 ; D-WSZERO S14g: BUFTX+10, LINE/CIRCLE statement-exclusive (was $EF6F)
GFX_ASPMAJ equ $F572 ; BUFTX+11 (was $EF93)
GFX_ARCF   equ $F573 ; BUFTX+12 (was $EF96)
GFX_SNEG   equ $F574 ; BUFTX+13 (was $EFBB)
GFX_ENEG   equ $F575 ; BUFTX+14 (was $EFBC)
```
and a guard in the S14d block ([basic/sysvars.inc:5744](basic/sysvars.inc)):
```
    IF GFX_MODE != BUFTX + 10 || GFX_ENEG != BUFTX + 14 || GFX_ENEG + 1 > GFX_POVF
                db      S14G_LINE_CIRCLE_CELLS_OUTSIDE_BUFTX
    ENDIF
```
0 ROM bytes.

### 2.3 AUDIO_VMASK → PRSCNT $FB35 (same job, equates)
Users 🔍: [basic/play.asm:36](basic/play.asm) (0 at `pl_args`, also the pinned $73E5 entry),
[:88-90](basic/play.asm) (OR in each voice's bit, BETWEEN the voice string evaluations),
[sub/playparse.asm:54,72,123](sub/playparse.asm) (read; `ld hl,AUDIO_VMASK` clears a bit for an
empty voice; the commit ORs it into MUSICF). Not read by the ISR (playsvc.asm: 0 hits). Host test
tests/test_play_parse.py writes it by sym — unaffected.
Lifetime: one PLAY statement, live across expression evaluation → not BUF-safe-by-type needed, any
byte no expression/ISR writes: PRSCNT qualifies (§1). Job: the reference's PRSCNT is PLAY's operand-
parse status; AUDIO_VMASK is PLAY's operand-parse status (which voices were given). Encoding
differs (mask vs count|bit7) — S8 precedent; PEEK row in §4.
Edit: `AUDIO_VMASK equ $FB35 ; D-WSZERO S14g: PRSCNT, the reference's PLAY parse status (was
DISKOP_OP)` at [basic/sysvars.inc:3822](basic/sysvars.inc). 0 ROM. (It stops aliasing DISKOP_OP:
nothing relied on the alias — the PLAY parse never runs a FAT primitive or a hook.)

### 2.4 DISKOP_OP / FOPEN_SEL / LE_OP → KANAST $FCAC (idle byte, equates)
Users 🔍 (diskless-relevant): LE_OP — LIST/LLIST [basic/list.asm:93,107](basic/list.asm) (written
before the tenant, READ BACK after it to pick the sink), STORE / DELETE / RENUM / AUTO / relink via
[basic/program.asm:1335,1345](basic/program.asm), read by [sub/lineedit.asm:104](sub/lineedit.asm).
FOPEN_SEL — written by `chan_gate` [basic/files.asm:155](basic/files.asm) **on every path, the
unclaimed (diskless) one included**: `PRINT DSKF(0)` with no disk ROM goes
[basic/expr.asm:1565](basic/expr.asm) → chan_gate → `ld (FOPEN_SEL),a` → bare hook → ERR 5. So the
group is NOT legitimately DISK-ONLY and cannot just be tagged and left (after S15 that store would
land in program RAM). DISKOP_OP — `fatprim_op` [basic/fat.asm:375](basic/fat.asm),
[sub/fatprim.asm:72](sub/fatprim.asm), and disk.rom (disk/kernel.asm:1058,1141,4563,4724,5292-5520,
via the generated ABI, tools/gen_resident_abi.py:147).
What the reference does: its disk hooks take arguments in registers (expansion-protocol.md §8.6:
BC / HL / DE). **Why not registers here**: FOPEN_SEL is an ARMED selector — the hook $FE5D is
reached by callers that are not the verb (disk/kernel.asm:4715-4724 "DISARM THE SELECTOR ON THE
WAY OUT ... leaving it armed means the NEXT such call falls through into a FAT mount"), so the
idle/armed state must persist in RAM; a register carries nothing to a caller that did not load it.
`subrom_call` also overwrites A (the slot id) — A cannot carry a tenant selector. → tier 3, an
exclusive idle byte. LE_OP may still go to a register (S14g-d, optional); AUDIO_VMASK left (2.3).
Edit: `DISKOP_OP equ $FCAC ; D-WSZERO S14g: KANAST -- kana / EU dead-key state; C-BIOS keeps
neither (dead keys store nothing, cbios main.asm:2862) and zero-fills it at init_ram: idle (was
$EE38)` at [basic/sysvars.inc:3351](basic/sysvars.inc). FOPEN_SEL / LE_OP follow by alias
(sysvars.inc:3448, :3720; disk/equates.inc:175). 0 ROM; disk.rom re-assembles (ABI).
The comment at sysvars.inc:677 ("MUST NOT alias the audio/disk param cells (DISKOP_OP/AUDIO_VMASK
$E9FB)") names a stale address — update it with the move.

### 2.5 ERRMARK ($EEBD) → KANAMD $FCAD (idle byte, equates)
Users 🔍: ~14 write-only landmark stores ($DD expression error via `errmark_expr`
[basic/interp.asm:1941-1945](basic/interp.asm), $DB undefined line :1917, $EE tape I/O in
basic/bload.asm:308, basic/cload.asm:1094, sub/save.asm:109, sub/bload.asm:112, program.asm ×6);
ONE functional reader: `els_tc_common` [basic/missing.asm:616-620](basic/missing.asm) — clear, `call
eval`, read ($DD ⇒ Syntax error, else Type mismatch). Many host tests and probes read it by sym
(tests/test_usr.py:216, tests/msxtest.py, probes/basic/basic_probe_clear.py:141 — POKE 0, CLEAR,
read back) — it must PERSIST across statements, so neither BUF nor a leaf host.
No same-job reference cell (ERRFLG $F414 already holds zerobas's error number). Tier 3.
Edit: `ERRMARK equ $FCAD ; D-WSZERO S14g: KANAMD -- Japanese-only typeset, idle on C-BIOS; a
persistent landmark the tests read (was $EEBD)` at [basic/sysvars.inc:858](basic/sysvars.inc). 0 ROM.

### 2.6 WSRC_TYP ($F11B, 2 B) → a register (seg B −17 B)
Users 🔍: only [basic/float-arith.asm:1442-1531](basic/float-arith.asm) (widen_fac_to /
widen_lhsframe_to / wsrc_go): stored at entry (:1444, :1449), dereferenced twice (:1480 mantissa
count, :1523 pad count). The reference keeps the operand type in VALTYP and passes it in A.
Design: load the TYPE (not its address) once at entry into A, park it in B until the mantissa count
is chosen, carry the `cp 8` result across the unpack loop as F on the stack. B is free from entry
to `ld b,7` (the zero path, `ld c,a`, the dexp block touch A/C/D/E/HL only) 🔍; the loop makes no
call, so `push af` / `pop af` around it is balanced. WSRC ($F84D, ARG tail) stays — DE is
clobbered by the dexp block and the source pointer must survive it.
```
before (12+10 B)                         after (8+6 B)
widen_fac_to:                            widen_fac_to:
  ld   de,FACTYP                           ld   a,(FACTYP)       ; A = the type (2/4/8)
  ld   (WSRC_TYP),de                       ld   de,FAC
  ld   de,FAC                              jr   wsrc_go
  jr   wsrc_go                           widen_lhsframe_to:
widen_lhsframe_to:                         ld   a,(LHS_FACTYP)
  ld   de,LHS_FACTYP                       ld   de,LHS_FAC
  ld   (WSRC_TYP),de                     wsrc_go:
  ld   de,LHS_FAC                          ld   (WSRC),de
wsrc_go:                                   ld   b,a              ; +1: WSRC_TYP's job, in B
  ld   (WSRC),de                           push hl
  push hl                                  ld   de,(WSRC)        ; (dead: DE already = WSRC; -4 B optional)
  ld   de,(WSRC)                           ...unchanged through wsrc_dexp_ok / inc hl...
  ...                                      ld   a,b              ; was ld de,(WSRC_TYP) / ld a,(de): -4
  ld   de,(WSRC_TYP)                       cp   8
  ld   a,(de)                              ld   b,7
  cp   8 / ld b,7 / jr z / ld b,3          jr   z,wsrc_mbytes_ok
wsrc_mbytes_ok:                            ld   b,3
  ...loop...                             wsrc_mbytes_ok:
  push hl                                  push af               ; +1: Z = double, across the loop
  ld   hl,(WSRC_TYP)                       ...loop unchanged...
  ld   a,(hl)                              pop  af               ; Z = double
  pop  hl                                  ld   b,9
  cp   8                                   jr   nz,wsrc_padcount
  ld   b,9 / jr nz / ld b,1                ld   b,1
wsrc_padcount: jp zero_fill              wsrc_padcount: jp zero_fill
```
Δ: −4 −4 +1 −3 −7 = **−17 B in seg B** (`widen_fac_to` $3779, segment B $3299..$3FC7 — no pin,
padded to $4000 on its own: free to shrink; main low wall grows). −21 with the dead reload. ⏱
~−50 T per widen (three 16-bit indirections out, a push/pop in) — a TIER 5 gain on FOR/NEXT, which
D-NEXTCOST measured at two widens per NEXT. Delete `WSRC_TYP` from sysvars.inc:4800 and fix the
header comment (:1432-1440 says "(WSRC)/(WSRC_TYP) hold which pair") — the fix falsifies it.
🔍 No other image assembles this body: no sub/ sub2/ disk/ file includes float-arith.asm (grep);
sub.sym's widen_fac_to is main's address, an import.

### 2.7 GFX_PTX / GFX_PTY ($EFBF/$EFC0) → registers E / D (seg C −6, sub p0 −24)
Users 🔍: written only at [basic/graphics.asm:159-162](basic/graphics.asm) (POINT, after the range
check, immediately before `ld a,2 / ld (GFX_OP),a / call gfx_tenant`); read only by `gfx_point`
[sub/graphics.asm:497-521](sub/graphics.asm), three times (head, MC branch, G2 branch) — each read
pair is `ld a,(GFX_PTX) / ld e,a / ld a,(GFX_PTY) / ld d,a`, i.e. the tenant WANTS them in E/D.
Register path 🔍: `gfx_tenant` = `call sr_inl0 / db / ret` (basic/graphics.asm:51); `sr_inl0`/
`inl_go` preserve BC/DE/HL (basic/subromcall.asm:171-187, its own header says so); `subrom_call`
pushes/pops DE around the IY build (:61-76, "HL/DE pass through"); C-BIOS CALSLT saves BC/DE/HL in
the shadow set, restores them before `jp clprim` → `jp (ix)`, and hands the callee's back on return
(cbios src/slot.asm:125-186, :423-433); `graphics_tenant` touches only A/F before `jp z,gfx_point`
(sub/graphics.asm:53-80); `gfx_is_mc` clobbers A only (:373-376), so the two re-reads are dead.
gfx_point / gpt_g2 have no other entry (grep). The reference's POINT also passes the coordinates
to its pixel-address routine in registers.
```
basic/graphics.asm:159-162 before (8 B)       after (2 B)
  ld   a,c        ; x                           ld   d,e       ; D = y, 0..191
  ld   (GFX_PTX),a                              ld   e,c       ; E = x, 0..255 -- DE rides through
  ld   a,e        ; y                                          ; gfx_tenant / subrom_call / CALSLT
  ld   (GFX_PTY),a
sub/graphics.asm:498-501, 510-513, 518-521: delete all three 8-B load quads (-24 B).
```
DE is reloaded with the result after the call (`ld a,(GFX_RES) / ld e,a / ld d,0`), so nothing
downstream reads the old DE. Update the "Byte-neutral swap" comment above :159 and gfx_point's
header (:485-488 "marshalled the target into GFX_PTX/GFX_PTY").
**Pin**: seg C −6 → refill 6 B (`python3 tools/pin_plan.py` REFILL / exact_fill, as S14d's pl_exit),
refilled where the bytes were freed. **Fallback (0 ROM)**: s14_plan's leaf host — any 2 bytes of
MULPROD/DIVPAD: the write and the read are adjacent with only gfx_tenant/CALSLT between, POINT is
a FUNCTION whose operands are evaluated before any leaf family (fp_mul/div/add, tk_float, widen,
PLF, caddsub's FP_OPMODE) goes live, and nothing interrupt-time uses the host (S12 §2.3) — add the
pair to S12's matrix; ⚠️ UNVERIFIED by reach.py (S12's session-scratch tool is not in the repo).

### 2.8 INDLR_N ($EEC0) → the Z80 stack (seg C −2)
Users 🔍: only [basic/strvar.asm:451, 550, 575-577](basic/strvar.asm) (INPUT$). Lifetime: from the
count's eval, ACROSS the channel expression's eval (`sid_fnum: call eval`), fch_check, the mode
classify / fch_select, str_temp_alloc, and the read loop whose `arl_getbyte` CALSLTs / hooks clobber
every register (hence RAM today).
🔴 Found by the design: the channel expression may itself contain INPUT$ —
`A$=INPUT$(3,#VAL(INPUT$(1)))` — whose own `ld (INDLR_N),a` and loop leave INDLR_N = 0, so the
outer read raises **ERR 5** at `jp z,gb_illegal` (🔮 today; the VG-8020 reads 3 bytes). The stack
form fixes it: each INPUT$ keeps its own n.
```
strvar.asm:451  ld (INDLR_N),a  (3)        ->  push af            (1)  ; A = n: n rides the stack
strvar.asm:467  jp nz,str_eval_no          ->  jp nz,sid_no       (same size)
strvar.asm:487  jp nz,str_eval_no          ->  jp nz,sid_no       (same size)
sid_read: ld a,(INDLR_N)  (3)              ->  pop de / pop af / push de  (3)  ; the cursor stays on top for sfi_done
after `call check_expr_errors`:            +   ld b,(hl)          (1)  ; B = n: the temp's [len] (str-engine.asm:11 [len:1][ptr:2])
sidr_lp (19 B):                            ->  (14 B)
  push hl                                      push bc
  call arl_getbyte                             push hl
  pop hl                                       call arl_getbyte
  jp c,gp_past_eof                             pop hl
  ld (hl),a                                    pop bc
  inc hl                                       jp c,gp_past_eof   ; raises: raise_error resets SP
  ld a,(INDLR_N) / dec a / ld (INDLR_N),a      ld (hl),a
  jr nz,sidr_lp                                inc hl
                                               djnz sidr_lp
  jp sfi_done                                  jp sfi_done
new, after `jp sfi_done` (never fallen into):
sid_no:  pop de                            (1)  ; drop n (DE is dead on a decline)
         jp  str_eval_no                   (3)  ; jr cannot reach $49BA from ~$4AC4
```
25 → 23 B: **−2 in seg C**. The two declines after the count keep str_eval_no's exact exit state
(A = the char, CF clear, HL = cursor); every raise (gb_illegal, fch_check, sid_raise, gp_past_eof,
check_expr_errors) resets SP. str_temp_alloc's success is the only path to `ld b,(hl)` (its
failures set FPERR and check_expr_errors raises) 🔍 (str-engine.asm:590-630). ⏱ the loop is ~8 T per
byte faster. Delete INDLR_N (sysvars.inc:897) and fix the comments that name it
(files.asm:2530, strvar.asm's D-INPDCON block "consumes INDLR_N bytes", PROVENANCE.md:2803).

### 2.9 PRDEST / PRDEV ($EF38/$EF39) → PTRFIL $F864 / BUF $F5FD (seg C +2)
Users 🔍: PRDEST writers — every statement head [basic/interp.asm:577-578](basic/interp.asm), repl
:78, error tails (arrays.asm:164, interp.asm:1155, subromcall.asm:101, input.asm:42), PRINT#
[basic/print.asm:158](basic/print.asm), LPRINT :50, LLIST [basic/list.asm:109](basic/list.asm), ASCII
SAVE [basic/save.asm:299,309](basic/save.asm), tape ASCII SAVE :422/:431, init_filechan
[basic/files.asm:1569](basic/files.asm); readers `pchar` [basic/print.asm:610](basic/print.asm),
:466, :756. PRDEV writers — print.asm:49, :134, :147 (`exp_dev_set`), list.asm:111, save.asm:299
(the one-store pair, guarded by the `IF PRDEV - PRDEST - 1` at :295), :424, :432, files.asm:1570;
readers pchar :620 and the column query :759, **both only when PRDEST ≠ 0**. Every PRDEST:=1 site
sets PRDEV earlier in the same statement (PRINT#: all five device arms and the disk arm reach
`exp_hash_go` through `exp_dev_set`/`exp_sep`; LPRINT :49-50; LLIST :109-111; both SAVEs) 🔍.
The reference: PTRFIL ≠ 0 ⇔ output goes to a file (its OUTDO/ISFLIO test); C-BIOS's ISFLIO reads
exactly PTRFIL's low byte ("tests if I/O to device is taking place"); zerobas's own OUTDO (RST 18h,
basic/islands.asm:222-236) is pchar. So **PRDEST → PTRFIL low = the same job**. PRDEV has no
published home until D-FCBSHAPE (then: the active FCB's device byte, FCB+4, through PTRFIL).
Why NOT PRDEV at PTRFIL+1 (the 0-byte variant P1): PRDEV is stale between statements (LLIST /
LPRINT / a CRT: or GRP: PRINT# leave 1/2/4), so `PRINT PEEK(&HF865)` would read 2 after a CRT:
PRINT# where today zerobas reads 0 (C-BIOS zero) and the reference's idle PTRFIL is 0 — a NEW
visible divergence (🔮, measured by `ovprdev`'s knife K-WS86). PRDEV in BUF $F5FD instead: read
only while PRDEST ≠ 0 within the statement that set it; the statement's item expressions write BUF
only at STRSCR+0..8 (S14d); PRINT USING's cells (BUFTX), the render window ($F600+), TSV_PTR/CNT
($F5FA-$F5FC) are distinct bytes; INPUT / LINE INPUT / INPUT # staging that passes $F5FD are other
statements that never read PRDEV; the CAS: sink buffers in the channel block (cload.asm:430), the
GRP: sink (sub2/grpprt.asm) and LPTOUT touch no BUF (grep).
```
sysvars.inc:1774  PRDEST equ $F864 ; D-WSZERO S14g: PTRFIL's low byte -- nonzero while output goes to a
                                   ; device, the byte C-BIOS's ISFLIO tests; the high byte is never written (was $EF38)
sysvars.inc:1781  PRDEV  equ $F5FD ; D-WSZERO S14g: BUF, between TSV_CNT and DB_WIN; read only while PRDEST != 0,
                                   ; set before it by every PRDEST:=1 site (was $EF39)
save.asm:295-299 before (6 B emitted)          after (8 B)
    IF PRDEV - PRDEST - 1 ... ENDIF   (delete)
    ld   hl,1                                   xor  a
    ld   (PRDEST),hl                            ld   (PRDEV),a        ; 0 = the disk sink (D-ASAVEDEV)
                                                inc  a
                                                ld   (PRDEST),a       ; 1 = route pchar to it
new guard (S14c block):
    IF PRDEV < TSV_CNT + 1 || PRDEV + 1 > DB_WIN
                db      S14G_PRDEV_OUTSIDE_THE_BUF_GAP
    ENDIF
```
**+2 in seg C** (save.asm, `ascii_save` $6972). Fix save.asm:289-294's comment ("One store sets
both: PRDEV is the byte after PRDEST") — falsified by the move. init_filechan's cold `ld (PRDEV),a`
(seg D, unchanged bytes) now zeroes a BUF byte at boot/NEW/RUN — ⚠️ UNVERIFIED that none of its
callers holds a BUF cell live at that moment (by reading: they are statement heads).

### 2.10 LE_OP → register C (optional; seg C −4, seg F −5, sub p1 −2)
Every LE op marshals its inputs in RAM (SL_NUM/SL_TOK, SL_DELPTR, RN_PTR, LST_PTR) 🔍, so BC is free
at the call; `sc_inl1`/`sc_call`/`subrom_call`/CALSLT pass C (§2.7); the tenant entry `ei / call
le_dispatch` keeps it. LIST reads the verb back after the call — push it instead.
```
list.asm:93-107  ld (LE_OP),a / ld (LST_PTR),hl / call le_call / jp nz,raise_error / ... / ld a,(LE_OP)  (15 B)
             ->  push af / ld (LST_PTR),hl / call le_call_op / jp nz,raise_error / ... / pop af       (11 B)
program.asm:1335  ld (LE_OP),a -> ld c,a (-2);  `le_call:` label goes (its only caller was list.asm:95)
program.asm:1344-1345  ld a,1 / ld (LE_OP),a -> ld c,LE_OP_RELINK (-3)
sub/lineedit.asm:104  ld a,(LE_OP) -> ld a,c (-2)
```
`raise_error` resets SP, so the pushed verb on the error arm is harmless 🔍 (interp.asm, the
`gp_raise` / `sid_raise` comments rely on the same). Not needed for S15 (LE_OP already left with
DISKOP_OP in S14g-a); it frees bytes and leaves KANAST to the disk family alone. Fix the sysvars.inc
comments :3448-3559 ("read LE_OP BACK", "One subrom_call reaches exactly one LE_OP").

---------------------------------------------------------------------------------------------------

## 3. Slices, cheapest first

| slice | what | window B | ROM | pin safety |
|---|---|---|---|---|
| **S14g-a** | equates: FCH_RDMODE→FLKINP, 5 CIRCLE/LINE cells→BUFTX+10..14, AUDIO_VMASK→PRSCNT, DISKOP_OP(+FOPEN_SEL,+LE_OP)→KANAST, ERRMARK→KANAMD; 1 guard; stale comment sysvars.inc:677 | 8 | 0 (main, sub, sub2); disk.rom immediates only (generated ABI) | none touched |
| **S14g-b** | WSRC_TYP → B / F (§2.6) | 2 | seg B −17 (−21) | seg B has no pin; `make basic-reloc` reads the low wall |
| **S14g-c** | INDLR_N on the stack (+ the nested-INPUT$ fix) and PRDEST→PTRFIL / PRDEV→BUF $F5FD; 1 guard | 3 | seg C −2 +2 = **0** | net 0 in seg C by construction; code between strvar ($4A3F) and save.asm ($6972) shifts −2 then back — `jr`s spanning either edit point re-checked by the assembler and `pin_plan.py --check` |
| **S14g-d** | POINT in E/D (§2.7) [+ LE_OP in C, §2.10] | 2 | seg C −6 [−10], sub p0 −24, [seg F −5, sub p1 −2] | seg C refill of exactly 6 [10] B from seg F via pin_plan's exact fill, placed where freed; else fall back to the leaf host (0 ROM) for PTX/PTY |

After S14g-d: `ram_map --floor-top F380` lists only SH_* (13 names, 18 B). Walls (estimates, hand
counts — `make basic-reloc` is the reading, never these): low +17..21; sub p0 10 → 34; sub p1 +2;
seg F +5 (+ whatever the refill moves out of it); seg C / D / E unchanged.
Each slice: full battery once before commit (S14 §4.7), plus diskbasic- / bdos- / fat-error- /
nodisk-acceptance for a/c (DISKOP_OP, FCH_RDMODE, PRDEST are disk-machine cells too).

---------------------------------------------------------------------------------------------------

## 4. Witness (basic_probe_wszero.py pattern) and knives

Sum rows: tape fills the window with $A5, the statements below run AFTER the load, then `900`
sums the vacated bytes (VG-8020: N × 165, the load's own fill). Decimal addresses: DISKOP_OP 60984,
ERRMARK 61117, INDLR_N 61120, PRDEST/PRDEV 61240-61241, FCH_RDMODE 61286, GFX_MODE 61295,
ASPMAJ 61331, ARCF 61334, SNEG/ENEG 61371-61372, PTX/PTY 61375-61376, WSRC_TYP 61723-61724.

* **`s14ga`** (8 B, 🔮 VG 1320; before S14g-a zerobas differs): `ON ERROR GOTO 100` (RESUME NEXT);
  `OPEN"CAS:D"FOR INPUT AS#1:LINE INPUT#1,A$` (FCH_RDMODE); `SCREEN 2:LINE(0,0)-(40,40),15,B:
  LINE(50,0)-(90,40),15,BF:CIRCLE(128,96),40,15,-1,-5,1.5:SCREEN 0` (GFX_MODE via LINE and the
  spokes, ASPMAJ, ARCF, SNEG/ENEG); `PLAY"C","","E"` (AUDIO_VMASK); `A$=5` then `A$=+` (ERRMARK,
  els_tc_common: ERR 13 then 2, printed); `DELETE 5000` (no such line: ERR 5 on both — R-D2 — the
  tenant RAN and wrote LE_OP); `X=DSKF(0)` (chan_gate's diskless FOPEN_SEL write — ⚠️ UNVERIFIED
  that the VG-8020 answers with a trappable error too; drop it if the two machines disagree before
  the move). Tape: `tape(all) + build_cas_ascii("D","A,B\r\n")`.
* **`s14gb`** (2 B, VG 330) and **`ovwsrc`**: `F=A%+1.5:G#=2!+1/3#:H!=1/3#+2!:FOR I#=1 TO 2.5
  STEP .5:NEXT:PRINT"[W";F;G#;H!;I#"]"` (both widen entries, single and double, LHS and FAC).
* **`s14gc`** (3 B, VG 495), **`ovinpd`** and **`ovprdev`**:
  `ovinpd`: `OPEN"CAS:D"FOR INPUT AS#1:A$=INPUT$(3,#VAL(INPUT$(1))):PRINT"[I";A$;"]"`, key `1` typed,
  tape `tape(all) + build_cas_ascii("D","HELLO\r\n")`
  — 🔮 **DIVERGES on the S14g-b build** (zerobas `Illegal function call`, VG `[IHEL]`), SAME after:
  a behaviour fix with its own row, like `inpoom`. Plus `A$=INPUT$(5,#1)` (the plain loop).
  `ovprdev`: `OPEN"CRT:"FOR OUTPUT AS#2:PRINT#2,"AB","C":CLOSE#2:PRINT"[P";PEEK(&HF864);PEEK(&HF865);"]"`
  — 🔮 SAME `[P 0 0]` (PTRFIL idle between statements on both).
* **`s14gd`** (2 B, VG 330) and **`ovpt`**: `SCREEN 2:PSET(3,4),5:PSET(4,3),9:A=POINT(3,4):
  B=POINT(4,3):C=POINT(VAL("3"),4)*300*200:SCREEN 0:PRINT"[T";A;B;C"]"` — x≠y with different
  colours, so a swap shows; the `*300*200` keeps a leaf family next to POINT for the fallback.
* **`s14g`** (all 15 B, VG 2475) once the four are in: the regression row for S15.
* Measurements, not gates (both machines, scored, then decide): `PRINT PEEK(&HF6A6)` after INPUT /
  LINE INPUT / READ; `PLAY"C","D":PRINT PEEK(&HFB35)`. Today zerobas never writes FLKINP / PRSCNT
  (C-BIOS zero) while the VG-8020 does, so a difference here PRE-EXISTS the move; it changes only
  in value. Record it; a faithful encoding is its own item (S8 precedent: DRWFLG).

Knives (continue at K-WS75; each must first prove it BUILT — non-empty ROM, hash ≠ the slice's):
* K-WS75: S14g-a's 11 names back at their window addresses, guards off → `s14ga` diverges. HIT 🔮
* K-WS76 (negative control, BUFTX): GFX_ARCF := STRSCR+1 (MKI$'s staging), guards off; row
  `ovcirc` = `CIRCLE(128,96),40,15,1,2+CVI(MKI$(0))` — the end-angle eval runs MKI$ after ARCF:=1,
  writes 0 there → a full circle instead of an arc → diverges. HIT 🔮 (proves the row SEES a
  BUF overlap; the shipped placement is past STRSCR+8).
* K-WS77 (negative control, ERRMARK): ERRMARK := FAC ($F7F6) → `A$=5` reads FAC's nonzero lead
  byte as the landmark → ERR 2 instead of 13 → `s14ga` diverges. HIT 🔮
* K-WS78 (negative control, AUDIO_VMASK): AUDIO_VMASK := STRSCR+0 → `PLAY"C",LEFT$(MKI$(0),0)+"D"`
  (MKI$ writes STRSCR+0 = 2 between the voices) drops voice 0 → `PRINT PEEK(&HFB3F)` (MUSICF)
  differs. HIT 🔮
* K-WS79 (negative control, FCH_RDMODE): FCH_RDMODE := STRSCR+0 — `read_into_strscr` zeroes it as
  the quote state (files.asm:1424-1431) → `LINE INPUT#1` of "A,B" stops at the comma → `s14ga`
  (prints A$) diverges. HIT 🔮
* K-WS80 (S14g-b): `widen_lhsframe_to` loads FACTYP instead of LHS_FACTYP → `H!=1/3#+2!` / `2!+1/3#`
  unpack the wrong mantissa length → `ovwsrc` diverges. HIT 🔮
* K-WS81 (S14g-b): the two pad counts swapped (`ld b,1` ↔ `ld b,9`) → every single-precision widen
  zero-pads wrongly → `ovwsrc` diverges. HIT 🔮
* K-WS82 (S14g-c): strvar.asm restored from HEAD (the RAM counter), everything else kept →
  `ovinpd` diverges. HIT 🔮
* K-WS83 (S14g-c, the P1 hazard measured): PRDEV := $F865 (PTRFIL+1), save.asm's one-store back →
  `ovprdev` reads `[P 0 2]` vs `[P 0 0]` → diverges. HIT 🔮 — this is the evidence for BUF over P1.
* K-WS84 (S14g-c, negative control): PRDEV := STRSCR+1, guard off → `PRINT#2,MKI$(0)+"X"` on CRT:
  rewrites PRDEV to 0 mid-statement → the disk sink on a CRT: channel → diverges. HIT 🔮
* K-WS85 (S14g-d): main's pair replaced by `ld d,c / nop` (D = x, E stays y: the coordinates
  swapped on the way in) → `ovpt` reads (4,3) for (3,4) → diverges. HIT 🔮
* (opt.) K-WS86 (LE_OP in C): sub/lineedit.asm `ld a,b` instead of `ld a,c` → `DELETE 5000` runs
  another op → `s14ga`'s ERR line diverges. HIT 🔮

---------------------------------------------------------------------------------------------------

## 5. What this does NOT prove (blind spots, stated)

* The idle-host census is a grep of names and literals over the four syms, C-BIOS sources and the
  repack patches; no RUNTIME fill row was run for PRSCNT / KANAST / KANAMD / PTRFIL / FLKINP
  (S10.0's instrument would; S11 did it only for $F71C-$F74C). The VG-8020's own values in them
  are unmeasured (only matters for PEEK fidelity, §4's measurements).
* S14g-a's BUFTX proof inherits S14d's "no expression writes BUF past STRSCR+8" — a grep + rows,
  never a reach set (s14_plan §2.6 asked for one).
* "BC/DE/HL pass through CALSLT" is read from C-BIOS src/slot.asm; the repack patches touch no slot
  code (by file name: ctrl-keys, eu-drop-*, home-key, ins-del-keys, key-trap-hook, linttb-scroll,
  vdp-reg7) — ⚠️ the patch bodies were not read.
* Byte counts are hand counts from the listing-free source (cross-checked only where the sym gives
  label distances: sid_read→sidr_lp 17 B, sidr_lp→sidr_done 22 B match). `make basic-reloc` and
  `tools/pin_plan.py --check` are the reading.
* The forward-reference question for `GFX_MODE equ BUFTX + 10` (pasmo, ram_map.py, ws_shift.py) —
  sidestepped with literals + a guard.
* `ovinpd`'s ERR 5 prediction is reasoned from the code, not run; `X=DSKF(0)`'s VG answer is
  unmeasured.
* Nothing here re-checks the DISK machine's own use of the new homes beyond disk.sym and a literal
  grep of disk/ — S15 checklist item 8's four acceptance gates are the check.

## 6. Findings in passing (not S14g's to fix)

1. **Nested INPUT$ in INPUT$'s channel argument raises ERR 5** (INDLR_N shared) — fixed as a side
   effect of S14g-c; `ovinpd` is its row.
2. **INPUT$ on a DISK channel inside an INPUT # statement leaves FCH_RDMODE = 2** (strvar.asm:543 is
   inside an expression): `INPUT #1,A$(LEN(INPUT$(1,#2))),B$` reads B$ raw — commas kept, CR-LF as
   data — where the field rule should apply. Disk-only (the CAS: arm never sets 2). 🔮 unmeasured;
   pre-existing, unchanged by the move.
3. **The S14f hazard on GFX_MODE was a false alarm** (§2.2) — the TODO paragraph that says "NOT moved,
   by a found hazard" should be inverted, not deleted, when S14g-a lands.
4. **The reference's CIRCLE cells CLINEF $F935 / CSCLXY $F941 are occupied by S7's SUB_INT_RAM
   trampoline** — the same-job homes exist; moving the trampoline would be its own slice.
5. **s14_plan.md §6's refused-table rows for ERRMARK (FLKINP) and DISKOP_OP (NLONLY) are stale** —
   both hosts were taken (rule-first FCH_RDMODE; S14f's VARTYPE).
6. **sysvars.inc:677 still says DISKOP_OP/AUDIO_VMASK live at $E9FB** — two moves out of date.
7. **`widen_fac_to`'s `ld de,(WSRC)` at wsrc_go is a dead reload** (DE already holds it) — 4 B, folded
   into S14g-b as optional.
