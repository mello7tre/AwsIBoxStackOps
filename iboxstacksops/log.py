import logging
from . import fargs
from .common import *

logging.basicConfig()                                                           
logging.getLogger('botocore').setLevel('CRITICAL')                              
logger = logging.getLogger('stackops')                                              
logger.setLevel(logging.INFO)


def get_msg_client():
    try:
        fargs.slack_channel
    except:
        fargs.slack_channel = None

    if (fargs.slack_channel
        and fargs.action in [
            'update', 'create', 'delete', 'cancel', 'continue']
        and 'IBOX_SLACK_TOKEN' in os.environ
        and 'IBOX_SLACK_USER' in os.environ):
        slack_web = slack.WebClient(
            token=os.environ['IBOX_SLACK_TOKEN'])
        return slack_web
    
    return None
