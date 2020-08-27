import time
import concurrent.futures
from traceback import print_exc
import boto3 as base_boto3
from . import cfg, istack
from .log import logger


class IboxError(Exception):
    pass


class IboxErrorECSService(Exception):
    pass


def show_confirm():
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
    elif args.pause and args.pause > 0:
        time.sleep(args.pause)


def concurrent_exec(command, stacks):
    data = {}

    if cfg.jobs == 1 or len(stacks) == 1:
        for s, v in stacks.items():
            data[s] = istack.exec_command(s, v, command)
            if list(stacks)[-1] != s:
                _pause()
    else:
        jobs = cfg.jobs if cfg.jobs else len(stacks)

        with concurrent.futures.ProcessPoolExecutor(
                max_workers=jobs) as executor:
            future_to_stack = {
                executor.submit(istack.exec_command, s, v, command): s
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


def get_aws_clients():
    kwarg_session = {}

    if cfg.region:
        kwarg_session['region_name'] = cfg.region

    boto3 = base_boto3.session.Session(**kwarg_session)

    cloudformation = boto3.client('cloudformation')
    res_cloudformation = boto3.resource('cloudformation')
    s3 = boto3.client('s3')

    cfg.client = cloudformation

    return {
        'boto3': boto3,
        'cloudformation': cloudformation,
        'res_cloudformation': res_cloudformation,
        's3': s3,
    }


def get_exports():
    logger.info('Getting CloudFormation Exports')
    exports = {}
    paginator = cfg.client.get_paginator('list_exports')
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
