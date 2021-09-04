import boto3
from . import cfg


class myboto3(object):
    def __init__(self, istack=None, region=None):
        self.istack = istack

        try:
            cfg.parallel
            self.parallel = cfg.parallel
        except Exception:
            self.parallel = None

        kwarg_session = {}
        region_name = region if region else cfg.region
        if region_name:
            kwarg_session["region_name"] = region_name

        if cfg.profile:
            kwarg_session["profile_name"] = cfg.profile

        if not self.parallel and not region:
            try:
                self.boto3 = cfg.boto3
            except Exception:
                self.boto3 = boto3.session.Session(**kwarg_session)
                cfg.boto3 = self.boto3
        else:
            self.boto3 = boto3.session.Session(**kwarg_session)

        self.region_name = self.boto3.region_name

    def client(self, name):
        attr_name = f"cli_{self.region_name}_{name}"

        if self.parallel and self.istack:
            obj = self.istack
        else:
            obj = cfg

        try:
            client = getattr(obj, attr_name)
        except Exception:
            client = self.boto3.client(name)
            setattr(obj, attr_name, client)

        return client

    def resource(self, name):
        attr_name = f"res_{self.region_name}_{name}"

        if self.parallel:
            obj = self.istack
        else:
            obj = cfg

        try:
            resource = getattr(obj, attr_name)
        except Exception:
            resource = self.boto3.resource(name)
            setattr(obj, attr_name, resource)

        return resource
