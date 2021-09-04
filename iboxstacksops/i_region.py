from . import cfg, ssm, replica
from .aws import myboto3
from .log import logger, get_msg_client
from .tools import smodule_to_class
from .common import *


class ibox_region(object):
    def __init__(self, name, base_data):
        # aws clients/resource
        self.boto3 = myboto3(self, name)
        self.ssm = self.boto3.client("ssm")

        # set property
        self.name = name
        self.bdata = base_data

        if isinstance(base_data, dict):
            for n, v in base_data.items():
                setattr(self, n, v)

        # self.cfg should contains parsed args
        # inside method processed by istack (in a parallel way)
        # i need to set attr to self.cfg and not to the common cfg
        self.cfg = smodule_to_class(cfg)

    def ssm_setup(self):
        result = ssm.setup(self)
        return result

    def ssm_get(self):
        result = ssm.get_by_path(self, cfg.SSM_BASE_PATH)
        return result

    def ssm_put(self):
        result = ssm.put(self)
        return result

    def mylog(self, msg):
        message = f"{self.name} # {msg}"
        try:
            print(message)
        except IOError:
            pass

    def replicate(self):
        self.ssm_map = ssm.get_by_path(self, cfg.SSM_BASE_PATH)
        action = getattr(replica, cfg.command_replicate)
        result = action(self)
        return result


def exec_command(name, data, command, region=None, **kwargs):
    iregion = ibox_region(name, data)

    return getattr(iregion, command)(**kwargs)
