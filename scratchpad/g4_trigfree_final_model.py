#!/usr/bin/env python3
"""FINAL asm-faithful model of the trig-free arc boundary vector + ARCBIG
(spec-basic-graphics-g4.md §5.2.1 REVISED). This mirrors EXACTLY what will be
coded in Z80 (resident continuous-sign compares via fp_cmp against HALF_PI/
PI/THREE_HALF_PI; tenant QTAB quarter-wave fold+lookup, integer round-scale,
+-1 nudge, and the ARCBIG raw-diff-with-zero-wrap-fix). Validated against
every captured VG-8020 arc (g4_pointsets.json) + the round1 boundary
re-captures (g4_arc_boundary_capture.json) before writing any asm."""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
PTS = json.load(open(os.path.join(HERE, "g4_pointsets.json")))
BND = json.load(open(os.path.join(HERE, "g4_arc_boundary_capture.json")))

# --- QTAB: 65-entry quarter-wave, capped at 255 (asm byte domain) ----------
QTAB = []
for i in range(65):
    v = round(256*math.sin(2*math.pi*i/256))
    QTAB.append(255 if v > 255 else v)

def qtab_fold(b):          # b: 0..255 -> fold index 0..64
    m = b & 0x7F
    return m if m <= 64 else 128 - m

def qtab_lookup(b):
    return QTAB[qtab_fold(b & 0xFF)]

def raw_brad(theta_abs):
    # resident: ONE bounded fp_mul (theta*128/pi) + round-half-up (gfx_round_arga_de)
    return round(theta_abs * 128.0 / math.pi)   # unmasked, e.g. 0..~257

HP = math.pi/2; PI_ = math.pi; TP = 3*math.pi/2

def cmp3(x, c):
    # fp_cmp-equivalent: 1 (x<c) / 2 (x==c) / 4 (x>c)
    if x < c: return 1
    if x == c: return 2
    return 4

def resident_signs(theta_abs):
    # exactly the 3-compare decision tree gfx_circ_boundary_prep will implement
    c1 = cmp3(theta_abs, HP)
    c2 = cmp3(theta_abs, TP)
    if c1 == 2 or c2 == 2:
        sign_c = 0
    elif c1 == 1 or c2 == 4:
        sign_c = 1
    else:
        sign_c = -1
    if theta_abs == 0:
        sign_s = 0
    else:
        c3 = cmp3(theta_abs, PI_)
        if c3 == 2:
            sign_s = 0
        elif c3 == 1:
            sign_s = 1
        else:
            sign_s = -1
    return sign_c, sign_s

def bvec_mag(r, tab):
    return (r*tab + 128) >> 8

def bvec_nudge(mag, sign):
    if sign == 0:
        return 0
    if mag != 0:
        return sign*mag
    return sign

def gfx_circ_bvec(bradlo, sign_c, sign_s, r):
    tab_c = qtab_lookup((bradlo + 64) & 0xFF)
    magx = bvec_mag(r, tab_c)
    x = bvec_nudge(magx, sign_c)
    tab_s = qtab_lookup(bradlo & 0xFF)
    magy = bvec_mag(r, tab_s)
    y = bvec_nudge(magy, sign_s)
    return x, -y   # screen convention

def arcbig_calc(raw_s, raw_e):
    diff = (raw_e - raw_s) & 0xFF
    if diff == 0 and raw_e != raw_s:
        return True
    return diff > 128

def midpoint_circle_octants(r):
    pts=set(); x,y=0,r; d=1-r
    while x<=y:
        for sx in(1,-1):
            for sy in(1,-1): pts.add((sx*x,sy*y)); pts.add((sx*y,sy*x))
        if d<0: d+=2*x+3
        else: d+=2*(x-y)+5; y-=1
        x+=1
    return pts

def cross(A,B): return A[0]*B[1]-A[1]*B[0]

def full_pipeline(cx, cy, r, a0, a1):
    """Reproduces resident marshalling (brad+signs per boundary) then tenant
    gfx_circ_bvec_prep + gfx_circle_op's arc mask, end to end."""
    rs = raw_brad(abs(a0)); sc_s, ss_s = resident_signs(abs(a0))
    re_ = raw_brad(abs(a1)); sc_e, ss_e = resident_signs(abs(a1))
    S = gfx_circ_bvec(rs & 0xFF, sc_s, ss_s, r)
    E = gfx_circ_bvec(re_ & 0xFF, sc_e, ss_e, r)
    big = arcbig_calc(rs, re_)
    pts=set()
    for dx,dy in midpoint_circle_octants(r):
        P=(dx,dy)
        s_ok = cross(S,P) <= 0
        e_ok = cross(P,E) <= 0
        keep = (s_ok or e_ok) if big else (s_ok and e_ok)
        if keep: pts.add((cx+dx,cy+dy))
    return pts

CASES=[("arc_0_hpi",0,1.57),("arc_hpi_pi",1.57,3.14),("arc_wrap",3,1),("arc_full628",0,6.28)]
allok=True
print("=== captured arcs (FINAL asm-faithful model) ===")
for label,a0,a1 in CASES:
    d=PTS[label]; cx,cy=d["cx"],d["cy"]; r=int(d["ops"].split(")")[1].split(",")[1])
    ref={(x,y) for x,y in d["pts"]}
    got=full_pipeline(cx,cy,r,a0,a1)
    ok = got==ref
    allok &= ok
    print(f"  {label:12s} a=({a0},{a1}) r={r}  {'MATCH' if ok else f'DIFF +{len(got-ref)} -{len(ref-got)}'}")

print("\n=== round1 boundary re-captures ===")
for label,c in BND["round1"].items():
    ops=c["ops"]
    args=ops.split(")",1)[1].lstrip(",").split(",")
    r=int(args[0]); a0,a1=float(args[2]),float(args[3])
    ref={(x,y) for x,y in c["pts"]}
    got=full_pipeline(c["cx"],c["cy"],r,a0,a1)
    ok = got==ref
    allok &= ok
    print(f"  {label:26s} ({a0},{a1}) -> {'MATCH' if ok else f'DIFF +{len(got-ref)} -{len(ref-got)}'}")

# spoke cases (from the acceptance battery): verify they at least produce sane
# (non-crashing, directionally-plausible) vectors -- no pts oracle here, just a
# sanity readout.
print("\n=== spoke cases (sanity, no pts oracle -- CIRCLE_CASES battery) ===")
for label,a0,a1 in [("spoke_270",-1.57,0),("spoke_wedge2",-0.1,-1.57)]:
    r=15
    rs = raw_brad(abs(a0)); sc_s, ss_s = resident_signs(abs(a0))
    re_ = raw_brad(abs(a1)); sc_e, ss_e = resident_signs(abs(a1))
    S = gfx_circ_bvec(rs & 0xFF, sc_s, ss_s, r)
    E = gfx_circ_bvec(re_ & 0xFF, sc_e, ss_e, r)
    print(f"  {label}: a=({a0},{a1}) S={S} E={E}")

print("\n"+("ALL MATCH -- asm-faithful model de-risked" if allok else "*** MISMATCH ***"))
