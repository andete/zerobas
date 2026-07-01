; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; Part of zerobas-disk, included by disk.asm (build with `pasmo -I disk`).
; ROM header + signature, INIT, DOS-boot bridge, $4030/$50A9, DRVTBL, work-area builders + templates
; CLEAN-ROOM: every constant, address and algorithm here traces to a public source
; or a black-box oracle probe; nothing is derived from disassembly. See disk/PROVENANCE.md.

; --- ROM skeleton -----------------------------------------------------------
                org     $4000

; --- MSX cartridge / disk-ROM header ---------------------------------------
; Standard 16-byte cartridge header (MSX2 TH, cartridge ROM format), identical
; in shape to the main zerobas ROM: ID, INIT, STATEMENT, DEVICE, TEXT, then 6
; reserved bytes. INIT is a *word* at $4002 (the BIOS CALLs through it); the
; header is exactly 16 bytes, so the disk entry-point table begins at $4010.
                db      "AB"            ; ROM signature              ($4000)
                dw      init            ; INIT entry point           ($4002)
                dw      0               ; STATEMENT expansion (none) ($4004)
                dw      0               ; DEVICE expansion (none)    ($4006)
                dw      0               ; TEXT / BASIC program (none)($4008)
                dw      0,0,0           ; reserved                   ($400A-$400F)

; --- Disk-ROM entry-point table (MSX2 TH, disk ROM interface) --------------
; Six JP instructions at fixed offsets from the ROM base. The BIOS disk
; subsystem CALLs these; each is 3 bytes, so they land exactly on the +$10,
; +$13, +$16, +$19, +$1C, +$1F boundaries. The `ds` guard is a compile-time
; assert that the header above is exactly 16 bytes (pasmo errors if $ > $4010).
                ds      $4010 - $, $00
                jp      dskio           ; +$10  sector read/write    ($4010)
                jp      dskchg          ; +$13  disk-change status   ($4013)
                jp      getdpb          ; +$16  build DPB from BPB   ($4016)
                jp      choice          ; +$19  format-choice string ($4019)
                jp      dskfmt          ; +$1C  format disk          ($401C)
                jp      mtoff           ; +$1F  motors off           ($401F)

; --- extended disk-ROM kernel entry: $4030 ($4000 + $30) -------------------
; MSXDOS.SYS's resident init CALLs $4030 expecting the disk ROM's "get work area"
; routine. The six standard entries above end at $401F; the $4022-$402F slots are
; further disk-ROM/DOS-kernel entries. The MSX-DOS-1 *boot* does not call them
; (a3 §8.11), but the later COMMAND.COM-load phase calls $402D (×944 on stock,
; disk_probe_dosboot_veneer.py), so $402D now carries a Tier-2 kernel veneer; the
; rest of $4022-$402C stay $00 fill. $4030 IGNORES its inputs and returns a fixed
; work-area pointer in HL, preserving every other register (black-box oracle, a3
; §8.13: disk_probe_dosboot_4030.py --sweep). Inlined at exactly $4030 (not a JP)
; so it lands on the address the boot CALLs; `ld hl,nn`+`ret` preserves AF too.
                ds      $402D - $, $00  ; pad $4022-$402C (unused kernel-entry slots)
                jp      k_402D          ; $402D: COMMAND.COM-load kernel entry (Tier-2)
                ld      hl, GETWRK_AREA ; $4030: return our work-area base
                ret                     ; ($4033) HL = work area, all else preserved

