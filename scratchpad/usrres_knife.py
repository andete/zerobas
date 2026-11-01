"""D-USRSTRRES knives: cut each mechanism, rebuild (hash the ROM), run
usrstr-acceptance, record which rows go red, restore. Sequential; restores the
tree and rebuilds at the end."""
import hashlib, os, re, shutil, subprocess, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROM = os.path.join(REPO, "build", "basic-reloc.rom")
KNIVES = {
    "K1 no set_factyp2 in str_usr": ("basic/usr.asm",
        "                call    set_factyp2         ; as `eval` would: ev_usr is normally\n",
        "                                            ; KNIFE K1\n"),
    "K2 no USR in the string probe": ("basic/strvar.asm",
        "                jp      z,str_usr           ; routine leaves VALTYP 3 -- run it here\n",
        "                nop                         ; KNIFE K2\n                nop\n                nop\n"),
    "K3 no comparison-site skip": ("basic/expr.asm",
        "                jr      z,cl_rel_num\n",
        "                nop                         ; KNIFE K3\n                nop\n"),
    "K4 cache hit never taken": ("basic/usr.asm",
        "                jr      nz,evu_run\n",
        "                jr      evu_run             ; KNIFE K4\n"),
}


def sh(cmd):
    return subprocess.run(cmd, shell=True, cwd=REPO, capture_output=True, text=True)


def romhash():
    return hashlib.sha256(open(ROM, "rb").read()).hexdigest()[:12]


base = romhash()
print("base rom", base, flush=True)
ONLY = sys.argv[1:]
for name, (path, old, new) in KNIVES.items():
    if ONLY and not any(name.startswith(o) for o in ONLY):
        continue
    full = os.path.join(REPO, path)
    keep = open(full).read()
    if keep.count(old) != 1:
        sys.exit(f"{name}: anchor count {keep.count(old)}")
    open(full, "w").write(keep.replace(old, new))
    try:
        b = sh("make repack-machine")
        h = romhash() if b.returncode == 0 else "BUILD-FAILED"
        if h == base or h == "BUILD-FAILED":
            # an inert plant reports `red rows: -` exactly like a knife the gate
            # cannot see -- refuse instead of reading it
            print(f"{name:32s} rom {h}: PLANT DID NOT TAKE -- no reading", flush=True)
            continue
        g = sh("make usrstr-acceptance")
        rows = sorted(set(re.findall(r"ref '([A-Z])", g.stdout)))
        print(f"{name:32s} rom {h} ({'differs' if h != base else 'SAME AS BASE: INERT'})"
              f"  gate rc={g.returncode}  red rows: {' '.join(rows) or '-'}", flush=True)
    finally:
        open(full, "w").write(keep)
sh("make repack-machine")
print("restored rom", romhash(), "(base", base + ")", flush=True)
