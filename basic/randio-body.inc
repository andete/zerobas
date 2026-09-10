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
                ; D-LOC: FCH_RECNOS[channel] := 0 on every random OPEN. The CF-3300
                ; reads LOC = 0 on a fresh channel before any GET/PUT (D-LOCSEM r.get:
                ; 0,3,7); a fresh zerobas boot read -1 there -- power-on garbage, since
                ; the table is RAM nobody had written. oo_random stashes the channel in
                ; OO_RECLEN_CHAN before it calls here; sub-side because main page 1 has
                ; 4 B. Re-OPEN after CLOSE reading 0 is the same rule, unmeasured.
                ld      a,(OO_RECLEN_CHAN)
                ld      l,a
                ld      h,0
                add     hl,hl
                ld      de,FCH_RECNOS
                add     hl,de
                xor     a
                ld      (hl),a
                inc     hl
                ld      (hl),a
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

; mul_reclen — A:HL := HL * GP_RECLEN, a 24-bit product. Clobbers A,DE (BC is
; preserved).
; 🔴 D-PUTU32 (2026-09-10): THE PRODUCT IS 24 BITS, NOT 16. The 16-bit
; shift-and-add this replaces accumulated k*reclen with a plain `add hl,bc` and
; wrapped SILENTLY past 65535 -- that wrap was the whole reason PUT and GET
; refused record numbers above 255 (D-PUTDOMAIN), while the CF-3300 serves
; PUT#1,257 (offset 65536) and PUT#1,300 (76544). recno now arrives as an
; unsigned 16-bit DE from the evaluator, so k is 0..65534 and, with reclen
; 1..256, the product is < 2^24.
; TWO CASES, because reclen is 1..256 and 256 does not fit the 8-bit multiplier:
;   reclen == 256:  the product is k << 8, moved by bytes.
;   reclen  < 256:  8 iterations MSB-first over reclen's bits with the
;                   multiplicand FIXED in BC and the product doubling in A:HL --
;                   the LSB-first form would need a 24-bit shifting multiplicand
;                   and there is no register for its top byte.
mul_reclen:
                push    bc                  ; the header promised A,DE only
                ld      b,h
                ld      c,l                 ; BC = k, the multiplicand (fixed)
                ld      de,(GP_RECLEN)      ; DE = r
                ld      a,d
                or      a
                jr      z,mr_lt256
                ld      a,b                 ; r == 256: A:HL = k << 8
                ld      h,c
                ld      l,0
                pop     bc
                ret
mr_lt256:                                   ; A = 0 here; E = r (1..255)
                ld      h,a
                ld      l,a                 ; A:HL = 0
                ld      d,8                 ; 8 bits of r, MSB-first
