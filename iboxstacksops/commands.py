from . import cfg, istack, dashboard
from .tools import concurrent_exec, get_exports
from .common import *


def create():
    stacks = istack.get_stacks()
    cfg.exports = get_exports()
    result = concurrent_exec('create', stacks)
    print(result)


def update():
    stacks = istack.get_stacks()
    cfg.exports = get_exports()
    # pprint(stacks)
    result = concurrent_exec('update', stacks)
    if not cfg.dryrun:
        print(result)


def parameters():
    stacks = istack.get_stacks()
    cfg.exports = get_exports()
    result = concurrent_exec('parameters', stacks)


def info():
    stacks = istack.get_stacks()
    result = concurrent_exec('info', stacks)


def resolve():
    stacks = istack.get_stacks()
    cfg.exports = get_exports()
    result = concurrent_exec('resolve', stacks)


def dash():
    stacks = istack.get_stacks()
    cfg.dash_name = '_' + '_'.join(cfg.stack)
    cfg.jobs = 1
    result = concurrent_exec('dash', stacks)
