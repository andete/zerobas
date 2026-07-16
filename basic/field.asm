; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD

; field.asm — random-access record fields (Phase 2c slice 1): FIELD / LSET / RSET.
;
; MSX random-access files partition a channel's fixed record buffer into named
; string "fields"; GET reads a record into that buffer and PUT writes it back
; (slice 2). FIELD declares the partitioning; LSET/RSET store a value into a field
; left/right-justified and space-padded; reading a fielded variable yields its
; current slice of the buffer.
;
; zerobas stores string variables INLINE in STRTAB ([name0][name1][len][bytes]) —
; it has NO MS-BASIC-style descriptor that could simply point into the record
; buffer. So a fielded variable is recorded in a SIDE TABLE (FLD_TAB): each entry
; maps a 2-char var key to a (channel, offset, width) slice. The record buffer is
; the channel's FSECTOR_BUF (the same 512-byte buffer the write-back cache swaps
; per channel, basic/files.asm §channel manager), so a field's bytes live in the
; channel's context and travel with it. Two hooks make a fielded variable behave:
;   * READ  — str_eval's variable path calls fld_lookup, which selects the field's
;             channel, copies the slice into FLD_DESC as a [len][bytes] descriptor,
;             and points STRPTR there (so PRINT/CVI/comparison see the live bytes).
;   * WRITE — LSET/RSET select the channel and copy a string into the slice.
;
; Clean-room: original code. Verb semantics (FIELD partitions a buffer; LSET left-
; justifies + space-pads, RSET right-justifies; a too-long value truncates from the
; right) follow the public MSX-BASIC language reference; the side-table layout is
; zerobas' own design (forced by the inline string store). Tokens are oracle-locked
; to the VG-8020 crunch (FIELD $B1, LSET $B8, RSET $B9). No disassembly. See
; basic/PROVENANCE.md §random-access records.
;
; GET/PUT (slice 2) add the on-disk record I/O. The record length is `reclen`,
; per channel — 256 by default (oracle: a CF-3300 PUT of one record makes a
; 256-byte file), or the OPEN..AS #n LEN=r value (disk-BASIC option-closure Item 3;
; parsed in files.asm, held in FCH_RECLENS[ch], loaded into GP_RECLEN per calc).
; r is constrained to a power of two in 1..256 so records TILE the 512-byte sector
; (512/r per sector) and never straddle two sectors. Record N (1-based) occupies
; file bytes [(N-1)*reclen, N*reclen), i.e. file logical sector ((N-1)*reclen)>>9 at
; within-sector offset ((N-1)*reclen)&511 (frnd_calc) — 512/reclen records per
; 512-byte sector (r=256 -> the historical two per sector). PUT does a
; read-modify-write of the sector (preserving the other records) and extends the
; cluster chain when the record lies beyond the current end; GET reads the sector and
; copies the record into the buffer. The buffer choreography keeps the live record in
; FSECTOR_BUF and uses FWBUF for everything else (FAT metadata during allocation, then
; the data sector, then the dir update) — never both at once, so the record survives a
; chain walk. The walk reuses fat_read_fat_sector (FWBUF), NOT fat_next_cluster (which
; reads FAT into FSECTOR_BUF and would clobber the record). fat.asm is untouched.
;
; Scope / documented divergences (PROVENANCE.md):
;   * LSET/RSET require a FIELDed target; on a non-fielded var they error (real
;     MSX-BASIC left-justifies into the var's current value — a Phase-3 nicety).
;   * a fielded READ takes precedence over a plain STRTAB value; assigning a fielded
;     name with plain LET does not "disconnect" the field (real MSX-BASIC does).
;   * field widths are 1..255; FIELD overflow past the record length is not checked.
;   * record numbers are 1..255 (file < 64 KB — the same 16-bit size ceiling the
;     loader text path documents); bare GET/PUT (no record number) default to record
;     1 — the auto-incrementing "current record" is not tracked.
;   * sparse / out-of-order PUT (writing record M before some earlier record exists)
;     leaves the skipped records' bytes undefined; in-order writes are well-defined.

; ===========================================================================
; Field-table primitives
; ===========================================================================

; fld_init — mark every field-table slot free (chan byte = 0). Clobbers A,B,DE,HL.
; Called at cold start (init_filechan) and on NEW/CLEAR/RUN (clear_vars).
fld_init:
                ld      hl,FLD_TAB
                ld      b,FLD_SLOTS
fldi_lp:
                ld      (hl),0              ; chan = 0 -> free slot
                ld      de,FLD_ENTSZ
                add     hl,de
                djnz    fldi_lp
                ret

; fld_clear_chan — free every field entry belonging to channel A (used when the
; channel is closed). A = channel. Clobbers A,B,C,DE,HL.
fld_clear_chan:
                ld      c,a                 ; C = channel to clear
                ld      hl,FLD_TAB
                ld      b,FLD_SLOTS
fldcc_lp:
                ld      a,(hl)              ; entry chan
                cp      c
                jr      nz,fldcc_next
                ld      (hl),0              ; matches -> free it
fldcc_next:
                ld      de,FLD_ENTSZ
                add     hl,de
                djnz    fldcc_lp
                ret

; fld_find — locate a field entry by variable key BC (B=name0, C=name1).
; out: CF set  -> found,     HL -> entry (chan byte).
;      CF clear -> not found.
; Clobbers A, DE, HL (BC preserved).
fld_find:
                ld      hl,FLD_TAB
fldf_lp:
                ld      a,(hl)              ; chan
                or      a
                jr      z,fldf_next         ; free slot -> skip
                inc     hl
                ld      a,(hl)              ; k0
                inc     hl                  ; HL -> k1
                cp      b
                jr      nz,fldf_back
                ld      a,(hl)              ; k1
                cp      c
                jr      nz,fldf_back
                dec     hl
                dec     hl                  ; HL -> chan (entry start)
                scf
                ret
fldf_back:
                dec     hl
                dec     hl                  ; back to chan
fldf_next:
                ld      de,FLD_ENTSZ
                add     hl,de
                ld      a,h
                cp      high FLD_TABEND
                jr      nz,fldf_lp
                ld      a,l
                cp      low FLD_TABEND
                jr      nz,fldf_lp
                or      a                   ; reached end -> CF clear (not found)
                ret

; fld_fill_record — fill the active channel's record buffer (FSECTOR_BUF, 512
; bytes) with spaces. Used by a RANDOM open so unwritten fields read as spaces.
; Clobbers A? no — only BC/DE/HL.
fld_fill_record:
                ld      hl,FSECTOR_BUF
                ld      de,FSECTOR_BUF+1
                ld      bc,511
                ld      (hl),' '
                ldir
                ret