mr_loop:
                add     hl,hl               ; A:HL <<= 1 ...
                rla                         ;   (bit 15 of HL -> CF -> bit 0 of A;
                                            ;   A's own top bit is beyond 24 bits)
                sla     e                   ; r's top bit -> CF
                jr      nc,mr_skip
                add     hl,bc               ; A:HL += k
                adc     a,0
mr_skip:
                dec     d
                jr      nz,mr_loop
                pop     bc
                ret

; frnd_calc — split GP_RECNO into GP_SEC (file sector index) + GP_WITHIN (byte
; offset within the 512-byte sector). byteoffset = (recno-1) * reclen, a 24-bit
; value from mul_reclen (A:HL); GP_SEC = byteoffset >> 9; GP_WITHIN = byteoffset
; & 511. GP_SEC stays 16-bit by construction: a 720 KB disk has 1440 sectors, so
; any offset that fits the disk shifts to under 2^16. D-PUTU32 (2026-09-10)
; replaced the 16-bit split; the previous comment here recorded that the 16-bit
; bound "comes from mul_reclen above, which wraps SILENTLY" -- it did, and now
; neither routine caps anything. Clobbers A,DE,HL.
frnd_calc:
                call    load_reclen         ; GP_RECLEN = this channel's record size
                ; D-LOC: FCH_RECNOS[GP_CHAN] := GP_RECNO, the per-channel record number
                ; LOC(#n) reads (basic/expr.asm ev_ff_loc). Sited here, sub page 1,
                ; because every random GET/PUT passes through this calc and the
                ; resident form overran main page 1 by ~12 B. GP_CHAN and GP_RECNO
                ; are page-3 cells, always mapped.
                ld      a,(GP_CHAN)
                ld      l,a
                ld      h,0
                add     hl,hl
                ld      de,FCH_RECNOS
                add     hl,de
                ld      de,(GP_RECNO)
                ld      (hl),e
                inc     hl
                ld      (hl),d
                ld      hl,(GP_RECNO)
                dec     hl                  ; HL = k (0..65534)
                call    mul_reclen          ; A:HL = k * reclen, the byte offset
                push    af                  ; [offset bits 16..23]
                ld      a,h
                and     1
                ld      d,a
                ld      e,l
                ld      (GP_WITHIN),de      ; GP_WITHIN = offset & 511
                pop     af
                ld      l,h
                ld      h,a                 ; HL = offset >> 8 (bytes 1..2 of the 24)
                srl     h
                rr      l                   ; HL = offset >> 9
                ld      (GP_SEC),hl
                ret

; fat_rand_put — write the record buffer (FSECTOR_BUF[0..256)) to record GP_RECNO.
;   out: Cy = 0 ok; Cy = 1 = disk full / I/O error / record out of range.
fat_rand_put:
                ; D-PUTU32: no high-byte cap any more -- the reference serves record
                ; 257 and beyond, and the 24-bit offset math reaches it. Record 0
                ; stays invalid (ERR 5 on the CF-3300, D-GETREC).
                ld      hl,(GP_RECNO)
                ld      a,h
                or      l
                jp      z,frp_err           ; `jp`: the two-pass body below pushed
                                            ; frp_err out of jr range (D-STRADDLE)
                call    frnd_calc           ; GP_SEC, GP_WITHIN
                ; old_nsec = ceil(FWR_BYTES / 512) = (size + 511) >> 9, over the
                ; 4-byte size (D-PUTU32: it used to read the low 16 bits only)
                ld      hl,(FWR_BYTES)
                ld      de,511
                add     hl,de
                ld      a,(FWR_BYTES+2)
                adc     a,0                 ; A:HL = size + 511 (< 2^24 on a 720 KB disk)
                ld      l,h
                ld      h,a
                srl     h
                rr      l                   ; HL = (size + 511) >> 9
                ld      (GP_OLDNSEC),hl
                ; 🎯 D-STRADDLE: A RECORD THAT CROSSES A SECTOR BOUNDARY IS WRITTEN
                ; IN TWO PASSES. The body below used to be straight-line and its
                ; overlay was ONE `ldir` into `FWBUF + within` for the whole
                ; record -- so record 6 at r=100 (within=500) wrote 88 bytes PAST
                ; the 512-byte buffer, into the sysvars above it.
                ; `tests/test_rand_straddle.py` is the witness: it builds the
                ; expected sector image INDEPENDENTLY and guards the bytes above
                ; FWBUF+512, neither of which a round-trip can do (`PUT` and
                ; `GET` share the offset, so they agree on the same wrong answer).
                ld      hl,FSECTOR_BUF
                ld      (GP_SRC),hl         ; pass cursor into the record
                ld      hl,(GP_RECLEN)
                ld      (GP_LEFT),hl        ; bytes still to move
frp_pass:
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
                ; n = min(left, 512 - within) -- what fits in THIS sector
                call    frnd_pass_len       ; BC = n, and GP_LEFT -= n
                ld      hl,(GP_WITHIN)
                ld      de,FWBUF
                add     hl,de
                ex      de,hl               ; DE = FWBUF + within (dest)
                ld      hl,(GP_SRC)         ; src = the record, advanced per pass
                ldir
                ld      (GP_SRC),hl         ; HL is past the bytes just moved
                ld      de,(GP_PHYS)
                ld      hl,FWBUF
                call    write_sector
                ret     c
                ld      hl,(GP_LEFT)
                ld      a,h
                or      l
                jr      z,frp_done          ; the record is fully written
                ; ⚠️ THE NEXT PASS STARTS AT OFFSET 0 OF THE NEXT SECTOR. Only a
                ; record longer than a sector could need a third pass, and
                ; reclen <= 256 < 512, so this loops at most once.
                ld      hl,0
                ld      (GP_WITHIN),hl
                ld      hl,(GP_SEC)
                inc     hl
                ld      (GP_SEC),hl
                jr      frp_pass
frp_done:
                call    frnd_update_size    ; FWR_BYTES = max(old, recno*reclen)
                jp      fat_dir_update      ; tail: stamp first cluster + size into dir

; frnd_pass_len — BC := min(GP_LEFT, 512 - GP_WITHIN), and GP_LEFT -= BC.
; The bytes of the record that fit in the sector this pass is holding.
; Clobbers A,BC,DE,HL.
frnd_pass_len:
                ld      hl,512
                ld      de,(GP_WITHIN)
                or      a
                sbc     hl,de               ; HL = avail (1..512)
                ex      de,hl               ; DE = avail
                ld      hl,(GP_LEFT)
                or      a
                sbc     hl,de               ; left - avail
                jr      nc,fpl_split        ; left >= avail -> this pass takes avail
                ; the whole rest fits: n = left, nothing left over
                add     hl,de               ; HL = left again
                ld      b,h
                ld      c,l
                ld      hl,0
                ld      (GP_LEFT),hl
                ret
fpl_split:
                ld      (GP_LEFT),hl        ; the remainder for the next pass
                ld      b,d
                ld      c,e                 ; n = avail
                ret
frp_err:
                scf
                ret

; frnd_update_size — FWR_BYTES = max(FWR_BYTES, GP_RECNO*reclen), over the 4-byte
; size: the candidate is mul_reclen's 24-bit A:HL (D-PUTU32; it used to assume
; recno <= 255 and zero the high word). GP_RECLEN was loaded by the frnd_calc
; that precedes every fat_rand_put. Clobbers A,DE,HL.
frnd_update_size:
                ld      hl,(GP_RECNO)
                call    mul_reclen          ; A:HL = recno * reclen (candidate new size)
                push    hl                  ; [candidate low word]
                ex      de,hl               ; DE = candidate low word
                ld      hl,(FWR_BYTES)
                or      a
                sbc     hl,de               ; current_low - candidate_low
                ld      hl,(FWR_BYTES+2)
                ld      d,0
                ld      e,a                 ; DE = candidate high word (0:A)
                sbc     hl,de               ; current_high - candidate_high - borrow
                pop     hl                  ; HL = candidate low word (flags survive)
                ret     nc                  ; current >= candidate -> keep
                ld      (FWR_BYTES),hl      ; grow to recno*reclen
                ; D-LOF §4c: keep LOF's size field in step. MEASURED on the
                ; CF-3300 (docs/lof-cf3300-characterization.md §3): after
                ; `PUT #1,1` the reference reports LOF = 256 while the on-disk
                ; DIRECTORY entry still holds 0 -- which is also the row that
                ; refuted "LOF reads the directory". A RANDOM PUT moves the field
                ; live; a sequential PRINT # does NOT (and must not).
                ld      (FAT_FILESIZE),hl
                ld      h,0
                ld      l,a                 ; HL = the candidate's high word
                ld      (FWR_BYTES+2),hl
                ld      (FAT_FILESIZE+2),hl
                ret

; fat_rand_get — read record GP_RECNO into the record buffer (FSECTOR_BUF[0..256)).
;   out: Cy = 0 ok; Cy = 1 = I/O error / record out of range. A record beyond the
;        file end is returned as spaces (lenient).
fat_rand_get:
                ld      hl,(GP_RECNO)       ; D-PUTU32: record 0 only; no 255 cap
                ld      a,h
                or      l
                jr      z,frg_err
                call    frnd_calc
                ; 🎯 D-STRADDLE: THE READ SPANS TWO SECTORS TOO, and its failure is
                ; a wrong ANSWER rather than corruption -- the single `ldir` used
                ; to copy the tail of a straddling record out of the bytes ABOVE
                ; FWBUF. Same two-pass shape as `fat_rand_put`, minus the extend.
                ld      hl,FSECTOR_BUF
                ld      (GP_SRC),hl         ; here the cursor is the DESTINATION
                ld      hl,(GP_RECLEN)
                ld      (GP_LEFT),hl
frg_pass:
                xor     a
                ld      (GP_FLAGS),a        ; read only (do not extend)
                call    frnd_locate
                jr      c,frg_eoffill       ; beyond EOF -> spaces
                ld      de,(GP_PHYS)
                ld      hl,FWBUF
                call    read_sector
                ret     c
                ; FSECTOR_BUF[..] = FWBUF[within..within+n) for this sector's share
                call    frnd_pass_len       ; BC = n, and GP_LEFT -= n
                ld      hl,(GP_WITHIN)
                ld      de,FWBUF
                add     hl,de               ; HL = FWBUF + within (src)
                ld      de,(GP_SRC)         ; dest, advanced per pass
                ldir
                ld      (GP_SRC),de         ; DE is past the bytes just moved
                ld      hl,(GP_LEFT)
                ld      a,h
                or      l
                jr      z,frg_ok
                ld      hl,0
                ld      (GP_WITHIN),hl
                ld      hl,(GP_SEC)
                inc     hl
                ld      (GP_SEC),hl
                jr      frg_pass
frg_ok:
                or      a                   ; Cy = 0 (A is 0 here)
                ret
; ⚠️ A SECOND PASS THAT RUNS OFF THE END TAKES THE WHOLE RECORD WITH IT: the
; `jr c,frg_eoffill` above fires on either pass, and frg_eoffill fills the
; ENTIRE record with spaces rather than only the missing tail. That matches the
; lenient empty-record rule this routine already has (a GET past EOF is not an
; error here), and it is a DECISION, not an oversight -- what the reference does
; with a record half past EOF is unmeasured, and no row here can carry it while
; `oo_parse_reclen` still refuses a straddling length.
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
