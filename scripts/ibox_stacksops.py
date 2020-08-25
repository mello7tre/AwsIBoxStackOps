#!/usr/bin/env python3
import sys
from iboxstacksops import parser, fargs, tools, log


def main():
    parser.set_fargs(sys.argv[1:])
    tools.get_aws_clients()

    try:
        fargs.func()
    except tools.IboxError as e:
        log.logger.error(e.args[0])
        return e


if __name__ == "__main__":
    result = main()

    if isinstance(result, tools.IboxError):
        exit(1)
