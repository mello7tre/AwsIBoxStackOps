import os
from . import cfg

try:
    import slack
except ModuleNotFoundError:
    HAVE_MSG = False
else:
    HAVE_MSG = True
    MSG_AUTH = os.environ.get("IBOX_SLACK_TOKEN")
    MSG_USER = os.environ.get("IBOX_SLACK_USER")


def init(stack=None):
    try:
        cfg.MSG_CLIENT
    except Exception:
        if HAVE_MSG and MSG_AUTH and MSG_USER and cfg.slack_channel:
            cfg.MSG_USER = MSG_USER
            cfg.MSG_CLIENT = slack.WebClient(token=MSG_AUTH)
