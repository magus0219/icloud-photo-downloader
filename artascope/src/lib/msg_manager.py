#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/14
from artascope.src.lib.user_config_manager import ucm
from artascope.src.model.user_config import NotifyType
from artascope.src.util.slack_sender import send_message as send_slack_message
from artascope.src.util.email_sender import send_message as send_email_message


class MsgManager:
    @staticmethod
    def send_message(username: str, msg: str):
        user_setting = ucm.load(username)

        if not user_setting:
            return
        else:
            notify_type = user_setting.notify_type

            if notify_type == NotifyType.SLACK:
                send_slack_message.delay(
                    token=user_setting.slack_token,
                    channel=user_setting.slack_channel,
                    msg=msg,
                )
            elif notify_type == NotifyType.EMAIL:
                send_email_message.delay(
                    smtp_host=user_setting.smtp_host,
                    smtp_port=user_setting.smtp_port,
                    smtp_user=user_setting.smtp_user,
                    smtp_password=user_setting.smtp_password,
                    msg_from=user_setting.msg_from,
                    msg_to=user_setting.msg_to.split(";"),
                    msg=msg,
                )
