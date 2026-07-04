; Copyright (c) 2026 Joost Yervante Damad
; SPDX-License-Identifier: 0BSD
; Part of zerobas-disk, included by disk.asm (build with `pasmo -I disk`).
; Tier-2 MSX-DOS-1 kernel veneers + relocated bodies (Interface A: the de-facto DOS ABI)
; CLEAN-ROOM: every constant, address and algorithm here traces to a public source
; or a black-box oracle probe; nothing is derived from disassembly. See disk/PROVENANCE.md.

; --- MSX-DOS-1 kernel continuation entry: $50A9 ($4000 + $10A9; a3 §8.26/§8.27) -
; The relocated kernel CALLs $50A9 right after publishing its BDOS vector; on the
; genuine CF-3300 this disk-ROM routine (`CALL $472D` + work-area setup) reaches A>.
; Our code ends far below $50A9, so the entry is positioned with a `ds` fill (like
; $4030). We reproduce the BLACK-BOX contract (disk_probe_dosboot_50a9.py):
;   side effect : W50A9_WRKB ($F242) := $00   (the only non-stack write observed)
;   returns     : A=$00, F=$42 (Z+N) ; DE=IX=$F1AA ; HL=$F359 ; BC, IY preserved
; `sub a` yields exactly A=$00 / F=$42 ($42 = Z|N: 0-0 sets Z+N, clears S/H/PV/C); the
; following loads do not disturb the flags, so the exit AF is exact. Inputs ignored
; (the kernel passes AF=C340 BC=0000 DE=DC80 HL=D606 IX=F195 IY=C0AB; none consumed).
                ds      $4E4B - $, $00  ; pad to the $4E4B kernel veneer (was $50A9 fill)
                jp      k_4E4B          ; $4E4B: COMMAND.COM-load kernel veneer
                ds      $4EDE - $, $00  ; pad to the $4EDE kernel veneer
                jp      k_4EDE          ; $4EDE: COMMAND.COM-load kernel veneer
