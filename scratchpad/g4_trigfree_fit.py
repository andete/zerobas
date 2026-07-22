#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""G4 TRIG-FREE arc boundary fit. Replace the float math-pack SIN/COS (the hang
source) with a compact integer sine TABLE to compute the two boundary vectors
(round(r*cos), -round(r*sin)) to pixel precision, then feed the UNCHANGED integer
cross-product arc mask. Verify it reproduces the captured VG-8020 arc pixels
EXACTLY -- de-risk before coding (the recurring arc lesson).

Model (what the asm will do):
  brad = flt_to_int16(theta * (TN/2pi)) & (TN-1)          # ONE bounded fp_mul + mask
  cos88 = COSTAB[brad] ; sin88 = SINTAB[brad]             # 8.8 fixed, +-256
  Sx = nudge(round(r*cos88/256), cos88) ; Sy = -nudge(round(r*sin88/256), sin88)
The cross-product mask (16-bit bounded) is IDENTICAL to the current tenant."""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
PTS = json.load(open(os.path.join(HERE, "g4_pointsets.json")))
BND = json.load(open(os.path.join(HERE, "g4_arc_boundary_capture.json")))

TN = 256                                   # table entries over full circle (~1.4 deg)
SINTAB = [round(256*math.sin(2*math.pi*i/TN)) for i in range(TN)]   # 8.8, +-256
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

def nudge(scaled, tabval):
    """round(r*tab/256) but keep a +-1 direction when the true value is
    sub-half-nonzero (the gfx_round_nonzero rule -- reference distinguishes
    1.57 from 1.58 at a cardinal)."""
    if scaled!=0: return scaled
    if tabval>0: return 1
    if tabval<0: return -1
    return 0

def bvec_trigfree(theta, r):
    # SIGN from quadrant COMPARES (theta vs pi/2, pi, 3pi/2 -- no multiply, no hang);
    # MAGNITUDE from the integer table. This preserves near-cardinal direction
    # (1.57 is in quad 0 => cos>0) that a coarse table would quantize to zero.
    HP=math.pi/2; PI=math.pi; TP=3*math.pi/2; TAU=2*math.pi
    t = theta % TAU
    sign_c = 1 if (t<HP or t>TP) else (-1 if (HP<t<TP) else 0)
    sign_s = 1 if (0<t<PI) else (-1 if (PI<t<TAU) else 0)
    b = round(t*(TN/TAU)) % TN                       # table index (magnitude only)
    mag_c = round(r*abs(costab(b))/256)
    mag_s = round(r*abs(sintab(b))/256)
    sx = sign_c*mag_c if mag_c else sign_c           # nudge: dir sign when |.|->0
    sy = sign_s*mag_s if mag_s else sign_s
    return (sx, -sy)                                  # screen: +angle -> -y

def bvec_float(theta, r):                    # control: the current float model
    c = round(r*math.cos(theta)); s = round(r*math.sin(theta))
    # emulate gfx_round_nonzero nudge
    if c==0 and math.cos(theta)!=0: c = 1 if math.cos(theta)>0 else -1
    if s==0 and math.sin(theta)!=0: s = 1 if math.sin(theta)>0 else -1
    return (c, -s)

def cross(A,B): return A[0]*B[1]-A[1]*B[0]

def arc_mask(cx,cy,r,a0,a1,bvec):
    S=bvec(abs(a0),r); E=bvec(abs(a1),r)
    sweep=(abs(a1)-abs(a0))%(2*math.pi)
    if a1!=0 and (abs(a1)%(2*math.pi))==0: sweep=2*math.pi
    if sweep==0: sweep=2*math.pi
    big = sweep>math.pi
    pts=set()
    for (dx,dy) in midpoint_circle_octants(r):
        P=(dx,dy)
        sside = cross(S,P)<=0            # cross(S,P)<=0
        eside = cross(P,E)<=0           # cross(P,E)<=0
        keep = (sside or eside) if big else (sside and eside)
        if keep: pts.add((cx+dx,cy+dy))
    return pts

CASES=[("arc_0_hpi",0,1.57),("arc_hpi_pi",1.57,3.14),("arc_wrap",3,1),("arc_full628",0,6.28)]
def ref_pts(label):
    if label in PTS: return {(x,y) for x,y in PTS[label]["pts"]}
    return None

print(f"TABLE: {TN} entries, 8.8 fixed. Verify trig-free == float == captured.\n")
allok=True
for label,a0,a1 in CASES:
    d=PTS[label]; cx,cy=d["cx"],d["cy"]; r=int(d["ops"].split(")")[1].split(",")[1])
    ref=ref_pts(label)
    tf=arc_mask(cx,cy,r,a0,a1,bvec_trigfree)
    fl=arc_mask(cx,cy,r,a0,a1,bvec_float)
    e_tf=tf-ref; m_tf=ref-tf; e_fl=fl-ref; m_fl=ref-fl
    st_tf="MATCH" if not e_tf and not m_tf else f"DIFF +{len(e_tf)} -{len(m_tf)}"
    st_fl="MATCH" if not e_fl and not m_fl else f"DIFF +{len(e_fl)} -{len(m_fl)}"
    print(f"  {label:12s} a=({a0},{a1}) r={r}  trigfree:{st_tf:16s} float:{st_fl}")
    if e_tf or m_tf:
        allok=False
        print(f"       trigfree extra{sorted(e_tf)[:4]} miss{sorted(m_tf)[:4]}")
        print(f"       S_tf={bvec_trigfree(abs(a0),r)} E_tf={bvec_trigfree(abs(a1),r)}  "
              f"S_fl={bvec_float(abs(a0),r)} E_fl={bvec_float(abs(a1),r)}")

# also verify against the agent's boundary re-captures
print("\nBoundary re-captures (round1):")
for label,c in BND["round1"].items():
    ops=c["ops"]
    # CIRCLE(cx,cy),r,color,start,end -> args after ')'
    args=ops.split(")",1)[1].lstrip(",").split(",")
    if len(args)<4: continue
    r=int(args[0]); a0,a1=float(args[2]),float(args[3])
    ref={(x,y) for x,y in c["pts"]}
    tf=arc_mask(c["cx"],c["cy"],r,a0,a1,bvec_trigfree)
    e=tf-ref; mm=ref-tf
    print(f"  {label:26s} ({a0},{a1}) -> {'MATCH' if not e and not mm else f'DIFF +{len(e)} -{len(mm)}'}")
    if e or mm: allok=False

print("\n"+("ALL TRIG-FREE MATCH -- de-risked" if allok else "*** mismatches -- tune TN/nudge ***"))
