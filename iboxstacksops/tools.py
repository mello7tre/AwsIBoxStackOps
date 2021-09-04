import time
import concurrent.futures
from traceback import print_exc
from .aws import myboto3
from . import cfg
from .log import logger
from .common import *


def show_confirm():
    if cfg.parallel or cfg.answer_yes:
        return True

    print("\nEnter [y] to continue or any other key to exit: ", end="")
    sys.stdin = open(0)
    answer = sys.stdin.read(1)

    if not answer or answer.lower() != "y":
        return False
    else:
        return True


def _pause_or_stop():
    if cfg.pause == 0:
        if not show_confirm():
            return True
    elif cfg.pause and cfg.pause > 0:
        time.sleep(cfg.pause)


def concurrent_exec(command, stacks, smodule, region=None, **kwargs):
    n_failed = 0
    do_exit = False
    data = {}
    func = getattr(smodule, "exec_command")

    jobs = cfg.jobs if cfg.jobs else len(stacks)
    if jobs == 0:
        return

    cfg.parallel = False if not cfg.parallel and jobs == 1 else True

    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as executor:
        future_to_stack = {}
        for s, v in stacks.items():
            ex_sub = executor.submit(func, s, v, command, region, **kwargs)

            future_to_stack[ex_sub] = s

            if not cfg.parallel and list(stacks)[-1] != s:
                concurrent.futures.wait({ex_sub: s})
                if _pause_or_stop():
                    do_exit = True
                    break

        for future in concurrent.futures.as_completed(future_to_stack):
            stack = future_to_stack[future]
            try:
                data[stack] = future.result()
            except IboxError as e:
                data[stack] = e.args[0]
                n_failed += 1
            except Exception as e:
                print(f"{stack} generated an exception: {e}")
                print_exc()
                raise IboxError(e)

    if n_failed == len(stacks):
        raise IboxError(f"All failed:\n{data}")

    if do_exit:
        print(data)
        exit(0)
    else:
        return data


def get_exports(obj=None):
    logger.info("Getting CloudFormation Exports")
    exports = {}

    if not obj:
        boto3 = myboto3()
        client = boto3.client("cloudformation")
    else:
        boto3 = getattr(obj, "boto3")
        client = boto3.client("cloudformation")

    paginator = client.get_paginator("list_exports")
    response_iterator = paginator.paginate()
    for e in response_iterator:
        for export in e["Exports"]:
            name = export["Name"]
            value = export["Value"]
            exports[name] = value
        # if all(key in exports for key in ['BucketAppRepository']):
        #    return exports

    return exports


def stack_resource_to_dict(stack):
    out = {}
    for n in dir(stack):
        if not n.startswith("__"):
            prop = ""
            words = n.split("_")
            for w in words:
                prop += w.capitalize()
            out[prop] = getattr(stack, n)

    return out


def smodule_to_class(smodule):
    class obj(object):
        pass

    cls = obj()
    for n in dir(smodule):
        if not n.startswith("_"):
            value = getattr(smodule, n)
            setattr(cls, n, value)

    return cls
