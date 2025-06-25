import os
import json
import uuid
import time

from . import cfg
from .aws import myboto3


class msg(object):
    def __init__(self):
        self.msg_channel = getattr(cfg, "msg_topic", os.environ.get("IBOX_MSG_CHANNEL"))

        if not self.msg_channel:
            return

        if self.msg_channel.startswith("arn:aws"):
            boto3 = myboto3()
            self.msg_client = boto3.client("sns")
            self.msg_client_type = "sns"
            self.thread_id = str(uuid.uuid4())
        else:
            self.msg_client = None

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
                    "threadId": self.thread_id,
                    "enableCustomActions": False,
                },
            }
            self.msg_client.publish(
                TopicArn=self.msg_channel, Message=json.dumps(custom_notification)
            )
            time.sleep(1)
