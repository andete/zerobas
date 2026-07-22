#!/usr/bin/env python3
"""Validate the EXACT integer model intended for the Z80 port (truncating
brad via flt_to_int16 semantics, quadrant sign via integer compares against
0/64/128/192 with an exact-zero case) against every pinned oracle: the four
captured arcs (g4_pointsets.json), round1 boundary re-captures, round2
presence/absence sweep, and round3 (a near-zero start angle -0.01,1.57)."""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
PTS = json.load(open(os.path.join(HERE, "g4_pointsets.json")))
BND = json.load(open(os.path.join(HERE, "g4_arc_boundary_capture.json")))

TN = 256
SINTAB = [round(256*math.sin(2*math.pi*i/TN)) for i in range(TN)]
def costab(b): return SINTAB[(b+TN//4) % TN]
def sintab(b): return SINTAB[b % TN]

def midpoint_circle_octants(r):
    pts=set(); x,y=0,r; d=1-r
    while x<=y:
        for sx in(1,-1):
            for sy in(1,-1): pts.add((sx*x,sy*y)); pts.add((sx*y,sy*x))
        if d<0: d+=2*x+3
        else: d+=2*(x-y)+5; y-=1
        x+=1
    return pts

def flt_to_int16_trunc(x):
    # truncate toward zero, matching basic/float.asm flt_to_int16 semantics
    return int(x) if x >= 0 else -int(-x)

def brad_of(theta_abs):
    # theta_abs already |angle|; one bounded fp_mul by 128/pi, truncated,
    # masked to 8 bits (mod 2pi in the discretized system)
    K = 128.0/math.pi
    raw = flt_to_int16_trunc(theta_abs*K)
    return raw & 0xFF

def quadrant_signs(brad):
    # integer compares against the exact quadrant boundaries 0/64/128/192,
    # mirroring bvec_trigfree's continuous t<HP/t>TP-style strict compares,
    # WITH the exact-zero case at the boundaries themselves.
    if brad == 64 or brad == 192:
        sign_c = 0
    elif brad < 64 or brad > 192:
        sign_c = 1
    else:
        sign_c = -1
    if brad == 0 or brad == 128:
        sign_s = 0
    elif 0 < brad < 128:
        sign_s = 1
    else:
        sign_s = -1
    return sign_c, sign_s

def bvec_asm(theta_abs, r):
    brad = brad_of(theta_abs)
    sign_c, sign_s = quadrant_signs(brad)
    mag_c = round(r*abs(costab(brad))/256)
    mag_s = round(r*abs(sintab(brad))/256)
    sx = sign_c*mag_c if mag_c else sign_c
    sy = sign_s*mag_s if mag_s else sign_s
    return (sx, -sy)

def cross(A,B): return A[0]*B[1]-A[1]*B[0]

def arc_mask(cx,cy,r,a0,a1,bvec):
    S=bvec(abs(a0),r); E=bvec(abs(a1),r)
    b_s = brad_of(abs(a0)); b_e = brad_of(abs(a1))
    big = ((b_e - b_s) & 0xFF) > 128
    pts=set()
    for (dx,dy) in midpoint_circle_octants(r):
        P=(dx,dy)
        sside = cross(S,P)<=0
        eside = cross(P,E)<=0
        keep = (sside or eside) if big else (sside and eside)
        if keep: pts.add((cx+dx,cy+dy))
    return pts

CASES=[("arc_0_hpi",0,1.57),("arc_hpi_pi",1.57,3.14),("arc_wrap",3,1),("arc_full628",0,6.28)]
allok=True
print("=== captured arcs ===")
for label,a0,a1 in CASES:
    d=PTS[label]; cx,cy=d["cx"],d["cy"]; r=int(d["ops"].split(")")[1].split(",")[1])
    ref={(x,y) for x,y in d["pts"]}
    tf=arc_mask(cx,cy,r,a0,a1,bvec_asm)
    e=tf-ref; m=ref-tf
    ok = not e and not m
    allok &= ok
    print(f"  {label:12s} a=({a0},{a1}) r={r}  {'MATCH' if ok else f'DIFF +{len(e)} -{len(m)} extra={sorted(e)[:5]} miss={sorted(m)[:5]}'}")

print("\n=== round1 boundary re-captures ===")
for label,c in BND["round1"].items():
    ops=c["ops"]
    args=ops.split(")",1)[1].lstrip(",").split(",")
    r=int(args[0]); a0,a1=float(args[2]),float(args[3])
    ref={(x,y) for x,y in c["pts"]}
    tf=arc_mask(c["cx"],c["cy"],r,a0,a1,bvec_asm)
    e=tf-ref; m=ref-tf
    ok = not e and not m
    allok &= ok
    print(f"  {label:26s} ({a0},{a1}) -> {'MATCH' if ok else f'DIFF +{len(e)} -{len(m)}'}")

print("\n=== round2 presence/absence sweep (a0 near pi/2, end=3.14) ===")
# figure out which single point is the boundary point in question: diff between
# full arc_hpi_pi(1.57,3.14) point-set (22 pts, 'present') and the 21-pt variant
ref_present = None
for label,c in BND["round2"].items():
    ops=c["ops"]; a0=float(c["a0"]); expect_present=c["present"]; n=c["n"]
    args=ops.split(")",1)[1].lstrip(",").split(",")
    r=int(args[0]); a1=float(args[3])
    cx,cy = 60,60
    tf=arc_mask(cx,cy,r,a0,a1,bvec_asm)
    got_n = len(tf)
    ok = (got_n == n)
    allok &= ok
    print(f"  {label:16s} a0={a0} expect_n={n} got_n={got_n} present={expect_present} {'OK' if ok else 'FAIL'}")

print("\n=== round3 (near-zero start, colour-plane single-point check) ===")
c = BND["round3"]
print(" ", c["ops"], "-> not independently checkable here (colour-plane capture, not a point-set); skipping numeric check")

print("\n" + ("ALL ASM-MODEL MATCH" if allok else "*** MISMATCH -- asm model needs adjustment ***"))
