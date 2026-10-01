; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; Part of zerobas-disk, included by disk.asm (build with `pasmo -I disk`).
; FAT12 + BDOS/FCB file layer (read + write-back substrate)
; CLEAN-ROOM: every constant, address and algorithm here traces to a public source
; or a black-box oracle probe; nothing is derived from disassembly. See disk/PROVENANCE.md.

; --- BDOS WRITE calls (disk/PROVENANCE.md §BDOS interface, §FAT12 write-back) -

; bdos_create ($16) — create (or truncate-if-exists) the file named in the FCB,
; ready for sequential writing from offset 0.
;   in:  DE = FCB pointer (FCB+1 = 11-byte 8.3 name)
;   out: A = $00 created / $FF error (disk full / write protect / I/O)
; Mounts the volume, then finds or makes a root-directory slot for the name and
; writes a fresh dir entry (name, attribute $00, first cluster = 0, size = 0,
; timestamps = 0 — see the date/time divergence in disk/PROVENANCE.md). No data
; cluster is allocated yet: the first cluster is allocated lazily on the first
; Sequential Write, so a zero-byte file occupies no clusters (matching MSX-DOS).
bdos_create:
                jp      bdos_create_body    ; Tier-2 3b: divert; veneer fills the gap
                ds      $46BA - $, $00      ; pure $00 pad (M26, tier2-m26-spec.md
                                            ; §2.4: trace --resync confirmed $46BA is
                                            ; the kernel's real fixed $2F RDABS dispatch
                                            ; address, landing in dead pad -- NOT 61
                                            ; bytes into bdos_create's body as first
                                            ; guessed; no relocation needed)
k_46BA:         jp      rdabs_body          ; $46BA: BDOS $2F RDABS canonical entry (M26)
                ds      $46C8 - $, $00      ; anchor the canonical address
                jp      k_46C8              ; $46C8: COMMAND.COM-load kernel veneer
                ds      $46E6 - $, $00      ; pad to bdos_create_failpop (net-zero)
bdos_create_failpop:
                pop     hl
bdos_create_err:
                xor     a
                ld      (BDOS_WRMODE), a
                ld      a, $FF
                ret

; bdos_seqwrite ($15) — write the next 128-byte record FROM the DTA into the file.
;   out: A = $00 ok / $01 disk full / $FF error (MSX2 TH, BDOS conventions)
; Buffers RECSIZE (128) bytes from BDOS_DTA into SECTOR_BUF at offset BDOS_WRBUFLEN;
; whenever the buffer fills (512 bytes) it is flushed to the file's current data
; sector (allocating/extending the cluster chain as needed) and the buffer resets.
; BDOS_WRBYTES accumulates the true byte count for Close to stamp into the dir
; entry. (CP/M / MSX-DOS sequential write delivers a fixed 128-byte record from
; the DTA — MSX2 TH FCB sequential I/O; record framing as the read side.)
bdos_seqwrite:
                jp      bdos_seqwrite_body  ; M26 WRABS (tier2-m26-spec.md): relocated --
                                            ; the old span here collided mid-instruction
                                            ; with the real $30 WRABS dispatch address,
                                            ; $4720 (trace --resync confirmed: it's the
                                            ; displacement byte of the `jr c, bsw_full`
                                            ; that used to live at this offset). Real
                                            ; body now bdos_seqwrite_body (disk/kernel.asm
                                            ; free tail); only symbolic callers
                                            ; (driver.asm/kernel.asm `jp bdos_seqwrite`)
                                            ; keep working unchanged.
                ds      $4720 - $, $00      ; pad up to the pinned canonical entry
k_4720:         jp      wrabs_body          ; $4720: BDOS $30 WRABS canonical entry (M26)

; --- FAT12 layer (disk/PROVENANCE.md §FAT12 layer) -------------------------
; Read-only FAT12 on top of the DSKIO sector reader. Sources: Microsoft FAT
; filesystem specification (BPB, FAT, directory) and ECMA-107 (geometry).
; Assumes 512-byte sectors (validated at mount); the on-disk BPB supplies every
; other geometry value, so the same code serves any FAT12 image the BPB
; describes. These routines are internal helpers; the BDOS/FCB layer (next TODO
; item) wires them to zerobas's BLOAD path. End-to-end validation waits on the
; openMSX machine config + oracle probe 2 (DSKIO boot-sector read).

