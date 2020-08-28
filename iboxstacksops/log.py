import logging
import slack
from . import cfg
from .common import *

logging.basicConfig()
logging.getLogger('botocore').setLevel('CRITICAL')
logger = logging.getLogger('stacksops')
logger.setLevel(logging.INFO)


def get_msg_client():
    try:
        cfg.slack_channel
    except Exception:
        cfg.slack_channel = None

    if (cfg.slack_channel
            and cfg.action in [
                'update', 'create', 'delete', 'cancel', 'continue']
            and 'IBOX_SLACK_TOKEN' in os.environ
            and 'IBOX_SLACK_USER' in os.environ):
        slack_web = slack.WebClient(token=os.environ['IBOX_SLACK_TOKEN'])
        return slack_web

    return None
