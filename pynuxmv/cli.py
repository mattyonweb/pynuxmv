#!/usr/bin/env python

import argparse
import pynuxmv.main as nxmv
import subprocess as sp
import re


credits_ = r"^\*\*\*.*$"
credits_regex = re.compile(credits_, re.M)

noproof  = r"^-- no proof or counterexample found with bound.*$"
noproof_regex = re.compile(noproof, re.M)

whitespaces = r"\n{2,}"
whitespaces_regex   = re.compile(whitespaces)


def show_credits():
    print("""
    *** This is nuXmv 2.0.0 (compiled on Mon Oct 14 17:39:30 2019)
    *** Copyright (c) 2014-2019, Fondazione Bruno Kessler
    *** For more information on nuXmv see https://nuxmv.fbk.eu
    *** or email to <nuxmv@list.fbk.eu>. 
""")

        
def execute_nuxmv(xmv_fname, nuxmv_args, verbose=False):
    stdout = sp.check_output(["nuXmv"] + nuxmv_args + [xmv_fname],
                             universal_newlines=True)
    
    if not verbose:
        stdout = re.sub(credits_regex, "", stdout)
        
    print(re.sub(whitespaces_regex, "",
                 re.sub(noproof_regex, "", stdout)))

        
def clio():
    parser = argparse.ArgumentParser()
   
    parser.add_argument('fname_input', type=str, help='file name input')
    parser.add_argument('fname_output', type=str, help='file name output')
    parser.add_argument("--only_transpile", type=bool,
                        help="transpile without checking with nuxmv",
                        default=False
    )

    args, nuxmv_args = parser.parse_known_args()

    with open(args.fname_input, "r") as f:
        src = f.read()

    xmv_fnames, _ = nxmv.run(src, args.fname_output, True)

    if not args.only_transpile:
        show_credits()
        
        for fname in xmv_fnames:
            execute_nuxmv(fname, nuxmv_args)

if __name__ == "__main__":
    clio()
