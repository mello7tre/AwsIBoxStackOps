import yaml
import logging
import builtins
import pprint
from tqdm import tqdm
from io import StringIO

logging.basicConfig()
logging.getLogger("botocore").setLevel("CRITICAL")
logger = logging.getLogger("stacksops")
logger.setLevel(logging.INFO)
logger.propagate = False

name = "iboxstacksops"
__version__ = "1.0.5"


class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)


class IboxError(Exception):
    pass


class IboxErrorECSService(Exception):
    pass


def tqdm_print(*args, sep="", end="\n", flush=False, **kwargs):
    s = sep.join(str(a) for a in args)
    s += end
    tqdm.write(s, end=end)
    if flush:
        tqdm._instances.clear()  # optional: force flush if needed


def tqdm_pprint(*args, **kwargs):
    buf = StringIO()
    _original_pprint(*args, stream=buf, **kwargs)
    tqdm.write(buf.getvalue().rstrip())


def yaml_exclamation_mark(dumper, data):
    if data.startswith(("!Ref", "!GetAtt", "!GetAZs")):
        tag = data.split(" ")[0]
        value = dumper.represent_scalar(tag, data.replace(f"{tag} ", ""))
    else:
        value = dumper.represent_scalar("tag:yaml.org,2002:str", data)

    return value


yaml.add_representer(str, yaml_exclamation_mark)

# Remove other handlers and add our tqdm handler
logger.handlers = []
formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
tqdm_handler = TqdmLoggingHandler()
tqdm_handler.setFormatter(formatter)
logger.addHandler(tqdm_handler)

# patch print
builtins.print = tqdm_print

# patch pprint
_original_pprint = pprint.pprint
pprint.pprint = tqdm_pprint