; ===========================================================================
; FIELD #f, w1 AS v1$, w2 AS v2$, ...
; ===========================================================================
; HL = cursor at the FIELD token. Drops any prior fields on the channel, then walks
; the comma list assigning each variable a slice [running offset, width].
ex_field:
                inc     hl                  ; past the FIELD token
                call    skip_spaces
                ld      a,(hl)
                cp      '#'
                jr      nz,exf_havech
                inc     hl
exf_havech:
                call    eval                ; DE = channel; HL advanced
                ld      a,d
                or      a
                jp      nz,stmt_error       ; > 255 -> bad file number
                ld      a,e
                call    fch_valid
                jp      nc,stmt_error       ; 0 or > MAXF -> bad file number
                ld      a,e
                ld      (FLD_CHAN),a
                ; the channel must be open (FCH_MODES[ch] != 0).
                push    hl                  ; guard cursor across the array read
                ld      d,0
                ld      e,a
                ld      hl,FCH_MODES
                add     hl,de
                ld      a,(hl)
                pop     hl
                or      a
                jp      z,stmt_error        ; channel not open
                ; re-FIELD replaces: drop prior fields on this channel, offset = 0.
                push    hl
                ld      a,(FLD_CHAN)
                call    fld_clear_chan
                pop     hl
                xor     a
                ld      (FLD_CUROFF),a
                ld      (FLD_CUROFF+1),a
                ; a comma separates the channel from the field list: FIELD #f , w AS v$
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jp      nz,stmt_error
                inc     hl
