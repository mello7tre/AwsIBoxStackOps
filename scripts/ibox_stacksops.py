#!/usr/bin/env python3
import sys
from iboxstacksops import parser, fargs, tools


if __name__ == "__main__":
    parser.set_fargs(sys.argv[1:])
    tools.set_region()

    fargs.func()
