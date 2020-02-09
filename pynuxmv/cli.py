#!/usr/bin/env python

import argparse
import pynuxmv.main as nxmv
import subprocess as sp

# working with positional arguments
def execute_nuxmv(xmv_fname, nuxmv_args):
    sp.call(["nuXmv"] + nuxmv_args + [xmv_fname])

def clio():
    parser = argparse.ArgumentParser()
   
    parser.add_argument('fname_input', type=str, help='file name input')
    parser.add_argument('fname_output', type=str, help='file name output')
    parser.add_argument("--check", type=bool,
                        help="transpiles and then launching nuxmv",
                        default=True
    )

    args, nuxmv_args = parser.parse_known_args()

    with open(args.fname_input, "r") as f:
        src = f.read()

    xmv_fnames, _ = nxmv.run(src, args.fname_output, True)

    if args.check:
        for fname in xmv_fnames:
            execute_nuxmv(fname, nuxmv_args)

if __name__ == "__main__":
    clio()
