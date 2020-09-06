from . import (cfg, template, parameters, resolve, actions, events,
               outputs, dashboard, ssm)
from .aws import myboto3
from .tools import IboxError, get_exports
from .log import logger, get_msg_client
from .common import *


class ibox_stack(object):
    def __init__(self, name, base_data, region=None):
        # aws clients/resource
        self.boto3 = myboto3(self, region)
        self.cloudformation = self.boto3.resource('cloudformation')
        self.s3 = self.boto3.client('s3')
        self.client = self.boto3.client('cloudformation')

        # set property
        self.name = name
        self.bdata = base_data
        self.stack = None

        for n, v in base_data.items():
            setattr(self, n, v)

    def create(self):
        self.exports = cfg.exports
        self.template = template.get_template(self)
        self.c_parameters = {}
        parameters.process(self)
        result = actions.create(self)
        if result:
            return {self.name: self.stack.stack_status}

    def update(self):
        self.stack = self.cloudformation.Stack(self.name)
        self.exports = cfg.exports
        self.template = template.get_template(self)
        parameters.process(self)
        resolve.process(self)
        result = actions.update(self)

        if result:
            self.stack.reload()
            return self.stack.stack_status

    def delete(self):
        self.stack = self.cloudformation.Stack(self.name)
        result = actions.delete(self)

    def cancel_update(self):
        self.stack = self.cloudformation.Stack(self.name)
        result = actions.cancel_update(self)

        if result:
            self.stack.reload()
            return self.stack.stack_status

    def continue_update(self):
        self.stack = self.cloudformation.Stack(self.name)
        result = actions.continue_update(self)

        if result:
            self.stack.reload()
            return self.stack.stack_status

    def parameters(self, check=None):
        self.exports = cfg.exports
        self.template = template.get_template(self)
        parser = parameters.get_stack_parameter_parser(self)
        if check:
            parameters.add_stack_params_as_args(parser)
        else:
            logger.info(f'{self.name} Parameters:')
            parser.print_help()

    def info(self):
        self.stack = self.cloudformation.Stack(self.name)
        outputs.show(self, 'before')
        parameters.show_override(self)

    def log(self):
        self.stack = self.cloudformation.Stack(self.name)
        actions.log(self)

    def resolve(self):
        self.exports = cfg.exports
        self.template = template.get_template(self)
        parameters.process(self, show=None)
        resolve.show(self)

    def ssm(self):
        self.ssm = self.boto3.client('ssm')
        ssm.put_parameter(self, self.bdata)

    def mylog(self, msg, chat=True):
        message = f'{self.name} # {msg}'
        try:
            print(message)
        except IOError:
            pass
        # logger.info(message)
        client = get_msg_client()
        if client and chat:
            client.chat_postMessage(
                channel=f'#{cfg.slack_channel}',
                text=message,
                username=os.environ['IBOX_SLACK_USER'],
                icon_emoji=':robot_face:')

    def dash(self):
        dashboard.add_stack(self)


def exec_command(name, data, command, region=None, **kwargs):
    istack = ibox_stack(name, data, region)

    return getattr(istack, command)(**kwargs)


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


def get_stacks(names=[]):
    boto3 = myboto3()
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

    return data