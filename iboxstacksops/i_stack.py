from . import (
    cfg,
    template,
    parameters,
    resolve,
    actions,
    events,
    outputs,
    dashboard,
    ssm,
    route53,
)
from .aws import myboto3
from .log import logger, get_msg_client
from .tools import smodule_to_class
from .common import *


class ibox_stack(object):
    def __init__(self, name, base_data, region=None):
        # aws clients/resource
        self.boto3 = myboto3(self, region)
        self.cloudformation = self.boto3.resource("cloudformation")
        self.s3 = self.boto3.client("s3")
        self.client = self.boto3.client("cloudformation")

        # set property
        self.name = name
        self.bdata = base_data
        self.stack = None

        if isinstance(base_data, dict):
            for n, v in base_data.items():
                setattr(self, n, v)

        # self.cfg should contains parsed args
        # inside method processed by istack (in a parallel way)
        # i need to set attr to self.cfg and not to the common cfg
        self.cfg = smodule_to_class(cfg)

    def create(self):
        self.exports = self.cfg.exports
        self.template = template.get_template(self)
        self.c_parameters = {}
        parameters.process(self)
        resolve.process(self)
        result = actions.create(self)
        if result:
            return {self.name: self.stack.stack_status}

    def update(self):
        self.stack = self.cloudformation.Stack(self.name)
        self.exports = self.cfg.exports
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

    def rollback(self):
        self.stack = self.cloudformation.Stack(self.name)
        result = actions.rollback(self)

        if result:
            self.stack.reload()
            return self.stack.stack_status

    def parameters(self, check=None):
        self.exports = self.cfg.exports
        self.template = template.get_template(self)
        parser = parameters.get_stack_parameter_parser(self)
        if check:
            parameters.add_stack_params_as_args(self, parser)
            return self.stack_parsed_args, self.parameters
        else:
            logger.info(f"{self.name} Parameters:")
            parser.print_help()

    def info(self):
        self.stack = self.cloudformation.Stack(self.name)
        self.template = template.get_template(self)
        outputs.show(self, "before")
        parameters.show_override(self)

    def log(self):
        self.stack = self.cloudformation.Stack(self.name)
        actions.log(self)

    def resolve(self):
        self.exports = self.cfg.exports
        self.template = template.get_template(self)
        parameters.process(self, show=None)
        resolve.show(self)

    def ssm(self):
        self.ssm = self.boto3.client("ssm")
        ssm.put_parameters(self, self.bdata)

    def replicate(self, ssm_map, iregion):
        self.cfg.exports = iregion.cfg.exports
        self.cfg.stacks = iregion.cfg.stacks
        # pprint(ssm_map)
        for n, v in ssm_map.items():
            if n.startswith(f"{self.name}/"):
                parameter = n.split("/")[1]
                setattr(self.cfg, parameter, v)

        result = getattr(self, f"{self.cfg.command_replicate}")()

        return result

    def mylog(self, msg, chat=True):
        message = f"{self.name} # {msg}"
        try:
            print(message)
        except IOError:
            pass
        # logger.info(message)
        client = get_msg_client()
        if client and chat:
            try:
                client.chat_postMessage(
                    channel=f"#{cfg.slack_channel}",
                    text=message,
                    username=os.environ["IBOX_SLACK_USER"],
                    icon_emoji=":robot_face:",
                )
            except Exception as e:
                logger.warning(f"Error sending message to channel: {e}")

    def dash(self):
        dashboard.add_stack(self)

    def r53(self):
        self.route53 = self.boto3.client("route53")
        result = route53.create(self)
        return result

    def stackset_update(self):
        cfg.fields = cfg.STACKSET_INSTANCES_SHOW_TABLE_FIELDS
        self.exports = self.cfg.exports
        self.template = template.get_template(self, stackset=True)
        self.stack = True
        parameters.process(self)
        result = actions.stackset_update(self)
        if result:
            return {self.name: None}

    def stackset_info(self):
        self.exports = self.cfg.exports
        self.template = template.get_template(self, stackset=True)
        self.stack = True
        if not self.cfg.compact:
            self.cfg.OUT_WIDTH = 80
        parameters.show_override(self)

    def stackset_parameters(self):
        self.exports = self.cfg.exports
        self.template = template.get_template(self, stackset=True)
        parser = parameters.get_stack_parameter_parser(self)
        logger.info(f"{self.name} Parameters:")
        parser.print_help()

    def stackset_show(self):
        result = actions.stackset_show(self)

    def stackset_instances(self):
        cfg.fields = cfg.STACKSET_INSTANCES_SHOW_TABLE_FIELDS
        cfg.output = "text"
        result = actions.stackset_instances(self)


def exec_command(name, data, command, region=None, **kwargs):
    istack = ibox_stack(name, data, region)

    return getattr(istack, command)(**kwargs)
