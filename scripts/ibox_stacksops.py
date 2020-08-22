#!/usr/bin/env python3
import sys
from iboxstacksops import args, cfg

parser = args.get_parser()
args = parser.parse_known_args(sys.argv[1:])
