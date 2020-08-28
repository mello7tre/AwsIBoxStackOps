import boto3
from . import cfg


class myboto3(object):
    def __init__(self, istack=None):
        self.istack = istack

        try:
            cfg.parallel
            self.parallel = cfg.parallel
        except Exception:
            self.parallel = None

        kwarg_session = {}
        if cfg.region:
            kwarg_session['region_name'] = cfg.region

        if not self.parallel:
            try:
                self.boto3 = cfg.boto3
            except Exception:
                self.boto3 = boto3.session.Session(**kwarg_session)
                cfg.boto3 = self.boto3
        else:
            self.boto3 = boto3.session.Session(**kwarg_session)

        self.region_name = self.boto3.region_name

    def client(self, name):
        if self.parallel:
            obj = self.istack
        else:
            obj = cfg

        try:
            client = getattr(obj, f'cli_{name}')
        except Exception:
            client = self.boto3.client(name)
            setattr(obj, f'cli_{name}', client)

        return client

    def resource(self, name):
        if self.parallel:
            obj = self.istack
        else:
            obj = cfg

        try:
            resource = getattr(obj, f'res_{name}')
        except Exception:
            resource = self.boto3.resource(name)
            setattr(obj, f'res_{name}', resource)

        return resource
