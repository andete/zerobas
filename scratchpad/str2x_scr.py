import os, sys
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, "probes/programs"); import run_programs
text = open(sys.argv[1]).read()
for m in [run_programs.REF, run_programs.ZB[0]]:
    r = run_programs.run(m, "scr", text)
    print("==", m, r[0]); print(repr(r[1])); print("\n".join(r[2]))