; --- MSX-DOS-1 kernel SFIRST/SNEXT dir-search entries: $4FB8/$5006 (M19) -------
; While processing BDOS SFIRST ($11) / SNEXT ($12) the relocated kernel CALLs these
; two page-1 disk-ROM entries to walk the root directory for entries matching the
; search FCB's 8.3 pattern. Both are our own $00 pad (inside the $4EE1..$50A9 fill,
; below the $50A9/$50C4/$50D5/$50E0 veneers), so before this the CALL NOP-slid into
; the $50A9 stub tail and returned a bogus "entry found" -> DIR hung (M19 §3). Each
; is inserted as an additional descending ds-anchor in this chain ($4FB8, $5006 slot
; in address order between $4EDE and $50A9), consuming existing pad -> net-zero.
; Black-box entry contract (M19 §2, callseq/capture, no stock CODE decoded): entry
; DE -> the kernel's search-FCB copy (drive byte + 11-byte 8.3 pattern, ?=$3F
; wildcard); the runtime DTA base lives in the fixed work-area cell $F23D (the
; kernel's current-DTA pointer, set via its own SETDTA before the search). Bodies
; (sfirst_body/snext_body/dirscan_match) live in the free tail; clean-room -- our
; own fat_mount/fat_find root-dir walk + published SFIRST/SNEXT contract. See
; docs/tier2-m19-spec.md.
                ds      $4FB8 - $, $00  ; pad up to the pinned $4FB8 SFIRST entry
sfirst:
                jp      sfirst_body     ; -> free-tail: find FIRST matching dir entry (M19)
                ds      $5006 - $, $00  ; pad up to the pinned $5006 SNEXT entry
snext:
                jp      snext_body      ; -> free-tail: find NEXT matching dir entry (M19)
; --- MSX-DOS-1 kernel FSIZE entry: $501E (M28 §3.1/§3.2, [LANDED-B]) ----------
; While processing BDOS FSIZE ($23) the relocated kernel CALLs this page-1 disk-
; ROM entry (same dispatcher class as $4788/$4793, M26: DE=$DA40 kernel FCB
; copy, A=$25/B=$00/C=$00, ret=$D88A). Sits in the dead-$00 pad between snext
; ($5006, ends $5008) and $504E LOGIN -- a 3-byte `jp fsize_body` wires directly,
; RDABS/M26-style, no relocation needed. Body = fsize_body (free tail): a real
; GET FILE SIZE (fat_mount + fat_find, ceil(size/128) -> copy+33..35); the prior
; stub returned a constant A=L=$03 for every input and never searched at all.
                ds      $501E - $, $00  ; pad up to the pinned $501E FSIZE entry (M28)
k_501E:
                jp      fsize_body      ; $501E: BDOS $23 FSIZE canonical entry (M28)
; --- MSX-DOS-1 kernel LOGIN entry: $504E (M22a; tier2-m22-cpmver-spec.md) ------
; While processing BDOS LOGIN ($18) the relocated kernel CALLs this page-1 disk-
; ROM entry for the online-drive bitmap. Was un-wired $00 pad, NOP-sliding into
; the $5058 SETDTA-cache veneer below: garbage exit AND a silent stomp of
; DOS_DTAPTR from whatever DE happened to hold (benign-by-luck only because DE
; was $0080 at the observed call site, §4.3). Body = login_body (free tail).
; CLEAN-ROOM: published LOGIN online-drive-bitmap contract (map.grauw.nl) +
; our own DRVCNT cell; no stock routine internals decoded.
                ds      $504E - $, $00  ; pad up to the pinned $504E LOGIN entry (M22a)
k_504E:
                jp      login_body      ; $504E: BDOS $18 LOGIN canonical entry (M22a)
; --- MSX-DOS-1 kernel SETDTA-time entry: $5058 (M19) --------------------------
; While processing BDOS SETDTA ($1A) the relocated kernel CALLs this page-1
; disk-ROM entry to cache the new DTA pointer into the disk work area. Black-box
; contract (M19, callseq/capture/callwatch causal pin, no stock CODE decoded):
; entry DE = the new DTA pointer (=$D403 for DIR; register-identical ours==stock,
; 51 calls each), and stock's routine stores it at the fixed work-area cell $F23D
; (proven: on stock $F23D=$D403 and SFIRST reads it via PCs $4FCC/$4FEF; on ours,
; before this veneer, $F23D was never written -> SFIRST/SNEXT wrote the found entry
; to a stale/garbage DTA -> DIR reported "File not found"). Wiring $5058 to cache
; DE at $F23D makes SFIRST/SNEXT (which read DOS_DTAPTR=$F23D) target the real
; runtime DTA. Same un-wired-$50xx-entry class as M13/M17/M18. Body =
; setdta_cache_body (free tail). CLEAN-ROOM: our own DE->$F23D store + the observed
; entry-register / write-target contract; no stock routine internals decoded.
                ds      $5058 - $, $00  ; pad up to the pinned $5058 SETDTA-cache entry
setdta_cache:
                jp      setdta_cache_body ; -> free-tail: ($F23D) := DE (runtime DTA; M19)
; --- MSX-DOS-1 kernel GETALLOC entry: $505D (M20 REVISION 3; tier2-m20-spec.md) -----
; While processing BDOS GETALLOC ($1B) the relocated kernel CALLs this page-1 disk-ROM
; entry to compute the DIR "nn bytes free" footer. Black-box contract (M20 §2, no stock
; CODE decoded): entry regs byte-identical ours==stock (C=$1B BC=$5D1B DE=$D100
; HL=$C924 IX=$F195); the un-wired $00 pad here made the CALL NOP-slide into the $50A9
; stub tail (garbage exit -> "0 bytes free"). Exit contract (map.grauw.nl _ALLOC):
; A=sectors/cluster, BC=bytes/sector, DE=total data clusters, HL=free clusters.
; REVISION 3 (this span): Revisions 1 (register-only) and 2 (+ resident FAT buffer +
; IY + a per-drive DPB+19 field) were both BUILT and FALSIFIED -- the A/BC/DE/HL scan
; math was correct in both (host-unit-tested + confirmed at getalloc_body's own ret),
; but the DIR footer was wrong regardless, IDENTICALLY so both with and without the
; IY/DPB+19 wiring. Root cause (this span, a narrow read of 20 RAM-KERNEL bytes at the
; shared post-handler exit path $D8AA-$D8BD -- NOT stock ROM/COMMAND.COM code -- to
; answer one question, "what does the branch at $D8AE test"; same technique already
; used to pin $F23D/$F247/$F347/$F306 in prior milestones): the kernel's common BDOS-
; exit path gates HL passthrough on a flag cell, $F306 (set to $01 by the dispatcher on
; every BDOS call, per tier2-gdate-spec.md's earlier pin) -- a handler that leaves
; $F306 set has its HL SILENTLY OVERWRITTEN with H:=B,L:=A (the CP/M single-byte-result
; B:A->HL mirror) instead of passed through. Stock's $505D handler clears it; ours never
; did, so our correct HL was replaced by a mirror of our own A/BC (explaining the exact
; wrong constant observed, `$0202`=514, in both falsified revisions). Causally proven by
; a poke test (forcing $F306:=0 flips the branch and the handler's real HL survives).
; `gdate_handler` below already clears $F306 (previously assumed "harmless stock
; parity" -- it is in fact load-bearing, and the only reason GDATE's HL reaches its
; caller). Revision 3 = Revision 1's register-only body (own FAT scan via read_sector/
; WBUF, reusing fat.asm's fac_entry_from_wbuf unpack -- no new RAM cell, no IY, no
; DPB+19, both proven unnecessary) + one added store: clear $F306 before `ret`, loading
; the final A value AFTER the clear (order matters: A must hold sectors/cluster at
; `ret`; the clear only needs A=0 transiently as the store source).
; CLEAN-ROOM: our own FAT scan (fat_mount + read_sector + fat.asm's fac_entry_from_wbuf,
; all pre-existing oracle-validated primitives) + the published GETALLOC A/BC/DE/HL
; contract (map.grauw.nl) + the black-box-pinned $F306 dispatcher-flag semantics
; (register/memory VALUES + one narrow RAM-kernel byte read, no stock ROM decoded).
                ds      $505D - $, $00  ; pad up to the pinned $505D GETALLOC entry
getalloc:
                jp      getalloc_body   ; -> free-tail: FAT free-cluster scan (M20 rev3)
; --- MSX-DOS-1 kernel DSKRST entry: $509F (M22a; tier2-m22-cpmver-spec.md) -----
; While processing BDOS DSKRST ($0D) the relocated kernel CALLs this page-1
; disk-ROM entry to flush/reset the disk work area. Was un-wired $00 pad,
; NOP-sliding into our OWN $50A9 continuation stub below — which happens to
; reproduce the exact register contract by coincidence (§4.4: "pad-slide
; luck", the same class of latent bug M21a-RC-1 broke later). Body =
; dskrst_body (free tail): a wired `jp` to the same stub, replacing luck with
; an explicit entry. Real flush semantics are unverifiable here (no dirty
; buffers at these call sites); the register contract is the observable
; surface (§8.4 residual).
                ds      $509F - $, $00  ; pad up to the pinned $509F DSKRST entry (M22a)
k_509F:
                jp      dskrst_body     ; $509F: BDOS $0D DSKRST canonical entry (M22a)
                ds      $50A9 - $, $00  ; pad remainder up to the kernel's $50A9 target
w50a9_stub:
                sub     a               ; A=$00, F=$42 (Z+N) -- the exact exit AF
                ld      (W50A9_WRKB), a ; $F242 := $00  (the only persistent write)
                ld      de, W50A9_RET_DE ; DE = $F1AA
                ld      ix, W50A9_RET_DE ; IX = $F1AA (= DE)
                ld      hl, W50A9_RET_HL ; HL = $F359
                ret                     ; AF=$0042, BC/IY untouched

; --- MSX-DOS-1 kernel CONIN line-read entry: $50E0 (M12d pin; tier2-conin-spec.md v3) --
; BUFIN (BDOS func $0A) has the relocated kernel CALL a disk-ROM console-line routine;
; the M12d black-box pin (guarded callseq, no stock bytes decoded) fixed the entry as the
; CALL target $50E0 (regs byte-identical ours==stock at first entry: DE=$DA40 HL=$C924
; ret=$D88A) and the register convention as DE -> buffer, [DE]=max length (the published
; BDOS func-$0A layout: [+0]=max/[+1]=count/[+2..]=chars; confirmed by a second pin
; walking HL/D/E across 7 CHGET calls with an injected keystroke). No return register --
; the result lives in the buffer (func-$0A contract). Our `$50B7-$5453` region is our own
; $00 padding (active code ends at the $50A9 routine above), so before this veneer BUFIN
; NOP-slid straight into the $5454 CONOUT veneer below (one garbage char, no block) --
; the M12 root cause. Body = conin_line_body (free tail): reimplements the func-$0A
; buffered-line read from the published CHGET ($009F) / CHPUT ($00A2) / func-$0A buffer
; ABI, clean-room -- the stock routine's internals were never read (spec §3 Option A).
;
; --- MSX-DOS-1 kernel SELDSK-time entry: $50D5 (M17; tier2-m17-spec.md) --------
; While processing BDOS SELDSK (func $0E) the relocated kernel CALLs this page-1
; disk-ROM entry (register-identical ours==stock at entry: AF=0044 BC=D50E DE=D3FF
; HL=D349 IX=F459 IY=DC5B, ret=D88A -- a real CALL boundary, M17 §2.1). Black-box
; contract: read the logical-drive count from $F347 into A, preserve BC/DE/HL/IX/IY
; (return F irrelevant so far, §4). Our $50B8-$5453 block is our own $00 padding, so
; before this veneer the CALL NOP-slid into the $5454 CONOUT veneer and never
; returned to the trampoline -> the M17 SELDSK stall (no A> prompt). Body =
; seldsk_drv_body (free tail); clean-room -- the stock routine's internals were never
; read (only its entry/exit registers + a DATA-cell read-watch of $F347).
; --- MSX-DOS-1 kernel CURDRV-time entry: $50C4 (M18; tier2-m18-spec.md) ---------
; While processing BDOS CURDRV (func $19) the relocated kernel CALLs this page-1
; disk-ROM entry (register-identical ours==stock at entry: AF=0044 BC=C419 DE=D3FF
; HL=D502 SP=DBFE IY=DC5B, ret=D88A -- a real CALL boundary, M18 §2.1). Black-box
; contract (readwatch causal pin): read the CURRENT-drive index from $F247 into A,
; preserve BC/DE/HL/IX/IY. Our $50B8-$50D4 block is our own $00 padding, so before
; this veneer the CALL NOP-slid and never read the drive -> the kernel's later
; 'A'+drive letter math used a bogus index ($C400 + 2 = 'C>') instead of A>. Body =
; curdrv_body (free tail); clean-room -- the stock routine's internals were never
; read (only its entry/exit registers + a DATA-cell read-watch of $F247).
                ds      $50C4 - $, $00  ; pad up to the pinned $50C4 kernel entry
curdrv:
                jp      curdrv_body     ; -> free-tail: A = ($F247) current drive (M18)
                ds      $50D5 - $, $00  ; pad up to the pinned $50D5 kernel entry
seldsk_drv:
                jp      seldsk_drv_body ; -> free-tail: A = ($F347) drive count (M17)
                ds      $50E0 - $, $00  ; pad up to the pinned CONIN line-routine entry
conin:
                jp      conin_line_body ; -> free-tail buffered-line CHGET loop (M13)

; --- MSX-DOS-1 kernel CONOUT-worker entry: $53A7 (M22b; tier2-m22b-conout53a7-spec.md) --
; The relocated kernel CALLs this page-1 disk-ROM entry for EVERY BDOS CONOUT
; ($02) character (ret=$D88A, B=$A7 fingerprint, C=$02, char in E — the same
; dispatcher class as the M22a eleven). It was un-wired $00 pad; pre-M22a the
; CALL NOP-slid 173 bytes into the $5454 CONOUT veneer below, which happens to
; implement the exact right observable contract (emit E via CHPUT, A:=E) — the
; accident every M8-M21 console-parity probe rode. M22a's new $543C CONST
; veneer (below) now sits earlier in that same slide and intercepts it instead,
; silently dropping every func-2 char (date/A>/echo/DIR listing). This veneer
; restores the pre-M22a behavior explicitly instead of by accident; net-zero,
; 3 bytes carved from the existing pad before $543C. CLEAN-ROOM: $53A7 is a
; de-facto page-1 kernel-ABI address (class of $4010/$5454), pinned by
; call-target + register observation only (400/400 region-entry samples);
; body = conout_body, the proven $5454 implementation (M8/M10).
                ds      $53A7 - $, $00  ; pad up to the pinned $53A7 CONOUT-worker entry (M22b)
k_53A7:
                jp      conout_body     ; $53A7: BDOS $02 CONOUT canonical entry (M22b slice 1)

; --- MSX-DOS-1 kernel console entries: $543C/$5445/$544E (M22a) ---------------
; While processing BDOS CONST ($0B) / CONIN ($01) / INNOE ($08) the relocated
; kernel CALLs these page-1 disk-ROM entries. All three were un-wired $00 pad,
; NOP-sliding into the $5454 CONOUT veneer below — each would have emitted a
; garbage char via CONOUT (E's leftover value) instead of polling/reading the
; keyboard, without ever consuming a queued key (tier2-m22-cpmver-spec.md §4.5).
; Bodies (const_body/conin_body/innoe_body, free tail) use the same CHSNS/CHGET
; inter-slot primitives conin_line_body/conout_body already use.
; CLEAN-ROOM: published CONST/CONIN/INNOE contracts (map.grauw.nl) + our own
; pg0_mainrom_in/out inter-slot path; no stock routine internals decoded.
                ds      $543C - $, $00  ; pad up to the pinned $543C CONST entry (M22a)
k_543C:
                jp      const_body      ; $543C: BDOS $0B CONST canonical entry (M22a)
                ds      $5445 - $, $00  ; pad up to the pinned $5445 CONIN entry (M22a)
k_5445:
                jp      conin_body      ; $5445: BDOS $01 CONIN canonical entry (M22a)
                ds      $544E - $, $00  ; pad up to the pinned $544E INNOE entry (M22a)
k_544E:
                jp      innoe_body      ; $544E: BDOS $08 INNOE canonical entry (M22a)

; --- MSX-DOS-1 kernel CONOUT entry: $5454 ($4000 + $1454; a3 §8.38) ---------
; The relocated kernel CALLs $5454 to emit its sign-on banner one character at a
; time (the boot's first divergence point, disk_probe_dosboot_pctrace.py). It is
; the disk ROM's CONOUT: output the char in A via the BIOS CHPUT path, preserving
; BC/DE/HL/IX/IY. Black-box call-chain on the stock: $5454 -> $408F -> $001C
; (CALSLT) -> resident kernel -> $F398 -> $00A2 (CHPUT); first call A=$0D (the
; banner's leading CR). $5454 is a HARD IMMEDIATE in MSXDOS.SYS (`CD 54 54`
; present in the pristine just-loaded image, unchanged at call time -- not a
; relocated vector). CLEAN-ROOM: $5454 is a cross-vendor de-facto-standard entry,
; byte-identical across seven vendors' disk ROMs in the shared ASCII-kernel block
; ($4768-$576F) -- the same ABI class as $4010 DSKIO / $4016 GETDPB, never a byte
; copy (oracle-artifacts.md "Cross-vendor disk-ROM set"; spec-diskrom-kernel.md
; §1.3). Our code ends far below $5454, so the entry is positioned with a `ds`
; fill (like $4030/$50A9), consuming otherwise-$00 page padding -- nothing shifts.
; M8/§8.67: the first-cut no-op was PROVEN to be the COMPLETE COMMAND.COM-load
; blocker (aligned pctrace from $0100 diverges at exactly $5454; ours spins in the
; banner loop forever, 56 distinct PCs, while stock proceeds, 482). So CONOUT now
; does the real thing: emit A via the main-ROM CHPUT ($00A2) through a genuine
; inter-slot call. The body lives in the free tail (conout_body); $5454 just diverts
; to it (the 2 extra bytes shift the $5456 bodies gap, absorbed by `ds $5FE5 - $`).
                ds      $5454 - $, $00  ; pad up to the kernel's $5454 CONOUT target
conout:
                jp      conout_body     ; -> free-tail inter-slot CHPUT call (M8)

; --- MSX-DOS-1 kernel DIRIN entry: $5462 (M22a; tier2-m22-cpmver-spec.md) ------
; While processing BDOS DIRIN ($07) the relocated kernel CALLs this page-1
; disk-ROM entry. Was inside fat_find_body's span (relocated to the free tail
; below, §4.6) — fat_find_body never had a canonical-address requirement of its
; own (only reached by label from fat.asm's `fat_find` veneer), so moving it
; frees this slot outright. Body = dirin_body (free tail).
                ds      $5462 - $, $00  ; pad up to the pinned $5462 DIRIN entry (M22a)
k_5462:
                jp      dirin_body      ; $5462: BDOS $07 DIRIN canonical entry (M22a)
k_5465:
                jp      lstout_body     ; $5465: BDOS $05 LSTOUT canonical entry
                                        ; (lands naturally at $5465 = k_5462 + 3 bytes;
                                        ;  was squatted by callf_body_body, M27 §4)

; --- lstout_body - the real $5465 LSTOUT (BDOS $05); characterised 2026-07-04 -----
; Output the char (in E) to the list device via the main-ROM LPTOUT ($00A5),
; preserving BC/DE/HL. Entry E=char is the $5465 LSTOUT contract (= the $5454 CONOUT
; contract; black-box confirmed: kernel func-5 worker entry has E=char, A=$00,
; ret=$D88A -- disk/docs/tier2-lstout-characterisation.md §3.3). Pages the main BIOS
; ROM into page 0 (pg0_mainrom_in), calls LPTOUT, restores (pg0_mainrom_out); DI spans
; the half-mapped window; EI on exit -- the same structure conout_body uses for CHPUT.
;   in:  E = char ; out: BC/DE/HL preserved (IX/IY untouched)
; BIOS-DELEGATING by design (two-interface rule, [[cbios-target-cf3300-oracle]]):
; LSTOUT does NOT poke the printer ports ($90/$91) itself -- it calls the main BIOS's
; LPTOUT and inherits whatever the host BIOS does. On real CF-3300 hardware this drives
; the printer (and, faithfully, blocks if none is attached -- matching stock, which
; tight-polls status port $90). On C-BIOS it inherits C-BIOS's own $00A5, TODAY A STUB
; -> LSTOUT safely no-ops (no port poll, no hang). *** C-BIOS LPTOUT is a LATER FIX ***
; (tier2-lstout-characterisation.md §4): once C-BIOS grows a real $00A5, LSTOUT here
; starts working with no change to this ROM. NB: the DI window means a real-hardware
; no-printer poll would block with interrupts off (no Ctrl-STOP escape) -- an authentic-
; hang edge case, not reachable on our targets (C-BIOS no-op / real-hw-with-printer).
; CLEAN-ROOM: E=char is the BDOS LSTOUT ($05) ABI; $00A5 LPTOUT is the published BIOS
; entry (same documented class as CHPUT $00A2 already called by conout_body); no oracle
; bytes decoded. Lives in the $5456-$5FE4 gap section (net-zero: absorbed by the
; `ds $5FE5 - $` pad below, so nothing downstream shifts / the FDC-window guard holds).
lstout_body:
                ld      a, e                ; char arrives in E ($5465 LSTOUT contract)
                ld      (CONOUT_CHAR), a    ; stash across the slot work (A needed for paging)
                push    bc
                push    de
                push    hl
                di                          ; no interrupt while the BIOS is half-mapped
                call    pg0_mainrom_in
                ld      a, (CONOUT_CHAR)
                call    $00A5               ; LPTOUT - output A to the list device
                call    pg0_mainrom_out     ; restore page 0
                ei
                pop     hl
                pop     de
                pop     bc
                ret

; ===== Tier-2 3b: relocated Disk-BASIC routine bodies ($5456-$5FE4 gap) =====
; Each colliding routine's body lives here; its low-region slot holds `entry:
; jp entry_body` + the ds-anchored veneer(s) + padding, sized to exactly fill the
; original span (net-zero — nothing downstream shifts). Each body ends with a `jp`
; back to the label that followed it, so fall-through is preserved. Callers reach
; the routine through its unchanged low-region entry label.
; (fat_find_body relocated to runtime.asm, M22a — its old span here collided
; with the $5462 DIRIN canonical entry above, tier2-m22-cpmver-spec.md §4.6.)

; callf_body_body — the $0030 RST 30h / CALLF handler (the load-bearing one).
; CALLF is `F7 <slot> <lo> <hi>`: RST 30h pushes the return address (which points
; at the inline operand) and lands here. H.PHYD ($FFA7 = F7 87 10 40 C9) is exactly
; this — every PHYDIO from the boot/DOS reaches our DSKIO through it. The callee
; (DSKIO, $4010) takes A,B,C,DE,HL and CY=read/write, so this handler must deliver
; ALL of them UNTOUCHED. It saves the caller's registers to page-3 scratch, reads
; the operand off the stack to find the target address + the post-operand return,
; then arranges the stack so a plain `ret` jumps to the target with every register
; (and the carry flag) restored, and the target's own RET lands on the byte after
; the operand (H.PHYD's trailing C9). Our disk ROM is in page 1, so the target is
; directly reachable — no real inter-slot switch needed. (§8.4) Reached directly
; from p0_env_tab's $0030 entry (pageenv.asm, free tail) since M22a removed the
; 3-byte `callf_body` veneer that used to sit at $41F0 (it collided with the
; CPMVER canonical entry, tier2-m22-cpmver-spec.md §4.1).
; Only `ld`/`inc hl`/`pop`/`push`/`ret` are used between entry and the call, none
; of which touch the flags, so the caller's CY (the DSKIO read/write bit) survives.
callf_body_body:                        ; ends in ret
                ld      (R30_HL), hl    ; stash caller HL
                ld      (R30_BC), bc    ; stash caller BC
                ld      (R30_DE), de    ; stash caller DE
                push    af              ; copy AF out without disturbing the return ptr
                pop     hl              ; HL = AF image (push/pop is SP-neutral)
                ld      (R30_AF), hl    ; stash caller AF (incl. carry)
                pop     hl              ; HL = return addr -> inline operand [slot][lo][hi]
                inc     hl              ; -> lo
                ld      e, (hl)
                inc     hl              ; -> hi
                ld      d, (hl)         ; DE = target address (e.g. $4010)
                inc     hl              ; HL = operand+3 = byte after CALLF (H.PHYD's C9)
                push    hl              ; ultimate return: target's RET lands here
                push    de              ; target address on top
                ld      hl, (R30_AF)    ; restore caller AF (carry = DSKIO read/write)
                push    hl
                pop     af
                ld      bc, (R30_BC)    ; restore caller BC
                ld      de, (R30_DE)    ; restore caller DE
                ld      hl, (R30_HL)    ; restore caller HL (DSKIO transfer address)
                ret                     ; -> target; its RET -> operand+3 -> caller

bdos_seqread_body:                      ; [bdos_seqread, bsr_have) -> falls into bsr_have
                ; EOF once every file byte has been delivered (BYTESLEFT == 0).
                ld      hl, (BDOS_BYTESLEFT)        ; low word
                ld      de, (BDOS_BYTESLEFT + 2)    ; high word
                ld      a, h
                or      l
                or      d
                or      e
                jp      z, bsr_eof                  ; no bytes left -> EOF (jr->jp: relocated)
                ld      a, (BDOS_RECIDX)
                cp      RECPERSEC
                jp      c, bsr_have     ; records still left in SECTOR_BUF (jr->jp)
                call    fat_read_file_sector
                jp      c, bsr_eof      ; chain ended early -> EOF (jr->jp)
                xor     a
                ld      (BDOS_RECIDX), a    ; back to record 0
                jp      bsr_have

bdos_create_body:                       ; [bdos_create, bdos_create_failpop) — ends in ret
                push    de              ; FCB across fat_mount
                call    fat_mount
                jp      c, bdos_create_failpop      ; jr->jp: relocated
                pop     hl              ; HL = FCB
                inc     hl              ; HL = FCB+1 = 8.3 name
                call    fat_dir_create  ; find/make a dir slot, write the entry
                jp      c, bdos_create_err          ; jr->jp: relocated
                ; prime the write iterator: no cluster yet, empty buffer, 0 bytes.
                xor     a
                ld      (BDOS_WRSECIDX), a
                ld      hl, 0
                ld      (BDOS_WRCLUS), hl
                ld      (BDOS_WRFIRST), hl
                ld      (BDOS_WRBUFLEN), hl
                ld      (BDOS_WRBYTES), hl
                ld      (BDOS_WRBYTES + 2), hl
                ld      a, 1
                ld      (BDOS_WRMODE), a    ; file is open for write
                xor     a                   ; A = $00 success
                ret

frs_mul_body:                           ; [frs_mul, frs_eof) loop; entered via frs_mul stub
                add     hl, de
                djnz    frs_mul_body        ; HL = (cluster-2) * secPerClus
                ld      de, (FAT_FIRSTDATA)
                add     hl, de
                ld      a, (FAT_CLUSSEC)
                ld      e, a
                ld      d, 0
                add     hl, de              ; HL = absolute logical sector
                ex      de, hl
                ld      hl, SECTOR_BUF
                call    read_sector
                ret     c
                ld      a, (FAT_CLUSSEC)
                inc     a
                ld      (FAT_CLUSSEC), a
                or      a                   ; Cy = 0 success
                ret

write_sector:                           ; relocated (entry collided with $4935 veneer)
                ld      b, 1            ; one sector
                ld      c, $F9          ; media byte (ignored, single drive)
                ld      a, 0            ; drive 0 (ignored)
                scf                     ; Cy = 1 = WRITE direction (MSX2 TH DSKIO)
                jp      dskio           ; tail-call: dskio returns to our caller

; --- MSX-DOS-1 kernel _GDATE entry: $553C ($4000 + $153C; M9 date slice) ----
; The kernel BDOS dispatcher ($D831; table $D8BE + 3*C) routes _GDATE ($2A) here
; after paging in the disk ROM via the $F368 hook. CF-3300 and C-BIOS are
; clock-less MSX1, so _GDATE returns the documented MSX-DOS-1 default date
; 1984-01-01 (a Sunday) -- a constant, NOT a reproduction of stock's stored
; day-count -> Y/M/D math. Return contract (observed black-box at the GDATE
; return $CC04): HL=year, D=month, E=day, A=day-of-week(0=Sun), BC=0, F=$44.
; `xor a` yields A=$00 and F=$44 (Z|P/V) exactly; the preceding loads do not
; disturb the flags. CLEAN-ROOM: documented default + black-box return contract;
; no stock bytes. $553C fell inside fac_loop_body; that body is relocated just
; below (label-referenced via fat.asm `jp fac_loop_body`; net-zero -- the tail
; `ds $5FE5 - $` absorbs the shift). See docs/tier2-gdate-spec.md.
                ds      $553C - $, $00      ; pad to the canonical _GDATE entry
gdate_handler:
                ld      hl, $07C0           ; year = 1984
                ld      de, $0101           ; D = month 01, E = day 01
                ld      bc, $0000
                xor     a                   ; A = 0 (Sunday); F = $44 (Z,P/V), as stock
                ld      ($F306), a          ; clear dispatcher re-entrancy flag (stock parity)
                ret

fac_loop_body:                          ; [fac_loop, fac_have_sec) -> falls into fac_have_sec; relocated past $553C
                ld      de, (FAT_WRTMP)
                push    hl
                or      a
                sbc     hl, de
                pop     hl
                jp      nc, fac_full        ; jr->jp: relocated
                push    hl
                ld      a, l
                and     1
                ld      (FAT_PARITY), a
                ld      e, l
                ld      d, h
                srl     d
                rr      e                   ; DE = cluster >> 1
                add     hl, de              ; HL = fatofs = cluster * 3/2
                ld      a, l
                ld      (FAT_BYTEIDX), a
                ld      a, h
                and     1
                ld      (FAT_BYTEIDX + 1), a    ; byteidx = fatofs & $1FF
                ld      a, h
                srl     a                   ; FAT sector offset = fatofs >> 9
                ld      e, a
                ld      d, 0
                ld      hl, (FAT_FATSTART)
                add     hl, de              ; HL = absolute FAT sector
                ld      de, (FAT_WRTMP2)
                push    hl
                or      a
                sbc     hl, de
                pop     hl
                jp      z, fac_have_sec     ; jr->jp: already loaded -> no re-read
                ld      (FAT_WRTMP2), hl    ; remember the new cached sector
                ld      (FAT_FATSEC), hl
                ex      de, hl
                ld      hl, WBUF
                call    read_sector
                jp      c, fac_rderr        ; jr->jp: relocated
                jp      fac_have_sec        ; fall-through preserved

fac_e_odd_body:                         ; [fac_e_odd, fat_write_fat_entry) — ends in ret
                ld      a, (FAT_B1)
                ld      l, a
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                ld      a, (FAT_B0)
                rrca
                rrca
                rrca
                rrca
                and     $0F
                ld      e, a
                ld      d, 0
                add     hl, de
                ex      de, hl
                ret

ffds_nopad_body:                        ; [ffds_nopad, ffds_alloc) -> falls into ffds_alloc
                ld      hl, (BDOS_WRCLUS)
                ld      a, h
                or      l
                jp      z, ffds_alloc       ; jr->jp: no cluster yet -> allocate the first
                ld      a, (BDOS_WRSECIDX)
                ld      hl, FAT_SECPERCLUS
                cp      (hl)
                jp      c, ffds_haveclus    ; jr->jp: room in the current cluster
                jp      ffds_alloc          ; fall-through preserved

; (fdc_entloop_body/fdc_useslot_body relocated to runtime.asm, M22a — their old
; span here collided with the $55DB/$55E6/$55FF GTIME/STIME/VERIFY canonical
; entries below, tier2-m22-cpmver-spec.md §4.2.)

; --- MSX-DOS-1 kernel GTIME/STIME/VERIFY entries: $55DB/$55E6/$55FF (M22a) ----
; While processing BDOS GTIME ($2C) / STIME ($2D) / VERIFY ($2E) the relocated
; kernel CALLs these page-1 disk-ROM entries. All three fell inside the
; fdc_entloop_body/fdc_useslot_body span (now relocated above): STIME executed
; FDC-flavored retry-loop code (wrong exit registers), and GTIME's walk ended in
; a WARM BOOT — killing whatever program was running (the M22a root cause;
; tier2-m22-cpmver-spec.md §4.2). Bodies (gtime_body/stime_body/verify_body,
; free tail) reproduce the pinned oracle contracts (§5.1); none clear $F306 —
; every exit HL is the kernel's own H:=B,L:=A mirror (§5.2, the M20 rule
; inverted for this tier).
; CLEAN-ROOM: published GTIME/STIME/VERIFY contracts (map.grauw.nl, MSX2 TH
; §BDOS) + the black-box-pinned oracle register buffer; no stock CODE decoded.
                ds      $55DB - $, $00  ; pad up to the pinned $55DB GTIME entry (M22a)
k_55DB:
                jp      gtime_body      ; $55DB: BDOS $2C GTIME canonical entry (M22a)
                ds      $55E6 - $, $00  ; pad up to the pinned $55E6 STIME entry (M22a)
k_55E6:
                jp      stime_body      ; $55E6: BDOS $2D STIME canonical entry (M22a)
                ds      $55FF - $, $00  ; pad up to the pinned $55FF VERIFY entry (M22a)
k_55FF:
                jp      verify_body     ; $55FF: BDOS $2E VERIFY canonical entry (M22a)

; ===== Tier-2: COMMAND.COM-load kernel entries — veneer scaffold (milestone 3a) =====
; The relocated MSX-DOS-1 kernel + COMMAND.COM call back into ~21 disk-ROM entry
; points at fixed page-1 addresses (the de-facto-standard shared-kernel ABI;
; spec-diskrom-kernel.md §5). zerobas exposes each as a 3-byte `jp k_XXXX` veneer
; at its canonical address, with the contract body in this free-tail region.
; This 3a pass places the FIVE free-region entries (no relocation needed); $402D
; (in the $4022-$402F pad) is the sixth non-colliding entry, wired above. Bodies
; are register-preserving stubs for now — our ROM does not yet reach the
; COMMAND.COM-load phase — so this scaffold changes no current behaviour; the 14
; entries that collide with active code arrive in the 3b relocation pass, and
; milestone 4 fills each contract. CLEAN-ROOM: exposing ABI entry points + own
; contract code, never shared-kernel bytes — same legitimacy class as the $4010
; BIOS jump table. Veneer safety confirmed by disk_probe_dosboot_veneer.py.
                ds      $5FE5 - $, $00  ; pad to the first free-region kernel entry
                jp      k_5FE5          ; $5FE5
                ds      $607B - $, $00
                jp      k_607B          ; $607B  (BDOS callback; spec §5.2)

; ===== FDC-window P0 fix (2026-07-04): position-free bodies relocated OUT of the
; $7F80-$7FBF FDC register window into this free-region corridor ==================
; The National WD2793 FDC registers ($7FB8-$7FBF) are memory-mapped AND mirrored x8
; across the whole $7F80-$7FBF window, so ROM bytes there read back as register
; values. fdc_useslot_body (create's dir-slot claim) and p0_env_tab's head had drifted
; into that window (~M27), silently breaking create/write persistence. All three
; blocks are reached only by label -- their absolute address is irrelevant -- so they
; live here, in the 5.4 KB of dead $00 pad between the $607B and $75A5 COMMAND.COM-load
; kernel veneers (0 canonical entries, no FDC window). The trailing `ds $75A5 - $`
; still pins k_75A5 exactly -> net-zero canonical addresses. Spec:
; disk/docs/tier2-remediation-spec.md Phase B.

; fdc_entloop_body / fdc_useslot_body — create's directory-slot scan + claim.
; Position-free: reached only by fat.asm's `fdc_entloop`/`fdc_useslot` veneers.
; Kept contiguous, same relative order (M21a-RC-1 convention). Neither falls through
; (each ends in an absolute jp), so the relocation is byte-for-byte behaviour-neutral.
fdc_entloop_body:
                push    bc
                push    hl
                ld      a, (hl)
                or      a
                jp      z, fdc_useslot      ; jr->jp: $00 end-marker -> free slot here
                cp      $E5
                jp      z, fdc_useslot      ; jr->jp: $E5 deleted -> reusable slot
                ld      de, (FAT_NAMEPTR)
                call    name_cmp
                jp      z, fdc_useslot      ; jr->jp: same-name existing entry
                pop     hl
                ld      de, 32
                add     hl, de
                pop     bc
                djnz    fdc_entloop_body
                ld      hl, (FAT_DIRSEC)
                inc     hl
                ld      (FAT_DIRSEC), hl
                ld      hl, (FAT_DIRREM)
                dec     hl
                ld      (FAT_DIRREM), hl
                jp      fdc_secloop         ; jr->jp: relocated

fdc_useslot_body:
                pop     hl                  ; HL = dir entry slot in WBUF
                pop     bc
                ld      de, (FAT_DIRSEC)
                ld      (BDOS_DIRSEC), de
                push    hl
                ld      de, WBUF
                or      a
                sbc     hl, de              ; HL = offset within the sector
                ld      (BDOS_DIROFF), hl
                pop     hl
                push    hl
                ex      de, hl              ; DE = dest slot
                ld      hl, (FAT_NAMEPTR)
                ld      bc, 11
                ldir                        ; name -> entry +0..10
                xor     a
                ld      (de), a             ; +11 = $00 (normal file; matches MSX-DOS)
                inc     de
                ld      b, 20               ; +12..+31 is 20 bytes
                jp      fdc_zero            ; fall-through preserved

; p0_env_tab — the page-0 RST/CALLF/INT vector template, read by lay_page0_env
; THROUGH the ROM page (`ld hl, p0_env_tab`; pageenv.asm). Formerly pinned at $7FB7,
; straddling the FDC window (its head entries read back as register garbage, tolerated
; only empirically); now fully clear of every window so EVERY entry reads correctly.
; The $0030 entry points DIRECTLY at callf_body_body (M22a: no intermediate veneer).
; (cell, handler) pairs; terminated by a 0 cell. No two JP triples overlap.
p0_env_tab:
                dw      $000C, rdslt_h  ; RST 8  RDSLT  (read byte from a slot)
                dw      $0014, wrslt_h  ; RST 10 WRSLT  (write byte to a slot)
                dw      $001C, calslt_h ; RST 18 CALSLT (inter-slot call)
                dw      $0024, enaslt_h ; ENASLT (enable slot in a page)
                dw      $0030, callf_body_body ; RST 30 CALLF (M22a: direct, no veneer)
                dw      $0038, INT_H_HIRAM ; maskable-int vector -> A-3 high-RAM handler
                                           ; (NOT page-1 int_h: page 1 is reclaimed by the TPA)
                dw      0               ; end of table

; ===== M28 (tier2-m28-blockrandom-spec.md): $23 FSIZE + $26 WRBLK ===============
; Completes the block/random FCB surface: a real GET FILE SIZE and a real RANDOM
; BLOCK WRITE. Both land here, in the same free-region corridor as the FDC-window
; fix bodies (0 canonical entries, no FDC window) -- net-zero, `ds $75A5 - $` below
; still pins k_75A5 exactly.

; ff_secloop..ff_found — RELOCATED VERBATIM from disk/fat.asm's old $47B9-$4828 span
; (M28 §3.1/§4, [LANDED-B]). $47BE (5 bytes inside the old ff_secloop, the `jr z,
; ff_notfound`) is the kernel's FIXED canonical $26 WRBLK dispatch entry -- a
; collision freed the same way the FDC-window fix and M26 free colliding canonical
; addresses: relocate OUR code, not the kernel's $D8BE dispatch table (not ours to
; edit). Position-free: reached only by fat_find_body's `jp ff_secloop` (runtime.asm)
; and its own internal `jr ff_secloop` back-edge; every ff_* label below is local to
; this block, so the whole unit moves as one byte-identical piece (no jr/jp
; conversions needed -- unlike fdc_entloop_body/fdc_useslot_body, which split into
; two separately-addressed routines, this block keeps its single entry point).
ff_secloop:
                ld      hl, (FAT_DIRREM)
                ld      a, h
                or      l
                jr      z, ff_notfound      ; scanned every root sector
                ld      de, (FAT_DIRSEC)
                ld      hl, SECTOR_BUF
                call    read_sector
                ret     c                   ; propagate FDC error
                ld      hl, SECTOR_BUF
                ld      b, 16               ; 512 / 32 entries per sector
ff_entloop:
                push    bc
                push    hl
                ld      a, (hl)
                or      a
                jr      z, ff_endmark       ; $00 = end of directory
                cp      $E5
                jr      z, ff_skip          ; deleted entry
                push    hl
                ld      de, 11
                add     hl, de
                ld      a, (hl)             ; attribute byte (+11)
                pop     hl
                and     $18                 ; volume-label | directory -> skip
                jr      nz, ff_skip
                ld      de, (FAT_NAMEPTR)
                call    name_cmp
                jr      z, ff_found
ff_skip:
                pop     hl
                ld      de, 32
                add     hl, de              ; next 32-byte directory entry
                pop     bc
                djnz    ff_entloop
                ld      hl, (FAT_DIRSEC)
                inc     hl
                ld      (FAT_DIRSEC), hl
                ld      hl, (FAT_DIRREM)
                dec     hl
                ld      (FAT_DIRREM), hl
                jr      ff_secloop
ff_endmark:
                pop     hl
                pop     bc
ff_notfound:
                scf
                ret
ff_found:
                pop     hl                  ; HL = directory entry
                pop     bc
                push    hl
                ld      de, 26
                add     hl, de
                ld      a, (hl)             ; first cluster low (+26)
                inc     hl
                ld      h, (hl)             ; first cluster high (+27)
                ld      l, a
                ld      (FAT_FIRSTCLUS), hl
                pop     hl
                push    hl
                ld      de, 28
                add     hl, de
                ld      de, FAT_FILESIZE
                ld      bc, 4
                ldir                        ; file size (+28..31, LE)
                pop     hl
                or      a                   ; Cy = 0 found
                ret

; fsize_body — MSX-DOS-1 kernel FSIZE ($23) canonical entry $501E's real body
; (M28 §3.2). Wired IN PLACE at $501E (dead-$00 pad, no relocation -- [LANDED-B]).
; Entry: DE=$DA40 (kernel 37-byte FCB copy, name pre-filled at copy+1..11),
; A=$25/B=$00/C=$00, ret=$D88A -- same dispatcher class as $4788/$4793 (M26).
; Locates the file (fat_mount + fat_find, reused wholesale from the existing dir
; search) and sets copy+33..35 = ceil(size/128) as a 24-bit little-endian count;
; not found -> A=L=$FF (map.grauw.nl _FSIZE contract). The prior stub returned a
; constant A=L=$03 for every input and never searched or wrote the field at all.
; CLEAN-ROOM: reuses fat_mount/fat_find (our own, pre-existing) + the published
; GET FILE SIZE contract; no stock routine internals decoded.
fsize_body:
                push    de
                pop     ix                  ; IX = kernel FCB-copy pointer ($DA40)
                push    ix
                pop     de
                call    fat_mount
                jp      c, fsize_miss
                push    ix
                pop     de
                inc     de                  ; DE -> copy+1 (11-byte 8.3 name)
                ex      de, hl              ; HL -> name (fat_find's contract)
                call    fat_find            ; Cy=0 found -> FAT_FILESIZE set
                jp      c, fsize_miss
                ; r0..r2 := ceil(FAT_FILESIZE / 128) = (size + 127) >> 7, 24-bit.
                ld      hl, (FAT_FILESIZE)
                ld      de, (FAT_FILESIZE + 2)
                ld      bc, 127
                add     hl, bc
                jr      nc, fsize_noc
                inc     de
fsize_noc:
                ; 32-bit DE:HL >>= 7 (7 iterations of a whole-value logical shift right;
                ; the discarded top byte, D, is always 0 for any file this ROM's FAT12
                ; volumes can hold).
                ld      b, 7
fsize_shift:
                srl     d
                rr      e
                rr      h
                rr      l
                djnz    fsize_shift
                ; r0..r2 = low 24 bits of DE:HL = L, H, E (LE)
                ld      (ix+33), l
                ld      (ix+34), h
                ld      (ix+35), e
                xor     a                   ; A = 0 = found
                ld      l, a                ; L := A (A=L=0, the pinned success contract)
                jp      rrnd_finish         ; jp: rrnd_finish is far below (out of jr range)
fsize_miss:
                ld      a, $FF
                ld      l, a                ; L := A (A=L=$FF, not-found)
                jp      rrnd_finish

; ===========================================================================
; $26 WRBLK — RANDOM BLOCK WRITE (M28 §3.3, [LANDED-A]/[LANDED-B])
; ===========================================================================
; wrblk_body — the real $47BE canonical WRBLK entry. Entry: DE=$DA40 (kernel FCB
; copy), HL = requested record count, A=$26/B=$00/C=$00, ret=$D88A. Contract
; ([LANDED-A]): RS = copy+14..15 (0 -> 128); start record RR = copy+33..35
; (24-bit LE); byte budget = (HL*RS) & $FFFF; CR/EX (copy+32/+12) untouched;
; past-EOF writes grow the file with a CONTIGUOUS FAT chain through the gap (no
; sparse holes; gap bytes stay whatever was already on disk -- no zero-fill);
; size := max(old, new_RR*RS); RR += HL_REQUESTED (not actual -- the write-side
; advance asymmetry vs RDBLK's actual-based advance); return A=0, HL = the
; ORIGINAL requested count (preserved, carries no result). HL=0 is a size-only
; call: RR-at-or-past-EOF just bumps the size field (no data, no chain change);
; RR-before-EOF is the SHRINK path, which stock gets wrong (leaves the FAT
; inconsistent -> a later FCLOSE fails) -- signed off (§6 Q3) to do the SANE
; thing instead: free the tail chain + EOF-mark so FCLOSE keeps succeeding. This
; is an INTENTIONAL, DOCUMENTED divergence from stock's known-broken behaviour,
; not a regression (see tier2-bdos-coverage.md).
; Unlike RDRND/WRRND (which only reuse the kernel's OWN preceding FOPEN state,
; FAT_FIRSTCLUS/FAT_FILESIZE, never touching the directory entry), WRBLK must
; persist size/first-cluster back to disk -- so it re-locates the entry itself
; (fat_mount + fat_find on copy+1..11) to recover FAT_DIRSEC/a dirent offset for
; fat_dir_update, exactly like fsize_body/fopen_fill_body/fren_body already do.
; This also freshly re-confirms FAT_FIRSTCLUS/FAT_FILESIZE (redundant with the
; kernel's own FOPEN for the same file, but harmless) before the per-record loop.
; CLEAN-ROOM: reuses fat_mount/fat_find/fat_alloc_cluster/fat_next_cluster/
; fat_write_fat_entry/fat_dir_update/write_sector (our own, pre-existing) + the
; published RANDOM BLOCK WRITE contract (map.grauw.nl) + the [LANDED-A] oracle
; contract; no stock routine internals decoded.
wrblk_body:
                ld      (WRBLK_REQ), hl     ; capture the requested count FIRST -- everything
                                            ; below clobbers HL (fat_mount/fat_find/the multiply)
                push    de
                pop     ix                  ; IX = kernel FCB-copy pointer ($DA40)
                push    ix
                pop     de
                call    fat_mount
                jp      c, wrblk_ioerr
                push    ix
                pop     de
                inc     de                  ; DE -> copy+1 (11-byte 8.3 name)
                ex      de, hl              ; HL -> name (fat_find's contract)
                call    fat_find            ; Cy=0 found -> FAT_FIRSTCLUS/FAT_FILESIZE set
                jp      c, wrblk_ioerr
                ; recover the dirent's own location for the eventual fat_dir_update
                ; (fat_find leaves HL -> the matched entry inside SECTOR_BUF).
                ld      de, SECTOR_BUF
                or      a
                sbc     hl, de
                ld      (BDOS_DIROFF), hl
                ld      hl, (FAT_DIRSEC)
                ld      (BDOS_DIRSEC), hl
                ; reseed our own DTA cell (M19 lesson: the kernel's real SETDTA only
                ; ever touches DOS_DTAPTR, never BDOS_DTA).
                ld      hl, (DOS_DTAPTR)
                ld      (BDOS_DTA), hl
                ; resolve RS := copy+14..15, 0 -> 128 (RECSIZE)
                ld      a, (ix+14)
                ld      e, a
                ld      a, (ix+15)
                ld      d, a
                ld      a, d
                or      e
                jr      nz, wrblk_rs_ok
                ld      de, RECSIZE
wrblk_rs_ok:
                ld      (WRBLK_RS), de
                ; load RR (24-bit, copy+33..35) into WRBLK_REC
                ld      a, (ix+33)
                ld      (WRBLK_REC), a
                ld      a, (ix+34)
                ld      (WRBLK_REC + 1), a
                ld      a, (ix+35)
                ld      (WRBLK_REC + 2), a
                ; HL_requested == 0 ? -> size-only / shrink path (no per-record loop)
                ld      hl, (WRBLK_REQ)
                ld      a, h
                or      l
                jp      z, wrblk_zero_path
                ld      (WRBLK_CNT), hl
                ; M29: reset the position cursor once before the per-record loop
                ; starts -- wrblk_position_ext will (re)validate it on its first
                ; call this wrblk_body invocation (wrblk_zero_path never calls
                ; wrblk_position_ext, so this is unreached/irrelevant there).
                xor     a
                ld      (WRBLK_CURVALID), a
; --- main per-record loop: position (extending through any gap), overlay RS DTA
; bytes at the record's (rec&3)*128 slot within its 512-byte sector, persist. ---
wrblk_loop:
                ld      hl, (WRBLK_CNT)
                ld      a, h
                or      l
                jp      z, wrblk_loop_done
                call    wrblk_position_ext  ; Cy=0 ok, SECTOR_BUF <- target sector's bytes
                jp      c, wrblk_full
                ld      a, (WRBLK_RECSEC)
                ld      l, a
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl              ; HL = WRBLK_RECSEC * 128 (0/128/256/384)
                ld      de, SECTOR_BUF
                add     hl, de
                ex      de, hl              ; DE = dest in SECTOR_BUF
                ld      hl, (BDOS_DTA)      ; HL = source record in the caller's DTA
                ld      bc, (WRBLK_RS)
                ldir
                call    rrnd_sector         ; DE = absolute logical sector to persist
                                            ; (reused unchanged: pure function of
                                            ; FAT_CURCLUS/FAT_CLUSSEC, valid regardless
                                            ; of how they were last set)
                ld      hl, SECTOR_BUF
                call    write_sector
                jp      c, wrblk_ioerr
                ; advance DTA by RS
                ld      hl, (BDOS_DTA)
                ld      de, (WRBLK_RS)
                add     hl, de
                ld      (BDOS_DTA), hl
                ; WRBLK_REC += 1 (24-bit)
                ld      hl, (WRBLK_REC)
                inc     hl
                ld      (WRBLK_REC), hl
                ld      a, h
                or      l
                jr      nz, wrblk_reci_noc
                ld      a, (WRBLK_REC + 2)
                inc     a
                ld      (WRBLK_REC + 2), a
wrblk_reci_noc:
                ld      hl, (WRBLK_CNT)
                dec     hl
                ld      (WRBLK_CNT), hl
                jp      wrblk_loop
wrblk_loop_done:
                ; new_RR := RR_start + HL_requested (24-bit + 16-bit)
                ld      a, (ix+33)
                ld      l, a
                ld      a, (ix+34)
                ld      h, a
                ld      de, (WRBLK_REQ)
                add     hl, de
                ld      (ix+33), l
                ld      (ix+34), h
                ld      a, (ix+35)
                adc     a, 0
                ld      (ix+35), a
                ; size := max(old size, new_RR * RS)
                call    wrblk_mul_rr_rs     ; WRBLK_MULACC := (ix+33..35, = new_RR) * RS
                call    wrblk_size_max
                call    wrblk_set_wrfirst
                call    fat_dir_update
                jp      c, wrblk_ioerr2
                xor     a
                ld      hl, (WRBLK_REQ)
                jp      wrblk_finish
wrblk_zero_path:
                ; HL_requested == 0: compute target := RR (unchanged) * RS, then either
                ; grow-or-hold (target >= old size) or shrink (target < old size). RR
                ; itself is NOT advanced (+= 0, a no-op) per [LANDED-A].
                call    wrblk_mul_rr_rs     ; WRBLK_MULACC := (ix+33..35, = RR unchanged) * RS
                ; compare WRBLK_MULACC vs FAT_FILESIZE (32-bit unsigned, MSB first)
                ld      a, (WRBLK_MULACC + 3)
                ld      hl, FAT_FILESIZE + 3
                cp      (hl)
                jr      nz, wzp_decided
                ld      a, (WRBLK_MULACC + 2)
                dec     hl
                cp      (hl)
                jr      nz, wzp_decided
                ld      a, (WRBLK_MULACC + 1)
                dec     hl
                cp      (hl)
                jr      nz, wzp_decided
                ld      a, (WRBLK_MULACC)
                dec     hl
                cp      (hl)
wzp_decided:
                jr      c, wzp_shrink       ; MULACC < FAT_FILESIZE -> shrink path
                call    wrblk_size_max      ; MULACC >= old size -> grow-or-hold (no chain change)
                call    wrblk_set_wrfirst
                jr      wzp_dirupdate
wzp_shrink:
                call    wrblk_shrink        ; frees the tail chain + EOF-marks; sets
                                            ; BDOS_WRBYTES itself (not via wrblk_size_max)
                jp      c, wrblk_ioerr2
                call    wrblk_set_wrfirst
wzp_dirupdate:
                call    fat_dir_update
                jp      c, wrblk_ioerr2
                xor     a
                ld      hl, (WRBLK_REQ)     ; = 0
                jp      wrblk_finish
wrblk_full:
                ld      a, 1                ; disk-full path ([C]-only, not black-box-provoked)
                ld      hl, (WRBLK_REQ)
                jp      wrblk_finish
wrblk_ioerr:
wrblk_ioerr2:
                ld      a, 2                ; generic FDC I/O error (fdc_read_data convention)
                ld      hl, (WRBLK_REQ)
wrblk_finish:                              ; shared tail: M20 dispatcher-flag rule, preserve A/HL
                push    af
                push    hl
                xor     a
                ld      ($F306), a
                pop     hl
                pop     af
                ret

; wrblk_position_ext — position (or extend) the file's iterator to record
; WRBLK_REC (24-bit). M29 (tier2-m29-wrblk-position-cursor-spec.md): keeps an
; incremental cursor (WRBLK_CURVALID/WRBLK_CURSEC) across calls within one
; wrblk_body invocation instead of re-fat_open-ing and re-walking from the head
; every time -- WRBLK_REC is strictly non-decreasing per call (kernel.asm:884),
; so the target sector-in-file is always >= the cursor's last position. First
; call this wrblk_body invocation (or any call once positioned) still walks
; forward via wrblk_read_or_extend_sector exactly as the old from-head walk did;
; only the redundant re-walk of already-visited sectors is elided. Unlike
; rrnd_position, EXTENDS the chain contiguously through any gap instead of
; returning EOF ([LANDED-A]/§6 Q2 full past-EOF extend).
;   out: Cy = 0 ok (SECTOR_BUF holds the target sector's current on-disk bytes --
;        a freshly allocated sector reads back whatever is already on the disk,
;        "uninitialised", no zero-fill, EXCEPT the delta==0 same-sector case,
;        where SECTOR_BUF already holds it from the previous call -- no I/O);
;        Cy = 1 = disk full / I/O error
;        WRBLK_RECSEC := WRBLK_REC & 3 (record-in-sector; the codebase's fixed
;        4-records/512-byte-sector convention -- independent of RS, which only
;        scales the byte quantity copied per record and the RR/byte-budget
;        bookkeeping, per spec §3.3)
wrblk_position_ext:
                ld      a, (WRBLK_REC)
                and     3
                ld      (WRBLK_RECSEC), a
                ; target sector-in-file = WRBLK_REC >> 2 (24-bit value; D:E:A below)
                ld      a, (WRBLK_REC + 2)
                ld      d, a
                ld      a, (WRBLK_REC + 1)
                ld      e, a
                ld      a, (WRBLK_REC)
                ld      b, 2
wpe_shr:
                srl     d
                rr      e
                rra
                djnz    wpe_shr
                ; D:E:A = target sector-in-file; D is always 0 for any file this ROM's
                ; FAT12 (720K-class floppy) volumes can hold, so BC below is a safe
                ; 16-bit sector-in-file count.
                ld      c, a
                ld      b, e                ; BC = target_sec (16-bit; D/high byte always 0)
                ld      a, (WRBLK_CURVALID)
                or      a
                jr      z, wpe_fresh
                ; --- cursor valid: incremental path, no fat_open ---------------
                push    bc                  ; save target_sec
                pop     hl                  ; HL = target_sec
                ld      de, (WRBLK_CURSEC)
                or      a
                sbc     hl, de              ; HL = target_sec - WRBLK_CURSEC (>=0, monotonic)
                ld      a, h
                or      l
                jr      z, wpe_same         ; delta==0 -> already positioned, no I/O
                ; delta >= 1: advance HL steps via wrblk_read_or_extend_sector
                ld      (WRBLK_CURSEC), bc  ; bc still holds target_sec
                ex      de, hl              ; DE = delta
wpe_adv:
                push    de                  ; wrblk_read_or_extend_sector clobbers BC/DE
                                            ; internally (wroe_mul's djnz counter) -- same
                                            ; save/restore rrnd_position uses around
                                            ; fat_read_file_sector for the identical reason
                call    wrblk_read_or_extend_sector
                pop     de
                ret     c
                dec     de
                ld      a, d
                or      e
                jr      nz, wpe_adv
                ret                         ; Cy=0 (wrblk_read_or_extend_sector cleared it)
wpe_same:
                or      a                   ; Cy=0, no I/O -- SECTOR_BUF already holds
                ret                         ; the target sector from the previous call
wpe_fresh:
                call    fat_open            ; iterator -> FAT_FIRSTCLUS, clussec 0
                ld      (WRBLK_CURSEC), bc
                ld      a, 1
                ld      (WRBLK_CURVALID), a
                inc     bc                  ; BC = walk-loop count (>=1; sector 0 needs 1 step)
wpe_walk:
                push    bc                  ; wrblk_read_or_extend_sector clobbers BC
                                            ; internally (wroe_mul's djnz counter) -- same
                                            ; save/restore rrnd_position uses around
                                            ; fat_read_file_sector for the identical reason
                call    wrblk_read_or_extend_sector
                pop     bc
                ret     c
                dec     bc
                ld      a, b
                or      c
                jr      nz, wpe_walk
                ret

; wrblk_read_or_extend_sector — like fat.asm's fat_read_file_sector, but when the
; chain runs out (cluster<2 empty-file case, or cluster>=$0FF8 end-of-chain) this
; ALLOCATES a new cluster and links it CONTIGUOUSLY instead of returning EOF. Does
; NOT modify fat_read_file_sector itself (kept byte-identical -- same non-goal
; precedent as M26): a parallel routine, reusing fat_advance/fat_next_cluster/
; fat_alloc_cluster/fat_write_fat_entry. Captures FAT_CURCLUS BEFORE this step's
; own advance/allocate (WRBLK_PREVCLUS) so a freshly allocated cluster links onto
; the TRUE last-good cluster, not a stale EOC/free value fat_advance may have just
; produced; also seeds FAT_FIRSTCLUS when the allocation is the file's very first
; cluster (empty file), so a LATER call in the same wrblk_body loop (re-fat_opens
; every record) walks the newly-grown chain correctly.
;   out: Cy = 0 ok (SECTOR_BUF holds the sector's current on-disk bytes); Cy = 1 =
;        disk full / I/O error
wrblk_read_or_extend_sector:
                ld      hl, (FAT_CURCLUS)
                ld      (WRBLK_PREVCLUS), hl
                ld      a, (FAT_CLUSSEC)
                ld      hl, FAT_SECPERCLUS
                cp      (hl)
                jr      c, wroe_incluster
                call    fat_advance
wroe_incluster:
                ld      hl, (FAT_CURCLUS)
                ld      de, 2
                or      a
                sbc     hl, de
                jr      c, wroe_need_extend ; cluster < 2 (free / empty file)
                ld      hl, (FAT_CURCLUS)
                ld      de, $0FF8
                or      a
                sbc     hl, de
                jr      nc, wroe_need_extend ; cluster >= $0FF8 = end-of-chain
                jr      wroe_have_valid
wroe_need_extend:
                call    fat_alloc_cluster   ; HL = new cluster; Cy=1 disk full
                ret     c
                ld      de, (WRBLK_PREVCLUS)
                ld      a, d
                or      e
                jr      z, wroe_first
                push    hl                  ; save new cluster
                ex      de, hl              ; HL = previous (last-good) cluster
                pop     de                  ; DE = new cluster (link value)
                push    de
                call    fat_write_fat_entry ; previous -> new
                pop     hl                  ; HL = new cluster
                ret     c
                jr      wroe_have_new
wroe_first:
                ld      (FAT_FIRSTCLUS), hl ; file's very first cluster (was empty)
wroe_have_new:
                ld      (FAT_CURCLUS), hl
                xor     a
                ld      (FAT_CLUSSEC), a
wroe_have_valid:
                ; sector = firstData + (cluster-2)*secPerClus + clussec (identical
                ; tail shape to fat_read_file_sector/frs_mul_body -- deliberately NOT
                ; shared/modified, a new parallel routine per the §4 non-goal precedent)
                ld      hl, (FAT_CURCLUS)
                ld      de, 2
                or      a
                sbc     hl, de
                ex      de, hl              ; DE = cluster - 2
                ld      hl, 0
                ld      a, (FAT_SECPERCLUS)
                ld      b, a
wroe_mul:
                add     hl, de
                djnz    wroe_mul            ; HL = (cluster-2) * secPerClus
                ld      de, (FAT_FIRSTDATA)
                add     hl, de
                ld      a, (FAT_CLUSSEC)
                ld      e, a
                ld      d, 0
                add     hl, de              ; HL = absolute logical sector
                ex      de, hl
                ld      hl, SECTOR_BUF
                call    read_sector
                ret     c
                ld      a, (FAT_CLUSSEC)
                inc     a
                ld      (FAT_CLUSSEC), a
                or      a                   ; Cy = 0 success
                ret

; wrblk_mul_rr_rs — WRBLK_MULACC(32-bit LE, WBUF+500) := RR(24-bit, ix+33..35) *
; RS(16-bit, WRBLK_RS). Classic LSB-first shift-add multiply, 24 iterations: a
; 32-bit zero-extended copy of RS (WRBLK_MULOP, WBUF+504) is doubled each
; iteration and added into WRBLK_MULACC whenever the corresponding bit of a
; shifting 24-bit copy of RR (WRBLK_MULN, WBUF+508) is 1. Deliberately
; register-free (RAM-only state) so every step is an independently-checkable
; byte operation -- host-unit-tested (tests/test_wrblk_mul.py). Runs after
; fat_find's SECTOR_BUF scan and before fat_dir_update's own WBUF read/write, so
; WBUF's tail is safe transient scratch here (§ equates.inc note).
;   out: WRBLK_MULACC = the 32-bit product; trashes AF, BC, DE, HL
wrblk_mul_rr_rs:
                xor     a
                ld      (WRBLK_MULACC), a
                ld      (WRBLK_MULACC + 1), a
                ld      (WRBLK_MULACC + 2), a
                ld      (WRBLK_MULACC + 3), a
                ld      hl, (WRBLK_RS)
                ld      (WRBLK_MULOP), hl
                xor     a
                ld      (WRBLK_MULOP + 2), a
                ld      (WRBLK_MULOP + 3), a
                ld      a, (ix+33)
                ld      (WRBLK_MULN), a
                ld      a, (ix+34)
                ld      (WRBLK_MULN + 1), a
                ld      a, (ix+35)
                ld      (WRBLK_MULN + 2), a
                ld      b, 24
wmr_loop:
                ld      a, (WRBLK_MULN)
                and     1
                jr      z, wmr_noadd
                ld      a, (WRBLK_MULACC)
                ld      hl, WRBLK_MULOP
                add     a, (hl)
                ld      (WRBLK_MULACC), a
                ld      a, (WRBLK_MULACC + 1)
                inc     hl
                adc     a, (hl)
                ld      (WRBLK_MULACC + 1), a
                ld      a, (WRBLK_MULACC + 2)
                inc     hl
                adc     a, (hl)
                ld      (WRBLK_MULACC + 2), a
                ld      a, (WRBLK_MULACC + 3)
                inc     hl
                adc     a, (hl)
                ld      (WRBLK_MULACC + 3), a
wmr_noadd:
                ld      a, (WRBLK_MULN + 2)
                srl     a
                ld      (WRBLK_MULN + 2), a
                ld      a, (WRBLK_MULN + 1)
                rra
                ld      (WRBLK_MULN + 1), a
                ld      a, (WRBLK_MULN)
                rra
                ld      (WRBLK_MULN), a
                ld      a, (WRBLK_MULOP)
                add     a, a
                ld      (WRBLK_MULOP), a
                ld      a, (WRBLK_MULOP + 1)
                adc     a, a
                ld      (WRBLK_MULOP + 1), a
                ld      a, (WRBLK_MULOP + 2)
                adc     a, a
                ld      (WRBLK_MULOP + 2), a
                ld      a, (WRBLK_MULOP + 3)
                adc     a, a
                ld      (WRBLK_MULOP + 3), a
                djnz    wmr_loop
                ret

; wrblk_size_max — BDOS_WRBYTES(32) := max(FAT_FILESIZE, WRBLK_MULACC). Simple
; 32-bit unsigned compare (MSB byte first); copies the winner into BDOS_WRBYTES.
wrblk_size_max:
                ld      a, (WRBLK_MULACC + 3)
                ld      hl, FAT_FILESIZE + 3
                cp      (hl)
                jr      nz, wsm_decided
                ld      a, (WRBLK_MULACC + 2)
                dec     hl
                cp      (hl)
                jr      nz, wsm_decided
                ld      a, (WRBLK_MULACC + 1)
                dec     hl
                cp      (hl)
                jr      nz, wsm_decided
                ld      a, (WRBLK_MULACC)
                dec     hl
                cp      (hl)
wsm_decided:
                jr      c, wsm_keepold      ; MULACC < FILESIZE -> old size wins
                ld      hl, WRBLK_MULACC
                ld      de, BDOS_WRBYTES
                ld      bc, 4
                ldir
                ret
wsm_keepold:
                ld      hl, FAT_FILESIZE
                ld      de, BDOS_WRBYTES
                ld      bc, 4
                ldir
                ret

; wrblk_set_wrfirst — BDOS_WRFIRST := FAT_FIRSTCLUS (may have just been updated by
; wrblk_read_or_extend_sector's very-first-cluster case, or zeroed by wrblk_shrink's
; empty-file case) -- the field fat_dir_update stamps into the dirent's first-
; cluster word.
wrblk_set_wrfirst:
                ld      hl, (FAT_FIRSTCLUS)
                ld      (BDOS_WRFIRST), hl
                ret

; wrblk_shrink — HL_requested==0 and the target size (WRBLK_MULACC, already =
; RR*RS) is BEFORE the file's current end -- shrink to that size ([LANDED-A]/§6
; Q3 "DO THE SANE THING": stock corrupts the FAT here so a later FCLOSE fails;
; ours frees the tail chain + EOF-marks the new last cluster so FCLOSE keeps
; succeeding -- an INTENTIONAL, DOCUMENTED divergence from stock, not a
; regression). Sets BDOS_WRBYTES itself (the target size) -- does NOT go through
; wrblk_size_max, which would wrongly keep the OLD (larger) size.
;   out: Cy = 0 ok, Cy = 1 = I/O error
wrblk_shrink:
                ld      hl, WRBLK_MULACC
                ld      de, BDOS_WRBYTES
                ld      bc, 4
                ldir                        ; BDOS_WRBYTES := target size
                ld      a, (WRBLK_MULACC)
                ld      hl, WRBLK_MULACC + 1
                or      (hl)
                inc     hl
                or      (hl)
                inc     hl
                or      (hl)                ; Z iff target size == 0 (all 4 bytes)
                jp      z, wshrink_empty
                ; keep_sectors = ceil(target_size / 512) = (target_size + 511) >> 9
                ld      hl, (WRBLK_MULACC)
                ld      de, 511
                add     hl, de
                ld      a, (WRBLK_MULACC + 2)
                adc     a, 0                ; A:HL = target_size + 511 (24-bit-safe)
                ld      l, h
                ld      h, a                ; HL = (target_size+511) >> 8
                srl     h
                rr      l                   ; HL = (target_size+511) >> 9 = keep_sectors
                ; keep_clusters = ceil(keep_sectors / SECPERCLUS), repeated subtraction
                ; (SECPERCLUS is a small BPB constant; keep_sectors is bounded to a
                ; floppy's few-thousand-sector range -- cheap either way)
                ld      a, (FAT_SECPERCLUS)
                ld      c, a
                ld      b, 0                ; BC = SECPERCLUS
                push    bc
                pop     de
                dec     de
                add     hl, de              ; HL = keep_sectors + SECPERCLUS - 1
                ld      de, 0               ; DE = quotient accumulator
wshrink_divloop:
                or      a
                sbc     hl, bc
                jr      c, wshrink_divdone
                inc     de
                jr      wshrink_divloop
wshrink_divdone:
                ld      (WRBLK_KEEPCNT), de ; keep_clusters (>= 1, since target size > 0)
                ld      hl, (FAT_FIRSTCLUS)
wshrink_walk:
                ld      de, (WRBLK_KEEPCNT)
                dec     de
                ld      a, d
                or      e
                jr      z, wshrink_atlast   ; consumed keep_clusters-1 steps -> HL = last-to-keep
                ld      (WRBLK_KEEPCNT), de
                call    fat_next_cluster
                push    hl
                ld      de, $0FF8
                or      a
                sbc     hl, de
                pop     hl
                jr      nc, wshrink_atlast  ; chain shorter than expected -- stop defensively
                jr      wshrink_walk
wshrink_atlast:
                ; HL = the cluster to KEEP as the file's new (and only surviving) tail.
                push    hl
                call    fat_next_cluster    ; HL := its CURRENT link (the old tail start)
                ld      (WRBLK_NEXTCLUS), hl
                pop     hl                  ; HL = the keep-cluster
                ld      de, EOC
                call    fat_write_fat_entry ; keep-cluster := EOC in every FAT copy
                jp      c, wshrink_ioerr
                ld      hl, (WRBLK_NEXTCLUS)
                jr      wshrink_freeloop
wshrink_empty:
                ld      hl, (FAT_FIRSTCLUS) ; HL = old first cluster (the whole chain to free)
                push    hl
                ld      hl, 0
                ld      (FAT_FIRSTCLUS), hl ; file becomes clusterless
                pop     hl
wshrink_freeloop:
                ld      a, h
                or      l
                jr      z, wshrink_freedone ; HL == 0 -> nothing to free
                push    hl
                ld      de, $0FF8
                or      a
                sbc     hl, de
                pop     hl
                jr      nc, wshrink_freedone ; HL >= $0FF8 (EOC) -> nothing more to free
                push    hl                  ; HL = cluster to free
                call    fat_next_cluster    ; HL := its current link
                ld      (WRBLK_NEXTCLUS), hl
                pop     hl                  ; HL = the cluster to free (restored)
                ld      de, 0
                call    fat_write_fat_entry ; mark it free ($000)
                jp      c, wshrink_ioerr
                ld      hl, (WRBLK_NEXTCLUS)
                jr      wshrink_freeloop
wshrink_freedone:
                or      a
                ret
wshrink_ioerr:
                scf
                ret

                ds      $75A5 - $, $00
                jp      k_75A5          ; $75A5
                ds      $77B8 - $, $00
                jp      k_77B8          ; $77B8
                ds      $782B - $, $00
                jp      k_782B          ; $782B
; --- contract bodies (stubs; filled in milestone 4; added as each veneer lands) ---
k_402D:         ret
k_41FD:         ret
k_4558:         ret
k_46C8:         ret
; k_47B2 — M21b: generic BDOS RDBLK-via-page1 handler (tier2-m21-spec.md §5.4/
; §5.5; was: a COMMAND.COM-only diagnostic loader, Tier-2 M5.4 first cut).
; The kernel's $27 RDBLK handler ($D887, ret=$C51D) CALLs $47B2 for BOTH the
; boot-time COMMAND.COM self-load (DE=$DC5B) and the runtime typed-command TPA
; load (DE=$DA40) — both hand a fully-formed FCB of the SAME shape (§5.4), and
; by the time this runs the kernel's own preceding FOPEN (page-1 $4462, M21a)
; has already located the file and left FAT_FIRSTCLUS/FAT_FILESIZE seeded for
; it, so no re-search is needed here: just re-prime the iterator and stream.
; Requested count (entry HL) is treated as an upper bound in principle, but
; every observed caller requests far more than any file this ROM handles and
; relies on EOF to stop the transfer — reading straight to EOF is a documented
; simplification, the same shape as bdos_rdblk's own random-record-0-only
; assumption (disk/driver.asm).
;   in:  DE = FCB pointer (kernel work buffer); HL = requested record count
;   out: A = $01 EOF (MSX2 TH; matches stock's observed constant, §0.1/§5.5)
;        HL = BC = total bytes transferred (= the file's full size, since the
;        transfer always runs to EOF); IY = the entry DE (kernel work pointer,
;        §5.4/§8.50); IX = the drive-A DPB (§8.50's original boot contract,
;        extended unconditionally per §5.4 — both callers get the same body).
;        $F306 cleared (Tier-2 dispatcher-flag rule, M20).
; CLEAN-ROOM: our own file layer streaming into the caller's own DTA; COMMAND.COM
; is data we copy, never disassembled.
k_47B2:         push    de                  ; save entry DE (kernel work ptr) for the IY return
                ; Seed OUR internal BDOS_DTA from the kernel's own live DTA pointer
                ; (DOS_DTAPTR, $F23D -- M19) rather than trusting BDOS_DTA itself:
                ; the kernel's real SETDTA writes DOS_DTAPTR only, never our own
                ; mini-BDOS's cell, so BDOS_DTA is stale leftover from whatever
                ; this ROM's own internal loader last used it for (found the hard
                ; way: it read back $1A80, the END of the boot-time COMMAND.COM
                ; load, at the runtime BDOSX.COM call).
                ld      hl, (DOS_DTAPTR)
                ld      (BDOS_DTA), hl
                call    fat_open            ; re-prime the iterator (FAT_FIRSTCLUS already found)
                ld      hl, FAT_FILESIZE
                ld      de, BDOS_BYTESLEFT
                ld      bc, 4
                ldir                        ; BDOS_BYTESLEFT = true file size (fresh read)
                ld      a, RECPERSEC
                ld      (BDOS_RECIDX), a    ; buffer empty -> first read refills
k47b2_rdloop:   call    bdos_seqread        ; A=$00 record delivered / $01 EOF
                or      a
                jr      nz, k47b2_done      ; EOF -> the file is fully transferred
                ld      hl, (BDOS_DTA)      ; advance DTA one record
                ld      de, RECSIZE         ; 128
                add     hl, de
                ld      (BDOS_DTA), hl
                jr      k47b2_rdloop
; k47b2_done — the file is fully transferred; reproduce the pinned return contract
; (§5.5, exact register match at $C51D: AF=$0142 HL=$0480 for the runtime caller;
; §8.50, HL=BC=FAT_FILESIZE IX=DRVA_DPB IY=entry-DE for the boot caller).
k47b2_done:     xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                or      a                   ; clear carry (A=0 already; overwritten by dec next)
                ld      b, 1
                dec     b                   ; B=0; F = Z=1,N=1,C=0 (§5.5's AF=$0142 flag half)
                ld      ix, DRVA_DPB        ; IX = $F195 drive-A DPB (§8.50)
                ld      hl, (FAT_FILESIZE)  ; HL = total bytes transferred (LD: flags unaffected)
                push    hl
                pop     bc                  ; BC = HL (§5.5: "the genuine BDOS $27 returns the
                                             ; count in both")
                pop     iy                  ; IY = saved entry DE (kernel work pointer)
                ld      a, 1                ; A = $01 EOF (LD: flags unaffected) -> AF = $0142
                ret
k_4919:         ret
k_4935:         ret
k_498C:         ret
k_49B4:         ret
k_4A39:         ret
k_4B59:         ret
k_4BE5:         ret
k_4C25:         ret
k_4E4B:         ret
k_4EDE:         ret
k_5FE5:         ret
k_607B:         ret
k_75A5:         ret
k_77B8:         ret
k_782B:         ret

; p1_blit_tmpl — clean-room blit routine (§8.35), LDIR'd to P1_BLIT ($E77A) by
; build_resident.  Called from dskio (page-1 ROM) via `call P1_BLIT` when the
; DSKIO transfer destination is in page 1 ($4000-$7FFF): the FDC read was
; redirected to SECTOR_BUF; this copies SECTOR_BUF to the original page-1 target
; by briefly switching page-1 sub-slot from disk ROM (3-1) to RAM (3-0).
;
; Runs from page-3 RAM (always-mapped), so the page-1 sub-slot flip is safe.
; The call return address (a page-1 ROM address) is still on the stack while
; page 1 = RAM; sub-slot 1 is restored BEFORE `ret`, so the RET lands in the ROM.
;
; $FFFF secondary register: write = direct sub-slot IDs (bits [3:2] = page-1
; sub-slot); read = complement of the written value (MSX2 TH §2.4).  We CPL
; after reading to recover the "write" form, mask bits 3:2 to 00 (sub-slot 0 =
; RAM), then write; on return CPL to restore original sub-slot 1.
;
; Source: MSX2 TH §2.4 (expanded-slot secondary register semantics); sub-slot
; layout confirmed by black-box differential (set_ramad / page0_ram_in, same
; host).  Clean-room: never reads the stock $EF95 or any proprietary driver.
; Lives in the free tail (LDIR-relocated; moved here from the cramped pre-$41FD
; region so the wa_seg M5.6 additions fit, §8.58). wa_seg_*_tmpl follows it
; immediately so build_resident copies BOTH with one LDIR (RAM-contiguous).
;   in:  P1_DEST = page-1 target address (word in page-3 scratch)
;   out: 512 bytes from SECTOR_BUF copied to (P1_DEST); page-1 sub-slot restored
p1_blit_tmpl:
                ld      a, ($FFFF)          ; A = inverted sub-slot state (MSX2 TH)
                cpl                         ; A = actual sub-slot write value
                push    af                  ; save original state for restore
                and     $F3                 ; bits 3:2 -> 00: page 1 = sub-slot 0 (RAM)
                ld      ($FFFF), a          ; page 1 now maps to RAM
                ld      hl, SECTOR_BUF      ; source: FDC data was read here
                ld      de, (P1_DEST)       ; dest: original page-1 target (now RAM)
                ld      bc, 512
                ldir
                pop     af                  ; A = original sub-slot write value
                ld      ($FFFF), a          ; page 1 back to disk ROM (sub-slot 1)
                ret
p1_blit_end:

; wa_seg_*_tmpl — clean-room bodies for the $F368/$F36B work-area segment-switch
; hooks (§8.58), LDIR'd to WA_SEG by build_resident and wired into the $F368 table
; by build_wa_table. The relocated kernel CALLs $F368 to map the disk ROM into
; page 1 (so it can run a page-1 disk-ROM routine) and $F36B to map RAM into page 1
; (so it can read its data living UNDER the page-1 ROM). On this expanded slot 3,
; subslot 1 = disk ROM, subslot 0 = RAM (machine config); the page-1 subslot is
; bits [3:2] of the slot-3 secondary register, $04 = subslot 1, $00 = subslot 0.
;
; Contract (measured stock, §8.58): register-TRANSPARENT (entry regs == exit regs);
; only persistent effect = SLTTBL[3] ($FCC8) and the live secondary register
; ($FFFF) set to $04 (rom) / $00 (ram). We read-modify-WRITE only the page-1 bits
; (mask $F3) so the other pages' subslots are preserved, source the current value
; from the SLTTBL mirror (write-form; $FFFF reads back complemented, so the mirror
; is the safe source), update the mirror then the live register, under DI. No EI:
; faithful -- the kernel calls these with interrupts already off (§8.58 trace).
; Bodies run from page-3 RAM (always mapped), so the page-1 flip never unmaps them.
; Lives in the free tail (LDIR-relocated; ROM position must not disturb canonical
; addresses -- the inline-before-$41FD placement overflowed that gap, §M5.6).
;
; Clean-room: our own standard expanded-slot switch (MSX2 TH §2.4 secondary-slot +
; SLTTBL); the stock $DF57/$DF59 bytes are never read. Straight-line + one PC-
; relative jr, so a plain LDIR relocates it verbatim.
;   in:  -            ; out: page-1 subslot of slot 3 set; all registers preserved
wa_seg_rom_tmpl:                            ; $F368 body: map disk ROM into page 1
                push    af
                push    bc                  ; B is our scratch -> preserve (transparent)
                ld      a, $04              ; page-1 bits = subslot 1 (disk ROM)
                jr      wa_seg_set_tmpl     ; (relocatable: PC-relative)
wa_seg_ram_tmpl:                            ; $F36B body: map RAM into page 1
                push    af
                push    bc
                ld      a, $00              ; page-1 bits = subslot 0 (RAM)
wa_seg_set_tmpl:
                di
                ld      b, a                ; B = desired page-1 subslot bits
                ld      a, (SLTTBL3)        ; current slot-3 subslot (write-form mirror)
                and     $F3                 ; clear page-1 bits, keep pages 0/2/3
                or      b                   ; merge new page-1 bits
                ld      (SLTTBL3), a         ; update RAM mirror first
                ld      ($FFFF), a          ; ...then the live secondary-slot register
                pop     bc
                pop     af
                ret
wa_seg_end_tmpl:
WA_SEG_ROM      equ     WA_SEG + (wa_seg_rom_tmpl - wa_seg_rom_tmpl)   ; = WA_SEG
WA_SEG_RAM      equ     WA_SEG + (wa_seg_ram_tmpl - wa_seg_rom_tmpl)

; f365_iord_tmpl — clean-room body for the fixed disk-work-area slot-read stub at
; $F365 (M15 OI-1/§7 pin: unbuilt/FF on ours; §7.1 causally BOUNDS the func-9 STROUT
; output blocker to completing `wa_seg` + this stub). Reads the PPI primary-slot-
; select register (port $A8) and returns; the disk-ROM work area's own per-char
; output loop CALLs this fixed address (observed black-box: reader PC = $F365 itself,
; i.e. an executed 2-instruction stub, never disassembled — see docs/tier2-m15-spec.md
; §7.2). Installed at the FIXED address $F365 (not WA_SEG-relative: the kernel calls
; it by that absolute address, like WA_JMPTAB), by install_f365 below.
; CLEAN-ROOM: IN A,(n) reading port $A8 is the documented i8255 PPI primary-slot-
; select register (MSX2 TH ch.2 / i8255 PPI datasheet, docs/allowed-sources.md class
; A) — our own encoding of a public 2-instruction sequence, not read from the ROM.
;   in: - ; out: A = primary-slot register; other registers preserved
f365_iord_tmpl:
                in      a, ($A8)
                ret
f365_iord_end:

; install_f365 — copies f365_iord_tmpl to the fixed address $F365. Lives in the
; free tail (no budget limit) and is reached by a single 3-byte `call` from
; build_resident's cramped pre-$41FD path (see init.asm) instead of inlining the
; ld/ld/ld/ldir sequence there, which overflows that region's canonical-address
; budget (M15 §7.1/§7.2: verified — an inline second copy there makes 3-pass/
; symbol-table assembly silently emit an empty object file, no error printed).
install_f365:
                ld      hl, f365_iord_tmpl
                ld      de, F365_STUB
                ld      bc, f365_iord_end - f365_iord_tmpl
                ldir
                ret

; res_print_tmpl — clean-room body for the resident $-string print routine, relocated
; to RES_PRINT ($F1C9) by install_res_print (M15 §9.2/§9.3(ii)). The kernel CALLs
; $F1C9 with DE -> a '$'-terminated string. Emits each char via conout_body (the
; proven $5454 CONOUT path func-2/conin_line_body already use) before advancing --
; the M15 root cause was that our first cut consumed the string without emitting it.
; conout_body preserves BC/DE/HL/IX/IY internally, but only across ITS OWN entry
; state; since E is overwritten with the char before the call, DE (the string
; pointer) is saved/restored around the call here. Straight-line + one PC-relative
; jr, so a plain LDIR relocates it verbatim.
; CLEAN-ROOM: derives from the published func-9 STROUT contract ('$'-terminated
; string at DE) + our own conout_body; no stock bytes (never reads $F392/$F2AC/
; $F237/$D88A-region routine bytes, docs/tier2-m15-spec.md §5/§9).
;   in:  DE -> '$'-terminated string ; out: DE past the '$', A=$24, others as Z80 CP
res_print_tmpl:
                ld      a, (de)         ; A = next string byte
                inc     de
                cp      '$'             ; $24 = MS-DOS string terminator
                ret     z               ; done -> return to the kernel
                push    de              ; save the string pointer (E about to change)
                ld      e, a            ; conout_body's ABI: char in E (M10)
                call    conout_body     ; emit via $5454 CONOUT path -> CHPUT
                pop     de              ; restore the string pointer
                jr      res_print_tmpl  ; (relocatable: PC-relative loop)
res_print_end:

; install_res_print — copies res_print_tmpl to RES_PRINT ($F1C9). Lives in the free
; tail (no budget limit) and is reached by a single 3-byte `call` from build_resident's
; cramped pre-$41FD path (init.asm), same rationale as install_f365 (§7.1/§7.2/§9.3).
install_res_print:
                ld      hl, res_print_tmpl
                ld      de, RES_PRINT
                ld      bc, res_print_end - res_print_tmpl
                ldir
                ret

; seldsk_drv_body — the $50D5 kernel SELDSK-time entry (M17; tier2-m17-spec.md).
; The relocated kernel CALLs $50D5 while processing BDOS SELDSK ($0E) to read the
; logical-drive count. Black-box contract (M17 §2.1, readwatch causal pin): read
; $F347 into A, preserve BC/DE/HL/IX/IY. Reached directly from the fixed $50D5 veneer
; (jp seldsk_drv_body) -- lives here in the free tail like conin_line_body/conout_body.
; CLEAN-ROOM: derives from the observed DATA-cell read contract (return [$F347]) +
; our own code; no stock/kernel bytes decoded (only entry/exit regs + the $F347 read).
;   in: -    ; out: A = ($F347) = drive count ; BC/DE/HL/IX/IY preserved
seldsk_drv_body:
                ld      a, (DRVCNT)     ; DRVCNT = $F347 = logical-drive count ($02)
                ret

; curdrv_body — the $50C4 kernel CURDRV-time entry (M18; tier2-m18-spec.md).
; The relocated kernel CALLs $50C4 while processing BDOS CURDRV ($19) to read the
; CURRENT-drive index. Black-box contract (M18 §2.1, readwatch causal pin): read
; $F247 into A, preserve BC/DE/HL/IX/IY. Reached directly from the fixed $50C4 veneer
; (jp curdrv_body) -- lives here in the free tail like seldsk_drv_body.
; CLEAN-ROOM: derives from the observed DATA-cell read contract (return [$F247]) +
; our own code; no stock/kernel bytes decoded (only entry/exit regs + the $F247 read).
;   in: -    ; out: A = ($F247) = current drive ; BC/DE/HL/IX/IY preserved
curdrv_body:
                ld      a, (CURDRV_CELL) ; CURDRV_CELL = $F247 = current-drive index ($00)
                ret

; ===== M19: runtime directory search (BDOS SFIRST $11 / SNEXT $12) =============
; sfirst_body / snext_body / dirscan_match / name_cmp_wild — the bodies behind the
; $4FB8 (SFIRST) / $5006 (SNEXT) page-1 kernel entries. They walk our own root
; directory (reusing fat_mount + the fat_find ff_secloop/ff_entloop structure),
; match each 8.3 name against the kernel's search-FCB pattern (with the ? wildcard),
; copy the found entry's drive-byte + 32-byte directory image to the runtime DTA,
; and persist the scan position in BDOS_SRCHIDX so SNEXT resumes where the prior
; call stopped. Return A=$00 found / A=$FF exhausted (published SFIRST/SNEXT
; contract; the flags are irrelevant to the caller — M19 §2.4).
;
; PINNED black-box contract (M19 §2/§4, callseq/capture — NO stock CODE decoded):
;   - entry DE -> the kernel's search-FCB copy: drive byte at +0, 11-byte 8.3 name
;     pattern at +1..+11 (?=$3F matches any single char; DIR issues all-? -> lists
;     every entry). Observed DE=$DA40, [$DA40]=80 3F 3F ... (M19 §2.3/§4.5).
;   - the runtime DTA base is the kernel's current-DTA pointer, the fixed work-area
;     word at DOS_DTAPTR ($F23D) (=$D403 here, set via the kernel's own SETDTA just
;     before the search); read fresh each call (M19 §4.1). It receives one drive
;     byte (current drive + 1) then the 32-byte raw dir entry (observed: DTA=
;     01 <32-byte entry>, M19 §4.4).
;   - NO attribute filter: SFIRST/SNEXT surface EVERY non-$E5, non-$00 entry incl.
;     volume-label ($08) and subdir ($10) entries (stock returned the SandStone
;     volume label as match #1; COMMAND.COM's formatter does the label filtering /
;     "nn files" count, not us — M19 §4.4/§7, verified against test.dsk).
; CLEAN-ROOM: our own dir walk over our own fat_* layer + the published FCB /
; directory-entry / SFIRST-SNEXT contract; the stock routine's internals (108/101
; page-1 PCs) were never decoded — only entry/exit registers, call counts, and
; one-sided DATA reads of OUR OWN memory. See docs/tier2-m19-spec.md.

; setdta_cache_body — the $5058 kernel SETDTA-time entry (M19). Caches the new DTA
; pointer (DE) into the disk work-area cell DOS_DTAPTR ($F23D), so the SFIRST/SNEXT
; bodies can read the runtime DTA from a fixed cell (as stock's SFIRST does, PCs
; $4FCC/$4FEF). Register-transparent (like curdrv_body/wa_seg): preserves A/BC/DE/
; HL/IX/IY. Reached from the fixed $5058 veneer (jp setdta_cache_body).
; CLEAN-ROOM: our own DE->$F23D store + the observed entry DE=DTA / write-$F23D
; contract; no stock routine internals decoded. See docs/tier2-m19-spec.md.
;   in:  DE = new DTA pointer ; out: ($F23D) := DE ; all registers preserved
setdta_cache_body:
                ld      (DOS_DTAPTR), de    ; $F23D := DE (runtime DTA pointer)
                ret

; getalloc_body — the $505D kernel GETALLOC-time entry (M20 REVISION 3;
; tier2-m20-spec.md). BDOS $1B GETALLOC: return the volume's allocation geometry.
;
; Walks clusters 2..(rawTotal-1) sector-by-sector into WBUF (the SAME fatofs/byteidx/
; parity math and the SAME shared fac_entry_from_wbuf unpack that fat_alloc_cluster
; uses -- fat.asm; not modified, not called in place, so the Tier-1 write path stays
; byte-unchanged), counting $000 (free) entries instead of stopping at the first one.
; The cluster/free-counter/loop-bound live on the CPU stack across each
; fac_entry_from_wbuf call (it clobbers AF/BC/DE/HL and preserves nothing -- same
; push/pop-around-the-call idiom as fat.asm's own fac_have_sec).
;
; The FIX (Revision 3, see the $505D veneer comment above for the full root-cause
; writeup): clear the dispatcher's HL-passthrough flag ($F306) before `ret`, loading
; the final A value AFTER the clear. Without this the kernel's common BDOS-exit path
; silently overwrites our correct HL with a mirror of our own A/BC.
;
; Any FDC read error takes the fail-safe exit (A=0 BC=$0200 DE=0 HL=0) -- matches
; fat_total_clusters' own "report no free space" error posture.
;
; CLEAN-ROOM: our own FAT scan (fat_mount + read_sector, reusing fat.asm's existing
; fac_entry_from_wbuf unpack) + the published GETALLOC A/BC/DE/HL contract (map.grauw.nl
; MSX-DOS BDOS functions) + the black-box-pinned $F306 dispatcher-flag semantics (no
; stock CODE decoded).
;   out (success): A=(FAT_SECPERCLUS) BC=$0200 DE=total data clusters
;                  HL=free-cluster count ; ($F306):=$00
;   out (fail-safe): A=0 BC=$0200 DE=0 HL=0
getalloc_body:
                call    fat_mount               ; geometry -> FAT_* scratch (SECTOR_BUF)
                jp      c, ga_fail
                call    fat_total_clusters       ; DE = dataClusters + 2 (rawTotal)
                push    de                       ; stack[0] = rawTotal (stays for the scan)
                ld      hl, $FFFF
                ld      (FAT_WRTMP2), hl         ; no FAT sector cached yet (fat_alloc_
                                                 ; cluster's own init, same convention)
                ld      de, 0                    ; DE = free-cluster counter
                ld      hl, 2                    ; HL = cluster under test
ga_scanloop:
                pop     bc                       ; BC = rawTotal (peek: pop then re-push)
                push    bc
                push    hl                       ; save cluster across the compare
                or      a
                sbc     hl, bc                   ; HL = cluster - rawTotal
                pop     hl                       ; restore cluster
                jp      z, ga_scandone           ; cluster == rawTotal -> scan complete
                ; fatofs = cluster + (cluster>>1)  (== floor(cluster*3/2), the same
                ; math fac_loop_body uses -- Microsoft FAT spec §3.2 12-bit packing)
                push    de                       ; save free counter across the call below
                push    hl                       ; save cluster (need it after the call)
                ld      a, l
                and     1
                ld      (FAT_PARITY), a
                ld      e, l
                ld      d, h
                srl     d
                rr      e                        ; DE = cluster >> 1
                add     hl, de                   ; HL = fatofs
                ld      a, l
                ld      (FAT_BYTEIDX), a
                ld      a, h
                and     1
                ld      (FAT_BYTEIDX + 1), a     ; byteidx = fatofs & $1FF
                ld      a, h
                srl     a                        ; FAT sector offset = fatofs >> 9
                ld      e, a
                ld      d, 0
                ld      hl, (FAT_FATSTART)
                add     hl, de                   ; HL = absolute FAT sector for this cluster
                ld      de, (FAT_WRTMP2)
                push    hl
                or      a
                sbc     hl, de
                pop     hl
                jp      z, ga_havesec            ; already the cached sector -> no re-read
                ld      (FAT_WRTMP2), hl
                ld      (FAT_FATSEC), hl
                ex      de, hl
                ld      hl, WBUF
                call    read_sector
                jp      c, ga_rderr
ga_havesec:
                call    fac_entry_from_wbuf      ; DE = 12-bit entry value (clobbers
                                                 ; AF/BC/DE/HL -- fat.asm's own contract)
                ld      a, d
                or      e
                pop     hl                       ; restore cluster
                pop     de                       ; restore free counter
                jr      nz, ga_notfree
                inc     de                       ; entry == $000 -> free, bump counter
ga_notfree:
                inc     hl                       ; next cluster
                jp      ga_scanloop
ga_rderr:
                pop     hl                       ; discard saved cluster
                pop     de                       ; discard saved free counter
                pop     hl                       ; discard rawTotal
                jp      ga_fail
ga_scandone:
                ex      de, hl                   ; HL := free-cluster count (final)
                pop     de                       ; DE := rawTotal
                dec     de
                dec     de                       ; DE := total data clusters (final)
                xor     a
                ld      ($F306), a               ; clear dispatcher HL-passthrough flag
                                                 ; (M20 REVISION 3 fix -- see $505D veneer)
                ld      bc, $0200                ; BC := bytes/sector (final)
                ld      a, (FAT_SECPERCLUS)      ; A := sectors/cluster (final)
                or      a                        ; Cy = 0 (success)
                ret
ga_fail:
                xor     a
                ld      ($F306), a               ; clear here too (consistent with the
                                                 ; success path; harmless -- A=0 already
                                                 ; forces free_bytes=0 either way)
                ld      bc, $0200                ; BC := 512 (belt-and-braces)
                ld      de, 0
                ld      hl, 0
                ret

; sfirst_body — BDOS SFIRST ($11): find the FIRST matching root-dir entry.
;   in:  DE -> search FCB (name pattern at DE+1) ; out: A=$00 found / $FF none
sfirst_body:
                inc     de                  ; DE -> the 11-byte 8.3 pattern (FCB+1)
                ld      (FAT_NAMEPTR), de   ; dirscan_match compares against this
                call    fat_mount           ; (re)parse BPB -> FAT_FIRSTROOT/FAT_ROOTSECS
                jp      c, ds_none          ; disk error -> no entry
                ld      hl, 0
                ld      (BDOS_SRCHIDX), hl  ; scan cursor := entry 0
                jr      dirscan_match

; snext_body — BDOS SNEXT ($12): resume from BDOS_SRCHIDX, find the NEXT match.
;   in:  DE -> search FCB (name pattern at DE+1) ; out: A=$00 found / $FF exhausted
snext_body:
                inc     de                  ; DE -> the 11-byte 8.3 pattern (FCB+1)
                ld      (FAT_NAMEPTR), de
                call    fat_mount           ; geometry back into scratch (idempotent)
                jp      c, ds_none
                ; fall through: BDOS_SRCHIDX already points at the next entry.

; dirscan_match — walk the root dir from BDOS_SRCHIDX; on the first entry matching
; the pattern (name_cmp_wild) copy its drive-byte + 32-byte image to the DTA, set
; BDOS_SRCHIDX := match-index + 1, return A=$00. On $00 end-mark or all sectors
; scanned, return A=$FF. Reconstructs the sector cursor from BDOS_SRCHIDX alone
; (idx>>4 = sectors to skip; idx&15 = entry-in-sector) so it never persists
; FAT_DIRSEC/FAT_DIRREM across calls (M19 §4.3/§4.4).
dirscan_match:
                ; sectorsToSkip = BDOS_SRCHIDX >> 4  (16 entries per 512-B sector)
                ld      hl, (BDOS_SRCHIDX)
                ld      b, 4
dsm_shr:
                srl     h
                rr      l
                djnz    dsm_shr             ; HL = idx >> 4 = sector offset
                ; FAT_DIRSEC := FAT_FIRSTROOT + sectorOffset
                ld      de, (FAT_FIRSTROOT)
                add     hl, de
                ld      (FAT_DIRSEC), hl
                ; FAT_DIRREM := FAT_ROOTSECS - sectorOffset
                ld      hl, (BDOS_SRCHIDX)
                ld      b, 4
dsm_shr2:
                srl     h
                rr      l
                djnz    dsm_shr2            ; HL = idx >> 4 again (sector offset)
                ex      de, hl              ; DE = sector offset
                ld      hl, (FAT_ROOTSECS)
                or      a
                sbc     hl, de
                jp      z, ds_none          ; already past the last root sector
                jp      c, ds_none          ; (defensive) offset beyond root
                ld      (FAT_DIRREM), hl
dsm_secloop:
                ld      hl, (FAT_DIRREM)
                ld      a, h
                or      l
                jp      z, ds_none          ; scanned every remaining root sector
                ld      de, (FAT_DIRSEC)
                ld      hl, SECTOR_BUF
                call    read_sector
                jp      c, ds_none          ; FDC error -> exhausted (no entry)
                ; start entry-in-sector = BDOS_SRCHIDX & 15
                ld      a, (BDOS_SRCHIDX)
                and     $0F
                ld      c, a                ; C = entry index within this sector
                ; HL = SECTOR_BUF + entry*32
                ld      hl, SECTOR_BUF
                ld      b, a
                or      a
                jr      z, dsm_athl
dsm_addent:
                ld      de, 32
                add     hl, de
                djnz    dsm_addent
dsm_athl:
                ld      a, 16
                sub     c
                ld      b, a                ; B = entries left in THIS sector (16-C)
dsm_entloop:
                ld      a, (hl)
                or      a
                jp      z, ds_none          ; $00 = end of directory -> exhausted
                cp      $E5
                jr      z, dsm_skip         ; deleted entry -> skip (no filter else)
                ld      de, (FAT_NAMEPTR)
                push    hl
                push    bc
                call    name_cmp_wild       ; Z if the 8.3 name matches the pattern
                pop     bc
                pop     hl
                jr      z, dsm_found
dsm_skip:
                ld      de, 32
                add     hl, de              ; next 32-byte directory entry
                call    dsm_bump            ; BDOS_SRCHIDX += 1 (advance past this one)
                djnz    dsm_entloop
                ; sector done: advance FAT_DIRSEC, dec FAT_DIRREM, next sector.
                ld      hl, (FAT_DIRSEC)
                inc     hl
                ld      (FAT_DIRSEC), hl
                ld      hl, (FAT_DIRREM)
                dec     hl
                ld      (FAT_DIRREM), hl
                jr      dsm_secloop
dsm_found:
                ; HL = matched 32-byte directory entry. Build the runtime DTA as the
                ; MSX-DOS SFIRST/SNEXT "found FCB" (drive + unopened FCB), matching
                ; stock byte-for-byte in every field COMMAND.COM's DIR reads (name,
                ; attribute, time, date, first cluster, size). The field layout was
                ; pinned black-box against stock's DTA + a readwatch of the DIR
                ; formatter's DTA reads (M19 §4.4):
                ;   DTA[0]      = drive (current drive + 1)
                ;   DTA[1..11]  = entry[0..10]  (11-byte 8.3 name)
                ;   DTA[12]     = 0  (FCB extent/EX)
                ;   DTA[13]     = entry[11]     (attribute)
                ;   DTA[14..22] = 0  (incl. the computed record-count field DIR
                ;                 never reads; left 0 -- black-box confirmed unread)
                ;   DTA[23..32] = entry[22..31] (time, date, first cluster, size)
                ; The attribute at DTA[13] is what lets DIR filter volume-label /
                ; subdir entries and count "nn files" correctly -- writing a verbatim
                ; raw entry (attr at DTA[12]) mis-set that filter (the alternating-
                ; garbage / wrong-count bug). CLEAN-ROOM: our own field copy from our
                ; own dir walk into the published FCB-result layout; no stock code.
                push    hl                  ; save entry ptr
                ld      de, (DOS_DTAPTR)    ; DE = runtime DTA base
                push    de                  ; save DTA base
                ; zero DTA[0..32] (33 bytes) so all gap/unset fields are $00.
                ld      h, d
                ld      l, e                ; HL = DTA base
                ld      (hl), 0
                push    hl
                pop     de                  ; DE = DTA base
                inc     de                  ; DE = DTA+1
                ld      bc, 32
                ldir                        ; propagate the $00 across DTA[1..32]
                pop     de                  ; DE = DTA base
                pop     hl                  ; HL = matched dir entry
                ; DTA[0] = drive (current drive + 1)
                ld      a, (CURDRV_CELL)
                inc     a
                ld      (de), a
                inc     de                  ; DE = DTA+1
                ; DTA[1..11] = entry[0..10] (name)
                push    hl                  ; keep entry base
                ld      bc, 11
                ldir                        ; -> DTA[1..11]; HL=entry+11, DE=DTA+12
                ; DTA[12] stays 0; DTA[13] = entry[11] (attr)
                inc     de                  ; DE = DTA+13
                ld      a, (hl)             ; entry[11] = attribute
                ld      (de), a
                ; DTA[14..22] stay 0; DTA[23..32] = entry[22..31]
                pop     hl                  ; HL = entry base
                ld      bc, 22
                add     hl, bc              ; HL = entry+22 (time/date/clus/size)
                ld      de, (DOS_DTAPTR)
                ld      a, e
                add     a, 23
                ld      e, a
                jr      nc, dsm_nohc
                inc     d
dsm_nohc:
                ld      bc, 10
                ldir                        ; -> DTA[23..32]
                call    dsm_bump            ; BDOS_SRCHIDX := match-index + 1
                xor     a                   ; A = $00 = found
                ret
ds_none:
                ld      a, $FF              ; A = $FF = no (more) matching entry
                ret

; dsm_bump — BDOS_SRCHIDX += 1 (advance the persistent scan cursor). Preserves all
; registers (HL is the live entry pointer at both call sites).
dsm_bump:
                push    hl
                ld      hl, (BDOS_SRCHIDX)
                inc     hl
                ld      (BDOS_SRCHIDX), hl
                pop     hl
                ret

; name_cmp_wild — compare an 11-byte dir name against the search pattern, with the
; FCB ? wildcard: a pattern byte of $3F matches any single character. Otherwise
; identical to name_cmp (case-insensitive via toupper). (Published CP/M-2.2 /
; MSX-DOS FCB match rule; M19 §4.5 — verified DIR issues an all-? pattern.)
;   in:  HL = directory-entry name, DE = search pattern ; out: Z set if match;
;        trashes A, B, DE, HL (HL/DE advanced 11 bytes; C preserved)
name_cmp_wild:
                ld      b, 11
ncw_loop:
                ld      a, (de)
                cp      $3F                 ; '?' pattern byte matches anything
                jr      z, ncw_next
                ld      a, (de)
                call    toupper
                ld      c, a
                ld      a, (hl)
                call    toupper
                cp      c
                ret     nz                  ; mismatch -> Z clear
ncw_next:
                inc     hl                  ; 16-bit inc: leaves flags intact
                inc     de
                djnz    ncw_loop
                ret                         ; Z set (all 11 positions matched)

; --- M24 slice B relocated bodies (tier2-m24-fclose-multicluster-spec.md §6) --

; rdb_recloop_body — verbatim relocation of disk/driver.asm's bdos_rdblk
; record/byte move loop (rdb_recloop..rdb_eof, unchanged since M21b). Moved
; here only because its old span's tail byte collided with the new $461D
; FMAKE-worker canonical entry; reached solely by driver.asm's own
; `jp rdb_recloop_body` fall-through (position-free, no external caller).
rdb_recloop_body:
                ld      hl, (RDBLK_DONE)
                ld      de, (RDBLK_REQ)
                or      a
                sbc     hl, de
                jr      z, rdb_ok           ; delivered every requested record
                ld      hl, (RDBLK_RECSIZE)
                ld      (RDBLK_CNT), hl     ; bytes still to copy for this record
rdb_byteloop:
                ld      hl, (RDBLK_CNT)
                ld      a, h
                or      l
                jr      z, rdb_recdone      ; whole record copied
                ; EOF when every file byte has been delivered (BYTESLEFT == 0)
                ld      hl, (BDOS_BYTESLEFT)
                ld      de, (BDOS_BYTESLEFT + 2)
                ld      a, h
                or      l
                or      d
                or      e
                jr      z, rdb_eof
                call    rdblk_getbyte       ; A = next file byte (advances buffer)
                jr      c, rdb_eof          ; chain ended early (defensive)
                ld      hl, (RDBLK_DST)
                ld      (hl), a
                inc     hl
                ld      (RDBLK_DST), hl
                ld      hl, (RDBLK_CNT)
                dec     hl
                ld      (RDBLK_CNT), hl
                jr      rdb_byteloop
rdb_recdone:
                ld      hl, (RDBLK_DONE)
                inc     hl
                ld      (RDBLK_DONE), hl
                jr      rdb_recloop_body
rdb_ok:
                xor     a                   ; A = $00 all requested records read
                ld      hl, (RDBLK_DONE)
                ld      b, h                ; BC = HL = records read (§8.33): the genuine
                ld      c, l                ; BDOS $27 returns the count in BOTH HL and BC,
                ret                         ; and MSXDOS.SYS init reads BC (§8.32 $024A branch)
rdb_eof:
                ld      a, $01              ; A = $01 EOF before all requested
                ld      hl, (RDBLK_DONE)    ; HL = records actually read
                ld      b, h                ; BC = HL = records read (§8.33; see rdb_ok)
                ld      c, l
                ret

; fat_mount_tail — verbatim relocation of disk/fat.asm's fat_mount continuation
; (from the numFATs*secPerFAT multiply setup through the final `ret`,
; unchanged). Moved here only because the multiply's `ld hl,0` tail byte
; collided with the new $477D WRSEQ-worker canonical entry; reached solely by
; fat_mount's own `jp fat_mount_tail` fall-through (position-free, no
; external caller). The diversion point had to move one instruction earlier
; than the collision itself (to `ld b,a`) to leave enough room for the
; 3-byte veneer to land exactly at $477D (a 3-byte-for-3-byte swap at the
; collision point alone leaves zero slack).
fat_mount_tail:
                ld      b, a                ; B = numFATs (loop count)
                ld      de, (SECTOR_BUF + BPB_FATSZ16)
                ld      (FAT_SECPERFAT), de ; cache for per-copy sector stride
                ld      hl, 0
fm_fatacc:
                add     hl, de
                djnz    fm_fatacc           ; HL = numFATs * secPerFAT
                ld      de, (FAT_FATSTART)
                add     hl, de
                ld      (FAT_FIRSTROOT), hl
                ; root sectors = (rootEnts*32 + 511) / 512  (512 B per sector)
                ld      hl, (SECTOR_BUF + BPB_ROOTENTCNT)
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl              ; HL = rootEnts * 32
                ld      de, 511
                add     hl, de
                ld      a, h
                srl     a                   ; HL >> 9  (== H >> 1, result < 256)
                ld      l, a
                ld      h, 0
                ld      (FAT_ROOTSECS), hl
                ; first data sector = firstRoot + rootSecs
                ld      de, (FAT_FIRSTROOT)
                add     hl, de
                ld      (FAT_FIRSTDATA), hl
                or      a                   ; Cy = 0 success
                ret

; wrseq_body — MSX-DOS-1 kernel per-record sequential-I/O worker entry
; $477D's body. CORRECTED (M25, tier2-m24-fclose-multicluster-spec.md
; "UPDATE 2"): the RAM kernel CALLs $477D for EVERY sequential record
; access -- BOTH BDOS $15 WRSEQ *and* BDOS $14 RDSEQ share this ONE page-1
; entry (confirmed black-box via `callwatch --in-func 0x14`; no register at
; entry distinguishes direction -- BC/DE/HL/AF identical in shape between a
; genuine WRSEQ hit and a RDSEQ hit), so direction is read from OUR OWN
; BDOS_WRMODE cell instead: nonzero forwards to bdos_seqwrite (unchanged);
; zero forwards to bdos_seqread. The companion fix in fopen_fill_body
; (disk/fat.asm) seeds the read-iterator state (fat_open, BDOS_RECIDX,
; BDOS_BYTESLEFT) that bdos_seqread depends on and that a real kernel-driven
; FOPEN never populated before -- without it bdos_seqread ran but always
; reported false EOF.
; DTA staleness (M21b lesson, see k_47B2 above): the kernel's real SETDTA
; only ever writes DOS_DTAPTR ($F23D), never our own mini-BDOS's BDOS_DTA
; cell, so BDOS_DTA must be reseeded from DOS_DTAPTR before EITHER
; bdos_seqread or bdos_seqwrite consumes it -- both directions need the
; reseed, not just write. DE (=IY=$DA40 kernel FCB pointer) is not consumed
; by either -- both are single-open-file global state, same as Tier-1. Exit
; A=$00/$01/$FF passes straight through from whichever real routine ran.
; $F306 left untouched (M24 spec §5 item 4: no observed load-bearing exit HL
; for this entry family -- default to the kernel's own H:=B,L:=A mirror
; unless the acceptance diff proves otherwise).
wrseq_body:
                ld      hl, (DOS_DTAPTR)
                ld      (BDOS_DTA), hl
                ld      a, (BDOS_WRMODE)
                or      a
                jr      nz, wrseq_body_write
                jp      bdos_seqread
wrseq_body_write:
                jp      bdos_seqwrite

; fdc_read_data_body — relocated fdc_read_data (M26, tier2-m26-spec.md): its
; old span at driver.asm's $435A collided with the real kernel's canonical
; $17 FREN dispatch entry, $4392 (56 bytes into the original 74-byte body --
; the fdc_rd_n1/fdc_rd_n2 status-decode tail). Logic below is byte-for-byte
; unchanged from the original; driver.asm's fdc_read_data is now a 3-byte
; `jp` thunk to here, freeing $4392 for the real `jp fren_body` veneer.
fdc_read_data_body:
                ld      e, 2            ; two 256-byte halves
fdc_rd_blk:
                ld      b, 0            ; djnz 0 -> 256 iterations
fdc_rd_wait:
                ld      a, (FDC_STATUS)
                bit     1, a            ; DRQ?
                jr      nz, fdc_rd_byte
                bit     0, a            ; BUSY?
                jr      nz, fdc_rd_wait
                jr      fdc_rd_status   ; finished with no DRQ -> short/error
fdc_rd_byte:
                ld      a, (FDC_DATA)
                ld      (hl), a
                inc     hl
                djnz    fdc_rd_wait
                dec     e
                jr      nz, fdc_rd_blk
fdc_rd_drain:
                ld      a, (FDC_STATUS) ; all 512 read; wait for command end
                bit     0, a
                jr      nz, fdc_rd_drain
fdc_rd_status:
                ld      a, (FDC_STATUS)
                and     ST_NOTRDY + ST_RNF + ST_CRC + ST_LOST
                jr      z, fdc_rd_ok
                ld      b, a            ; keep the error bits
                and     ST_NOTRDY
                jr      z, fdc_rd_n1
                ld      a, 2            ; not ready
                scf
                ret
fdc_rd_n1:
                ld      a, b
                and     ST_RNF
                jr      z, fdc_rd_n2
                ld      a, 8            ; record not found
                scf
                ret
fdc_rd_n2:
                ld      a, b
                and     ST_CRC
                jr      z, fdc_rd_n3
                ld      a, 4            ; CRC / data error
                scf
                ret
fdc_rd_n3:
                ld      a, 12           ; lost data / other
                scf
                ret
fdc_rd_ok:
                or      a               ; A = 0, Cy = 0
                ret

; bdos_seqwrite_body — relocated bdos_seqwrite (M26, tier2-m26-spec.md): its old
; span at disk/fat.asm's $46EE collided with the real kernel's canonical $30
; WRABS dispatch address, $4720 -- the displacement byte of the `jr c,
; bsw_full` that used to live there (trace --resync: ours fell through into
; live bdos_seqwrite tail code, silently zeroing BDOS_WRBUFLEN via the
; buffer-drain path before reaching bsw_ok's false-success `ret`). Logic
; below is byte-for-byte unchanged; disk/fat.asm's bdos_seqwrite is now a
; 3-byte `jp` thunk to here, freeing $4720 for the real `jp wrabs_body`
; veneer. Only symbolic callers (`jp bdos_seqwrite` in driver.asm/kernel.asm)
; reference this routine -- no external code jumps into bsw_ok/bsw_full/
; bsw_err/wrbytes_add_recsize's middle, so the whole unit relocates cleanly.
bdos_seqwrite_body:
                ld      a, (BDOS_WRMODE)
                or      a
                jr      z, bsw_err          ; not open for write
                ; copy RECSIZE bytes DTA -> SECTOR_BUF + BDOS_WRBUFLEN
                ld      hl, (BDOS_WRBUFLEN)
                ld      de, SECTOR_BUF
                add     hl, de              ; HL = dest in SECTOR_BUF
                ex      de, hl              ; DE = dest
                ld      hl, (BDOS_DTA)      ; HL = source record (settable DTA)
                ld      bc, RECSIZE
                ldir                        ; copy 128 bytes into the buffer
                ; advance buffered length and total byte count by RECSIZE.
                ld      hl, (BDOS_WRBUFLEN)
                ld      de, RECSIZE
                add     hl, de
                ld      (BDOS_WRBUFLEN), hl
                call    wrbytes_add_recsize ; BDOS_WRBYTES += RECSIZE (4-byte LE)
                ; if the 512-byte buffer is now full, flush it to the file.
                ld      hl, (BDOS_WRBUFLEN)
                ld      de, 512
                or      a
                sbc     hl, de
                jr      c, bsw_ok           ; buffer not full yet
                call    fat_flush_data_sector
                jr      c, bsw_full         ; disk full / write error
                ld      hl, 0
                ld      (BDOS_WRBUFLEN), hl ; buffer drained
bsw_ok:
                xor     a                   ; A = $00 success
                ret
bsw_full:
                ld      a, $01              ; disk full (MSX-DOS seq-write code)
                ret
bsw_err:
                ld      a, $FF
                ret

; wrbytes_add_recsize — BDOS_WRBYTES += RECSIZE, 4-byte little-endian add.
wrbytes_add_recsize:
                ld      hl, BDOS_WRBYTES
                ld      a, (hl)
                add     a, RECSIZE
                ld      (hl), a
                inc     hl
                ld      b, 3                ; carry through the upper 3 bytes
wba_loop:
                ld      a, (hl)
                adc     a, 0
                ld      (hl), a
                inc     hl
                djnz    wba_loop
                ret

; fdel_body — MSX-DOS-1 kernel FDEL ($13) canonical entry $436C's real body
; (M26, tier2-m26-spec.md sec 2.2). CLEAN-ROOM, single exact-match only
; (same fat_find precedent as fren_body -- BDOSX3 only exercises an exact
; name; '?' wildcard multi-delete is out of scope, confirmed at sign-off).
; PLACEMENT NOTE: this body first landed appended to disk/fat.asm's own end
; (next to fren_ioerr/rdabs_ioerr/wrabs_ioerr, following those three's own
; precedent), but that broke test_gdate.py/test_getdpb.py -- fat.asm's tail
; feeds straight into kernel.asm's own tightly-packed pinned-address
; corridor (GDATE $553C etc, disk/kernel.asm) with no slack for a body this
; size (same "64KB limit passed" class of hazard the FREN slice already hit
; once and worked around by using kernel.asm's OWN free tail instead -- see
; fdc_read_data_body below). Moved here for the same reason.
; Entry is a kernel-side FCB copy pointed to by DE (drive byte + 11-byte
; 8.3 name, zero-filled tail) -- same +1 name-field convention fren_body
; uses. Two things this body must do that fren_body didn't: (a) free the
; file's FAT12 chain (every cluster zeroed in EVERY on-disk FAT copy, via
; fat_next_cluster/fat_write_fat_entry) -- confirmed necessary by black-box
; on-disk $E5 forensics: stock frees both clusters of BDOSX3's 2-cluster
; scratch file, so a bare $E5 stamp alone would under-match stock (leak the
; chain); (b) only THEN stamp the directory entry's first byte $E5 and
; persist it. Order matters: fat_next_cluster/fat_write_fat_entry both use
; SECTOR_BUF as scratch, clobbering the dirent fat_find first located -- so
; the chain-free walk runs BEFORE re-locating the entry (a second fat_find
; call, cheap and reuses already-verified code rather than tracking a
; pointer across a clobbering call). IX holds the FCB-copy pointer across
; every helper call in this body (confirmed by inspection: fat_mount,
; fat_find, fat_next_cluster, fat_write_fat_entry, read_sector, and
; write_sector never touch IX -- only fopen_fill_body/fren_body do, in
; disk/fat.asm), so re-deriving the name pointer for the second fat_find is
; just IX+1 again.
fdel_body:
                push    de
                pop     ix                  ; IX = kernel FCB-copy pointer (held throughout)
                push    ix
                pop     de
                call    fat_mount
                jp      c, fdel_miss
                push    ix
                pop     de
                inc     de                  ; DE -> FCB-copy+1 (target 8.3 name)
                ex      de, hl              ; HL -> name (fat_find's contract)
                call    fat_find            ; Cy=0 found; FAT_FIRSTCLUS/FAT_FILESIZE set
                jp      c, fdel_miss
                ld      hl, (FAT_FIRSTCLUS)
                ld      a, h
                or      l
                jr      z, fdel_relocate    ; zero-length file: no chain to free
fdel_free_loop:
                push    hl                  ; stack: [cur cluster]
                call    fat_next_cluster    ; HL := next link (cur was consumed as input)
                ex      (sp), hl            ; stack: [next]; HL := cur
                ld      de, 0               ; free = $000 (Microsoft FAT spec sec 3.2)
                call    fat_write_fat_entry ; zero cur's entry in every on-disk FAT copy
                jp      c, fdel_chain_ioerr
                pop     hl                  ; HL := next
                ld      de, $0FF8           ; >= $0FF8 = end-of-chain (fat_next_cluster's own convention)
                or      a
                sbc     hl, de
                jr      nc, fdel_relocate   ; next >= $0FF8 -> chain fully freed
                add     hl, de              ; HL := next again (undo the probe subtraction)
                jr      fdel_free_loop
fdel_chain_ioerr:
                pop     hl                  ; discard the saved "next", keep the stack balanced
                jp      fdel_ioerr
fdel_relocate:
                ; SECTOR_BUF now holds FAT-sector content (clobbered by the chain
                ; walk above, or untouched if this file was zero-length) -- re-run
                ; fat_find for a fresh, valid dirent pointer + FAT_DIRSEC.
                push    ix
                pop     de
                inc     de
                ex      de, hl
                call    fat_find
                jp      c, fdel_miss
                ld      (hl), $E5           ; CP/M delete marker (Microsoft FAT spec sec 3.1)
                ld      de, (FAT_DIRSEC)
                ld      hl, SECTOR_BUF
                call    write_sector
                jp      c, fdel_ioerr
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                ld      h, a
                ld      l, a                ; HL = $0000 on success (pinned exit value)
                ret
fdel_miss:
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                scf
                ld      a, $FF              ; not-found (fren_miss convention; untested by BDOSX3)
                ret
fdel_ioerr:
                xor     a
                ld      ($F306), a          ; M20 dispatcher-flag rule
                scf
                ld      a, 2                ; generic FDC I/O error (fdc_read_data convention)
                ret

; rrnd_position / rrnd_sector / rdrnd_body / wrrnd_body — MSX-DOS-1 kernel
; RDRND ($21) / WRRND ($22) canonical entries $4788/$4793's real bodies (M26,
; tier2-m26-spec.md §2.3). CLEAN-ROOM. Entry is the same kernel FCB-copy
; convention as fdel_body/rdabs_body/wrabs_body: DE -> a 37-byte scratch copy
; of the FCB at $DA40; copy+33 = the FCB random-record field r0 (BDOS $18 SETRND
; / direct FCB poke). SCOPE (signed off at implementation time, same class of
; narrowing as FREN's/FDEL's single-exact-match precedent): only r0 (0..255,
; up to a 32640-byte file) positions the record; r1/r2 (copy+34/+35) are NOT
; read -- BDOSX3 only exercises r0 in {1,2} and no on-disk MSX-DOS-1 floppy
; file needs more than r0 to stay within this milestone's verified acceptance
; bar. PLACEMENT: kernel.asm's free tail (not disk/fat.asm's own end), per the
; FDEL slice's placement lesson (fat.asm's tail starves kernel.asm's own
; pinned-address corridor of slack for a body this size).
;
; rrnd_position seeds the existing sequential-read iterator (FAT_CURCLUS/
; FAT_CLUSSEC/BDOS_RECIDX/BDOS_BYTESLEFT/BDOS_DTA) to point at record r0,
; reusing fat_open + repeated fat_read_file_sector calls (each one reads
; exactly one more sector and advances the cluster chain as needed) rather
; than a dedicated fast-seek -- correct and simple, and the only sector-
; addressing arithmetic (firstData + (cluster-2)*secPerClus + clussec)
; already exists inside fat_read_file_sector/frs_mul_body. rdrnd_body then
; reuses bdos_seqread verbatim for the actual transfer (§4 non-goal: no
; change to bdos_seqread_body itself). wrrnd_body CANNOT reuse
; wrseq_body/bdos_seqwrite the same way -- that engine is append-oriented
; (BDOS_WRMODE-gated, a 512-byte-flush model for a file opened by FMAKE) and
; wrong for overlaying 128 bytes mid-file into a file opened for READ by
; FOPEN -- so it is a small, new read-modify-write body instead: overlay the
; DTA's 128 bytes into the sector rrnd_position already loaded into
; SECTOR_BUF, then persist via write_sector. Because fat_read_file_sector
; does not expose the absolute sector number it just read (only frs_mul_body,
; entered by `jp`, computes it, mid an unrelated read call already committed
; to SECTOR_BUF), wrrnd_body's rrnd_sector helper mirrors that same formula
; independently (does NOT modify frs_mul_body -- §4 non-goal) using the
; POST-call FAT_CURCLUS/FAT_CLUSSEC state: fat_read_file_sector always
; finishes with FAT_CURCLUS already advanced to the sector it read (if
; needed) and FAT_CLUSSEC incremented by exactly one past it -- so
; `FAT_CLUSSEC - 1` safely recovers the clussec of the sector just read, with
; no off-by-one or cluster-boundary hazard (confirmed by reading
; fat_read_file_sector's own body: the increment always follows the read,
; never precedes it, and is never separately normalised/wrapped).
;
; Register contract (capture, tier2-m26-spec.md §2.3): entry A=$25 B=$00
; C=$00 DE=$DA40 SP=$DBFE ret=$D88A (FDEL-dispatcher class, not RDABS's — no
; addr-low fingerprint, C is not the function number); exit A=$00 H=$00
; L=$00 on success. Stock's one clear random-op FCB side effect: CR (user
; FCB+32, mirrored at copy+32) := r0's low byte post-call -- reproduced here
; explicitly (copy+32 := copy+33) since it is a per-call random-op effect,
; not a generic kernel copy-back artifact (contrast fdel_body's DE=$03D0,
; which the kernel already reproduced with no fdel_body code at all).
rrnd_position:
                ld      hl, (DOS_DTAPTR)
                ld      (BDOS_DTA), hl      ; reseed our own DTA cell (M19 lesson:
                                            ; the kernel's real SETDTA only ever
                                            ; touches DOS_DTAPTR, never BDOS_DTA)
                ld      a, (ix+33)          ; A = r0 (target record, 0..255; see scope note)
                push    af
                call    fat_open            ; reset iterator to file start (FAT_FIRSTCLUS)
                pop     af
                ld      c, a                ; C = r0 (preserved across fat_open)
                and     3
                ld      (RRND_RECSEC), a    ; stash record-in-sector for after the seek loop
                                            ; (RAM: a ROM cell here silently no-op'd -> wrong record)
                ld      a, c
                srl     a
                srl     a                   ; A = target sector-in-file (r0 >> 2)
                inc     a                   ; A = seek-loop count (>= 1)
                ld      b, a
                ; BDOS_BYTESLEFT := FAT_FILESIZE - r0*RECSIZE (r0*128 <= 32640, always
                ; fits 16 bits, so only the filesize low word can matter here)
                ld      h, 0
                ld      l, c                ; HL = r0
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl              ; HL = r0 * 128
                ld      de, (FAT_FILESIZE)
                ex      de, hl              ; HL = filesize_lo16, DE = r0*128
                or      a
                sbc     hl, de              ; HL = filesize_lo16 - r0*128; Cy=1 if r0 is past EOF
                jr      c, rrnd_pos_beyond
                ld      (BDOS_BYTESLEFT), hl
                ld      hl, (FAT_FILESIZE + 2)
                ld      (BDOS_BYTESLEFT + 2), hl
                jr      rrnd_pos_seek
rrnd_pos_beyond:
                ld      hl, 0
                ld      (BDOS_BYTESLEFT), hl
                ld      (BDOS_BYTESLEFT + 2), hl
rrnd_pos_seek:
rrnd_pos_loop:
                push    bc
                call    fat_read_file_sector
                pop     bc
                jr      c, rrnd_pos_err     ; seek ran off the end of the chain
                djnz    rrnd_pos_loop
                ld      a, (RRND_RECSEC)
                ld      (BDOS_RECIDX), a
                or      a                   ; Cy = 0 ok
                ret
rrnd_pos_err:
                scf
                ret
                ds      1, $00              ; (was rrnd_recsector db 0 — cell moved to RAM
                                            ; RRND_RECSEC; byte retained for net-zero layout)

; rrnd_sector — recover the absolute logical sector number rrnd_position's
; seek loop last landed on (see the placement note above for why this is
; safe: FAT_CLUSSEC - 1, FAT_CURCLUS as-is).
;   out: DE = absolute logical sector number; trashes AF, BC, HL
rrnd_sector:
                ld      a, (FAT_CLUSSEC)
                dec     a
                ld      (RRND_CLUSSEC), a   ; (RAM: ROM cell here silently no-op'd)
                ld      hl, (FAT_CURCLUS)
                ld      de, 2
                or      a
                sbc     hl, de              ; HL = cluster - 2
                ex      de, hl              ; DE = cluster - 2
                ld      hl, 0
                ld      a, (FAT_SECPERCLUS)
                ld      b, a
rrnd_sector_mul:
                add     hl, de
                djnz    rrnd_sector_mul     ; HL = (cluster-2) * secPerClus
                ld      de, (FAT_FIRSTDATA)
                add     hl, de
                ld      a, (RRND_CLUSSEC)
                ld      e, a
                ld      d, 0
                add     hl, de              ; HL = absolute logical sector
                ex      de, hl              ; DE = absolute logical sector (write_sector's convention)
                ret
                ds      1, $00              ; (was rrnd_clussec_tmp db 0 — cell moved to RAM
                                            ; RRND_CLUSSEC; byte retained for net-zero layout)

rdrnd_body:
                push    de
                pop     ix                  ; IX = kernel FCB-copy pointer
                call    rrnd_position
                jp      c, rrnd_eof
                call    bdos_seqread        ; A=$00 record delivered / $01 EOF
                or      a
                jr      nz, rrnd_finish     ; EOF from seqread -- pass A through, HL untested
                ld      a, (ix+33)          ; CR (copy+32) := r0 (stock's random-op side effect)
                ld      (ix+32), a
                xor     a
                ld      h, a
                ld      l, a                ; HL = $0000 (pinned exit value, success)
                jr      rrnd_finish
rrnd_eof:
                ld      a, $01              ; positioned past end-of-file
                jr      rrnd_finish

wrrnd_body:
                push    de
                pop     ix                  ; IX = kernel FCB-copy pointer
                call    rrnd_position
                jp      c, wrrnd_ioerr      ; positioned past EOF -- FAT growth is out of
                                            ; scope this milestone (§4 non-goal), same as
                                            ; every other M26 fix
                ; SECTOR_BUF now holds the target sector (loaded by rrnd_position's seek
                ; loop) -- overlay the caller's DTA record into it at BDOS_RECIDX*RECSIZE.
                ld      a, (BDOS_RECIDX)
                ld      l, a
                ld      h, 0
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl
                add     hl, hl              ; HL = BDOS_RECIDX * 128
                ld      de, SECTOR_BUF
                add     hl, de              ; HL -> target record within SECTOR_BUF
                ex      de, hl              ; DE = dest in SECTOR_BUF
                ld      hl, (BDOS_DTA)      ; HL = source record in the caller's DTA
                ld      bc, RECSIZE
                ldir
                call    rrnd_sector         ; DE = absolute logical sector to persist
                ld      hl, SECTOR_BUF
                call    write_sector
                jp      c, wrrnd_ioerr
                ld      a, (ix+33)          ; CR (copy+32) := r0 (stock's random-op side effect)
                ld      (ix+32), a
                xor     a
                ld      h, a
                ld      l, a                ; HL = $0000 (pinned exit value, success)
                jr      rrnd_finish
wrrnd_ioerr:
                ld      a, 2                ; generic FDC I/O error (fdc_read_data convention,
                                            ; untested by BDOSX3 -- no negative-path record)
rrnd_finish:                                ; shared tail: M20 dispatcher-flag rule, preserve A
                push    af
                xor     a
                ld      ($F306), a
                pop     af
                ret

