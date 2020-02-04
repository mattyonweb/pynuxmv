#!/usr/bin/env python

import argparse
import pynuxmv.main as nxmv

# working with positional arguments

def clio():
    parser = argparse.ArgumentParser()
   
    parser.add_argument('fname_input', type=str, help='file name input')
    parser.add_argument('fname_output', type=str, help='file name output')

    args = parser.parse_args()

    filename = args.fname_input

    with open(args.fname_input, "r") as f:
        src = f.read()

    nxmv.run(src, args.fname_output, True)

if __name__ == "__main__":
    clio()