; read_sector — read one logical sector into a buffer via the DSKIO core.
;   in:  DE = logical sector number, HL = buffer
;   out: Cy = 0 ok, Cy = 1 error (A = DSKIO error code)
; --- MSX-DOS-1 kernel WRSEQ-worker entry: $477D (M24 slice B;
; tier2-m24-fclose-multicluster-spec.md) --------------------------------------
; The RAM kernel's BDOS $15 WRSEQ handling CALLs this page-1 entry once per
; 128-byte record (pinned black-box, ret=$D88A dispatcher class, DE=IY=$DA40
; kernel FCB pointer). Pre-M24 this fell on the high byte of fat_mount's own
; `ld hl,0` (the numFATs*secPerFAT multiply preamble), NOP'd through, then
; spun the multiply loop 256x on garbage B and clobbered our FAT geometry
; cells from stale SECTOR_BUF bytes -- silently discarding every WRSEQ
; record's data while reporting success. fat_mount's own multiply+remainder
; (fm_fatacc onward, unchanged) is relocated below to make room -- position-
; free, reached only by label from fat_mount's own `jp fat_mount_tail`
; fall-through above.
                ds      $477D - $, $00      ; pad up to the pinned $477D WRSEQ-worker entry
k_477D:
                jp      wrseq_body          ; $477D: BDOS $15 WRSEQ canonical entry (M24 slice B)
                ds      $4788 - $, $00      ; pad remainder (M26, tier2-m26-spec.md §2.3:
                                            ; trace --resync confirmed $4788 is the
                                            ; kernel's real fixed $21 RDRND dispatch
                                            ; address, dead pad -- the original
                                            ; "$21/$22 share one dispatch" callwatch
                                            ; read was a dedup artifact; no relocation
                                            ; needed, RDABS-shape)
k_4788:         jp      rdrnd_body          ; $4788: BDOS $21 RDRND canonical entry (M26)
                ds      $4793 - $, $00      ; pad remainder (M26, tier2-m26-spec.md §2.3:
                                            ; $4793 is $22 WRRND's own separate dispatch,
                                            ; same pad corridor, RDABS-shape)
k_4793:         jp      wrrnd_body          ; $4793: BDOS $22 WRRND canonical entry (M26)
                ds      $47B2 - $, $00      ; pad remainder (net-zero: k_47B2 unaffected)
                jp      k_47B2              ; $47B2: COMMAND.COM-load kernel veneer
                ds      $47B9 - $, $00      ; pad remainder (net-zero: anchors the 3b relocation below)
; --- M28: $26 WRBLK canonical entry $47BE -- 3b relocation (tier2-m28-blockrandom-
; spec.md §3.1/§4). $47BE used to be 5 bytes INSIDE ff_secloop (the old `jr z,
; ff_notfound` at old-$47BE, [LANDED-B]) -- a latent accidental target, harmless only
; because WRBLK was never exercised during boot. ff_secloop..ff_found (old $47B9-
; $4828, verbatim, position-free -- reached only by fat_find_body's `jp ff_secloop`
; and its own internal back-edge; every internal ff_* label is local to the block)
; is relocated OUT to kernel.asm's free tail (same technique as fdc_entloop_body /
; the FDC-window fix): we do NOT repoint the kernel's $D8BE RAM dispatch table (the
; fixed shared-kernel ABI, not ours) -- we free the canonical address by moving OUR
; colliding code, then expose the real `jp wrblk_body` veneer at $47BE.
                ds      $47BE - $, $00      ; pad the vacated 5 bytes ($47B9-$47BD)
k_47BE:         jp      wrblk_body          ; $47BE: BDOS $26 WRBLK canonical entry (M28)

; name_cmp — compare two 11-byte 8.3 name fields, case-insensitive.
;   in:  HL = directory entry name, DE = search name
;   out: Z set if equal; trashes A, BC, DE, HL
                ds      $4919 - $, $00      ; anchor canonical address
                ds      $4935 - $, $00      ; anchor canonical address
                ds      $4941 - $, $00      ; net-zero: absorbs the relocated write_sector
                ds      $498C - $, $00      ; anchor canonical address
                ds      $49B4 - $, $00      ; anchor canonical address
                ds      $49C3 - $, $00      ; pad to fac_have_sec (net-zero)
                ds      $4A39 - $, $00      ; anchor canonical address
                ds      $4A40 - $, $00      ; pad to fat_write_fat_entry (net-zero)
                ds      $4B59 - $, $00      ; anchor canonical address
                ds      $4B62 - $, $00      ; pad to ffds_alloc (net-zero)
                ds      $4BE5 - $, $00      ; anchor canonical address
                ds      $4C05 - $, $00      ; pad to fdc_useslot (net-zero)
                ds      $4C25 - $, $00      ; anchor canonical address
                ds      $4C29 - $, $00      ; pad to fdc_zero (net-zero)
