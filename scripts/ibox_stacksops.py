#!/usr/bin/env python3
import sys
from iboxstacksops import parser, fargs


if __name__ == "__main__":
    parser.set_fargs(sys.argv[1:])

    fargs.func()
