from . import cfg, ssm
from .aws import myboto3
from .log import logger, get_msg_client
from .common import *


class ibox_region(object):
    def __init__(self, name, base_data):
        # aws clients/resource
        self.boto3 = myboto3(self, name)
        self.ssm = self.boto3.client('ssm')

        # set property
        self.name = name
        self.bdata = base_data

        for n, v in base_data.items():
            setattr(self, n, v)

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
        message = f'{self.name} # {msg}'
        try:
            print(message)
        except IOError:
            pass


def exec_command(name, data, command, region=None, **kwargs):
    iregion = ibox_region(name, data)

    return getattr(iregion, command)(**kwargs)
