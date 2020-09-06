import time
import concurrent.futures
from traceback import print_exc
import boto3 as base_boto3
from . import cfg
from .log import logger
from .common import *


def show_confirm():
    if cfg.answer_yes:
        return True
    print('')
    answer = input('Enter [y] to continue or any other key to exit: ')
    if not answer or answer[0].lower() != 'y':
        return False
    else:
        return True


def _pause():
    if cfg.pause == 0:
        if not show_confirm():
            exit(0)
    elif cfg.pause and cfg.pause > 0:
        time.sleep(cfg.pause)


def concurrent_exec(command, stacks, smodule, region=None, **kwargs):
    data = {}
    func = getattr(smodule, 'exec_command')

    if cfg.jobs == 1 or len(stacks) == 1:
        for s, v in stacks.items():
            data[s] = func(s, v, command, region, **kwargs)
            if list(stacks)[-1] != s:
                _pause()
    else:
        cfg.parallel = True
        jobs = cfg.jobs if cfg.jobs else len(stacks)

        with concurrent.futures.ProcessPoolExecutor(
                max_workers=jobs) as executor:
            future_to_stack = {
                executor.submit(func, s, v, command, region, **kwargs): s
                for s, v in stacks.items()}
            for future in concurrent.futures.as_completed(future_to_stack):
                stack = future_to_stack[future]
                try:
                    data[stack] = future.result()
                except Exception as e:
                    print(f'{stack} generated an exception: {e}')
                    print_exc()
                    raise IboxError(e)

    return data


def get_exports():
    logger.info('Getting CloudFormation Exports')
    exports = {}
    client = cfg.boto3.client('cloudformation')
    paginator = client.get_paginator('list_exports')
    response_iterator = paginator.paginate()
    for e in response_iterator:
        for export in e['Exports']:
            name = export['Name']
            value = export['Value']
            exports[name] = value
        # if all(key in exports for key in ['BucketAppRepository']):
        #    return exports

    return exports


def stack_resource_to_dict(stack):
    out = {}
    for n in dir(stack):
        if not n.startswith('__'):
            prop = ''
            words = n.split('_')
            for w in words:
                prop += w.capitalize()
            out[prop] = getattr(stack, n)

    return out


def smodule_to_class(smodule):
    class obj(object):
        pass

    cls = obj()
    for n in dir(smodule):
        if not n.startswith('_'):
            value = getattr(smodule, n)
            setattr(cls, n, value)

    return cls