; --- INIT -------------------------------------------------------------------
; Called by the BIOS boot scan (or by zerobas-BASIC's slot scan, which finishes
; the scan C-BIOS skips — see basic/initext.asm). INIT does two things:
;
;   1. installs the standard HPHYD ($FFA7) -> DSKIO ($4010) inter-slot hook, so a
;      real MSX-BASIC / MSX-DOS host that issues PHYDIO reaches our sector engine.
;      This is the PROVIDER-direction surface (disk/docs/expansion-protocol.md
;      §4a/§5): the loader path on a standard machine is HPHYD -> DSKIO, and a
;      foreign host drives us through it. The host direction (zerobas-BASIC) does
;      NOT use this hook — it reaches the file layer through the SYSTEM vector
;      below — but installing HPHYD makes zerobas-disk a standard provider.
;
;   2. publishes the BDOS entry-point address into the SYSTEM sysvar ($F37D) and
;      seeds the default DTA (the INTERNAL path: zerobas-BASIC reaches the file
;      layer through this SYSTEM-vector BDOS entry, called across slots with
;      CALSLT — the entry *address* read back from $F37D, the slot from the INIT
;      scan's DISKSLOT capture). This is differentially oracle-confirmed
;      (disk_probe_bdos.py vs real MSX-DOS 1) and is kept alongside the new hook.
;
; HPHYD hook idiom (observed on the National CF-3300, disk/PROVENANCE.md §INIT;
; MSX2 TH §2 inter-slot calls): the 5 hook bytes are an inter-slot CALLF —
;   F7 <slot> <lo> <hi> C9  =  RST 30h ; slot id ; target addr ; RET
; F7 = RST 30h = CALLF, the BIOS inter-slot-call restart (a plain JP cannot cross
; slots). We point it at our own DSKIO entry ($4010) with this ROM's slot byte.
;
; OWN SLOT BYTE (the hard sub-problem). The MSX cartridge/disk INIT convention
; passes the ROM's slot id to INIT in a register (MSX2 TH cartridge-ROM INIT
; convention); established here by black-box oracle — a trace of the CF-3300 BIOS
; calling its disk INIT observed A = C = $87 = slot 3-1. zerobas-BASIC's own slot scan
; (basic/initext.asm) likewise leaves the slot byte in A at the CALSLT to this
; INIT: it does `ld a,(SCAN_SLOT)` immediately before loading IY/IX and calling
; CALSLT, and CALSLT passes AF through to the target — black-box confirmed: at
; our INIT entry A = $87 (slot 3-1) on every C-BIOS_MSX1_*_BASIC_DISK machine.
; So we read the slot byte from A as the FIRST thing INIT does, before anything
; clobbers it. COUPLING: this depends on the caller delivering the slot in A,
; which both the standard BIOS scan and basic/initext.asm do (the latter is our
; own code; the dependence is documented here and in disk/PROVENANCE.md §INIT).
;
; Sources: SYSTEM $F37D — MSX2 TH, work area; C-BIOS systemvars.asm. HPHYD $FFA7,
; CALLF/RST 30h idiom — disk/docs/expansion-protocol.md (CF-3300 black-box trace)
; + MSX2 TH §2. Slot-in-A INIT convention — MSX2 TH + CF-3300/own-scan oracle.
init:
                ; --- capture this ROM's slot byte (A on INIT entry; see header) ---
                ; Do this FIRST, before anything clobbers A.
                ld      (HOOK_SLOT), a      ; HOOK_SLOT = our slot byte (e.g. $87 = 3-1)

                ; --- install HPHYD ($FFA7) -> DSKIO ($4010) inter-slot CALLF ----
                ; Write the 5 hook bytes: F7 <slot> 10 40 C9
                ;   = RST 30h ; slot ; addr-lo ; addr-hi ; RET   (CALLF, MSX2 TH §2)
                ld      a, $F7              ; +0: RST 30h opcode (CALLF)
                ld      (HPHYD + 0), a
                ld      a, (HOOK_SLOT)      ; +1: this ROM's slot byte
                ld      (HPHYD + 1), a
                ld      a, low DSKIO_ENTRY  ; +2: target addr low  ($10)
                ld      (HPHYD + 2), a
                ld      a, high DSKIO_ENTRY ; +3: target addr high ($40)
                ld      (HPHYD + 3), a
                ld      a, $C9              ; +4: RET
                ld      (HPHYD + 4), a

                ; --- publish the BDOS entry as an executable JP vector ---------
                ; $F37D (SYSTEM) is the disk system's BDOS-call jump vector. The
                ; MSX-DOS boot CALLs it to Open/Read MSXDOS.SYS — black-box (a3
                ; §8.9): at step 7 the boot-sector code does `CALL $F37D` with
                ; C=$0F (BDOS Open File) and DE = an FCB in the boot sector. So
                ; $F37D must hold `JP <bdos dispatcher>`, NOT a bare address word:
                ; the boot EXECUTES these bytes (our old raw word `9F 43` ran as
                ; `SBC A,A / LD B,E / RST 38h` -> the $0038 wedge). Our bdos_entry
                ; is an oracle-validated FCB BDOS (Open $0F / SeqRead $14 / Close
                ; $10 / SetDTA $1A), and it is reachable from here even with RAM in
                ; page 0: our ROM stays in page 1 and bdos_entry's scratch is all
                ; page-3 RAM, both mapped throughout boot. zerobas-BASIC's own
                ; loader no longer reads $F37D (Phase 1.5 moved it to DSKIO + own
                ; FAT; see basic/sysvars.inc), so the JP form is free to install.
                ld      a, $C3              ; JP opcode
                ld      (SYSTEM), a
                ld      hl, bdos_entry
                ld      (SYSTEM + 1), hl    ; $F37D = C3 <bdos_entry lo> <hi>
                ; default the settable DTA to the MSX-DOS default ($0080) so a
                ; SeqRead before any $1A behaves as MSX-DOS does.
                ld      hl, DTA_DEFAULT
                ld      (BDOS_DTA), hl
                ; --- populate RAMAD0-3 so MSX-DOS can re-page RAM into page 0 ---
                ; The disk ROM's INIT owns the per-page RAM-slot table (§8.8/§8.16):
                ; MSXDOS.SYS's resident init reads RAMAD0-3 ($F341-4) to map RAM into
                ; page 0 (where the BIOS ROM was), and without it pages an empty slot
                ; ($FF) and wedges at $0038. set_ramad fills RAMAD only when the host
                ; left it uninitialised ($FF), so the C-BIOS hosts (which set their own
                ; RAMAD) are untouched. (provider-oracle-scope.md §8.16)
                call    set_ramad
                ; fall into the DOS-boot bridge (TH ch.3); it returns to the BIOS
                ; boot scan, falling through to BASIC for a non-system disk.
                ; --- intentional fall-through to boot_disk -------------------

