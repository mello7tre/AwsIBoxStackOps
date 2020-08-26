from . import cfg, istack
from .tools import concurrent_exec, get_exports
from .common import *


def create():
    stacks = istack.get_stacks()
    cfg.exports = get_exports()
    print('create command:')
    # pprint(stacks)
    result = concurrent_exec('create', stacks)
    print(result)


def update():
    stacks = istack.get_stacks()
    cfg.exports = get_exports()
    print('update command:')
    # pprint(stacks)
    result = concurrent_exec('update', stacks)
    print(result)


def parameters():
    stacks = istack.get_stacks()
    cfg.exports = get_exports()
    result = concurrent_exec('parameters', stacks)


def resolve():
    stacks = istack.get_stacks()
    cfg.exports = get_exports()
    result = concurrent_exec('resolve', stacks)
