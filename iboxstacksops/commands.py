from . import cfg, i_stack, i_region, events, show, ssm
from .tools import concurrent_exec, get_exports, show_confirm
from .common import *


def create():
    name = cfg.stack[0]
    stack = i_stack.ibox_stack(name, {})
    cfg.exports = get_exports()
    result = stack.create()
    if result:
        print(result)


def update():
    stacks = i_stack.get_stacks()
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
    stacks = i_stack.get_stacks()
    cfg.stacks = list(stacks.keys())
    print('You are going to DELETE the following stacks:')
    print(cfg.stacks)
    if not show_confirm():
        return
    result = concurrent_exec('delete', stacks)
    print(result)


def cancel_update():
    stacks = i_stack.get_stacks()
    cfg.exports = get_exports()
    result = concurrent_exec('cancel_update', stacks)
    print(result)


def continue_update():
    stacks = i_stack.get_stacks()
    cfg.exports = get_exports()
    result = concurrent_exec('continue_update', stacks)
    print(result)


def parameters():
    stacks = i_stack.get_stacks()
    cfg.exports = get_exports()
    result = concurrent_exec('parameters', stacks)


def info():
    stacks = i_stack.get_stacks()
    result = concurrent_exec('info', stacks)


def log():
    name = cfg.stack[0]
    stack = i_stack.ibox_stack(name, {})
    stack.log()


def resolve():
    stacks = i_stack.get_stacks()
    cfg.exports = get_exports()
    result = concurrent_exec('resolve', stacks)


def dash():
    stacks = i_stack.get_stacks()
    cfg.dash_name = '_' + '_'.join(cfg.stack)
    cfg.jobs = 1
    result = concurrent_exec('dash', stacks)


def show_table():
    stacks = i_stack.get_stacks()
    table = show.table(list(stacks.values()))
    print(table)


def ssm_setup():
    stacks = i_stack.get_stacks()
    result = concurrent_exec(
        'ssm_setup', {k: stacks for k in cfg.regions}, smodule=i_region)
    pprint(result)


def ssm_put():
    stacks = i_stack.get_stacks()
    cfg.exports = get_exports()
    concurrent_exec('parameters', stacks, **{'check': True})
    regions = ssm.get_setupped_regions()
    w_regions = cfg.regions if cfg.regions else regions
    result = concurrent_exec(
        'ssm_put', {k: stacks for k in w_regions if k in regions},
        smodule=i_region)


def ssm_show():
    regions = ssm.get_setupped_regions()
    result = concurrent_exec(
        'ssm_get', {k: {} for k in regions}, smodule=i_region)
    result = ssm.show(result)
    print(result)
