# DSKFMT.md DRAFT 2 -- review pass 2 (test writer, 2026-11-22): CLEAN under the small-call stop after XDFMT3

1. (CORE) what a refusal writes beyond the BPB / FAT's 4 bytes -> not readable by this probe on an empty disk: [A].
2. (EDGE) FAT byte 3 unpinned; D out vs D in -> [A].
3. (CORE, COMBINATION) a masked range test ($81-$84) -> XF3 0: $81 refused (A 12, E $80). zerobas: success, nothing
   formatted -> D-DSKFMTHIGH.
4. (EDGE, COMBINATION) HL / E follow HL or BC -> XF3 1-2: HL = entry + $1020 ($9030 for $8010), E follows H ($41 at
   $84xx with BC $2000).
5. Citations: D-DSKFMTREGS's F / C values (F $09 for 6-8 / $80; F $00 / C $00 on XF2 0) -> fixed. The "480 outputs"
   count is spec_rules' (DE and HL one output each, the pad not recorded).
No new behaviour on the core rule: FINAL (spec-method §7, small-call stop).
