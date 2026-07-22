#!/usr/bin/env python3
# Find the exact Bresenham variant that reproduces the VG-8020 captured LINE pixels.
# Oracle bitmaps captured in g3_line_char.out / char2.out.

# captured reference pixel sets (x,y) as {y: [xs]} or explicit sets
REF = {}
REF['shallow'] = {(x,y) for y,xs in {
    0:[0,1],1:[2,3,4],2:[5,6,7],3:[8,9],4:[10,11,12],5:[13,14,15],6:[16,17,18],7:[19,20]
}.items() for x in xs}
REF['steep'] = {(x,y) for x,ys in {
    0:[0,1],1:[2,3,4],2:[5,6,7],3:[8,9],4:[10,11,12],5:[13,14,15],6:[16,17,18],7:[19,20]
}.items() for y in ys}
REF['diag'] = {(i,i) for i in range(16)}
REF['neg'] = {(x,15-x) for x in range(16)}

ENDS = {'shallow':((0,0),(20,7)), 'steep':((0,0),(7,20)),
        'diag':((0,0),(15,15)), 'neg':((0,15),(15,0))}

def variant(x0,y0,x1,y1, err_init, cmp_ge, order_swap):
    """Generic integer Bresenham. err_init in {'0','half','dx'}; cmp_ge: step when
    err>=0 (True) vs err>0 (False). order_swap: if True and reversed, swap ends
    (direction independence via sorting the major axis ascending)."""
    pts=set()
    dx=abs(x1-x0); dy=abs(y1-y0)
    steep = dy>dx
    if steep:
        x0,y0=y0,x0; x1,y1=y1,x1; dx,dy=dy,dx
    if order_swap and x0>x1:
        x0,y0,x1,y1 = x1,y1,x0,y0
    sy = 1 if y1>=y0 else -1
    if err_init=='half': err = dx//2
    elif err_init=='dx': err = dx
    else: err = 0
    y=y0
    D = 2*dy - dx if err_init=='D' else None
    xr = range(x0, x1+1) if x1>=x0 else range(x0, x1-1, -1)
    sx = 1 if x1>=x0 else -1
    for x in xr:
        pts.add((y,x) if steep else (x,y))
        err += dy
        cond = (2*err >= dx) if cmp_ge else (2*err > dx)
        if cond:
            y += sy; err -= dx
    return pts

def test():
    import itertools
    best=None
    for ei in ['0','half','dx']:
        for ge in [True,False]:
            for osw in [True, False]:
                ok=True; detail={}
                for name,(a,b) in ENDS.items():
                    got = variant(*a,*b, ei, ge, osw)
                    match = got==REF[name]
                    detail[name]=match
                    ok = ok and match
                tag=f"err={ei:4} cmp={'>=' if ge else '>':2} swap={osw}"
                marks=" ".join(f"{n}:{'Y' if v else 'n'}" for n,v in detail.items())
                if ok: print(f"  ALL MATCH  {tag}   {marks}")
                elif sum(detail.values())>=3: print(f"  {sum(detail.values())}/4       {tag}   {marks}")
    # also dump my err=0,cmp>= shallow to eyeball
    print("\nshallow err=0 cmp>= swap0:")
    g=variant(0,0,20,7,'0',True,False)
    for y in range(8):
        print("   "+"".join('#' if (x,y) in g else '.' for x in range(21)))

test()

# --- find an overflow-safe formulation (err in [0,dmaj), no 2x) that matches ---
def variant2(x0,y0,x1,y1, init, thresh):
    """Bresenham keeping err>=0. init in {'0','half','halfloor'}; thresh in
    {'dmaj','half'} (step when err>=dmaj resp err>=ceil(dmaj/2)), subtract the
    matching amount. Sort major ascending (direction independent)."""
    pts=set(); dx=abs(x1-x0); dy=abs(y1-y0); steep=dy>dx
    if steep: x0,y0,x1,y1,dx,dy = y0,x0,y1,x1,dy,dx
    if x0>x1: x0,y0,x1,y1 = x1,y1,x0,y0
    sy = 1 if y1>=y0 else -1
    if init=='0': err=0
    elif init=='half': err=dx//2
    else: err=(dx+1)//2
    y=y0
    T = dx if thresh=='dmaj' else (dx+1)//2
    sub = dx if thresh=='dmaj' else dx  # subtract dmaj on step in both (keeps err in range for thresh dmaj)
    for x in range(x0,x1+1):
        pts.add((y,x) if steep else (x,y))
        err += dy
        if (err*2>=dx) if thresh=='2err' else (err>=T):
            y += sy; err -= dx
    return pts

ENDS2 = dict(ENDS)
# add asymmetric + reversed to force direction-independence discrimination
ENDS2['asym']    = ((0,0),(19,7))    # different from 20,7; check reversed matches
REF['asym']      = None  # fill by drawing both dirs and requiring equality only

print("\n=== overflow-safe formulation search (err>=0 forms) ===")
for init in ['0','half','halfloor']:
    for thresh in ['dmaj','half','2err']:
        allok=True; maxerr=0
        for name,(a,b) in ENDS.items():
            g=variant2(*a,*b,init,thresh)
            # track max err magnitude
            if g!=REF[name]: allok=False
        # direction independence on an asymmetric line
        di = variant2(0,0,19,7,init,thresh)==variant2(19,7,0,0,init,thresh)
        if allok:
            print(f"  MATCH oracle + {'DIRIND' if di else 'NOT-dirind'}  init={init:8} thresh={thresh}")
