from . import (cfg, template, parameters, resolve)
from .tools import IboxError, get_aws_clients, get_exports
from .log import logger, get_msg_client
from .common import *


STACK_BASE_DATA = [
    'StackName',
    'Description',
    'StackStatus',
    'CreationTime',
    'LastUpdatedTime',
]


class ibox_stack(object):
    def __init__(self, name, base_data):
        # check if stack exists
        try:
            # aws clients/resource
            aws = get_aws_clients()
            self.boto3 = aws['boto3']
            self.cloudformation = aws['res_cloudformation']
            self.s3 = aws['s3']
            self.client = aws['cloudformation']

            self.stack = self.cloudformation.Stack(name)
            self.stack.stack_status
        except Exception as e:
            raise IboxError(e)

        # set property
        self.name = name
        self.bdata = base_data
        self.create = None

        for n, v in base_data.items():
            setattr(self, n, v)

    def update(self):
        self.exports = cfg.exports
        self.template = template.get_template(self)
        parameters.process(self)
        resolve.process(self)

        return 'eccomi'

    def parameters(self):
        self.exports = cfg.exports
        self.template = template.get_template(self)
        parser = parameters.get_stack_parameter_parser(self)
        logger.info(f'{self.name} Parameters:')
        parser.print_help()

    def resolve(self):
        self.exports = cfg.exports
        self.template = template.get_template(self)
        parameters.process(self)
        resolve.show(self)

    def mylog(self, msg, chat=True):
        message = f'{self.name} # {msg}'
        logger.info(message)
        client = get_msg_client()
        if client and chat:
            client.chat_postMessage(
                channel=f'#{cfg.slack_channel}',
                text=message,
                username=os.environ['IBOX_SLACK_USER'],
                icon_emoji=':robot_face:',
            )


def exec_command(name, data, command):
    istack = ibox_stack(name, data)

    return getattr(istack, command)()


def _get_outputs(stack):
    try:
        s_outputs = stack['Outputs']
    except Exception:
        pass
    else:
        outputs = {}
        for output in s_outputs:
            key = output['OutputKey']
            value = output.get('OutputValue', None)
            outputs[key] = value

        return outputs


def _get_parameters(stack):
    try:
        s_parameters = stack['Parameters']
    except Exception as e:
        pass
    else:
        parameters = {}
        for parameter in s_parameters:
            key = parameter['ParameterKey']
            value = parameter.get(
                'ResolvedValue', parameter.get('ParameterValue'))
            parameters[key] = value

        return parameters


def get_base_data(stack):
    data = {'before': {}}
    for d in STACK_BASE_DATA:
        data[d] = stack.get(d, None)

    outputs = _get_outputs(stack)
    if outputs:
        data.update(outputs)
        data['before']['outputs'] = outputs

    parameters = _get_parameters(stack)
    if parameters:
        data['c_parameters'] = parameters

    # ugly fix
    try:
        data['LastUpdatedTime'] = data['LastUpdatedTime'].strftime(
            '%Y-%m-%d %X %Z')
        # data['LastUpdatedTime'] = data['LastUpdatedTime'][0:19]
    except Exception:
        pass

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


def get_stacks(names=[]):
    client = get_aws_clients()['cloudformation']
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

    return data