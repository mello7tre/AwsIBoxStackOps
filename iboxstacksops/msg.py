import os
import json
from urllib.parse import urlparse
from http.client import HTTPSConnection

from . import cfg

try:
    import slack
except ModuleNotFoundError:
    HAVE_SLACK = False
else:
    HAVE_SLACK = True


HTTP_HEADERS = {
    "Accept": "application/json",
    "Connection": "keep-alive",
    "Content-Type": "application/json",
}


class msg(object):
    def __init__(self):
        self.msg_channel = getattr(
            cfg, "msg_channel", os.environ.get("IBOX_MSG_CHANNEL")
        )

        if not self.msg_channel:
            return

        slack_auth = os.environ.get("IBOX_SLACK_TOKEN")
        slack_user = os.environ.get("IBOX_SLACK_USER")
        teams_auth = os.environ.get("IBOX_TEAMS_AUTH")

        if teams_auth:
            # For Teams use use request as msg_client
            # TODO add request url and parameters
            self.msg_client_type = "teams"
            self.init_http()
        elif HAVE_SLACK and slack_auth and slack_user:
            # For Slack use slack WebClient as msg_client
            self.msg_client_type = "slack"
            self.msg_client = slack.WebClient(token=slack_auth)
            self.msg_user = slack_user

    def init_http(self):
        teams_webhook_url = os.environ.get("IBOX_TEAMS_WEBHOOK_URL")
        url_parsed = urlparse(teams_webhook_url)
        http_host = url_parsed.netloc
        http_path = url_parsed.path
        self.msg_client = HTTPSConnection(http_host, timeout=2)
        self.msg_client_request = {
            "method": "POST",
            "url": http_path,
            "headers": HTTP_HEADERS,
        }

    def send_smg(self, message):
        try:
            self.msg_client
        except Exception:
            return

        if self.msg_client_type == "teams":
            # Teams
            try:
                self.msg_client_request["body"] = json.dumps({"text": message})
                self.msg_client.request(**self.msg_client_request)
                response = self.msg_client.getresponse()
                response.read()
            except Exception:
                self.msg_client.close()
                raise
        elif self.msg_client_type == "slack":
            # Slack
            self.msg_client.chat_postMessage(
                channel=f"#{self.msg_channel}",
                text=message,
                username=self.msg_user,
                icon_emoji=":robot_face:",
            )
