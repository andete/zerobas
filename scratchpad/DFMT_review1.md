# DSKFMT.md DRAFT 1 -- review pass 1 (test writer, 2026-11-22), ANSWERED by XDFMT2 (the CF-3300 row)

1. (CORE, NEW) the format really has the declared sides / tracks -> NOT measurable here: openMSX's .dsk image is a
   plain sector dump (every sector reads back); open list, with the reason.
2. (CORE) a refusal writes nothing, or writes the $F9 format -> XF2 1-7: refusals on a $FC disk leave $FC.
3. (CORE, COMBINATION) other invalid choices -> XF2 2-6: 6, 7, 8, $80, $FF all refused, E = choice - 1.
4. (CORE) the refusal's BC / HL kept or constant -> XF2 7 (BC $1234, HL $8800): kept.
5. (EDGE) success HL / B constant or following the work area -> XF2 8 (HL $8400, BC $3000): HL = entry + $1020;
   E $41 (against $49 for BC $2000) -- follows the size, rule not separated: open.
6. (EDGE) the FAT beyond 4 bytes, boot bytes 0-10 / 30+, CHOICE not called, DSKCHG / GETDPB after a format, EI entry
   -> open list.
7. Citations: run 1 was an earlier probe version (choices 0, 3, 1, 2) -> the page says so.
