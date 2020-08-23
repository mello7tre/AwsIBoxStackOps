#!/usr/bin/env python3
import sys
from iboxstacksops import parser, fargs


def populate_fargs(args):
    for n, v in vars(args).items():
        if not hasattr(fargs, n):
            setattr(fargs, n, v)


if __name__ == "__main__":
    parser = parser.get_parser()
    args = parser.parse_known_args(sys.argv[1:])

    populate_fargs(args[0])

    print(fargs.dashboard)
