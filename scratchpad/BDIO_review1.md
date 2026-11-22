# docs/disk/DSKIO.md DRAFT 1 -- review pass 1 (test writer, 2026-11-22), ANSWERED by XDSKIO2 (+ its PHYDIO twin)

2.1 (CORE, NEW BEHAVIOUR) HL "buffer + $200" vs "buffer + 512 x (attempted - 1)" -> B 2 from past the end: + 0;
    B 3 whole: + $400; B 3 from 1438: + $400 (XI2 0, 1, 4). The page's rule was WRONG; restated.
1.1 (CORE, COMBINATION) only buffer $A400 -> $8000 -> $8200, $A401 -> $A601 (XI2 2, 3): the buffer's offset.
2.2 (CORE) B "the sectors done" -> the tables show the sectors NOT done; prose fixed.
3.1 (CORE) D-DSKIOHL not a separate cause: zerobas's HL is D-PHYDIOREGS's working value ($0003 / $0001) and
    matches where the transfer stops early -> D-DSKIOHL WITHDRAWN (page and TODO).
1.2 (CORE, COMBINATION) the interrupt state after is the inter-slot return's -> [A], said so.
1.3, 1.4, 1.5, 2.3 (EDGE) -> Open (media $F8 past track 0, writes and their errors, page-1 buffers, D / E).
3.3 (EDGE) xdskio1.asm's inherited "run 1 had DE 0" -> XDSK1's history, kept as its note.

XDSKIO2 predictions: "+ $200" MISSED (the reviewer's alternative held); the twin PHYDIO HL as entered held.
Not FINAL: pass 1 found new behaviour (the HL rule) -> review pass 2.
