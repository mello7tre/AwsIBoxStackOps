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
    return
    result = concurrent_exec('update', w_stacks, i_stack, iregion.name)
    print(result)

    return result


def delete(iregion):
    w_stacks = stacks.get()
    iregion.cfg.stacks = list(w_stacks.keys())
    return
    result = concurrent_exec('delete', w_stacks, i_stack, iregion.name)
    print(result)

    return result
