from . import cfg, istack, iregion, events, show, ssm
from .tools import concurrent_exec, get_exports, show_confirm
from .common import *


def create():
    name = cfg.stack[0]
    stack = istack.ibox_stack(name, {})
    cfg.exports = get_exports()
    result = stack.create()
    if result:
        print(result)


def update():
    stacks = istack.get_stacks()
    cfg.stacks = list(stacks.keys())
    cfg.exports = get_exports()
    if len(stacks) > 1 and (cfg.role or cfg.type) and not cfg.dryrun:
        print('You are going to UPDATE the following stacks:')
        print(cfg.stacks)
        if not show_confirm():
            return
    result = concurrent_exec('update', stacks)
    if not cfg.dryrun:
        print(result)


def delete():
    stacks = istack.get_stacks()
    cfg.stacks = list(stacks.keys())
    print('You are going to DELETE the following stacks:')
    print(cfg.stacks)
    if not show_confirm():
        return
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


def show_table():
    stacks = istack.get_stacks()
    table = show.table(list(stacks.values()))
    print(table)


def ssm_setup():
    stacks = istack.get_stacks()
    result = concurrent_exec(
        'ssm_setup', {k: stacks for k in cfg.regions}, iregion)
    pprint(result)


def ssm_put():
    stacks = istack.get_stacks()
    result = concurrent_exec('ssm_put', stacks, iregion)


def ssm_show():
    regions = ssm.get_setupped_regions()
    result = concurrent_exec(
        'ssm_get', {k: {} for k in regions}, iregion)
    result = ssm.show(result)
    print(result)