; --- DOS-boot bridge (slice 2-Tier2-a1; MSX2 TH ch.3 steps 4-5) ------------
; Read logical sector 0 into the standard boot load address $C000; if it carries
; a boot signature ($EB/$E9 at byte 0) run the "custom boot program" at $C01E
; with CY reset (step 5). A data disk's byte $1E is the documented RET NC stub,
; so this returns and INIT falls through to BASIC unchanged — the regression-safe
; property (the bridge runs in every host's INIT). Steps 6-7 (the page-0 MSX-DOS
; environment + the CY-set $C01E) are slice a2; see provider-oracle-scope.md §8.
; No disk / read error / no signature all return cleanly to BASIC.
BOOT_LOAD       equ     $C000   ; standard boot-sector load address (MSX2 TH ch.3)
BOOT_ENTRY      equ     $C01E   ; custom-boot-program entry (BOOT_LOAD + $1E)
; page-0 RAM-swap scratch (transient, used only during INIT's boot bridge).
BOOT_SV_A8      equ     $E760   ; saved $A8 primary-slot config
BOOT_SV_SEC     equ     $E761   ; saved slot secondary ($FFFF) live value
; step-6 page-0 environment scratch (transient; used only by the $0030 CALLF
; handler and the CALSLT handler during the boot bridge). The $0030 handler must
; deliver A,B,C,DE,HL UNTOUCHED to the DSKIO callee, so it saves them here while
; it reads the inline CALLF operand off the stack. Own-choice free page-3 RAM
; after BOOT_SV_SEC. (provider-oracle-scope.md §8.4)
R30_HL          equ     $E762   ; $0030 handler: saved caller HL (word)
R30_BC          equ     $E764   ; $0030 handler: saved caller BC (word)
R30_DE          equ     $E766   ; $0030 handler: saved caller DE (word)
R30_AF          equ     $E768   ; $0030 handler: saved caller AF incl. carry (word)
CALSLT_HL       equ     $E76A   ; CALSLT handler: HL stash across the call setup (word)
; BDOS $27 (Random Block Read) scratch — transient within one RDBLK call. Own-choice
; free page-3 RAM after the step-6 block. Only the DOS-boot path (on a real-BIOS host)
; calls $27, so this never collides with the zerobas-BASIC host buffers (which use
; the standard DSKIO path, not bdos_entry). (disk/PROVENANCE.md §BDOS interface)
RDBLK_REQ       equ     $E76C   ; records requested (HL on entry) (word)
RDBLK_RECSIZE   equ     $E76E   ; record size from FCB+14 (word)
RDBLK_DONE      equ     $E770   ; records delivered so far (word; = HL on return)
RDBLK_CNT       equ     $E772   ; bytes left in the current record (word)
RDBLK_BUFPOS    equ     $E774   ; byte offset into SECTOR_BUF (word, 0..512)
RDBLK_DST       equ     $E776   ; current DTA write pointer (word; from BDOS_DTA)
; page-1 transfer bounce scratch (a3 §8.35; free page-3 RAM after RDBLK_DST)
P1_DEST         equ     $E778   ; saved page-1 destination word (dskio bounce path)
P1_BLIT         equ     $E77A   ; runtime address of the installed blit routine
; work-area segment-switch hooks ($F368/$F36B bodies), §8.58 / tier2-m5.6-spec.md.
; Installed into page-3 RAM immediately after P1_BLIT (one LDIR copies both, so
; WA_SEG must equal P1_BLIT + the blit length); entry offsets fixed by the template.
WA_SEG          equ     P1_BLIT + (p1_blit_end - p1_blit_tmpl)  ; base of the two hook bodies
; Inter-slot helper scratch (M8/§8.67 CONOUT + A-2/§8.70 int_h): transient page-3 RAM
; right after the WA_SEG hook bodies — dead during the DOS phase (SP is in page 2/3),
; written+read within one DI'd call. PG_SV_A8 is shared by both page-0 main-ROM calls.
CONOUT_CHAR     equ     WA_SEG + (wa_seg_end_tmpl - wa_seg_rom_tmpl)  ; CONOUT: saved char
PG_SV_A8        equ     CONOUT_CHAR + 1                              ; shared: saved $A8 config
; A-2b (tier2-a2b-spec.md): a private interrupt stack so int_h_body is NON-DESTRUCTIVE
; when an interrupt fires with a corrupt caller SP (a primary derail) — it never marches
; that stack through memory. int_h saves the caller SP, runs on its own 48-byte stack,
; then restores. INT_SP_SAVE sits ABOVE the stack top so a (pathological) overflow can't
; clobber the saved SP, keeping the return clean. Region: PG_SV_A8+1 .. INT_SP_SAVE+1
; resolves to $E7B2..$E7E3, clear of DRV_TRAMP ($E800). Own-choice free page-3 RAM; the
; ld (nn),sp / ld sp,(nn) save-restore is own-design, no oracle bytes (clean-room).
INT_STK_TOP     equ     PG_SV_A8 + 1 + 48                           ; SP top; 48-byte stack grows down
INT_SP_SAVE     equ     INT_STK_TOP                                 ; caller SP saved above the stack top (word)
; M13 (tier2-conin-spec.md v3): conin_line_body scratch, right after INT_SP_SAVE (word) --
; dead during the DOS phase like the other inter-slot scratch above; clear of DRV_TRAMP
; ($E800). CONIN_BUF stashes the caller's DE (buffer base) across pg0_mainrom_in/out,
; which clobber D/E; CONIN_MAX/CONIN_COUNT track the func-$0A buffer fill state.
CONIN_BUF       equ     INT_SP_SAVE + 2                             ; CONIN: buffer base (word)
CONIN_MAX       equ     CONIN_BUF + 2                                ; CONIN: max length ([DE+0])
CONIN_COUNT     equ     CONIN_MAX + 1                                ; CONIN: running fill count
; A-3 (tier2-a3-spec.md): the maskable-interrupt handler must live in ALWAYS-MAPPED
; memory. $0038 fires AFTER COMMAND.COM reclaims page 1 as RAM (wa_seg_ram), so a
; page-1 handler ($4251/int_h_body) is unmapped exactly when it is needed and the boot
; storms ($0038->$FF rst-loop). We install int_h_hiram_tmpl into page-3 high RAM here
; and point $0038 at it. $DDAE = stock's own handler address (oracle data point: WHERE,
; not how) — above MSXDOS.SYS's ~$DC7F landing + COMMAND.COM's stack, verified $FF and
; untouched on ours across the whole boot (harness read_block/write_watch, 2026-06-26).
INT_H_HIRAM     equ     $DDAE
SLTTBL          equ     $FCC5   ; SLTTBL base: per-primary mirror of the secondary-slot regs
SLTTBL3         equ     $FCC8   ; SLTTBL[3]: RAM mirror of slot-3 secondary-slot register (=SLTTBL+3)

