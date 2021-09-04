import os
import sys
import yaml
import json
import time
import botocore
from datetime import datetime, timedelta, tzinfo
from pprint import pprint, pformat


class IboxError(Exception):
    pass


class IboxErrorECSService(Exception):
    pass


CLF_YAML_FUNC = (
    "!Ref",
    "!GetAtt",
    "!GetAZs",
)


def yaml_exclamation_mark(dumper, data):
    if data.startswith(CLF_YAML_FUNC):
        tag = data.split(" ")[0]
        value = dumper.represent_scalar(tag, data.replace(f"{tag} ", ""))
    else:
        value = dumper.represent_scalar("tag:yaml.org,2002:str", data)

    return value


yaml.add_representer(str, yaml_exclamation_mark)
