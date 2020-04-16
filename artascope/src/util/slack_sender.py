#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/22
import uuid
from types import FunctionType
import slack
from artascope.src.config import (
    REDIS_SLACK_MSG_EXPIRE,
    REDIS_CONFIG,
)
from artascope.src.celery_app import app as celery_app
from artascope.src.util.prefix_redis import PrefixRedis
from artascope.src.exception import SlackSenderException


redis = PrefixRedis("slack", **REDIS_CONFIG)


def get_msg_block(channel_id, msg):
    return {
        "channel": channel_id,
        "text": msg.split("\n")[0],
        "blocks": [
            {"type": "context", "elements": [{"type": "mrkdwn", "text": msg}]},
            {"type": "divider"},
        ],
    }


def get_channel_id(client: slack.WebClient, channel: str = "dev"):
    # 获取channel_id
    channel_id = redis.hget("channel", channel)
    if channel_id is None:
        response = client.conversations_list(types="public_channel,private_channel")
        for one_channel in response["channels"]:
            redis.hset("channel", one_channel["name"], one_channel["id"])
            if one_channel["name"] == channel:
                channel_id = one_channel["id"]
        if channel_id is None:
            raise SlackSenderException("Channel {} not existed.".format(channel))
    else:
        channel_id = channel_id.decode("utf-8")
    return channel_id


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 5})
def send_message(
    token: str,
    msg: str,
    channel: str = "dev",
    msg_uuid=None,
    msg_generator: FunctionType = get_msg_block,
    callback: FunctionType = None,
    callback_params: dict = None,
):
    client = slack.WebClient(token=token)
    channel_id = get_channel_id(client, channel)

    if not msg_uuid:
        response = client.chat_postMessage(**msg_generator(channel_id, msg))

        assert (
            response["ok"] is True and response["ts"] is not None
        )  # raise error if not succeed
        msg_uuid = uuid.uuid4().hex
        msg_key = "msg:" + msg_uuid
        redis.setex(msg_key, REDIS_SLACK_MSG_EXPIRE, response["ts"])

    else:
        msg_key = "msg:" + msg_uuid
        ts = redis.get(msg_key)

        if not ts:  # 已经过期
            response = client.chat_postMessage(**get_msg_block(channel_id, msg))
            assert (
                response["ok"] is True and response["ts"] is not None
            )  # raise error if not succeed
            redis.setex(msg_key, REDIS_SLACK_MSG_EXPIRE, response["ts"])
        else:
            ts = ts.decode("utf-8")
            response = client.chat_update(ts=ts, **get_msg_block(channel_id, msg))
            assert (
                response["ok"] is True and response["ts"] is not None
            )  # raise error if not succeed
            redis.setex(msg_key, REDIS_SLACK_MSG_EXPIRE, response["ts"])

    if callback:
        callback(**callback_params)

    return msg_uuid
