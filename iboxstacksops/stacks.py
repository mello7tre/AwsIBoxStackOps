from . import cfg, parameters, outputs
from .aws import myboto3
from .log import logger
from .common import *


def get_base_data(stack):
    data = {
        'before': {},
        'after': {},
        'changed': {},
    }

    stack_outputs = outputs.get(stack)

    data.update(stack_outputs)
    data['before']['outputs'] = stack_outputs

    stack_parameters = parameters.get(stack)
    if stack_parameters:
        data['c_parameters'] = stack_parameters

    return data


def _get_stack(r, data):
    for s in r['Stacks']:
        stack_name = s['StackName']
        stack_data = get_base_data(s)
        stack_role = stack_data.get('EnvRole', None)
        stack_type = stack_data.get('StackType', None)
        if (stack_name in cfg.stack
                or stack_role in cfg.role
                or stack_type in cfg.type
                or 'ALL' in cfg.type):
            data[stack_name] = stack_data


def get(names=[], exit_if_empty=True, obj=None):
    if not obj:
        boto3 = myboto3()
        client = boto3.client('cloudformation')
    else:
        boto3 = getattr(obj, 'boto3')
        client = boto3.client('cloudformation')

    logger.info('Getting Stacks Description')
    data = {}

    if not names:
        names = cfg.stack

    if (not cfg.role
            and not cfg.type
            and len(names) < cfg.MAX_SINGLE_STACKS):
        for s in names:
            response = client.describe_stacks(StackName=s)
            _get_stack(response, data)
    else:
        paginator = client.get_paginator('describe_stacks')
        response_iterator = paginator.paginate()
        for r in response_iterator:
            _get_stack(r, data)

    if not data and exit_if_empty:
        logger.warning('No Stacks found!\n')
        exit(0)

    return data