exf_item:
                call    skip_spaces
                call    eval                ; DE = field width; HL advanced
                push    de                  ; save width across the "AS" + name parse
                call    skip_spaces
                ld      a,(hl)              ; "AS" (verbatim ASCII, not tokenised)
                call    upcase
                cp      'A'
                jp      nz,exf_syn
                inc     hl
                ld      a,(hl)
                call    upcase
                cp      'S'
                jp      nz,exf_syn
                inc     hl
                call    skip_spaces
                call    is_letter           ; a string variable name?
                jp      nc,exf_syn
                call    var_str_type        ; A=1 if `$` suffix
                or      a
                jp      z,exf_syn           ; must be a string var
                call    var_name_key        ; BC = key; HL past name + `$`
                pop     de                  ; DE = width (E = width, D = 0 for w<=255)
                push    hl                  ; guard cursor across the table write
                call    fld_add             ; add [FLD_CHAN, BC, FLD_CUROFF, E]; bump offset
                pop     hl
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      z,exf_comma
                jp      exec_stmt           ; end of the field list
exf_comma:
                inc     hl                  ; past ',' -> next field item
                jr      exf_item
exf_syn:
                pop     de                  ; discard the saved width
                jp      stmt_error

; fld_add — append a field entry: chan=(FLD_CHAN), key=BC, offset=(FLD_CUROFF),
; width=E; then advance FLD_CUROFF by the width. Silently drops if the table is
; full (documented). Clobbers A,DE,HL (BC,E preserved through the write).
fld_add:
                push    de                  ; preserve the width (E)
                ld      hl,FLD_TAB
fadd_lp:
                ld      a,(hl)
                or      a
                jr      z,fadd_free
                ld      de,FLD_ENTSZ
                add     hl,de
                ld      a,h
                cp      high FLD_TABEND
                jr      nz,fadd_lp
                ld      a,l
                cp      low FLD_TABEND
                jr      nz,fadd_lp
                pop     de                  ; table full -> drop this field
                ret
fadd_free:
                pop     de                  ; E = width
                ld      a,(FLD_CHAN)
                ld      (hl),a              ; chan
                inc     hl
                ld      (hl),b              ; k0
                inc     hl
                ld      (hl),c              ; k1
                inc     hl
                ld      a,(FLD_CUROFF)
                ld      (hl),a              ; off lo
                inc     hl
                ld      a,(FLD_CUROFF+1)
                ld      (hl),a              ; off hi
                inc     hl
                ld      (hl),e              ; width
                ; FLD_CUROFF += width
                ld      hl,(FLD_CUROFF)
                ld      d,0                 ; add the 8-bit width only
                add     hl,de
                ld      (FLD_CUROFF),hl
                ret

; ===========================================================================
; LSET / RSET v$ = s$
; ===========================================================================
ex_lset:
                xor     a                   ; justify = left
                jr      lrset_common
ex_rset:
                ld      a,1                 ; justify = right
lrset_common:
                ld      (LRSET_JUST),a
                inc     hl                  ; past the LSET/RSET token
                call    skip_spaces
                call    is_letter
                jp      nc,stmt_error
                call    var_str_type        ; A=1 if `$`
                or      a
                jp      z,stmt_error        ; must be a string var
                call    var_name_key        ; BC = key; HL advanced past name + `$`
                push    hl                  ; guard cursor across the lookup
                call    fld_find            ; CF set -> HL -> entry
                jr      nc,lrset_notfld
                ld      a,(hl)              ; chan
                ld      (FLD_CHAN),a
                inc     hl
                inc     hl
                inc     hl                  ; -> off lo
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = off
                ld      (LRSET_OFF),de
                inc     hl
                ld      a,(hl)              ; width
                ld      (LRSET_W),a
                pop     hl                  ; restore cursor
                call    skip_spaces
                ld      a,(hl)
                cp      EQ_TOKEN            ; '='
                jp      nz,stmt_error
                inc     hl
                call    skip_spaces
                call    str_eval            ; STRPTR -> [len][bytes]; HL advanced
                jp      nc,stmt_error       ; RHS not a string operand
                push    hl                  ; guard cursor across select + store
                ld      a,(FLD_CHAN)
                call    fch_select          ; FSECTOR_BUF = this channel's record buffer
                call    lrset_store
                pop     hl
                jp      exec_stmt
