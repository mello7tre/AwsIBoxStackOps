from . import cfg, ssm
from .aws import myboto3
from .tools import IboxError
from .log import logger, get_msg_client
from .common import *


class ibox_region(object):
    def __init__(self, name, base_data):
        # aws clients/resource
        self.boto3 = myboto3(self, name)
        self.cloudformation = self.boto3.resource('cloudformation')
        self.s3 = self.boto3.client('s3')
        self.client = self.boto3.client('cloudformation')

        # set property
        self.name = name
        self.bdata = base_data

        for n, v in base_data.items():
            setattr(self, n, v)

    def ssm_setup(self):
        self.ssm = self.boto3.client('ssm')
        result = ssm.setup(self)
        return result

    def mylog(self, msg):
        message = f'{self.name} # {msg}'
        try:
            print(message)
        except IOError:
            pass


def exec_command(name, data, command):
    iregion = ibox_region(name, data)

    return getattr(iregion, command)()
