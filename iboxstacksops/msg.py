import os
from urllib import request

from . import cfg

try:
    import slack
except ModuleNotFoundError:
    HAVE_SLACK = False
else:
    HAVE_SLACK = True


def msg_init(stack=None):
    obj = stack.cfg if stack else cfg

    try:
        return obj.MSG_CLIENT
    except Exception:
        msg_channel = getattr(obj, "msg_channel", os.environ.get("IBOX_MSG_CHANNEL"))

        if not msg_channel:
            return

        slack_auth = os.environ.get("IBOX_SLACK_TOKEN")
        slack_user = os.environ.get("IBOX_SLACK_USER")
        teams_auth = os.environ.get("IBOX_TEAMS_AUTH")

        if teams_auth:
            # For Teams use use request as msg_client
            # TODO add request url and parameters
            return request.Request("http://")
        elif HAVE_SLACK and slack_auth and slack_user:
            # For Slack use slack WebClient as msg_client
            obj.MSG_USER = slack_user
            obj.MSG_CLIENT = slack.WebClient(token=slack_auth)
            return obj.MSG_CLIENT