lrset_notfld:
                pop     hl
                jp      stmt_error          ; LSET/RSET on a non-fielded var (slice-1 limit)

; lrset_store — copy the [len][bytes] string at STRPTR into the record-buffer field
; FSECTOR_BUF+(LRSET_OFF), width (LRSET_W), justify (LRSET_JUST). The field is first
; space-filled, then min(srclen,width) bytes are copied (left- or right-aligned);
; a longer source truncates from the right. Clobbers A,BC,DE,HL.
lrset_store:
                ld      hl,(LRSET_OFF)
                ld      de,FSECTOR_BUF
                add     hl,de               ; HL = field start
                ; space-fill the whole field
                push    hl
                ld      a,(LRSET_W)
                or      a
                jr      z,lrs_filled
                ld      b,a
lrs_fill:
                ld      (hl),' '
                inc     hl
                djnz    lrs_fill
lrs_filled:
                pop     hl                  ; HL = field start
                ld      de,(STRPTR)
                ld      a,(de)              ; source length
                ld      c,a                 ; C = source length
    IF ROM_BASE < $4000
                push    hl                  ; guard field start
                ld      h,d
                ld      l,e                 ; HL = source descriptor addr
                call    pu_deref_body       ; HL -> source bytes (arrays
                                            ; slice-4a; shared with
                                            ; printusing.asm — page 1 has no
                                            ; slack for a 3rd duplicate)
                ex      de,hl               ; DE = source bytes
                pop     hl                  ; HL = field start (restored)
    ELSE
                inc     de                  ; DE -> source bytes
    ENDIF
                ld      a,(LRSET_W)
                cp      c
                jr      nc,lrs_ncopy        ; width >= len -> copy len
                ld      c,a                 ; width < len -> copy width (truncate)
lrs_ncopy:
                ld      a,(LRSET_JUST)
                or      a
                jr      z,lrs_copy          ; left: dest = field start
                ; right: dest = field start + (width - ncopy)
                ld      a,(LRSET_W)
                sub     c
                add     a,l
                ld      l,a
                jr      nc,lrs_copy
                inc     h
lrs_copy:
                ld      a,c
                or      a
                ret     z                   ; nothing to copy
                ld      b,c
lrs_cp:
                ld      a,(de)
                ld      (hl),a
                inc     de
                inc     hl
                djnz    lrs_cp
                ret

; ===========================================================================
; fld_lookup — READ hook for str_eval's variable path.
; in:  BC = variable key.
; out: CF set  -> BC is fielded; STRPTR -> FLD_DESC holds the slice [len][bytes].
;      CF clear -> not fielded (caller falls back to str_get_key). BC may be clobbered.
; Clobbers A,BC,DE,HL; preserves IX (fch_select is LDIR-only for a RANDOM channel).
; ===========================================================================
fld_lookup:
                call    fld_find            ; CF set -> HL -> entry
                ret     nc
                ld      a,(hl)              ; chan
                ld      (FLD_CHAN),a
                inc     hl
                inc     hl
                inc     hl                  ; -> off lo
                ld      e,(hl)
                inc     hl
                ld      d,(hl)              ; DE = off
                inc     hl
                ld      a,(hl)              ; width
                ld      (FLD_DESC),a        ; descriptor length = width
                push    de                  ; save offset
                push    af                  ; save width
                ld      a,(FLD_CHAN)
                call    fch_select          ; FSECTOR_BUF = this channel's record buffer
                pop     af                  ; A = width
                pop     de                  ; DE = offset
                ld      hl,FSECTOR_BUF
                add     hl,de               ; HL = slice start
                ld      de,FLD_DESC+1       ; DE = descriptor bytes
                or      a
                jr      z,fll_done          ; width 0 -> empty
                ld      b,a
