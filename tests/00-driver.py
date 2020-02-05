import subprocess as sub
import pynuxmv.main as nxm
import os
import re

# You should most likely change this...
nuxmv = "/home/groucho/aur/nuXmv-2.0.0-Linux/bin/nuXmv"


ltl_fail   = r"LTL specification.*is false"
invar_fail = r"invariant.*is false"
fail_regex = re.compile( '|'.join([ltl_fail, invar_fail]) )


def is_file_to_test(fname):
    try:
        return int(fname[:2]) >= 1 and fname.split(".")[-1] == "py" 
    except:
        return False
    
srcs = [fname for fname in os.listdir(".") if is_file_to_test(fname)]
srcs = sorted(srcs)

expected = { 
    "01-example.xmv": "pass",
    "02-example.xmv": "fail",
    "03-example.xmv": "pass",
    "04-example.xmv": "pass",
    "05-example.xmv0": "pass",
    "06-example.xmv": "pass",
    "07-example.xmv": "pass",
}

for fname in srcs:
    with open(fname, "r") as f:
        src = f.read()

    out_fname__ = os.path.splitext(fname)[0] + ".xmv"
    out_fnames, _ = nxm.run(src, out_fname__)

    cmd_file = f"unify"

    for out_fname in out_fnames:
        stdout = sub.check_output([nuxmv, "-source", cmd_file, out_fname], universal_newlines=True)

        if (res := fail_regex.findall(stdout)) and expected[out_fname] == "pass":
            print(f"{fname} ha fallito ma doveva funzionare:")
            for match in res:
                print(f"\t{match}")
            with open(f".{out_fname}.log", "w") as f:
                f.write(stdout)

        elif not (res := fail_regex.findall(stdout)) and not expected[out_fname] == "pass":
            print(f"{fname} ha funzionato ma doveva fallire")
            for match in res:
                print(f"\t{match}")
            with open(f".{out_fname}.log", "w") as f:
                f.write(stdout)

        else:
            print(f"{fname} OK")

