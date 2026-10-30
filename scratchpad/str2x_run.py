import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(REPO)
sys.path.insert(0, "probes/programs"); import run_programs
for prog in sys.argv[1:]:
    text = open(prog).read()
    print("#", prog)
    for m in [run_programs.REF] + run_programs.ZB:
        r = run_programs.run(m, os.path.basename(prog)[:-4], text)
        print("==", m, r[0]); print(r[1].replace("\r", ""))