fll_cp:
                ld      a,(hl)
                ld      (de),a
                inc     hl
                inc     de
                djnz    fll_cp
fll_done:
    IF ROM_BASE < $4000
                ; arrays slice-4a: FLD_DESC stays a fixed inline [len][bytes:255]
                ; buffer (never in the heap, spec §5.2) — wrap it as a [len][ptr]
                ; rvalue descriptor in the shared RVDESC (via the low-region
                ; mk_rvdesc; safe because fld_lookup's result is consumed
                ; immediately, RVDESC's standing single-shared-cell property).
                ld      a,(FLD_DESC)
                ld      hl,FLD_DESC+1
                call    mk_rvdesc           ; RVDESC := [len][ptr]; HL = RVDESC
    ELSE
                ld      hl,FLD_DESC
    ENDIF
                ld      (STRPTR),hl
                scf
                ret

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

; mul_reclen — HL := HL * GP_RECLEN. The record length is a power of two (enforced
; at OPEN), so the multiply is a shift: double HL while halving r until r == 1.
; Clobbers A,DE.
mul_reclen:
                ld      de,(GP_RECLEN)
mr_loop:
                ld      a,d
                or      a
                jr      nz,mr_shift         ; r >= 256 -> still shifting
                ld      a,e
                cp      2
                ret     c                   ; r == 1 -> HL unchanged (done)
mr_shift:
                add     hl,hl               ; HL <<= 1
                srl     d
                rr      e                   ; r >>= 1
                jr      mr_loop

; frnd_calc — split GP_RECNO into GP_SEC (file sector index) + GP_WITHIN (byte
; offset within the 512-byte sector). byteoffset = (recno-1) * reclen; GP_SEC =
; byteoffset >> 9; GP_WITHIN = byteoffset & 511. reclen tiles the sector (power of
; two 1..256), so a record never straddles two sectors. recno is 1..255 and reclen
; <= 256, so byteoffset <= 254*256 = 65024 (fits 16 bits). Clobbers A,DE,HL.
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
                ld      hl,0
                ld      (FWR_BYTES+2),hl
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

; ===========================================================================
; GET [#]f [, recno]   /   PUT [#]f [, recno]
; ===========================================================================
; Select the channel (must be open RANDOM), then read/write the record. The text
; cursor (HL) is guarded across fch_select + the disk op (CALSLT clobbers all).
ex_put:
                ld      a,1                 ; mode = PUT (write)
                jr      gp_common
ex_get:
                xor     a                   ; mode = GET (read)
gp_common:
                ld      (GP_MODE),a
                inc     hl                  ; past the GET/PUT token
                call    skip_spaces
                ld      a,(hl)
                cp      '#'
                jr      nz,gp_nochan
                inc     hl
gp_nochan:
                call    eval                ; DE = channel
                ld      a,d
                or      a
                jp      nz,stmt_error
                ld      a,e
                call    fch_valid
                jp      nc,stmt_error
                ld      a,e
                ld      (GP_CHAN),a
                ; optional ", recno" (else default record 1)
                call    skip_spaces
                ld      a,(hl)
                cp      ','
                jr      nz,gp_defrec
                inc     hl
                call    eval                ; DE = record number
                jr      gp_haverec
gp_defrec:
                ld      de,1
gp_haverec:
                ld      (GP_RECNO),de
                push    hl                  ; guard cursor across select + disk op
                ; the channel must be open RANDOM (FCH_MODES[ch] == 4).
                ld      a,(GP_CHAN)
                ld      e,a
                ld      d,0
                ld      hl,FCH_MODES
                add     hl,de
                ld      a,(hl)
                cp      4
                jr      nz,gp_err
                ld      a,(GP_CHAN)
                call    fch_select          ; FSECTOR_BUF + FWR_* = this channel's state
                ld      a,(GP_MODE)
                or      a
                jr      z,gp_doget
                call    fat_rand_put
                jr      gp_fin
gp_doget:
                call    fat_rand_get
gp_fin:
                pop     hl
                jp      c,load_error        ; disk error
                jp      exec_stmt
gp_err:
                pop     hl
                jp      stmt_error
