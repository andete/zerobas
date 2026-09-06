; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; randio-body.inc — the fat_rand_* random-access record engine (shared body).
;
; docs/spec-eviction-g4-space.md §3 (carve #1). This is the ON-DISK RECORD I/O
; layer BELOW FIELD/LSET/RSET/GET/PUT's parse heads: fat_rand_open (the RANDOM
; open), fat_rand_get/fat_rand_put (record read/write) + their private helpers
; (frnd_next/frnd_locate/frnd_fill_fwbuf/frnd_calc/frnd_update_size/
; load_reclen/mul_reclen). Composes basic/fat.asm's FAT12 primitives (fat_mount/
; fat_find/fat_dir_create/fat_alloc_cluster/fat_write_fat_entry/
; fat_read_fat_sector/read_sector/write_sector/fat_dir_update) WITHOUT modifying
; them -- exactly the same "co-located after fatprim, calls resolve sub-locally"
; mechanism the landed `dirverb` eviction already uses (sub/dirverb.asm).
;
; Included from TWO homes, the fat-prim-body.inc / format-body.inc pattern:
;   * (retired) the lean 16 KB cart, inline at this
;     file's ORIGINAL position (right after LSET/RSET/fld_lookup, before
;     "GET [#]f [, recno] / PUT [#]f [, recno]") -- BYTE-IDENTICAL to the
;     pre-eviction build (this file is a pure relocation of that exact code,
;     nothing added/removed/reordered).
;   * sub-ROM PAGE-1 tenant (sub/randio.asm, repack): fatprim.asm's fp_table
;     gains three new selector rows (DISKOP_SEL_RAND_OPEN/GET/PUT = 15/16/17)
;     -> t_fat_rand_open/get/put wrappers (sub/fatprim.asm) that `call` the
;     bodies below and marshal {HL,A,STATUS} via fp_stash_ok/fp_stash_err
;     (Cy cannot ride back through subrom_call/CALSLT). Every FAT12 primitive
;     call inside these bodies (fat_mount, fat_find, fat_dir_create,
;     fat_alloc_cluster, fat_write_fat_entry, fat_read_fat_sector, read_sector,
;     write_sector, fat_dir_update) resolves to the fatprim TENANT's own
;     sub-local copies (basic/fat-prim-body.inc, included by sub/fatprim.asm,
;     itself included BEFORE sub/randio.asm in sub/sub.asm) -- no rewiring, no
;     nested subrom_call/CALSLT. Channel/record state (DISK_FCB_NAME, FWR_*,
;     GP_RECNO, FSECTOR_BUF) is page-3 RAM, visible from both sides -- nothing
;     new to marshal. fld_fill_record (basic/fld-fill-body.inc, included right
;     before this file in sub/randio.asm) is the one other sub-local callee.
;
; NOT PART OF THIS CARVE (stays main-ROM-resident, both builds): FIELD's own
; parse head (ex_field/fld_add), LSET/RSET (ex_lset/ex_rset/lrset_store),
; fld_lookup (str_eval's variable-read hook), and GET/PUT's own parse head
; (ex_get/ex_put/gp_common) -- all of them call `fch_select`/`eval`/
; `raise_error`/`load_error`, which are main-ROM page-1 resident and
; UNREACHABLE from a page-1 sub-ROM tenant (the one straddle the spec's survey
; flagged, verified to sit entirely on the RESIDENT side of this carve
; boundary -- nothing below calls any of those four).
;
; Clean-room: our own code, extracted verbatim from basic/field.asm (see that
; file's header for the full FIELD/GET/PUT provenance -- public MSX-BASIC
; language reference + black-box CF-3300, zerobas' own side-table design).

; ===========================================================================
; Random-record on-disk I/O (Phase 2c slice 2): GET / PUT + the RANDOM open.
;
; Composes the fat.asm engine WITHOUT modifying it. Buffer discipline: the live
; record stays in FSECTOR_BUF; FWBUF is reused (sequentially) for FAT metadata,
; the data sector, and the dir update. The chain walk goes through frnd_next (which
; reads the FAT into FWBUF via fat_read_fat_sector) rather than fat_next_cluster
; (which reads it into FSECTOR_BUF and would destroy the record). Geometry comes
; from the mount done at RANDOM open and persists in the shared FAT_* vars, so
; GET/PUT never re-mount (which would read the boot sector into FSECTOR_BUF).
; ===========================================================================

; fat_rand_open — open or create the file in DISK_FCB_NAME as a RANDOM channel.
; Replaces slice 1's in-RAM-only stub. Mounts, finds (or creates) the file, seeds
; the per-channel state (FWR_FIRST = first cluster, FWR_BYTES = current size,
; FWR_DIRSEC/OFF = dir entry), and fills the record buffer with spaces.
;   out: Cy = 0 ok; Cy = 1 mount / dir-full / I/O error.
fat_rand_open:
                call    fat_mount
                ret     c
                ld      hl,DISK_FCB_NAME
                call    fat_find
                jr      c,fro_create
                ; existing file: fat_find set FAT_FIRSTCLUS/FILESIZE + FWR_DIRSEC/OFF.
                ld      hl,(FAT_FIRSTCLUS)
                ld      (FWR_FIRST),hl
                ld      hl,(FAT_FILESIZE)
                ld      (FWR_BYTES),hl
                ld      hl,(FAT_FILESIZE+2)
                ld      (FWR_BYTES+2),hl
                jr      fro_fill
fro_create:
                ld      hl,DISK_FCB_NAME
                call    fat_dir_create      ; empty entry; sets FWR_DIRSEC/OFF
                ret     c
                ld      hl,0
                ld      (FWR_FIRST),hl
                ld      (FWR_BYTES),hl
                ld      (FWR_BYTES+2),hl
                ; D-LOF §4b: the LOF field too. The FOUND arm above gets it from
                ; fat_find; this arm is the RANDOM half of the same create-path
                ; hole fat_io_create had, and it is why `OPEN "ZQ.DAT" AS #1 :
                ; PRINT LOF(1)` read a stale size. Sub-only body -- 0 main bytes.
                ld      (FAT_FILESIZE),hl
                ld      (FAT_FILESIZE+2),hl
fro_fill:
                call    fld_fill_record     ; record buffer = spaces
                or      a                   ; Cy = 0 success
                ret

; frnd_next — follow the FAT12 chain one link, reading the FAT into FWBUF (so the
; record in FSECTOR_BUF is preserved). Mirror of fat.asm's fat_next_cluster but over
; FWBUF, built on fat_read_fat_sector. in: HL = cluster; out: HL = next cluster
; (>= $0FF8 = end-of-chain); Cy = 1 on I/O error. Clobbers A,BC,DE,HL.
frnd_next:
                call    fat_read_fat_sector ; FWBUF = FAT sector; BYTEIDX/PARITY/FATSEC set
                ret     c
                ld      hl,(FAT_BYTEIDX)
                ld      de,FWBUF
                add     hl,de
                ld      a,(hl)
                ld      (FAT_B0),a          ; low byte
                ld      hl,(FAT_BYTEIDX)
                ld      de,511
                or      a
                sbc     hl,de
                jr      z,frnd_straddle     ; entry straddles into the next FAT sector
                ld      hl,(FAT_BYTEIDX)
                ld      de,FWBUF+1
                add     hl,de
                ld      a,(hl)
                jr      frnd_combine
frnd_straddle:
                ld      hl,(FAT_FATSEC)
                inc     hl
                ex      de,hl
                ld      hl,FWBUF
                call    read_sector
                ret     c
                ld      a,(FWBUF)
frnd_combine:
                ld      (FAT_B1),a          ; high byte
                ld      a,(FAT_PARITY)
                or      a
                jr      nz,frnd_odd
                ld      a,(FAT_B1)
                and     $0F
                ld      h,a
                ld      a,(FAT_B0)
                ld      l,a
                or      a                   ; Cy = 0
                ret
frnd_odd:
                ld      a,(FAT_B1)
                ld      l,a
                ld      h,0
                add     hl,hl
                add     hl,hl
                add     hl,hl
                add     hl,hl               ; HL = B1 << 4
                ld      a,(FAT_B0)
                rrca
                rrca
                rrca
                rrca
                and     $0F                 ; A = B0 >> 4
                ld      e,a
                ld      d,0
                add     hl,de
                or      a                   ; Cy = 0
                ret

; frnd_locate — resolve the physical sector for file-sector index (GP_SEC), walking
; (and, if GP_FLAGS bit0 set, extending) the cluster chain. On success GP_PHYS holds
; the absolute sector and Cy = 0. Cy = 1 means beyond-EOF (read mode) or disk-full /
; I/O error. Loop state lives in GP_* RAM (read/write CALSLT clobbers all registers).
frnd_locate:
                ; clusterIdx = GP_SEC / secPerClus; secInClus = GP_SEC % secPerClus.
                ld      hl,(GP_SEC)
                ld      a,(FAT_SECPERCLUS)
                ld      c,a
                ld      de,0                ; DE = clusterIdx
frl_div:
                ld      a,l
                cp      c
                jr      c,frl_divdone       ; HL (<256) < secPerClus -> remainder
                sub     c
                ld      l,a                 ; HL -= secPerClus (HL stays < 256)
                inc     de
                jr      frl_div
frl_divdone:
                ld      a,l
                ld      (GP_SECINCL),a
                ld      (GP_CLIDX),de
                ; cluster = FWR_FIRST (allocate the first cluster if the file is empty)
                ld      hl,(FWR_FIRST)
                ld      a,h
                or      l
                jr      nz,frl_havefirst
                ld      a,(GP_FLAGS)
                and     1
                jr      z,frl_eof           ; read mode + empty file -> beyond EOF
                call    fat_alloc_cluster   ; HL = new first cluster (marked EOC)
                ret     c
                ld      (FWR_FIRST),hl
frl_havefirst:
                ld      (GP_CLUS),hl
frl_walk:
                ld      hl,(GP_CLIDX)
                ld      a,h
                or      l
                jr      z,frl_walked
                ld      hl,(GP_CLUS)
                call    frnd_next           ; HL = next cluster
                ret     c
                ld      de,$0FF8
                push    hl
                or      a
                sbc     hl,de
                pop     hl
                jr      c,frl_inchain       ; next < $0FF8 -> a real cluster
                ; end-of-chain reached.
                ld      a,(GP_FLAGS)
                and     1
                jr      z,frl_eof           ; read mode -> beyond EOF
                call    fat_alloc_cluster   ; extend: new cluster (EOC)
                ret     c
                push    hl                  ; new cluster
                ld      de,(GP_CLUS)
                ex      de,hl               ; HL = prev cluster, DE = new (link value)
                call    fat_write_fat_entry ; prev -> new
                pop     hl                  ; HL = new cluster
                ret     c
frl_inchain:
                ld      (GP_CLUS),hl
                ld      hl,(GP_CLIDX)
                dec     hl
                ld      (GP_CLIDX),hl
                jr      frl_walk
frl_walked:
                ; P = firstData + (cluster-2)*secPerClus + secInClus
                ld      hl,(GP_CLUS)
                ld      de,2
                or      a
                sbc     hl,de
                ex      de,hl               ; DE = cluster - 2
                ld      hl,0
                ld      a,(FAT_SECPERCLUS)
                ld      b,a
frl_mul:
                add     hl,de
                djnz    frl_mul
                ld      de,(FAT_FIRSTDATA)
                add     hl,de
                ld      a,(GP_SECINCL)
                ld      e,a
                ld      d,0
                add     hl,de
                ld      (GP_PHYS),hl
                or      a                   ; Cy = 0 success
                ret
frl_eof:
                scf
                ret

; frnd_fill_fwbuf — fill FWBUF with 512 spaces (a fresh record sector with no prior
; on-disk content). Clobbers BC,DE,HL.
frnd_fill_fwbuf:
                ld      hl,FWBUF
                ld      de,FWBUF+1
                ld      bc,511
                ld      (hl),' '
                ldir
                ret

; load_reclen — GP_RECLEN := FCH_RECLENS[FCH_ACTIVE], the active channel's record
; length (set at OPEN, default 256). Called at the start of every record calc; the
; channel is already live (GET/PUT call fch_select first, setting FCH_ACTIVE).
; Clobbers A,DE,HL.
load_reclen:
                ld      a,(FCH_ACTIVE)
                add     a,a                 ; channel * 2 (word index)
                ld      e,a
                ld      d,0
                ld      hl,FCH_RECLENS
                add     hl,de
                ld      e,(hl)
                inc     hl
                ld      d,(hl)
                ld      (GP_RECLEN),de
                ret

; mul_reclen — HL := HL * GP_RECLEN. Clobbers A,DE (BC is preserved).
;
; 🔴 THIS USED TO BE A SHIFT, AND THE SHIFT IS WHY THE `LEN=` DOMAIN IS STILL
; POWERS OF TWO. The old body doubled HL while halving r until r == 1 -- exactly
; `HL * 2^floor(log2 r)` -- correct for a power of two and silently wrong for
; everything else: at r=100 it computed **×64**, so record 6 landed at
; within=320 instead of 500. `tests/test_open_len.py` is what caught that when
; D-RECLEN2 tried to widen the domain in 2026-08-30, because it checks
; `frnd_calc` against an INDEPENDENTLY derived offset; the emulator rows could
; not, since `PUT` and `GET` share the arithmetic and agree on the same wrong
; answer [[a-case-that-agrees-can-agree-for-the-wrong-reason]].
;
; 🎯 SO THIS IS ONE OF THREE THINGS THE WIDENING NEEDS, and the only one that
; can be fixed and PROVEN with no disk risk at all. The other two are
; `fat_rand_put`/`fat_rand_get` spanning two sectors, and `oo_parse_reclen`'s
; validator. Until those land nothing but a power of two reaches here, and for a
; power of two shift-and-add gives bit-identical answers -- so this change moves
; no shipped behaviour, which is precisely what makes it safe to land alone.
;
; Shift-and-add, LSB first: k <= 254 and r <= 256, so the product is <= 65024 and
; the running BC (k << bit) never exceeds 16 bits either.
mul_reclen:
                ld      de,(GP_RECLEN)      ; DE = r, the multiplier
                push    bc                  ; the header promised A,DE only
                ld      b,h
                ld      c,l                 ; BC = k, the multiplicand
                ld      hl,0                ; HL = product
mr_loop:
                ld      a,e
                and     1                   ; r bit 0 set -> add this partial
                jr      z,mr_skip
                add     hl,bc
mr_skip:
                sla     c
                rl      b                   ; BC <<= 1
                srl     d
                rr      e                   ; r >>= 1
                ld      a,d
                or      e
                jr      nz,mr_loop          ; r exhausted -> done
                pop     bc
                ret

; frnd_calc — split GP_RECNO into GP_SEC (file sector index) + GP_WITHIN (byte
; offset within the 512-byte sector). byteoffset = (recno-1) * reclen; GP_SEC =
; byteoffset >> 9; GP_WITHIN = byteoffset & 511. recno is 1..255 and reclen <= 256,
; so byteoffset <= 254*256 = 65024 (fits 16 bits). Clobbers A,DE,HL.
; ⚠️ THE ARITHMETIC HERE IS GENERAL SINCE `mul_reclen` stopped being a shift; what
; still requires a power of two is `fat_rand_put`/`fat_rand_get`, whose overlay is
; a single `ldir` that cannot cross a sector boundary. The sentence that stood
; here — ~~"reclen tiles the sector (power of two 1..256), so a record never
; straddles two sectors"~~ — described the CONSEQUENCE of the validator, not a
; property of this routine, and it will be wrong the day the validator widens.
frnd_calc:
                call    load_reclen         ; GP_RECLEN = this channel's record size
                ld      hl,(GP_RECNO)
                dec     hl                  ; HL = k (0..254)
                call    mul_reclen          ; HL = k * reclen = byte offset in file
                ; GP_WITHIN = HL & 0x01FF (low 9 bits)
                ld      a,h
                and     1
                ld      d,a
                ld      e,l
                ld      (GP_WITHIN),de
                ; GP_SEC = HL >> 9 = (HL >> 8) >> 1
                ld      l,h
                ld      h,0                 ; HL = HL >> 8
                srl     l                   ; HL = HL >> 9  (H stays 0; byteoffset < 32768)
                ld      (GP_SEC),hl
                ret

; fat_rand_put — write the record buffer (FSECTOR_BUF[0..256)) to record GP_RECNO.
;   out: Cy = 0 ok; Cy = 1 = disk full / I/O error / record out of range.
fat_rand_put:
                ld      a,(GP_RECNO+1)      ; recno high byte must be 0 (recno <= 255)
                or      a
                jr      nz,frp_err
                ld      a,(GP_RECNO)
                or      a
                jr      z,frp_err           ; record 0 invalid
                call    frnd_calc           ; GP_SEC, GP_WITHIN
                ; old_nsec = ceil(FWR_BYTES_lo16 / 512) = (size + 511) >> 9
                ld      hl,(FWR_BYTES)
                ld      de,511
                add     hl,de
                ld      a,h
                srl     a
                ld      l,a
                ld      h,0
                ld      (GP_OLDNSEC),hl
                ld      a,1
                ld      (GP_FLAGS),a        ; extend (allocate as needed)
                call    frnd_locate         ; GP_PHYS = sector; chain extended
                ret     c
                ; read the existing sector (S < old_nsec) or start from spaces.
                ld      hl,(GP_SEC)
                ld      de,(GP_OLDNSEC)
                or      a
                sbc     hl,de
                jr      c,frp_readold
                call    frnd_fill_fwbuf
                jr      frp_overlay
frp_readold:
                ld      de,(GP_PHYS)
                ld      hl,FWBUF
                call    read_sector
                ret     c
frp_overlay:
                ; FWBUF[within..within+reclen) = FSECTOR_BUF[0..reclen)
                ld      hl,(GP_WITHIN)
                ld      de,FWBUF
                add     hl,de
                ex      de,hl               ; DE = FWBUF + within (dest)
                ld      hl,FSECTOR_BUF      ; src = the record
                ld      bc,(GP_RECLEN)      ; reclen bytes (set by frnd_calc above)
                ldir
                ld      de,(GP_PHYS)
                ld      hl,FWBUF
                call    write_sector
                ret     c
                call    frnd_update_size    ; FWR_BYTES = max(old, recno*256)
                jp      fat_dir_update      ; tail: stamp first cluster + size into dir
frp_err:
                scf
                ret

; frnd_update_size — FWR_BYTES = max(FWR_BYTES, GP_RECNO*reclen). recno<=255 and
; reclen<=256, so the new size is <= 65280 and the high 2 bytes are 0. GP_RECLEN was
; loaded by the frnd_calc that precedes every fat_rand_put. Clobbers A,DE,HL.
frnd_update_size:
                ld      hl,(GP_RECNO)       ; recno (high byte 0 -- callers checked <=255)
                call    mul_reclen          ; HL = recno * reclen (candidate new size)
                push    hl                  ; save the candidate
                ld      de,(FWR_BYTES)
                or      a
                sbc     hl,de               ; new - current
                pop     hl                  ; HL = candidate again (flags from sbc survive)
                ret     c                   ; new < current -> keep
                ret     z                   ; equal -> keep
                ld      (FWR_BYTES),hl      ; grow to recno*reclen
                ; D-LOF §4c: keep LOF's size field in step. MEASURED on the
                ; CF-3300 (docs/lof-cf3300-characterization.md §3): after
                ; `PUT #1,1` the reference reports LOF = 256 while the on-disk
                ; DIRECTORY entry still holds 0 -- which is also the row that
                ; refuted "LOF reads the directory". A RANDOM PUT moves the field
                ; live; a sequential PRINT # does NOT (and must not).
                ld      (FAT_FILESIZE),hl
                ld      hl,0
                ld      (FWR_BYTES+2),hl
                ld      (FAT_FILESIZE+2),hl
                ret

; fat_rand_get — read record GP_RECNO into the record buffer (FSECTOR_BUF[0..256)).
;   out: Cy = 0 ok; Cy = 1 = I/O error / record out of range. A record beyond the
;        file end is returned as spaces (lenient).
fat_rand_get:
                ld      a,(GP_RECNO+1)
                or      a
                jr      nz,frg_err
                ld      a,(GP_RECNO)
                or      a
                jr      z,frg_err
                call    frnd_calc
                xor     a
                ld      (GP_FLAGS),a        ; read only (do not extend)
                call    frnd_locate
                jr      c,frg_eoffill       ; beyond EOF -> spaces
                ld      de,(GP_PHYS)
                ld      hl,FWBUF
                call    read_sector
                ret     c
                ; FSECTOR_BUF[0..reclen) = FWBUF[within..within+reclen)
                ld      hl,(GP_WITHIN)
                ld      de,FWBUF
                add     hl,de               ; HL = FWBUF + within (src)
                ld      de,FSECTOR_BUF
                ld      bc,(GP_RECLEN)      ; reclen bytes (set by frnd_calc above)
                ldir
                or      a                   ; Cy = 0
                ret
frg_eoffill:
                ld      hl,FSECTOR_BUF
                ld      de,FSECTOR_BUF+1
                ld      bc,255
                ld      (hl),' '
                ldir
                or      a                   ; Cy = 0 (lenient empty record)
                ret
frg_err:
                scf
                ret