; --- MSX-DOS-1 "get work area" return ($4030; a3 §8.13) ---------------------
; MSXDOS.SYS's resident init CALLs disk-ROM entry $4030 and uses the returned HL
; as a work-area base pointer. Black-box oracle (disk_probe_dosboot_4030.py
; --sweep on the genuine CF-3300): $4030 IGNORES its inputs and returns a FIXED
; pointer, preserving AF/BC/DE/IX/IY. We return a pointer to our own reserved
; page-3 RAM; the size + layout MSXDOS.SYS then expects at that pointer is the next
; oracle target.
;
; KERNEL-PLACEMENT LEVER (a3 §8.24). Black-box differential of the BDOS-vector write
; (disk_probe_dosboot_ramtop.py): MSXDOS.SYS places its resident kernel so its TOP
; sits at THIS work-area pointer and its base $067A (the kernel size) below it
; -- stock work area $DD0E -> kernel $D606; our old $E780 -> kernel $E106, straight
; onto our $E29A+ scratch (the §8.19 collision). NOT DRVTBL+1/HIMEM (§8.20/§8.23).
; So we return the STOCK's $DD0E: the kernel lands at $D6xx, below our scratch, and
; the 128-byte work area DOS fills ($DD0E-$DD8E) is clear of both kernel and scratch.
GETWRK_AREA     equ     $DD0E   ; MSX-DOS work-area base returned by $4030 (128 B reserved);
                                ; = the stock value so MSXDOS's kernel lands below our scratch
