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
srcs = sorted(srcs)

expected = { 
    "01-example-invarspec.xmv": "pass",
    "02-example-invarspec.xmv": "fail",
    "03-example-ltl.xmv": "pass",
    "04-example-ltl.xmv": "pass",
    "05-example-ltl.xmv0": "pass"
}

for fname in srcs:
    with open(fname, "r") as f:
        src = f.read()

    out_fname__ = os.path.splitext(fname)[0] + ".xmv"
    out_fnames, _ = nxm.run(src, out_fname__)

    logic    = "ltl" if "ltl" in fname else "invar"
    cmd_file = f"cmd_{logic}"

    for out_fname in out_fnames:
        stdout = sub.check_output([nuxmv, "-source", cmd_file, out_fname], universal_newlines=True)

        if (res := fail_regex[logic].findall(stdout)) and expected[out_fname] == "pass":
            print(f"{fname} ha fallito ma doveva funzionare:")
            for match in res:
                print(f"\t{match}")
            with open(f".{out_fname}.log", "w") as f:
                f.write(stdout)

        elif not (res := fail_regex[logic].findall(stdout))   and not expected[out_fname] == "pass":
            print(f"{fname} ha funzionato ma doveva fallire")
            for match in res:
                print(f"\t{match}")
            with open(f".{out_fname}.log", "w") as f:
                f.write(stdout)

        else:
            print(f"{fname} OK")

