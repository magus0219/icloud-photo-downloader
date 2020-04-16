#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/30
from typing import List
from artascope.src.model.mixin import JsonDataMixin


class NotifyType:
    NONE = 0
    SLACK = 1
    EMAIL = 2


class TargetType:
    SFTP = 1


class UserConfig(JsonDataMixin):
    def __init__(
        self,
        icloud_username: str,
        icloud_password: str,
        target_type: int = None,
        sftp_host: str = None,
        sftp_port: int = None,
        sftp_username: str = None,
        sftp_password: str = None,
        sftp_dir: str = None,
        admin_url_prefix: str = None,
        notify_type: int = None,
        slack_token: str = None,
        slack_channel: str = None,
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_user: str = None,
        smtp_password: str = None,
        msg_from: str = None,
        msg_to: str = None,
    ):
        self.icloud_username = icloud_username
        self.icloud_password = icloud_password

        self.target_type = target_type

        self.sftp_host = sftp_host
        self.sftp_port = sftp_port
        self.sftp_username = sftp_username
        self.sftp_password = sftp_password
        self.sftp_dir = sftp_dir

        self.admin_url_prefix = admin_url_prefix
        self.notify_type = notify_type
        self.slack_token = slack_token
        self.slack_channel = slack_channel

        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.msg_from = msg_from
        self.msg_to = msg_to

    def set_target_sftp(
        self, host: str, port: int, username: str, password: str, sftp_dir: str
    ) -> None:
        self.target_type = TargetType.SFTP
        self.sftp_host = host
        self.sftp_port = port
        self.sftp_username = username
        self.sftp_password = password
        self.sftp_dir = sftp_dir

    def set_nofity_slack(self, slack_token: str, slack_channel: str):
        self.notify_type = NotifyType.SLACK
        self.slack_token = slack_token
        self.slack_channel = slack_channel

    def set_notify_email(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        msg_from: str,
        msg_to: List[str],
    ):
        self.notify_type = NotifyType.EMAIL
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.msg_from = msg_from
        self.msg_to = msg_to
