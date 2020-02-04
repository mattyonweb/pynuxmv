import subprocess as sub
import pynuxmv.main as nxm
import os
import re


nuxmv = "/home/groucho/aur/nuXmv-2.0.0-Linux/bin/nuXmv"

fail_regex = {
    "ltl":   re.compile("LTL specification.*is false"),
    "invar": re.compile("invariant.*is false")
}

srcs = [fname for fname in os.listdir(".")
            if fname.split(".")[-1] == "py" and ("invarspec" in fname or "ltl" in fname)]


expected = { 
    "01-example-invarspec.py": "pass",
    "02-example-invarspec.py": "fail",
    "03-example-ltl.py": "pass",
}

for fname in srcs:
    with open(fname, "r") as f:
        src = f.read()

    out_fname = os.path.splitext(fname)[0] + ".xmv"
    nxm.run(src, out_fname)

    logic    = "ltl" if "ltl" in fname else "invar"
    cmd_file = f"cmd_{logic}"
    
    stdout = sub.check_output([nuxmv, "-source", cmd_file, out_fname], universal_newlines=True)

    if (res := fail_regex[logic].findall(stdout)) and expected[fname] == "pass":
        print(res)
        print(f"{fname} ha fallito ma doveva funzionare:")
        for match in res:
            print(f"\t{match.group()}")
        with open(".{out_fname}.log", "w") as f:
            f.write(stdout)

    elif not (res := fail_regex[logic].findall(stdout))   and not expected[fname] == "pass":
        print(f"{fname} ha funzionato ma doveva fallire")
        for match in res:
            print(f"\t{match.group()}")
        with open(f".{out_fname}.log", "w") as f:
            f.write(stdout)

    else:
        #print(stdout)
        print(f"{fname} OK")

