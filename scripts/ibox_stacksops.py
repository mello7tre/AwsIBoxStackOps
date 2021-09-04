#!/usr/bin/env python3
import sys
from iboxstacksops.parser import set_cfg
from iboxstacksops.common import IboxError
from iboxstacksops.log import logger
from iboxstacksops import cfg


def main():
    set_cfg(sys.argv[1:])

    try:
        cfg.func()
    except IboxError as e:
        logger.error(f"{e.args[0]}\n")
        return e


if __name__ == "__main__":
    result = main()

    if isinstance(result, IboxError):
        exit(1)
