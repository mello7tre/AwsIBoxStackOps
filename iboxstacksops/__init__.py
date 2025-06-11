import yaml
import logging


logging.basicConfig()
logging.getLogger("botocore").setLevel("CRITICAL")
logger = logging.getLogger("stacksops")
logger.setLevel(logging.INFO)


name = "iboxstacksops"
__version__ = "0.9.2"


class IboxError(Exception):
    pass


class IboxErrorECSService(Exception):
    pass


def yaml_exclamation_mark(dumper, data):
    if data.startswith(("!Ref", "!GetAtt", "!GetAZs")):
        tag = data.split(" ")[0]
        value = dumper.represent_scalar(tag, data.replace(f"{tag} ", ""))
    else:
        value = dumper.represent_scalar("tag:yaml.org,2002:str", data)

    return value


yaml.add_representer(str, yaml_exclamation_mark)
