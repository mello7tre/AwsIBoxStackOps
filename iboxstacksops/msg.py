import os

from . import cfg

try:
    import slack
except ModuleNotFoundError:
    HAVE_MSG = False
else:
    HAVE_MSG = True


def msg_init(stack=None):
    obj = stack.cfg if stack else cfg
    try:
        return obj.MSG_CLIENT
    except Exception:
        MSG_AUTH = os.environ.get("IBOX_MSG_TOKEN")
        MSG_USER = os.environ.get("IBOX_MSG_USER")
        MSG_CHAN = getattr(obj, "msg_channel", os.environ.get("IBOX_MSG_CHANNEL"))
        if HAVE_MSG and MSG_AUTH and MSG_USER and MSG_CHAN:
            obj.MSG_USER = MSG_USER
            obj.MSG_CLIENT = slack.WebClient(token=MSG_AUTH)
            return obj.MSG_CLIENT
