"""D-BUFMERGE: Joost's (b) ONE SHARED BUFFER, 2026-09-24 -- the address edits.
Anchored on each cell's `NAME equ $ADDR` text; refuses a missing or non-unique anchor."""
import re, sys
MOVES = {  # name: (old, new)
 # group A: $E760..$E779 -> $E560..$E579 (-$200), relative layout kept
 'RRND_RECSEC':('E760','E560'), 'RRND_CLUSSEC':('E761','E561'),
 'BOOT_SV_A8':('E760','E560'), 'BOOT_SV_SEC':('E761','E561'),
 'R30_HL':('E762','E562'), 'R30_BC':('E764','E564'), 'R30_DE':('E766','E566'),
 'R30_AF':('E768','E568'), 'CALSLT_HL':('E76A','E56A'),
 'RDBLK_REQ':('E76C','E56C'), 'RDBLK_RECSIZE':('E76E','E56E'), 'RDBLK_DONE':('E770','E570'),
 'RDBLK_CNT':('E772','E572'), 'RDBLK_BUFPOS':('E774','E574'), 'RDBLK_DST':('E776','E576'),
 'P1_DEST':('E778','E578'),
 # group B: $E7E8..$E819 -> $E57A..$E5AB (-$26E), relative layout kept
 'WRBLK_REC':('E7E8','E57A'), 'WRBLK_RECSEC':('E7EB','E57D'), 'WRBLK_RS':('E7EC','E57E'),
 'WRBLK_CNT':('E7EE','E580'), 'WRBLK_REQ':('E7F0','E582'), 'WRBLK_PREVCLUS':('E7F2','E584'),
 'WRBLK_KEEPCNT':('E7F4','E586'), 'WRBLK_NEXTCLUS':('E7F6','E588'),
 'WRBLK_CURVALID':('E7F8','E58A'), 'WRBLK_CURSEC':('E7F9','E58B'),
 'FAT_ALLOCHINT':('E7FB','E58D'), 'RDBLK_RRSTART':('E7FD','E58F'),
 'DRV_TRAMP':('E800','E592'), 'BDOS_SEQREC':('E814','E5A6'),
 'DBUF_PTR':('E816','E5A8'), 'MBUF_PTR':('E818','E5AA'),
 # the merge itself
 'SECTOR_BUF':('E2A0','E5C0'), 'WBUF':('E560','E7C0'),
}
files = {f: open(f).read() for f in ('disk/equates.inc', 'disk/init.asm')}
for name, (old, new) in MOVES.items():
    pat = re.compile(r'^(%s\s+equ\s+)\$%s\b' % (name, old), re.M)
    hits = [(f, len(pat.findall(s))) for f, s in files.items()]
    tot = sum(n for f, n in hits)
    if tot != 1:
        sys.exit(f'REFUSE: {name} ${old} matched {hits}')
    for f in files:
        files[f] = pat.sub(lambda m: m.group(1) + '$' + new, files[f])
for f, s in files.items():
    open(f, 'w').write(s)
print(f'moved {len(MOVES)} cells')