; --- MSX-DOS-1 kernel continuation entry $50A9 (a3 §8.26/§8.27) -------------
; After publishing its BDOS vector the relocated kernel does `CALL $50A9` (page 1 =
; our disk ROM, so it lands here). Black-box oracle (disk_probe_dosboot_50a9.py
; --stock): the routine IGNORES its register inputs, makes exactly ONE persistent
; memory write ($50A9_WRKB := $00, via its internal CALL $472D), and returns a fixed
; register contract -- A=0 / Z+N (AF=$0042), DE=IX=$F1AA, HL=$F359, BC + IY preserved.
; The returned HL/DE/IX point into the disk work area the kernel/disk-ROM already
; built; this entry only hands them back (it does not populate them). We reproduce the
; observed contract with our own code; the stock's $472D body is never disassembled.
W50A9_WRKB      equ     $F242   ; the one work-area cell $50A9 clears (semantic: black-box)
W50A9_RET_DE    equ     $F1AA   ; DE (= IX) on return: disk work-area pointer
W50A9_RET_HL    equ     $F359   ; HL on return: disk work-area pointer (DRVTBL+$11 region)
; --- $F348 DRVTBL: the disk-driver table MSXDOS.SYS dispatches through (§8.22) ---
; The disk ROM (not MSXDOS) builds this table; MSXDOS reads it to find the disk
; interface's slot, its reserved top-of-RAM, and the driver-routine pointers. The
; four driver pointers are always-mapped page-3 trampolines (the boot/DOS calls them
; while the disk ROM is NOT in any page, so a direct $40xx call won't reach it). We
; synthesise each as the proven H.PHYD form -- a self-contained CALLF stub
; `F7 <slot> <lo> <hi> C9` (RST 30h inter-slot call; MSX2 TH §2) -- into our own
; $4010-region BIOS entries, never the stock's $EF95 kernel bytes. DRV_TRAMP holds
; them in reserved page-3 RAM past the $4030 work area (free, gated DOS path only).
DRV_TRAMP       equ     $E800   ; 4 CALLF trampolines, 5 bytes each ($E800-$E813)
; Reserved top-of-RAM advertised in DRVTBL+1 (the stock's HIMEM value). NOTE: this is
; NOT the kernel-placement lever -- §8.20 ruled out HIMEM, §8.23 ruled out DRVTBL+1,
; and §8.24 proved the lever is DRVTBL+3 (the $4030 work-area pointer, GETWRK_AREA
; above). We still advertise the stock $DF93 here for fidelity (MSXDOS reads it), but
; placement is governed by GETWRK_AREA, not this field.
DOS_RESV_TOP    equ     $DF93   ; top-of-reserved-RAM advertised in DRVTBL+1 (not the lever)
boot_disk:
                xor     a               ; drive A
                ld      b, 1            ; one sector
                ld      c, a            ; media byte (ignored, single-drive)
                ld      de, 0           ; logical sector 0 (the boot sector)
                ld      hl, BOOT_LOAD   ; -> $C000 (page-3 RAM)
                or      a               ; Cy = 0 -> read
                call    dskio
                ret     c               ; no disk / read error -> BASIC
                ld      a, (BOOT_LOAD)  ; first byte = boot signature?
                cp      $EB
                jr      z, boot_sig_ok
                cp      $E9
                ret     nz              ; not a boot disk -> BASIC
boot_sig_ok:
                or      a               ; Cy = 0 -> step-5 "custom boot" call
                call    BOOT_ENTRY      ; step 5 (data-disk default RET NC returns here)
                ; --- step 6: stand up the page-0 MSX-DOS environment ----------
                ; Switch RAM into page 0 (the page-0 BIOS ROM, incl. the inter-slot
                ; primitives, vanishes) and lay the JP-vector set the boot code +
                ; MSXDOS.SYS dereference there (RDSLT/CALSLT/ENASLT/CALLF + the int
                ; vector) as our OWN page-1 handlers. Interrupts stay OFF the whole
                ; time: while page 0 is RAM the $0038 cell is not yet the BIOS
                ; handler. (provider-oracle-scope.md §8.4/§8.6)
                di
                call    page0_ram_in    ; RAM into page 0 (host-adaptive, gap B)
                call    lay_page0_env   ; write the inter-slot vector set into page 0
                ; --- hand the drive-A DPB pointer to MSXDOS.SYS in IX (§8.31) ---
                ; The disk-ROM boot procedure must enter MSXDOS.SYS with IX = the
                ; drive-A DPB pointer; MSXDOS.SYS keeps it (it CALLs $4030/$50A9 which
                ; PRESERVE IX, §8.13/§8.26) and dereferences it to read the directory +
                ; COMMAND.COM. Black-box: stock MSXDOS.SYS entry ($0200) has IX=$F195;
                ; ours had IX=$4034 (junk carried from INIT) -> the kernel computed a
                ; garbage DPB pointer and bailed to "Insert DOS disk" (§8.30). The boot
                ; sector PRESERVES IX from $C01E to the MSXDOS.SYS jump (measured), so
                ; setting it here propagates to entry. $F195 is built by build_resident
                ; (above, this same INIT) before boot_disk runs.
                ld      ix, DRVA_DPB    ; IX = $F195 = drive-A DPB the kernel expects
                ; --- step 7: CY-set $C01E -- "load the system" -----------------
                ; A real DOS disk's boot code now loads MSXDOS.SYS at $0100 and JPs
                ; in (no return). A non-system / data disk's $1E stub (D0 C9) takes
                ; the C9 RET on CY set and returns here, so we MUST tear the env
                ; back down before BASIC: this runs in every host's INIT, incl. the
                ; C-BIOS_*_BASIC_DISK regression on test720.dsk (sig $EB, stub D0 C9).
                ; dos_handoff (free-tail) defaults $F338=0 for DOS -- COMMAND.COM's
                ; "no AUTOEXEC -> prompt" branch (`ld a,($F338);and a;jr nz` @ $C26B) --
                ; restoring the host's dual-purpose stub for a returning data disk, then
                ; does the scf + step-7 call. Subroutine, not inline: this region is
                ; pad-packed to the $41FD anchor. (tier2-f338-default-spec.md)
                call    dos_handoff     ; DOS disk JPs into MSXDOS.SYS (no return)
                call    page0_ram_out   ; data disk returned: BIOS ROM back in page 0
                ei
                ret                     ; -> BIOS boot scan -> BASIC

; page0_ram_in — map page 3's slot/subslot (always RAM: the stack lives there)
; into page 0, so the boot code/MSXDOS see RAM where the BIOS ROM was. Derives
; the RAM slot from page 3 (gap B: host-adaptive, never hardcoded slot 3-0).
; Caller MUST DI (while page 0 is RAM the $0038 int vector is not the BIOS). Saves
; the originals for page0_ram_out. Clobbers A, C. (provider-oracle-scope.md §8.2)
page0_ram_in:
                in      a, ($A8)            ; primary slot config
                ld      (BOOT_SV_A8), a
                ld      a, ($FFFF)          ; slot secondary reg (reads inverted)
                cpl                         ; -> live value
                ld      (BOOT_SV_SEC), a
                ; page-0 primary := page-3 primary  ($A8 bits 7-6 -> bits 1-0)
                ld      a, (BOOT_SV_A8)
                and     %11000000
                rlca
                rlca
                ld      c, a
                ld      a, (BOOT_SV_A8)
                and     %11111100
                or      c
                out     ($A8), a
                ; page-0 subslot := page-3 subslot  ($FFFF bits 7-6 -> bits 1-0)
                ld      a, (BOOT_SV_SEC)
                and     %11000000
                rlca
                rlca
                ld      c, a
                ld      a, (BOOT_SV_SEC)
                and     %11111100
                or      c
                ld      ($FFFF), a
                ret

; page0_ram_out — restore the original page-0 mapping (BIOS ROM back in page 0).
page0_ram_out:
                ld      a, (BOOT_SV_SEC)
                ld      ($FFFF), a
                ld      a, (BOOT_SV_A8)
                out     ($A8), a
                ret

; set_ramad — populate RAMAD0-3 ($F341-4) with the host's RAM-slot id, so MSX-DOS
; can re-page RAM into page 0. The real CF-3300 main BIOS sets only EXPTBL and
; leaves RAMAD to the disk ROM (black-box differential, §8.8/§8.16); MSXDOS.SYS's
; resident init then reads RAMAD0-3 (84 reads observed on the stock, §8.16) to map
; RAM where the page-0 BIOS ROM was. Without it MSX-DOS pages an empty slot ($FF)
; and the CPU wedges at $0038 ($FF = RST 38h self-loop).
;
; HOST-ADAPTIVE + REGRESSION-SAFE. RAMAD is filled ONLY when the host left it
; uninitialised ($FF) -- the real-CF-3300 case where the disk-ROM job was skipped.
; The C-BIOS hosts set their own RAMAD (observed $C9..), so the $FF gate leaves them
; exactly as they were (and C-BIOS never boots DOS, so nothing reads RAMAD there).
;
; The value is the RAM slot id in standard F000SSPP form, derived from PAGE 3 (always
; RAM: the stack lives there) the same host-adaptive way page0_ram_in derives its
; swap slot -- primary from $A8 bits 15-14, and, if that primary is expanded (EXPTBL
; bit 7), the subslot from $FFFF. All four pages share this slot on the single-RAM-
; slot machines we target (CF-3300: slot 3-0 = $83, matching the stock's RAMAD0).
; Sources: MSX2 TH work area (RAMAD0-3, EXPTBL) + MSX2 TH ch.2 slot handling. No
; disk-ROM/MSX-DOS code is read; the disk-ROM-INIT responsibility + the read are
; black-box oracle observations (§8.8/§8.16).
set_ramad:
                ld      a, (RAMAD0)
                inc     a                   ; $FF -> $00 (Z): RAMAD uninitialised?
                ret     nz                  ; host already set RAMAD -> leave it alone
                ; --- clear the disk work-area flag $F340 (§8.33) -------------------
                ; MSXDOS.SYS init reads $F340 right after $4030 ($0246:
                ; LD A,($F340) / AND A / CALL Z,$0317): $00 = take the normal init
                ; path. The disk ROM clears it; ours left it uninitialised ($FF) ->
                ; AND A non-zero -> the CALL Z is skipped -> MSXDOS.SYS derails into a
                ; loop ($027C). Clear it here (after the gate, so the $FF gate check
                ; above is unaffected). Own work-area init; black-box (§8.33).
                xor     a
                ld      (DOS_F340), a
                ; --- derive the page-3 RAM slot id (F000SSPP) ---
                in      a, ($A8)
                rlca
                rlca
                and     3                   ; A = page-3 primary slot (PP)
                ld      c, a                ; C = PP
                ld      b, 0
                ld      hl, EXPTBL
                add     hl, bc              ; -> EXPTBL[PP]
                bit     7, (hl)             ; primary expanded?
                ld      a, c                ; not expanded: slot id = PP (flags preserved)
                jr      z, sr_store
                ld      a, ($FFFF)          ; expanded: fold in the page-3 subslot
                cpl                         ; $FFFF reads inverted -> live value
                rlca
                rlca
                and     3                   ; page-3 subslot (SS)
                rlca
                rlca                        ; SS << 2 (into bits 3-2)
                or      c                   ; | PP
                or      $80                 ; | expanded flag (bit 7)
sr_store:
                ld      (RAMAD0 + 0), a     ; page 0
                ld      (RAMAD0 + 1), a     ; page 1
                ld      (RAMAD0 + 2), a     ; page 2
                ld      (RAMAD0 + 3), a     ; page 3
                ; fall through to build the $F368 disk-work-area jump table -------
                ; (only reached under the same $FF gate -- the real-CF-3300 DOS host)

; build_wa_table — lay the disk system's resident jump table at $F368-$F37C.
; MSXDOS.SYS's resident init CALLs fixed work-area entries $F368/$F36B (the disk
; system's RAM-segment-switch hooks); on a 64K MSX with no memory mapper these are
; no-ops (one segment), confirmed black-box on the stock CF-3300: the calls are
; register/flag-transparent with NO memory, FDC, or I/O-port effects (§8.18,
; disk_probe_dosboot_f368.py). Absent the table our $F368 reads $FF and the CALL
; slides through $FF as RST 38h (the §8.17 derail). We point the seven slots
; $F368..$F37A at our own RET stub (wa_stub); $F37D (SYSTEM) is already our
; JP bdos_entry from INIT and is left intact (the loop stops at $F37C). The stub
; lives in our page-1 ROM, reachable exactly as int_h/$0038 already is (page 1 stays
; our disk ROM through boot). Clean-room: our own RET; the stock's $DFxx targets are
; never read. Source: MSX2 TH disk work area + MSX-DOS segment-switch hook model.
WA_JMPTAB       equ     $F368   ; disk-work-area resident jump table ($F368-$F37C, 7 slots)
build_wa_table:
                ld      hl, WA_JMPTAB
                ld      b, 7                ; 7 JP slots $F368..$F37A (3 bytes each)
bwt_loop:
                ld      (hl), $C3           ; JP opcode
                inc     hl
                ld      (hl), low wa_stub
                inc     hl
                ld      (hl), high wa_stub
                inc     hl
                djnz    bwt_loop
                ; Overwrite slots 0/1 with the real segment-switch bodies (§8.58):
                ; $F368 = map disk ROM into page 1, $F36B = map RAM into page 1. The
                ; remaining slots ($F36E/$F371/$F374) stay wa_stub -- never CALLed in
                ; the COMMAND.COM-load->A> trace (ncalls 0); $F377/$F37A unused.
                ld      hl, WA_JMPTAB + 0   ; $F368 -> wa_seg_rom
                ld      (hl), $C3
                inc     hl
                ld      (hl), low WA_SEG_ROM
                inc     hl
                ld      (hl), high WA_SEG_ROM
                ld      hl, WA_JMPTAB + 3   ; $F36B -> wa_seg_ram
                ld      (hl), $C3
                inc     hl
                ld      (hl), low WA_SEG_RAM
                inc     hl
                ld      (hl), high WA_SEG_RAM
                ; fall through to build the $F348 DRVTBL (same $FF gate)
; build_drvtbl — synthesise the four CALLF trampolines in page-3 RAM, then lay the
; $F348 DRVTBL pointing at them + our slot + reserved-top + the $4030 work area.
; Mirrors the disk ROM's own build (§8.22 write-watch: stock builds it from page 1);
; clean-room — every pointer aims at our own code, the stock $EF95/$DFxx bytes are
; never read. Runs only under set_ramad's $FF gate (the real-CF-3300 DOS host).
build_drvtbl:
                ; --- four CALLF trampolines: F7 <slot> <target-lo> 40 C9 ---------
                ld      hl, drv_targets ; ROM: low byte of each $40xx driver entry
                ld      de, DRV_TRAMP   ; RAM: where the stubs are laid
                ld      b, DRV_NTRAMP
bdt_tramp:
                ld      a, $F7          ; RST 30h (CALLF) opcode
                ld      (de), a
                inc     de
                ld      a, (HOOK_SLOT)  ; this ROM's slot byte
                ld      (de), a
                inc     de
                ld      a, (hl)         ; target low byte (e.g. $10 = DSKIO)
                ld      (de), a
                inc     de
                ld      a, high DSKIO_ENTRY ; $40: all driver entries are in page 1
                ld      (de), a
                inc     de
                ld      a, $C9          ; RET
                ld      (de), a
                inc     de
                inc     hl
                djnz    bdt_tramp
                ; --- the DRVTBL itself at $F348 ---------------------------------
                ld      a, (HOOK_SLOT)
                ld      (DRVTBL + 0), a             ; +0  slot id
                ld      hl, DOS_RESV_TOP
                ld      (DRVTBL + 1), hl            ; +1  reserved top-of-RAM
                ld      hl, GETWRK_AREA
                ld      (DRVTBL + 3), hl            ; +3  $4030 work-area pointer
                ld      hl, DRV_TRAMP + 0
                ld      (DRVTBL + 5), hl            ; +5  DSKIO  trampoline
                ld      hl, DRV_TRAMP + 5
                ld      (DRVTBL + 7), hl            ; +7  DSKCHG trampoline
                ld      hl, DRV_TRAMP + 10
                ld      (DRVTBL + 9), hl            ; +9  GETDPB trampoline
                ld      hl, 0
                ld      (DRVTBL + 11), hl           ; +11 unused (stock = $0000)
                ld      hl, DRV_TRAMP + 15
                ld      (DRVTBL + 13), hl           ; +13 DSKFMT trampoline (NOTE: stock +13 =
                                                    ; $F195 = the drive-A DPB pointer, not a
                                                    ; trampoline — §8.22's "driver pointers"
                                                    ; reading of +5/+7/+9/+13 needs revisiting;
                                                    ; but +13 is NOT the IX source, §8.30)
                ld      a, $AA
                ld      (DRVTBL + 15), a            ; +15 sentinel (stock = $AA)
                ; fall through to install the resident work-area routines (§8.28)
; build_resident — install the disk system's resident RAM ROUTINES the kernel CALLs
; from fixed work-area addresses (a3 §8.28). After $50A9 the kernel CALLs $F1C9, a
; $-terminated STRING-PRINT helper the genuine disk ROM relocates into the work area
; (stock body: CALL $F36B / LD A,(DE) / CALL $F368 / INC DE / CP '$' / RET Z /
; CALL $53A8 output / loop). Absent it ($FF) the CALL slides through RST 38h. We
; install OUR OWN clean-room body (never the stock bytes) into page-3 RAM (always
; mapped, no slot juggling). FIRST CUT: consume the string to its '$' terminator and
; return -- the kernel's control flow continues; banner output is added by a later
; re-trap if the kernel proves to need it. Runs under the same $FF gate as set_ramad.
build_resident:
                ld      hl, res_print_tmpl
                ld      de, RES_PRINT
                ld      bc, res_print_end - res_print_tmpl
                ldir
                ; --- the $F24E-$F2B7 no-op segment-hook stub table (§8.29/§8.61) ----
                ; The COMMAND.COM-load dispatch trace (disk_probe_dosboot_dispatch.py,
                ; stock) shows the kernel CALL ~18 fixed entries in $F252-$F2A3 between
                ; $50A9-return and the first real DSKIO. On a plain 64K machine that
                ; whole table is $C9 (RET): they are the disk system's RAM-segment bank
                ; in/out hooks (same no-op class as the $F368/$F36B hooks, §8.18) and do
                ; nothing without a memory mapper. Absent it ($FF) every CALL slides
                ; through RST 38h and the kernel derails (the §8.28a "Insert DOS disk").
                ; We fill it with RET so the no-op hooks return cleanly. Our own bytes
                ; (a constant), never the stock work-area code.
                ; §8.61 CORRECTION: the $C9 region ends at $F2B7 -- on the real CF-3300
                ; $F2B8+ is a kernel DATA structure (the "MSXDOS  SYS" name + a DPB/param
                ; block the disk ROM builds via $4354/$5667). Our old fill ran to $F2FD
                ; and CLOBBERED it. The fill now stops at RES_STUBS_END ($F2B8).
                ld      hl, RES_STUBS
                ld      (hl), $C9               ; RET
                ld      de, RES_STUBS + 1
                ld      bc, RES_STUBS_END - RES_STUBS - 1
                ldir
                ; --- drive-A DPB at $F195 (§8.30) -----------------------------------
                ; The kernel expects a valid drive-A DPB at $F195: $4030's input is
                ; IX=$F195 and the $50A9 contract hands IX back pointing into the work
                ; area; MSXDOS.SYS dereferences that DPB to read the directory +
                ; COMMAND.COM. The disk ROM builds it at boot ($F195 = drive-A id, then
                ; the 18-byte DPB our GETDPB produces byte-identical to the CF-3300,
                ; §8.13). Ours was $FF -> the kernel reads garbage geometry and warm-
                ; boots (§8.29). Lay the drive-A id ($00) at $F195+0 and CALL our own
                ; GETDPB (HL=base; it fills base+1=media onward) to build the DPB from
                ; the inserted disk's BPB -- the same disk boot_disk reads next, and
                ; DSKIO is already callable here. On a boot-sector read error GETDPB
                ; returns Cy=1 having written nothing past the id, so a not-ready disk
                ; cannot leave garbage. Our own code/data; never the stock $F1xx bytes.
                xor     a
                ld      (DRVA_DPB), a           ; $F195 +0 = drive-A id ($00)
                ld      hl, DRVA_DPB            ; GETDPB: HL = DPB base (fills base+1 on)
                call    getdpb
                ; --- p1_blit: page-3-resident routine for page-1 bounce (§8.35) --------
                ; Installed into P1_BLIT ($E77A) so dskio can CALL it from page-1 ROM
                ; while page 1 is temporarily remapped to RAM. Own-choice free page-3
                ; RAM after RDBLK_DST ($E776-$E777); clear of every other region.
                ; One LDIR copies BOTH templates: in ROM wa_seg_*_tmpl immediately
                ; follows p1_blit_tmpl (free tail), and in RAM WA_SEG = P1_BLIT +
                ; (p1_blit_end - p1_blit_tmpl), so the blocks stay contiguous (§8.58 /
                ; M5.6). Zero extra init bytes in this cramped pre-$41FD region.
                ld      hl, p1_blit_tmpl
                ld      de, P1_BLIT
                ld      bc, wa_seg_end_tmpl - p1_blit_tmpl
                ldir
                ret
RES_STUBS       equ     $F24E   ; no-op segment-hook stub table base (§8.29)
RES_STUBS_END   equ     $F2B8   ; one past the last stub ($F2B7); $F2B8+ = kernel data (§8.61)
DRVA_DPB        equ     $F195   ; drive-A DPB base (id byte + 18-byte DPB, §8.30)
DRVTBL          equ     $F348   ; MSX-DOS-1 disk-driver table (§8.22)
RES_PRINT       equ     $F1C9   ; resident $-string print routine the kernel CALLs (§8.28)
DRV_NTRAMP      equ     4       ; number of CALLF trampolines
; drv_targets — low byte of each $40xx driver entry the trampolines call. Order
; matches the stock DRVTBL's non-zero pointer slots (+5/+7/+9/+13): the hot pointer
; is sector I/O (DSKIO), then DSKCHG/GETDPB, then DSKFMT. (Standard disk-ROM jump
; table, MSX2 TH; refined by re-trap if a driver pointer's contract differs.)
drv_targets:
                db      $10     ; DSKIO  ($4010)
                db      $13     ; DSKCHG ($4013)
                db      $16     ; GETDPB ($4016)
                db      $1C     ; DSKFMT ($401C)
; wa_stub — the no-op body for the $F368 segment-switch hooks (RET; see above).
wa_stub:
                ret

; res_print_tmpl — clean-room body for the resident $-string print routine, relocated
; to RES_PRINT ($F1C9) by build_resident (§8.28). The kernel CALLs $F1C9 with DE -> a
; '$'-terminated string. Our first cut CONSUMES the string (advance DE past it) and
; returns; it does not yet emit the characters (the stock routes each char through a
; disk-ROM console primitive). Straight-line + relative-jump only, so a plain LDIR
; relocates it verbatim. Re-trap will show whether the kernel needs real output.
;   in:  DE -> '$'-terminated string ; out: DE past the '$', A=$24, others as Z80 CP
res_print_tmpl:
                ld      a, (de)         ; A = next string byte
                inc     de
                cp      '$'             ; $24 = MS-DOS string terminator
                ret     z               ; done -> return to the kernel
                jr      res_print_tmpl  ; (relocatable: PC-relative loop)
res_print_end:
; (p1_blit_tmpl + wa_seg_*_tmpl live in the free tail near the end of the ROM, so
;  this cramped pre-$41FD region stays within budget; build_resident LDIRs both.)