; fdc_di_save / fdc_io_done — bracket a sector op with a DI..(EI) guard.
; The WD2793 data transfer is a tight DRQ poll: a foreign interrupt (the 50 Hz
; VDP IRQ, live once MSX-DOS / COMMAND.COM run with EI) preempting the loop drops
; an FDC byte -> LOST DATA, an endless restore-retry livelock (a3 §8.34). MSX-DOS
; boot ran with interrupts masked, so this only bit in the DOS context. fdc_di_save
; records the caller's IFF2 then masks; fdc_io_done restores it on every exit,
; leaving the result (A = error code, Cy, HL) untouched. (`ld a,i` puts IFF2 in
; P/V; the entry clobbers A, but fdc_read_phys/fdc_write_phys take no A input.)
fdc_di_save:
                ld      a, i            ; P/V = IFF2 (interrupts enabled?)
                di
                jp      pe, fdc_di_on   ; PE -> IFF2 was set
                xor     a               ; were masked: remember 0
                ld      (FDC_IFF), a
                ret
fdc_di_on:
                ld      a, 1            ; were enabled: remember 1
                ld      (FDC_IFF), a
                ret

fdc_io_done:
                push    af              ; preserve result (A error code + Cy)
                ld      a, (FDC_IFF)
                or      a
                jr      z, fdc_iod_x    ; caller had interrupts masked: leave masked
                ei                      ; restore the caller's enabled interrupts
fdc_iod_x:
                pop     af
                ret

; div9 — divide HL by 9 (logical sector -> track*2+head, sector-1).
;   in:  HL = logical sector (0..1439)
;   out: B = quotient (HL / 9), L = remainder (0..8), H = 0; A trashed
div9:
                ld      b, 0
fdc_div_loop:
                ld      a, h
                or      a
                jr      nz, fdc_div_sub ; HL >= 256 -> definitely >= 9
                ld      a, l
                cp      9
                jr      c, fdc_div_done ; HL < 9 -> remainder in L
fdc_div_sub:
                ld      a, l
                sub     9
                ld      l, a
                jr      nc, fdc_div_nob
                dec     h
fdc_div_nob:
                inc     b
                jr      fdc_div_loop
fdc_div_done:
                ret

; dskchg — disk-change status inquiry ($4013).
; Returns CF set: "cannot tell".
; 🔴 THIS COMMENT READ "Fail with carry set until FDC driver lands" UNTIL
; 2026-09-09 — and the FDC driver is RIGHT ABOVE IT (`fdc_div_*`, relocated here
; from disk/driver.asm). The prerequisite it named landed long ago; the stub did
; not move, so the reasoning outlived the reason and a reader would go looking for
; a driver that is already there [[a-fix-falsifies-the-justification-beside-it]].
; ⚠️ WHETHER THE STUB SHOULD STAY IS UNMEASURED, and this note does not claim it
; should. "Cannot tell" is a legitimate answer for a driver that does not latch the
; disk-change line, `diskbasic-acceptance` is 34/34 with it, and nothing in the
; tree has yet asked what the reference answers here. That is a row nobody has
; written, not a defect anybody has found.
dskchg:
                scf
                ret

