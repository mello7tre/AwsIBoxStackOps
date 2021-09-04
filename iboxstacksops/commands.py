from . import cfg, stacks, i_stack, i_region, events, table, ssm
from .tools import concurrent_exec, get_exports, show_confirm
from .common import *


def create():
    name = cfg.stack[0]
    cfg.exports = get_exports()
    stack = i_stack.ibox_stack(name, {})
    result = stack.create()
    if result:
        pprint(result)

    return result


def update():
    w_stacks = stacks.get()
    cfg.stacks = list(w_stacks.keys())
    cfg.exports = get_exports()
    if len(w_stacks) > 1 and (cfg.role or cfg.type) and not cfg.dryrun:
        print("You are going to UPDATE the following stacks:")
        print(cfg.stacks)
        if not show_confirm():
            return
    result = concurrent_exec("update", w_stacks, i_stack)
    if not cfg.dryrun:
        pprint(result)

    return result


def delete():
    w_stacks = stacks.get()
    cfg.stacks = list(w_stacks.keys())
    print("You are going to DELETE the following stacks:")
    print(cfg.stacks)
    if not show_confirm():
        return
    result = concurrent_exec("delete", w_stacks, i_stack)
    pprint(result)

    return result


def cancel_update():
    w_stacks = stacks.get()
    cfg.exports = get_exports()
    result = concurrent_exec("cancel_update", w_stacks, i_stack)
    pprint(result)

    return result


def continue_update():
    w_stacks = stacks.get()
    cfg.exports = get_exports()
    result = concurrent_exec("continue_update", w_stacks, i_stack)
    pprint(result)

    return result


def rollback():
    w_stacks = stacks.get()
    cfg.exports = get_exports()
    result = concurrent_exec("rollback", w_stacks, i_stack)
    pprint(result)

    return result


def parameters():
    w_stacks = stacks.get()
    cfg.exports = get_exports()
    result = concurrent_exec("parameters", w_stacks, i_stack)


def info():
    if not cfg.compact:
        cfg.OUT_WIDTH = 80
    w_stacks = stacks.get()
    result = concurrent_exec("info", w_stacks, i_stack)


def log():
    name = cfg.stack[0]
    stack = i_stack.ibox_stack(name, {})
    stack.log()


def resolve():
    w_stacks = stacks.get()
    cfg.exports = get_exports()
    result = concurrent_exec("resolve", w_stacks, i_stack)

    return result


def dash():
    w_stacks = stacks.get()
    cfg.dash_name = "_" + "_".join(cfg.stack)
    cfg.jobs = 1
    result = concurrent_exec("dash", w_stacks, i_stack)

    return result


def show_table():
    w_stacks = stacks.get()
    s_table = table.get(list(w_stacks.values()))
    print(s_table)

    return s_table


def ssm_setup():
    w_stacks = stacks.get(exit_if_empty=False)
    result = concurrent_exec("ssm_setup", {k: w_stacks for k in cfg.regions}, i_region)
    pprint(result)


def ssm_put():
    w_stacks = stacks.get()
    cfg.exports = get_exports()
    stacks_params = concurrent_exec("parameters", w_stacks, i_stack, **{"check": True})
    regions = ssm.get_setupped_regions()
    w_regions = cfg.regions if cfg.regions else regions
    result = concurrent_exec(
        "ssm_put", {k: stacks_params for k in w_regions if k in regions}, i_region
    )
    pprint(result)


def ssm_show():
    w_stacks = stacks.get()
    regions = ssm.get_setupped_regions()
    result = concurrent_exec("ssm_get", {k: w_stacks for k in regions}, i_region)
    result = ssm.show(result)
    print(result)


def r53():
    w_stacks = stacks.get()
    cfg.exports = get_exports()
    result = concurrent_exec("r53", w_stacks, i_stack)
    pprint(result)


def replicate():
    regions = ssm.get_setupped_regions() if not cfg.regions else cfg.regions

    if cfg.no_replicate_current:
        try:
            regions.remove(cfg.boto3.region_name)
        except Exception as e:
            pass

    result = concurrent_exec("replicate", {k: {} for k in regions}, i_region)
    pprint(result)

    return result


def stackset():
    name = cfg.stack[0]
    stackset = stacks.get(stackset=True)
    cfg.exports = get_exports()
    stack = i_stack.ibox_stack(name, stackset[name])
    cmd = getattr(stack, f"stackset_{cfg.command_stackset}")
    result = cmd()

    return result
