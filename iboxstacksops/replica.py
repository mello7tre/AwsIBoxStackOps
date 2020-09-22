from . import stacks, i_stack
from .tools import concurrent_exec, get_exports
from .log import logger
from .common import *


def create(iregion):
    name = iregion.cfg.stack[0]
    stack = i_stack.ibox_stack(name, {})
    iregion.cfg.exports = get_exports(obj=iregion)
    return
    result = stack.create()
    if result:
        print(result)

    return result


def update(iregion):
    w_stacks = stacks.get(obj=iregion)
    iregion.cfg.stacks = list(w_stacks.keys())
    iregion.cfg.exports = get_exports(obj=iregion)
    result = concurrent_exec('replicate',
        w_stacks, i_stack, region=iregion.name,
        **{'ssm_map': iregion.ssm_map})
    print(result)

    return result


def delete(iregion):
    w_stacks = stacks.get()
    iregion.cfg.stacks = list(w_stacks.keys())
    result = concurrent_exec('replicate',
        w_stacks, i_stack, region=iregion.name,
        **{'ssm_map': iregion.ssm_map})
    print(result)

    return result
