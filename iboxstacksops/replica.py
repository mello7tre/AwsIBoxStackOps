from . import stacks, i_stack, table
from .tools import concurrent_exec, get_exports
from .log import logger
from .common import *


def create(iregion):
    name = iregion.cfg.stack[0]
    stack = i_stack.ibox_stack(name, {}, region=iregion.name)
    iregion.cfg.exports = get_exports(obj=iregion)
    result = stack.replicate(ssm_map=iregion.ssm_map, iregion=iregion)
    if result:
        print(result)

    return result


def update(iregion):
    w_stacks = stacks.get(obj=iregion)
    iregion.cfg.stacks = list(w_stacks.keys())
    iregion.cfg.exports = get_exports(obj=iregion)
    result = concurrent_exec(
        "replicate",
        w_stacks,
        i_stack,
        region=iregion.name,
        **{"ssm_map": iregion.ssm_map, "iregion": iregion}
    )
    print(result)

    return result


def delete(iregion):
    w_stacks = stacks.get(obj=iregion)
    iregion.cfg.stacks = list(w_stacks.keys())
    result = concurrent_exec(
        "replicate",
        w_stacks,
        i_stack,
        region=iregion.name,
        **{"ssm_map": iregion.ssm_map, "iregion": iregion}
    )
    print(result)

    return result


def show(iregion):
    w_stacks = stacks.get(obj=iregion)
    s_table = table.get(list(w_stacks.values()))
    print(s_table)

    return s_table
