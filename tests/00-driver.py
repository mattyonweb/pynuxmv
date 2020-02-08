import subprocess as sub
import pynuxmv.main as nxm
import os
import re
import sys
import argparse

# You should most likely change this...
nuxmv = "/home/groucho/aur/nuXmv-2.0.0-Linux/bin/nuXmv"



my_parser = argparse.ArgumentParser()
my_parser.add_argument('--testnum', action='store', type=str, default=None)
my_parser.add_argument('--verbose', action='store_true', default=False)
cli_args = my_parser.parse_args()


## Various regexes for pretty printing & co.

comments = r"^\*\*\*.*$"
noproof  = r"^-- no proof or counterexample found with bound.*$"
filter_output_regex = re.compile("|".join([comments, noproof]), re.M)
doublespaces = r"\n{2,}"
doublespaces_regex  = re.compile(doublespaces)


ltl_fail   = r"LTL specification.*is false"
invar_fail = r"invariant.*is false"
invar_unknown = r"invariant.*is unknown"
fail_regex = re.compile( '|'.join([ltl_fail, invar_fail, invar_unknown]) )




def is_file_to_test(fname):
    """ Check if it makes sense to test the file `fname` """
    try:
        return int(fname[:2]) >= 1 and fname.split(".")[-1] == "py" 
    except:
        return False



# Select only a single test file to run
if cli_args.testnum:
    srcs = [fname for fname in os.listdir(".") if is_file_to_test(fname) and fname.startswith(cli_args.testnum)]
else:
    srcs = [fname for fname in os.listdir(".") if is_file_to_test(fname)]
    srcs = sorted(srcs)


    
verbose = cli_args.verbose
    
expected = { 
    "01-example.xmv": "pass",
    "02-example.xmv": "fail",
    "03-example.xmv": "pass",
    "04-example.xmv": "pass",
    "05-example.xmv0": "pass",
    "06-example.xmv": "pass",
    "07-example.xmv": "pass",
    "08-example.xmv": "pass",
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
            if verbose:
                print(re.sub(doublespaces_regex, "", re.sub(filter_output_regex, "", stdout)))

