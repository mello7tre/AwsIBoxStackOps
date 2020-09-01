from . import cfg, istack, events
from .tools import concurrent_exec, get_exports, show_confirm
from .common import *


def create():
    name = cfg.stack[0]
    stack = istack.ibox_stack(name, {})
    cfg.exports = get_exports()
    result = stack.create()
    print(r)


def update():
    stacks = istack.get_stacks()
    cfg.exports = get_exports()
    # pprint(stacks)
    result = concurrent_exec('update', stacks)
    if not cfg.dryrun:
        print(result)


def delete():
    stacks = istack.get_stacks()
    print(f'You are going to DELETE the following stacks:\n{list(stacks.keys)}')
    if show_confirm():
        result = concurrent_exec('delete', stacks)
        print(result)


def cancel_update():
    stacks = istack.get_stacks()
    cfg.exports = get_exports()
    result = concurrent_exec('cancel_update', stacks)
    print(result)


def continue_update():
    stacks = istack.get_stacks()
    cfg.exports = get_exports()
    result = concurrent_exec('continue_update', stacks)
    print(result)


def parameters():
    stacks = istack.get_stacks()
    cfg.exports = get_exports()
    result = concurrent_exec('parameters', stacks)


def info():
    stacks = istack.get_stacks()
    result = concurrent_exec('info', stacks)


def log():
    name = cfg.stack[0]
    stack = istack.ibox_stack(name, {})
    stack.log()


def resolve():
    stacks = istack.get_stacks()
    cfg.exports = get_exports()
    result = concurrent_exec('resolve', stacks)


def dash():
    stacks = istack.get_stacks()
    cfg.dash_name = '_' + '_'.join(cfg.stack)
    cfg.jobs = 1
    result = concurrent_exec('dash', stacks)
