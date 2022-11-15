import os
from . import cfg

try:
    import slack
except ModuleNotFoundError:
    pass
else:
    MSG_AUTH = os.environ.get("IBOX_SLACK_TOKEN")
    MSG_USER = os.environ.get("IBOX_SLACK_USER")


def init(stack=None):
    try:
        cfg.MSG_CLIENT
    except Exception:
        if MSG_AUTH and MSG_USER and cfg.slack_channel:
            cfg.MSG_USER = MSG_USER
            cfg.MSG_CLIENT = slack.WebClient(token=MSG_AUTH)