; getdpb — build the Drive Parameter Block from the BPB ($4016 disk-ROM entry).
;
; Builds a real DPB from the on-disk BPB. This is the PROVIDER-direction surface
; (disk/docs/expansion-protocol.md §4a): a real MSX-BASIC / MSX-DOS host calls
; $4016 to obtain the mounted volume's geometry as a DPB, so the provider must
; answer it (a black-box trace of BLOAD/SAVE on the CF-3300 showed Disk BASIC
; DOES call GETDPB). zerobas's own loader path never calls $4016 — it derives
; geometry straight from the BPB (fat_mount) — but a foreign host driving us does.
;
; Calling convention (MSX disk-ROM interface; Nextor 2.1 Driver Development Guide
; §4.5.3, which restates the standard GETDPB contract):
;   in:  A  = drive (unit) number (0 = A:)  — ignored, single-drive machine
;        B  = C = media descriptor byte
;        HL = DPB base address MINUS ONE (the byte at base+0 is the drive number,
;             which GETDPB does NOT fill; GETDPB fills base+1 = media onward)
;   out: Cy = 0 ok (DPB filled), Cy = 1 = error (could not read the boot sector)
;
; DPB field layout + encodings: MSX2 Technical Handbook §3, Figure 3.11 (DPB
; structure), and the Nextor 2.1 Driver Development Guide §4.5.3 field formulas.
; Each field below cites its source + derivation. The whole layout was confirmed
; FIELD-FOR-FIELD against a black-box GETDPB trace of the National CF-3300
; reference on this same 720 KB image (carry=0, DPB bytes read out of RAM — the
; reference ROM's code was never read). See disk/PROVENANCE.md §DPB.
;
; fat_mount already parses the BPB into scratch (FAT_FATSTART / FAT_FIRSTROOT /
; FAT_FIRSTDATA / FAT_SECPERCLUS / FAT_NUMFATS / FAT_SECPERFAT) and leaves the
; boot sector in SECTOR_BUF, so GETDPB reuses those (our own code) and reads the
; remaining raw BPB fields (media, sector size, root-entry count) from SECTOR_BUF.
;
; 🔴 D-FATENG: THE FOUR `SECTOR_BUF + n` READS BELOW ARE THE ONLY LITERAL BUFFER
; REFERENCES LEFT IN THIS FILE, AND THEY ARE DELIBERATE. Everything else now
; loads its base from (DBUF_PTR)/(MBUF_PTR) so one engine can serve two callers.
; GETDPB does not need to: it is the disk DRIVER's $4016 entry (disk/init.asm:31),
; reached by MSX-DOS and by our own init -- never by BASIC, whose loader drives
; DSKIO $4010 instead (basic/fat.asm:10). Its buffer is therefore always the BDOS
; one. Converting them would cost a register getdpb does not have spare: HL walks
; the DPB destination across all four, and IX is not free in this file (22 uses;
; BDOS callers hold the FCB there).
; ⚠️ THE LATENT COUPLING, NAMED SO IT IS NOT REDISCOVERED: `fat_mount` above
; reads the boot sector through (DBUF_PTR). If GETDPB were ever reached while
; that pointer addressed BASIC's buffer, fat_mount would fill THAT buffer and the
; reads below would return stale bytes from SECTOR_BUF. Nothing does this today.
; A slice that makes BASIC reach GETDPB must convert these four first.
getdpb:
                ; HL = DPB base - 1 (Nextor §4.5.3). GETDPB fills from base+1 (media)
                ; onward; base+0 (drive number) is the caller's, not ours. So the
                ; first byte WE write (media) lands at HL+1. (CONFIRMED by the
                ; CF-3300 black-box trace: with HL = $C0FF the reference wrote the
                ; media byte at $C100 = HL+1; see disk/PROVENANCE.md §DPB.)
                inc     hl                  ; HL -> DPB +1 (media ID), = caller HL + 1
                push    hl                  ; keep DPB+1 pointer across fat_mount
                call    fat_mount           ; parse BPB; leaves boot sector in SECTOR_BUF
                pop     hl
                ret     c                   ; boot-sector read failed -> Cy = 1

                ; +1 media ID = BPB media descriptor (boot sector +21). TH Fig 3.11
                ; "media ID"; ECMA-107 / MS FAT spec media byte. (= $F9 on 720 KB.)
                ld      a, (SECTOR_BUF + 21)
                ld      (hl), a
                inc     hl                  ; HL -> DPB +2

                ; +2..3 sector size (LE) = BPB bytes-per-sector. TH Fig 3.11; we
                ; validated $0200 (512) at mount, so copy the BPB word verbatim.
                ld      a, (SECTOR_BUF + BPB_BYTSPERSEC)
                ld      (hl), a
                inc     hl
                ld      a, (SECTOR_BUF + BPB_BYTSPERSEC + 1)
                ld      (hl), a
                inc     hl                  ; HL -> DPB +4

                ; +4 directory mask = (sector size / 32) - 1  (Nextor §4.5.3:
                ; "directory mask = (sector size/32) - 1"). 512/32 - 1 = 15 = $0F.
                ; +5 directory shift = number of one-bits in the directory mask
                ;    (Nextor §4.5.3) = log2(entries per sector) = 4 for 512-byte
                ;    sectors. Sector size is validated = 512 at mount, so these are
                ;    the fixed 512-byte values $0F / $04 (CF-3300 oracle: 0f 04).
                ld      (hl), $0F           ; +4 directory mask
                inc     hl
                ld      (hl), 4             ; +5 directory shift
                inc     hl                  ; HL -> DPB +6

                ; +6 cluster mask = (sectors per cluster) - 1   (Nextor §4.5.3).
                ; +7 cluster shift = (one-bits in cluster mask) + 1 (Nextor §4.5.3);
                ;    for a power-of-two secPerClus this equals log2(secPerClus)+1.
                ;    720 KB: secPerClus = 2 -> mask = 1, shift = 2 (CF-3300: 01 02).
                ld      a, (FAT_SECPERCLUS) ; our own BPB-derived value (fat_mount)
                dec     a
                ld      (hl), a             ; +6 cluster mask = secPerClus - 1
                ld      c, a                ; C = cluster mask (count its one-bits)
                inc     hl                  ; HL -> DPB +7
                ld      b, 1                ; shift starts at 1 (Nextor: +1)
                ld      a, c
                or      a
                jr      z, gdpb_popdone
gdpb_pc_loop:
                srl     c
                jr      nc, gdpb_pc_next
                inc     b                   ; one more set bit -> +1 to the shift
gdpb_pc_next:
                ld      a, c
                or      a
                jr      nz, gdpb_pc_loop
gdpb_popdone:
                ld      (hl), b             ; +7 cluster shift
                inc     hl                  ; HL -> DPB +8

                ; +8..9 top sector of FAT (LE) = first FAT sector = reserved sectors.
                ; TH Fig 3.11 "top sector of FAT"; our FAT_FATSTART (fat_mount).
                ld      de, (FAT_FATSTART)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl                  ; HL -> DPB +10

                ; +10 number of FATs. TH Fig 3.11; our FAT_NUMFATS (BPB +16).
                ld      a, (FAT_NUMFATS)
                ld      (hl), a
                inc     hl                  ; HL -> DPB +11

                ; +11 number of directory entries (max 254). TH Fig 3.11; BPB +17
                ; root-entry count low byte (112 on 720 KB -> $70; high byte is 0).
                ld      a, (SECTOR_BUF + BPB_ROOTENTCNT)
                ld      (hl), a
                inc     hl                  ; HL -> DPB +12

                ; +12..13 top sector of data area (LE) = first data sector.
                ; TH Fig 3.11 "top sector of data area"; our FAT_FIRSTDATA.
                ld      de, (FAT_FIRSTDATA)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl                  ; HL -> DPB +14

                ; +14..15 amount of cluster + 1 (LE). TH Fig 3.11 "amount of cluster
                ; + 1"; = data-cluster count + 1. fat_total_clusters returns
                ; dataClusters + 2 (its highest-cluster-plus-one chain bound), so
                ; the DPB field is that value - 1. (CF-3300 oracle: $02CA = 714 =
                ; dataClusters(713) + 1 on this 720 KB image; fat_total_clusters
                ; returns 715, minus 1 = 714.) Microsoft FAT spec §3.3 cluster count.
                push    hl
                call    fat_total_clusters  ; DE = dataClusters + 2 (reads boot sec into WBUF)
                dec     de                  ; DE = dataClusters + 1 (the DPB encoding)
                pop     hl
                ld      (hl), e
                inc     hl
                ld      (hl), d
                inc     hl                  ; HL -> DPB +16

                ; +16 number of sectors per FAT. TH Fig 3.11; our FAT_SECPERFAT
                ; (BPB +22). 720 KB = 3. Single byte (FAT fits < 256 sectors).
                ld      a, (FAT_SECPERFAT)
                ld      (hl), a
                inc     hl                  ; HL -> DPB +17

                ; +17..18 top sector of directory area (LE) = first root-dir sector.
                ; TH Fig 3.11 "top sector of directory area"; our FAT_FIRSTROOT.
                ld      de, (FAT_FIRSTROOT)
                ld      (hl), e
                inc     hl
                ld      (hl), d
                ; +19..20 (FAT address in memory) is filled by the OS, not GETDPB
                ; (TH Fig 3.11) — left untouched, matching the CF-3300 oracle which
                ; left those two bytes unwritten.
                or      a                   ; Cy = 0 success
                ret

; fopen_fill_body — M21a: the real page-1 FOPEN dir-fill (tier2-m21-spec.md
; §5.2/§0.1). Reached as a page-1 TAIL-CALL from the kernel's FOPEN handler via
; the $4462 veneer (disk/driver.asm) — the return address already on the stack
; is the kernel's own BDOS-exit trampoline (§0.1 Fact 4), so this body's exit
; A/F ARE the BDOS FOPEN result, not an internal call's return value. The
; kernel has already filled FCB +0..+13 (search name/ext/extent/S1) via its own
; SFIRST/SNEXT-sourced LDIR before calling here (§5.2's division-of-labor
; finding) — this body owns ONLY +14(high)..+31.
;   in:  DE = FCB pointer (kernel work buffer, e.g. $DA40 runtime / $DC5B boot)
;   out: found:     A = $00, HL = $0000 (§6/§0.1 pinned contract at $C4A1)
;        not found: A = $FF                (§0.1 Fact 5, matches stock's $D88A)
;        $F306 cleared either way (Tier-2 dispatcher-flag rule, M20)
fopen_fill_body:
                push    de
                pop     ix                  ; IX = FCB pointer throughout
                xor     a
                ld      (ix+14), a          ; +14 unconditional pre-search clear (§0.1 facts 2/3)
                push    ix
                pop     de
                call    fat_mount
                jp      c, ffb_miss
                push    ix
                pop     de
                inc     de                  ; DE -> FCB+1 (11-byte 8.3 name)
                ex      de, hl              ; HL -> name (fat_find's contract)
                call    fat_find            ; Cy=0 found; HL preserved = &matched dirent
                jp      c, ffb_miss
                ; date/time (§0.1 addendum, confirmed against the FAT12 dir-entry
                ; layout on our own test disk): FCB+20/21 := dirent+24/25 (date),
                ; FCB+22/23 := dirent+22/23 (time) — a word-swap vs. the dirent's
                ; own time-then-date order, not a straight 4-byte copy.
                ld      de, 22
                add     hl, de              ; HL -> dirent+22 (time word)
                ld      a, (hl)
                ld      (ix+22), a
                inc     hl
                ld      a, (hl)
                ld      (ix+23), a
                inc     hl                  ; HL -> dirent+24 (date word)
                ld      a, (hl)
                ld      (ix+20), a
                inc     hl
                ld      a, (hl)
                ld      (ix+21), a
                ; +15 record count = ceil(size/128), capped at 128 ($80)
                ld      hl, (FAT_FILESIZE)
                ld      a, l
                and     $7F
                ld      b, a
                ld      a, 7
ffb_shift:
                srl     h
                rr      l
                dec     a
                jr      nz, ffb_shift
                ld      a, b
                or      a
                jr      z, ffb_noround
                inc     hl
ffb_noround:
                ; 🔴 D-FOPENRC (2026-10-01): the cap tested L alone, so a count of
                ; 256 ($0100, a 32 KB file) stored $00 where the CF-3300 stores $80
                ; (disk_probe_wrblk_alt.py --seek's FCB dump), and a size >= 64 KB
                ; lost its high word entirely. ANY high bit caps.
                ld      a, (FAT_FILESIZE + 2)
                ld      b, a
                ld      a, (FAT_FILESIZE + 3)
                or      b
                or      h
                ld      a, $80
                jr      nz, ffb_rcok
                ld      a, l
                cp      $81
                jr      c, ffb_rcok
                ld      a, $80
ffb_rcok:
                ld      (ix+15), a
                ; +16..19 size mirror (4-byte LE)
                push    ix
                pop     hl
                ld      bc, 16
                add     hl, bc
                ex      de, hl
                ld      hl, FAT_FILESIZE
                ld      bc, 4
                ldir
                ; +24 devid: oracle-observed constant (§3 RC-1). +25 dirloc is
                ; left at the kernel's pre-zero — a per-file directory-slot index
                ; we don't compute; confirmed cosmetic-only (the prior M21a run
                ; loaded and executed BDOSX.COM correctly with this field
                ; mismatched — see tier2-review-queue.md).
                ld      (ix+24), $40
                ; +26/27 top cluster, +28/29 last cluster (fresh open: both = first)
                ld      hl, (FAT_FIRSTCLUS)
                ld      (ix+26), l
                ld      (ix+27), h
                ld      (ix+28), l
                ld      (ix+29), h
                ; +30/31 relloc = 0
                ld      (ix+30), 0
                ld      (ix+31), 0
                ; Prime the READ-side iterator (M25, tier2-m24-fclose-
                ; multicluster-spec.md "UPDATE 2"): this body previously only
                ; populated FCB display fields, never the internal read state
                ; $14 RDSEQ depends on -- FAT_CURCLUS/FAT_CLUSSEC (fat_open),
                ; BDOS_RECIDX, BDOS_BYTESLEFT. Those were only ever seeded by
                ; our OWN bdos_open/bdos_rdblk, neither of which runs for a
                ; real kernel-driven $0F FOPEN -- so a subsequent $477D-routed
                ; RDSEQ (see wrseq_body below) found BDOS_BYTESLEFT still $0
                ; and returned a false EOF. Exact mirror of bdos_open's own
                ; read-state seeding (disk/driver.asm); reuses the
                ; FAT_FIRSTCLUS/FAT_FILESIZE this body already read above --
                ; no extra mount/find work.
                call    fat_open
                ld      a, RECPERSEC
                ld      (BDOS_RECIDX), a
                ld      hl, FAT_FILESIZE
                ld      de, BDOS_BYTESLEFT
                ld      bc, 4
                ldir
                ; M33 (tier2-m33-m32-fcb-position-spec.md §2.1): reset the
                ; per-open RDSEQ records-delivered counter alongside the other
                ; read-iterator seeding above (wrseq_writeback increments it).
                ld      hl, 0
                ld      (BDOS_SEQREC), hl
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                ld      hl, 0
                ret
ffb_miss:
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                scf
                ld      a, $FF
                ret

; fren_body — MSX-DOS-1 kernel FREN ($17) canonical entry $4392's real body
; (M26, tier2-m26-spec.md; M35 tier2-m35-m36-tierc-fixes-spec.md §M35 adds the
; collision pre-check below). CLEAN-ROOM: reuses fat_mount/fat_find exactly as
; fopen_fill_body does above (M21a) -- searches the root directory for the
; FCB's OLD 8.3 name (+1..11, CP/M rename convention), then overwrites the
; matched directory entry's name field in place with the NEW 8.3 name
; (+17..27, the "second half" of the rename FCB) and persists it via
; write_sector. fat_find leaves the matched entry inside SECTOR_BUF with
; FAT_DIRSEC holding that entry's own sector number -- exactly the state
; needed to write it back in place; no separate directory-entry-address
; bookkeeping is needed beyond what fat_find already provides.
;
; M35 collision pre-check (bdosx7 differential, Tier-C case 5): before the
; OLD-name find + rename, run a pure existence test on the NEW name
; (FCB+17..27) -- if it is already present, stock refuses the rename (A=$FF,
; mirroring fren_miss's exit) rather than silently producing a duplicate
; directory entry. fat_find takes no IX input and touches no IX-addressed
; state (confirmed: fat_find_body/ff_secloop/ff_found only use AF/BC/DE/HL),
; so IX (the FCB pointer, loaded once at entry) survives this extra call
; unclobbered and is simply re-derived into DE for the real old-name find
; below, byte-unchanged from the pre-M35 body.
fren_body:
                push    de
                pop     ix                  ; IX = FCB pointer
                push    ix
                pop     de
                call    fat_mount
                jp      c, fren_miss
                ; --- M35 collision pre-check: new name (FCB+17) must NOT already exist ---
                push    ix
                pop     hl
                ld      bc, 17
                add     hl, bc              ; HL -> FCB+17 (new 8.3 name, fat_find's contract)
                call    fat_find            ; Cy=0 -> new name FOUND (collision)
                jp      nc, fren_miss       ; refuse the rename, stock-matching A=$FF exit
                ; --- fall through: new name is free; proceed with the OLD-name find + rename ---
                push    ix
                pop     de
                inc     de                  ; DE -> FCB+1 (old 8.3 name)
                ex      de, hl              ; HL -> name (fat_find's contract)
                call    fat_find            ; Cy=0 found; HL = &matched dirent (in SECTOR_BUF)
                jp      c, fren_miss
                ex      de, hl              ; DE = &matched dirent (write destination)
                push    ix
                pop     hl
                ld      bc, 17
                add     hl, bc              ; HL = FCB+17 (new 8.3 name, source)
                ld      bc, 11
                ldir                        ; overwrite the dirent's name in place
                ld      de, (FAT_DIRSEC)
                ld      hl, (DBUF_PTR)
                call    write_sector
                jp      c, fren_ioerr
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                ret
fren_miss:
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                scf
                ld      a, $FF
                ret
fren_ioerr:
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                scf
                ld      a, 2                ; generic FDC I/O error (fdc_read_data convention)
                ret

; rdabs_body — MSX-DOS-1 kernel RDABS ($2F) canonical entry $46BA's real body
; (M26, tier2-m26-spec.md §2.4). CLEAN-ROOM, from the published contract
; (map.grauw.nl BDOS function reference, disk/docs/tier2-bdos-remaining-spec.md
; §2 table): in DE = start logical sector, H = sector count, L = drive
; (ignored -- single-drive ROM, same convention as read_sector/write_sector
; above). Target buffer = the runtime DTA (DOS_DTAPTR, $F23D -- M19/M21
; precedent, NOT our own internal BDOS_DTA cell). Calls dskio directly
; (disk/driver.asm) rather than read_sector, since RDABS must honour an
; arbitrary sector count, not just one.
; Exit contract empirically pinned via `capture` (BDOSX3 record 22, H=1):
; stock's own A=$00 B=$00 C=$01 D=$00 E=$00 H=$00 L=$00 on success -- C
; carries the original sector count (not officially documented; matched here
; since BDOSX3's zero-diff bar covers full register state, same discipline
; as M22a's VERIFY/CPMVER register-parity work). dskio clobbers B/C
; internally for its own CHS bookkeeping, so the original count is saved
; across the call on the stack, not left in a register.
rdabs_body:
                ld      b, h                ; B := sector count (dskio's own count param)
                push    bc                  ; preserve original count across the dskio call
                ld      hl, (DOS_DTAPTR)    ; target = runtime DTA
                xor     a                   ; drive ignored (single-drive); Cy=0 = read
                call    dskio
                pop     bc                  ; B := original count again (dskio clobbers B/C)
                jp      c, rdabs_ioerr
                ld      a, b                ; A := original count
                ld      c, a                ; C := count (pinned exit value)
                xor     a
                ld      b, a                ; B := $00 (pinned exit value)
                ld      ($F306), a          ; M20 dispatcher-flag rule
                ld      h, a
                ld      l, a                ; H=L=$00 (pinned exit value)
                ret
rdabs_ioerr:
                ld      b, a                ; preserve dskio's error code
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                ld      a, b                ; restore error code
                scf
                ret

; wrabs_body — MSX-DOS-1 kernel WRABS ($30) canonical entry $4720's real body
; (M26, tier2-m26-spec.md §2.5/§7). CLEAN-ROOM, mirror of rdabs_body above:
; in DE = start logical sector, H = sector count, L = drive (ignored --
; single-drive ROM). Source buffer = the runtime DTA (DOS_DTAPTR, $F23D).
; Calls dskio directly with Cy=1 (write direction) rather than a fixed-count
; wrapper, for the same arbitrary-count reason as RDABS. Entry/exit register
; contract pinned by black-box `capture` (BDOSX3 record 23, H=1): identical
; shape to RDABS's own pinned contract -- A=$00 B=$00 C=$01 D=$00 E=$00
; H=$00 L=$00 on success, C carrying the original sector count.
wrabs_body:
                ld      b, h                ; B := sector count (dskio's own count param)
                push    bc                  ; preserve original count across the dskio call
                ld      hl, (DOS_DTAPTR)    ; source = runtime DTA
                xor     a                   ; drive 0 (ignored, single-drive)
                scf                         ; Cy=1 = write direction (MSX2 TH DSKIO)
                call    dskio
                pop     bc                  ; B := original count again (dskio clobbers B/C)
                jp      c, wrabs_ioerr
                ld      a, b                ; A := original count
                ld      c, a                ; C := count (pinned exit value)
                xor     a
                ld      b, a                ; B := $00 (pinned exit value)
                ld      ($F306), a          ; M20 dispatcher-flag rule
                ld      h, a
                ld      l, a                ; H=L=$00 (pinned exit value)
                ret
wrabs_ioerr:
                ld      b, a                ; preserve dskio's error code
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                ld      a, b                ; restore error code
                scf
                ret
