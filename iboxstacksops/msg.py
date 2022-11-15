import os
from . import cfg

try:
    import slack
except ModuleNotFoundError:
    HAVE_MSG = False
else:
    HAVE_MSG = True


def init(stack=None):
    obj = stack.cfg if stack else cfg
    try:
        return obj.MSG_CLIENT
    except Exception:
        MSG_AUTH = os.environ.get("IBOX_SLACK_TOKEN")
        MSG_USER = os.environ.get("IBOX_SLACK_USER")
        if HAVE_MSG and MSG_AUTH and MSG_USER and getattr(obj, "slack_channel", None):
            obj.MSG_USER = MSG_USER
            obj.MSG_CLIENT = slack.WebClient(token=MSG_AUTH)
            return obj.MSG_CLIENT
