#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/30
from artascope.src.model.mixin import JsonDataMixin


class NotifyType:
    NONE = 0
    SLACK = 1


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
        admin_url_prefix=None,
        notify_type=None,
        slack_token=None,
        slack_channel=None,
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
