; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; fat.asm — loader-side FAT12 read+write engine driving the STANDARD $4010 DSKIO
; sector interface of whatever disk ROM occupies the slot.
; ===========================================================================
; This is the Phase-1.5 HOST side: zerobas-BASIC's disk loader verbs reach files
; through the disk ROM's standard DSKIO ($4010) physical-sector entry and own the
; FAT12 / directory logic themselves, instead of calling zerobas-disk's PRIVATE
; bdos_entry (SYSTEM vector $F37D). Driving the standard sector interface makes the
; loader disk-ROM-INDEPENDENT: any standard MSX1 disk ROM (our own, or a foreign
; one such as the National CF-3300) services the same loader unchanged.
;
; 🔴 THAT INDEPENDENCE IS A TRUE DESCRIPTION AND NO LONGER A JUSTIFICATION
; (corrected 2026-09-19). This header used to be cited across the tree as the
; reason the FAT engine must live in BASIC -- "the NECESSARY PRICE of the
; universal sector interface". Joost, 2026-09-15: "in practice I'd think any
; external cartridge providing a disk also provides disk basic", and earlier,
; "this seems a theoretical situation". With a foreign cartridge present it is
; THAT cartridge's Disk BASIC which claims the hooks and runs, whichever ROM our
; FAT sits in -- ordinary MSX behaviour, not a loss. So interop with a
; DSKIO-only disk ROM describes hardware that does not exist, and it is NOT a
; reason to keep this engine here. See spec-diskbasic-hook-rearchitecture.md
; Phase 4 and spec-diskcode-eviction.md 6.7.
; 🎯 WHAT DOES STILL BEAR ON IT is the charter, and only for our own primary
; deployment where our disk ROM is the one present: we reimplement MSX1 BASIC,
; so we implement its disk verbs. The FAT is in BASIC because we wrote the
; verbs, not because of interop.
;
; PORTED from disk/disk.asm (this project's OWN clean-room FAT12 code — porting our
; own code carries its provenance forward, not a forbidden disassembly). The only
; substantive change vs. the disk-ROM-side original is the physical-sector
; primitive: there `read_sector`/`write_sector` tail-called the LOCAL `dskio`
; (ROM offset +$10); in the port they CALSLT the in-slot disk ROM's DSKIO at
; $4010 across slots (the slot id is the INIT-scan's DISKSLOT capture).
; ⚠️ NEITHER PRIMITIVE IS IN THIS FILE ANY MORE — the eviction moved the whole
; primitive/sector layer to the page-1 tenant, so the CALSLT bodies now live in
; basic/fat-prim-body.inc (read_sector/write_sector) and sub/format.asm (its own
; private write path); D-SEEDHOLE2 removed the last two callerless shims that
; still carried those names here. The port's provenance below is unchanged --
; only the address of the code it describes is. Everything above the
; sector primitive — BPB parse, cluster-chain walk, 8.3 directory search, FAT12
; nibble pack/unpack, free-cluster allocation, multi-FAT sync, directory
; create/update — is byte-for-byte the same algorithm as disk.asm.
;
; CLEAN-ROOM: every constant/address/algorithm traces to an allowed source, cited
; inline (same provenance as disk/disk.asm, carried over):
;   * DSKIO register convention + $4010 offset — MSX2 Technical Handbook, disk-ROM
;     interface (§5); cross-checked by black-box openMSX observation of the real
;     National CF-3300 (disk/docs/expansion-protocol.md §3). CY = direction
;     (clear = read, set = write).
;   * CALSLT ($001C) inter-slot call + slot-id byte format — MSX2 TH / MSX Assembly
;     Page BIOS call list; CALSLT passes the caller's AF (hence the direction CY)
;     through to the target and returns the target's AF (hence the error CY) — this
;     is exactly how C-BIOS's clprim restores AF around `jp (ix)` (allowed C-BIOS
;     source, observed not transcribed). State is kept in RAM across the call
;     because CALSLT clobbers AF/BC/DE/HL/IX/IY.
;   * BPB / FAT / directory layout — Microsoft FAT filesystem specification; ECMA-107
;     geometry. Assumes 512-byte sectors (validated at mount).
;   * On-disk BSAVE ($FE) / tokenised-BASIC ($FF) markers — MSX-BASIC file formats
;     (public MSX-BASIC file-format reference), already in sysvars.inc.
; No reference BIOS / disk-ROM / MSX-BASIC / MSX-DOS disassembly was read.
; See basic/PROVENANCE.md §disk DSKIO host engine.
;
; REPACK EVICTION, PHASE 1 (docs/spec-evict-diskfile-cluster.md §11, funding
; D-F2-2 A2+VPEEK): the FAT12 PRIMITIVE/SECTOR layer below (dskio_calslt
; through fat_dir_update, PLUS fat_delete further down) moves to a sub-ROM
; PAGE-1 tenant (sub/fatprim.asm fatprim_tenant, SUBROM_IDX_FATPRIM) — a
; single selector-dispatched entry covering all 15 marshalled primitives
; (DISKOP_OP picks the routine; a subrom_call only reaches one tenant entry).
; The BYTE-GRANULAR fat_io_* cursor is NOT assembled in main at all any more:
; its WRITE half left with S10 increment 3 (D-ASAVEDOUT), its READ half
; (fat_io_open/fat_io_getbyte) with S10.C (2026-10-15), when OPEN FOR INPUT
; moved to disk.rom. (It "could not move yet" because ARL_GETBYTE reached it
; per byte -- spec §11; that vector now points at a per-byte HOOK crossing,
; basic/input.asm din_call, the reference's own $FE8A.) The shared bodies live in
; basic/fat-prim-body.inc (dskio_calslt..fat_dir_update) and
; basic/fat-delete-body.inc (fat_delete, kept separate only because it sits
; AFTER the resident cursor in this file — see that file's header).
; (BYTE-IDENTICAL to the pre-eviction build), the repack build emits resident
; SHIMS under the SAME names instead (this file's `IF the repack build`
; branches below), keeping every existing call site (`call fat_mount`,
; `call fat_find`, ...) unchanged. ⚠️ "Every existing call site" was the design
; intent and is NOT what the tree grew into: later evictions moved whole CALLERS
; across too, and five shims outlived their last main call site -- see the carve
; note above the shims. See basic/PROVENANCE.md §FAT12 primitive
; eviction.

; --- repack: resident shims replacing the FAT12 primitive/sector layer -----
; docs/spec-evict-diskfile-cluster.md §11. Every routine below keeps its
; ORIGINAL name and calling convention (register-input contract unchanged);
; only the BODY is now a dispatch to the sub-ROM PAGE-1 tenant fatprim_tenant
; (sub/fatprim.asm, SUBROM_IDX_FATPRIM), selected by a DISKOP_OP byte (RAM),
; since one subrom_call only reaches ONE tenant entry, not 15. Cy cannot ride
; back through subrom_call/CALSLT (its own `or a` always clears it,
; sub/format.asm's rule) -- so every primitive's disposition + HL/A outputs
; are marshalled through the DISKOP result block (basic/sysvars.inc),
; reloaded here uniformly (safe: DSKIO/CALSLT already clobbers HL at every
; existing call site, so no caller relies on HL surviving a primitive call
; unmarshalled). The three primitives whose REAL ABI needs something other
; than the uniform Cy+HL+A convention get bespoke treatment:
; fat_alloc_cluster (HL is a genuine, caller-read output -- covered by the
; uniform reload), name_cmp (Z, not Cy -- its own shim below), and
; fat_count_free (DE, not Cy -- rides back over FAT_WRTMP2 instead of a new
; RAM cell, see that cell's sysvars.inc comment).

; --- the UNIFORM shims (nine contiguous + fat_delete) -- ALL GONE -----------
; 🗑️ 2026-10-19: the last two (fat_mount / fat_find) left with AUTOEXEC.BAS's
; probe and NAME's lookup (note below the block); this header is the layer's
; history. fatprim_bounce stays for its one non-shim caller (oo_hdr_tail).
; Every one of these was, until 2026-07-27, an independent 34-byte copy of the
; SAME body: load a selector, bounce to the tenant, marshal Cy+HL+A back. Only
; the DISKOP_SEL_* immediate differed. Thirteen copies (the twelve there were
; then, plus fat_delete further down) cost 442 B of main page 1 to say one
; thing thirteen times, on a build with 8 B free.
;
; Collapsed to `ld a,<selector>` + a jump into ONE shared body (fatprim_bounce),
; which is what a shim layer should have looked like from the start. The
; register/flag contract is UNCHANGED and this is a pure dedup — see
; fatprim_bounce for the one substantive difference (a branchless tail that is
; flag-equivalent, not merely similar). Cost per shim: 4 B, was 34 B.
;
; ORDER MATTERS ONLY FOR REACH: the contiguous stubs sit directly above
; fatprim_bounce so every `jr` lands within range. fat_delete sits after the
; resident fat_io_* cursor (~324 B away) and therefore uses `jp`. Deleting a
; stub only SHORTENS that distance, so reach survives a carve a fortiori.
;
; ⚠️ THE COUNT IS NOT STABLE, AND EVERY MOVE HAS BEEN IN BOTH DIRECTIONS: D-FCH
; added fch_restage/fch_flush_active (14 contiguous), and D-SEEDHOLE2
; (2026-08-22) removed five that no main caller had reached for weeks —
; read_sector, write_sector, fat_read_fat_sector, fat_alloc_cluster,
; fat_write_fat_entry, 20 B of page 1. A shim here is worth its 4 B only while
; a MAIN caller exists; the sub-ROM tenant reaches the primitive directly, not
; through this layer.
;
; 🔴 HOW THEY BECAME ORPHANS, because the shape will recur on the next eviction:
; an eviction moves a CALLER into the sub-ROM but leaves its main-side shim
; standing, and the evicted body's own `call <name>` then reads — to a seed
; scrape keyed on NAMES — as a live external reference to the main label of that
; name, when it in fact resolves sub-locally. `d3885b3` (fat_rand_* -> sub-ROM)
; orphaned four of the five and `0cbf495` (the FILES walk -> sub-ROM) the fifth;
; both were invisible to `make deadcode` until the seed set was rebuilt on
; sub/basic-resident-abi.inc. docs/spec-deadcode-gate.md §11.


; (D-ROMSIZE step 1, 2026-10-19: the fat_mount / fat_find shims are gone too --
; 8 B, and with them the last uniform shim. Their two callers left main the same
; day: autoexec_run's presence probe is disk.rom's hk_auto, and NAME's handler
; (disk.rom hk_name), which called BACK into these two through the resident ABI
; (main_fat_mount / main_fat_find), uses that ROM's own fat_mount / fat_find.
; Both ran the sub-ROM tenant's rows 2 / 3, which have no sender now; they stay
; in the table (sub/fatprim.asm): the numbering is published.
; fatprim_bounce, below, keeps one caller: OPEN's header stamp (files.asm
; oo_hdr_tail, row 23).)

; (S10.C, 2026-10-15: the fat_open and fat_read_file_sector shims are gone --
; 8 B. Their only main callers were fat_io_open / fat_io_getbyte, main's resident
; copy of basic/fatio-body.inc, which left with OPEN FOR INPUT (hk_finp in
; disk.rom). Selectors 2/3 and their tenant rows stay: the numbering is published.)

; (D-FCBSHAPE S0, 2026-09-29: the fch_restage / fch_flush_active shims are gone.
; Their only callers were fch_load_ctx / fch_save_active, whose bodies moved into
; the tenant, where fat_restage_channel / fat_detach_channel are called locally.
; Selectors 19/20 and their tenant rows stay: the numbering is published.)

; (S10 increment 3, D-ASAVEDOUT, 2026-10-08: the fat_flush_data_sector,
; fat_io_create and fat_io_close stubs are gone -- 10 B of page 1. Their last
; main callers were pchar's SAVE ,A arm (fat_io_putbyte, whose flush was the
; first) and sv-diskwr.inc's disk_write_begin / _end; SAVE ,A is disk.rom's
; now. Selectors 23/24 and their tenant rows stay: the numbering is published.
; fat_io_close was the block's last stub and fell through into fatprim_bounce;
; fat_read_file_sector, above, already ends `jr fatprim_bounce`.)

; (SBH-3, 2026-10-03: the fat_dir_create / fat_dir_update shims are gone. Their
; only main callers were the fat_io_create / fat_io_close bodies, which now
; assemble only under SUB_BUILD / DISK_BUILD -- `make deadcode` reported both,
; 0x64af ~4 B and 0x64b3 ~2 B, with the bodies gated and the shims still in.
; Selectors 12/13 and their tenant rows stay: the numbering is published. The
; field.asm frp_overlay tail-call the old comment here named had already moved
; into the tenant with the fat_rand_* engine.)

; fatprim_bounce — the ONE body the thirteen uniform shims shared (none is left
; since 2026-10-19; OPEN's header stamp, files.asm oo_hdr_tail, calls it direct).
;   in:  A = DISKOP_SEL_* selector; the primitive's own register inputs are
;        already marshalled in the DISKOP block by the caller's contract.
;   out: exactly the pre-collapse contract — Cy=1 + HL/A reloaded on a tenant
;        error OR a missing sub-ROM, Cy=0 + HL/A reloaded on success.
;
; The tail is branchless where the originals branched, and that is the only
; instruction-level change. It is flag-equivalent, not approximately so:
;   * `or a` clears Cy and sets Z iff DISKOP_STATUS == 0 (success);
;   * `ld hl,(nn)` and `ld a,(nn)` DO NOT AFFECT FLAGS, so Z/Cy survive both
;     reloads — which is what lets the reload be shared by both dispositions
;     instead of duplicated into an error tail;
;   * `ret z` therefore returns success with Cy already clear (exactly what the
;     old `jr nz,<err>` fallthrough did), and the error path falls into `scf`.
; Reloading HL/A on BOTH paths is not new behaviour: every old shim's error tail
; did the same two loads before its `scf`.
fatprim_bounce:
                call    fatprim_op
                ret     c                   ; sub-ROM absent -> Cy=1
                ld      a,(DISKOP_STATUS)
                or      a                   ; Z iff success; ALSO clears Cy
                ld      hl,(DISKOP_HL)      ; flag-transparent
                ld      a,(DISKOP_A)        ; flag-transparent
                ret     z                   ; success: Cy clear from `or a`
                scf
                ret

; 🎯 THE `name_cmp` SHIM IS GONE, AND ITS DEATH IS A CARVE THIS SLICE DID NOT
; PLAN FOR (D-LFILES, docs/spec-basic-lfiles.md §6). It marshalled a Z result
; through DISKOP_STATUS for exactly ONE main-side caller — do_files's filespec
; filter — and D-LFILES moved that walk into the dirverb tenant, where `name_cmp`
; resolves to the sub-local primitive BODY instead. Main's every other user of
; the pattern match reaches it inside fat_find, which is itself a tenant call.
;
; The dead-code gate is what would have said so: leaving the shim here fails
; `make basic-reloc` with an unreachable span, which is the difference between a
; carve and a leak. DISKOP_SEL_NAME_CMP and the tenant's own dispatch arm
; (sub/fatprim.asm) are KEPT — the selector namespace is a published numbering and
; renumbering it to reclaim six sub-ROM bytes would be a drift risk against a wall
; that is not the binding one.






; (D-DSKFLOCAL, 2026-09-29: main's fat_count_free stub is gone -- its only
; caller was disk.rom's hk_dskf, which now runs the body locally.)




; ===========================================================================
; Byte-stream I/O layer — the loader-facing API the disk verbs call. This is the
; HOST analogue of disk.asm's bdos layer, but byte-granular instead of the FCB's
; 128-byte record framing: the verbs (BLOAD / LOAD / RUN / SAVE / BSAVE) stream
; bytes, and this layer maps them onto whole 512-byte FAT sectors. No FCB and no
; 128-byte zero-padding — exact byte counts are tracked, so a file's on-disk size
; is its true length (SAVE/BSAVE produce byte-exact images that round-trip).
; ===========================================================================

; 🗑️ S10.C (D-ROMSIZE, 2026-10-15): basic/fatio-body.inc IS NO LONGER INCLUDED
; HERE -- 111 B of main page 1. Its last main caller was OPEN FOR INPUT
; (files.asm `call fat_io_open`), and an INPUT channel is disk.rom's FCB now
; (hk_finp / hk_chin, disk/fat.asm). The ARL_GETBYTE default and the two
; restores that named fat_io_getbyte were dead stores (files.asm init_filechan).
; The body stayed shared by sub/bload.asm (BLOAD's tenant) and disk/kernel.asm
; (LOAD / MERGE) until 2026-10-19, when BLOAD's disk load moved to disk.rom
; (hk_dpbload) too: disk/kernel.asm is its one home now.

    IF BASICINT_PINS
; 📌 REFILL FOR D-BASICINT'S $6CF3 PIN (S10.C, 2026-10-15). S10.C took 128 B out
; of main page 1 AHEAD of the pinned $6CF3 -- the 111 B fatio-body.inc above, the
; fat_open / fat_read_file_sector shims (8), files.asm's df_or_loaderr (9) and
; OPEN's INPUT arm (1), cload.asm's restore (6), less the 7 B expr.asm's eof_dev
; grew by inlining the tape EOF crossing -- and every byte removed ahead of a pin
; grows its `ds` pad (files.asm `ds $6CF3 - $`). Joost: no growing holes. So three
; self-contained routines from PAST every pin (basic/program.asm; entered only by
; call / jp / the statement table, no `jr` across their edges -- tools/pin_plan.py's
; chunk list) moved HERE, at the hole itself, which also keeps every `jr` that
; spans the hole at its old reach: ex_for (102 B), cont_record (19), ctl_put (7).
; program.asm's copies are the ELSE arms (a switch-off build is a different
; machine with no pinned addresses to keep, [[a-scaffolded-build-is-a-different-machine]]).
; Their stories stay at the original sites.
; 🧮 D-LETNEWFIRST (2026-10-19): ex_for is 110 B now (+8: it creates the loop
; variable before the start expression). The pad does not move: vars.asm's `for_set`
; (-8) and ex_let_str (+1 -1, interp.asm) sit in the same stretch ahead of $6CF3,
; so its net is zero and `pin_plan.py --check` reads what it read before.
ex_for:
                inc     hl                  ; past the FOR token
                call    req_letter          ; D-NGRAM: FOR needs a loop variable
                call    for_name            ; FOR_CUR[0..2] = the key; A = the type
                cp      DEFTBL_STR          ; `FOR A$=` -- and `DEFSTR A` / `FOR AB=` --
                jp      z,type_mismatch_error ; are ERR 13, not ERR 2 (rows f.str and
                                            ; f.defstr, both references). The test is on
                                            ; the RESOLVED type, not on the `$` char,
                                            ; because f.defstr says the rule is.
                push    hl                  ; [cursor]
                call    var_alloc_or_find   ; D-LETNEWFIRST: A = the type, BC = the key
                                            ; (for_name's out) -> HL = the variable's
                                            ; entry, created zero-valued if new, BEFORE
                                            ; the start expression -- FOR's ONE lookup
                jp      nc,fp_runtime_error ; Out of memory, FPERR already set
                ex      (sp),hl             ; HL = cursor, [entry] across '=' + eval
                call    skip_eq             ; '=' -> $EF
                jp      nz,stmt_error
                call    inc_eval            ; DE = initial value, HL advanced
                ex      (sp),hl             ; HL = entry, [cursor]
                call    for_set_at          ; var := initial value, through the entry
                pop     hl
                call    skip_spaces
                cp      TO_TOKEN           ; TO -> $D9
                jp      nz,stmt_error
                call    inc_eval            ; the limit, as a factor leaves it
                push    hl
                ld      hl,FOR_LIM
                call    slot_store          ; D-FORFLOAT: typed, not an int16 tail
                pop     hl
                call    set_factyp2         ; the default STEP below is an int16 1
                call    skip_spaces
                ; D-NXARY: the default is loaded FIRST and eval overwrites it, so the
                ; two arms stop needing a join (-2 B). `ld de,nn` touches no flag, so
                ; the CP below still reads skip_spaces' char. Guarded in both
                ; directions by rows that already exist: f.step (forvar, `STEP -3` ->
                ; `-2 `) and m.step (nxlist, a negative step inside a list) take the
                ; STEP arm, every other loop row takes the default.
                ld      de,1                ; default step = +1
                cp      STEP_TOKEN         ; STEP -> $DC (optional)
                jr      nz,ef_havestep
                call    inc_eval            ; DE = step
ef_havestep:
                push    hl
                ld      hl,FOR_STEP
                call    slot_store          ; the step, typed
                pop     hl
                ld      (FOR_BODY),hl       ; the resume ptr (loop body)
                push    hl                  ; D-NXARY: and it rides the stack to the
                                            ; tail below instead of being re-loaded --
                                            ; ldir does not touch the stack (-1 B)
                ld      de,(CURLINE)
                ld      (FOR_LINE),de       ; CURLINE
                ; D-CTLPOOL: the FOR_STK_END bound test is gone with the array.
                ; ⚠️ FSP IS NOT TOUCHED HERE, and that is the invariant the whole
                ; NEXT walk rests on: the FOR run is [CSP, FSP), so lowering the
                ; frontier IS the push and the run stays contiguous -- nothing but
                ; a FOR frame is ever pushed without also moving FSP.
                ; ⚠️ Row a.dep8 (8 nested loops) is still the row that reaches the
                ; full-pool arm, and K-NA4 is still its knife.
                ld      hl,FOR_FRAME
                call    ctl_alloc
                jp      c,ef_over           ; collided with the variable area
                ex      de,hl               ; DE = the frame base (ldir destination)
                ld      hl,FOR_CUR          ; push the FOR_FRAME-byte frame
                ld      bc,FOR_FRAME
                ldir
                jp      pop_exec            ; HL = loop body -> run it
cont_record:
                ld      a,(DIRECTF)
                or      a
                ret     nz                  ; direct mode: leave the resume point alone
                ld      (CONTPTR),hl        ; resume token pointer (0 = fresh-line entry)
                ld      hl,(CURLINE)
                ld      (CONTLINE),hl       ; line to resume in (link-field addr)
                inc     a                   ; A is still 0 -> 1
                ld      (CONTVALID),a       ; a CONT resume point is now live
                ret
ctl_put:
                ld      a,l
                ld      (de),a
                inc     de
                ld      a,h
                ld      (de),a
                inc     de
                ret
    ENDIF


                include "basic/fatiocreate-body.inc"   ; fat_io_create: body under SUB_BUILD/DISK_BUILD only -- and only disk.rom includes it since 2026-10-19 (BSAVE left the sub-ROM); nothing assembles here

; 🔴 S10.B increment 2 (2026-10-06): `fat_io_append` (main's APPEND open -- the
; chain walk, the Ctrl-Z resume, the refusal of a missing file) IS GONE. APPEND is
; disk.rom's hk_fapp now, on the same 256 B record writer as OUTPUT; its rules
; moved with it (disk/kernel.asm). The fatprim tenant row 18 it called
; (sub/fiawalk.asm) keeps its table slot: the rows are numbered. (2026-10-19: the
; row is `jp fp_stash_ok` and sub/fiawalk.asm + basic/fiawalked-body.inc are
; deleted -- nothing had sent row 18 since this append left.)


                include "basic/fatiow-body.inc"        ; fat_io_putbyte/fwr_bytes_inc/fat_io_close: SUB_BUILD/DISK_BUILD only since D-ASAVEDOUT -- nothing assembles here; disk.rom its only home since 2026-10-19

; fat_delete — RESIDENT SHIM DELETED FROM THIS BUILD (D-ENDIFWALK, 5 B).
; It was the thirteenth uniform shim (`ld a,DISKOP_SEL_FAT_DELETE / jp
; fatprim_bounce`) and it had NO caller in main. The twelve above it are called by
; name from basic/files.asm (`call fat_io_open`, `call fat_rand_open`, …); this one
; is not, because main's KILL does not use the primitive layer at all — files.asm
; goes `ld a,DISKOP_SEL_KILL / call subrom_call`, and its own comment says the
; tenant is "calling fat_delete sub-locally". The shim outlived that eviction.
; ⚠️ Checked rather than assumed, because a resident shim is exactly the shape that
; can be reached by ADDRESS rather than by name: `fat_delete` is in no resident-ABI
; list and no dispatch table, and basic/main.asm's whole closure contained ONE
; mention of the name — this definition. The sub build keeps its own body
; (basic/fat-delete-body.inc, included only by sub/) and both its callers.

; --- fatprim_op: run fatprim-tenant op A ------------------------------------
; 💰 D-PAIRCARVE (2026-09-11): the `ld (DISKOP_OP),a` / `ld ix,...FATPRIM` /
; `call subrom_call` triple stood at THREE sites above, 10 B each against 3 for a
; call: 3 x 7 saved less this 10-byte body = 11 B. Returns what subrom_call
; returns: CF=1 iff the sub-ROM is absent. Clobbers IX, as subrom_call does.
fatprim_op:
                ld      (DISKOP_OP),a
                call    sr_inl1             ; D-STUBINL
                db      low (SUBROM_ENTRY_BASE_P1 + 3*SUBROM_IDX_FATPRIM)
                ret
