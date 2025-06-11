import os
import json
from urllib.parse import urlparse, urlencode
from http.client import HTTPSConnection

from . import cfg
from .aws import myboto3

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

ADAPTIVE_CARD = {
    "type": "message",
    "attachments": [
        {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": [
                    {
                        "type": "TextBlock",
                        "weight": "bolder",
                        "size": "medium",
                    }
                ],
            },
        }
    ],
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

        if self.msg_channel.startswith("arn:aws"):
            boto3 = myboto3()
            self.msg_client = boto3.client("sns")
            self.msg_client_type = "sns"
        elif teams_auth:
            # For Teams use use request as msg_client
            # TODO add request url and parameters
            self.init_graph_client()
            self.msg_client_type = "teams"
        elif HAVE_SLACK and slack_auth and slack_user:
            # For Slack use slack WebClient as msg_client
            self.msg_client = slack.WebClient(token=slack_auth)
            self.msg_user = slack_user
            self.msg_client_type = "slack"
        else:
            self.msg_client = None

    # oauth2 ms graph Teams Auth
    def init_graph_client(self):
        tenant_id = os.environ.get("IBOX_TEAMS_TENANT_ID")
        client_id = os.environ.get("IBOX_TEAMS_CLIENT_ID")
        client_secret = os.environ.get("IBOX_TEAMS_CLIENT_SECRET")
        team_id = os.environ.get("IBOX_TEAMS_TEAM_ID")
        channel_id = self.msg_channel

        if any(
            not n
            for n in [
                tenant_id,
                client_id,
                client_secret,
                team_id,
                channel_id,
            ]
        ):
            return

        token_client = HTTPSConnection("login.microsoftonline.com", timeout=2)
        token_client.request(
            "POST",
            f"/{tenant_id}/oauth2/v2.0/token",
            body=urlencode(
                {
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                }
            ),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response = token_client.getresponse()
        data = response.read().decode()
        token_info = json.loads(data)
        access_token = token_info.get("access_token")

        if access_token:
            self.headers = {
                "Authorization": f"Bearer {access_token}",
                "Connection": "keep-alive",
                "Content-Type": "application/json",
            }
            self.msg_client = HTTPSConnection("graph.microsoft.com", timeout=2)
            self.msg_url = f"/v1.0/teams/{team_id}/channels/{channel_id}/messages"

    # webhook Teams Auth (currently not used)
    def init_http(self):
        teams_webhook_url = os.environ.get("IBOX_TEAMS_WEBHOOK_URL")
        url_parsed = urlparse(teams_webhook_url)
        self.msg_client = HTTPSConnection(url_parsed.netloc, timeout=2)
        self.msg_client_request = {
            "method": "POST",
            "url": f"{url_parsed.path}?{url_parsed.query}",
            "headers": HTTP_HEADERS,
        }

    def send_smg(self, message):
        try:
            self.msg_client
        except Exception:
            return

        if self.msg_client_type == "sns":
            custom_notification = {
                "version": "1.0",
                "source": "custom",
                "content": {
                    "description": message,
                },
                "metadata": {
                    "enableCustomActions": False,
                },
            }
            response = self.msg_client.publish(
                TopicArn=self.msg_channel, Message=json.dumps(custom_notification)
            )
        elif self.msg_client_type == "teams":
            # Teams
            try:
                ADAPTIVE_CARD["attachments"][0]["content"]["body"][0]["text"] = message
                # self.msg_client_request["body"] = json.dumps(ADAPTIVE_CARD)
                # self.msg_client.request(**self.msg_client_request)
                self.msg_client.request(
                    "POST",
                    self.msg_url,
                    body=json.dumps(ADAPTIVE_CARD),
                    headers=self.headers,
                )
                response = self.msg_client.getresponse()
                response.read()
                # status = response.status
                # out = response.read().decode()
                # logger.info(f"Teams Msg Status: {status} - Response: {out}")
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
