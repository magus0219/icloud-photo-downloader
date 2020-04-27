#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/30
from artascope.src.model.mixin import JsonDataMixin


class NotifyType:
    NONE = 0
    SLACK = 1
    EMAIL = 2


class TargetType:
    SFTP = 1


class SchedulerEnable:
    Disable = 0
    Enable = 1


class ReindexEnable:
    Disable = 0
    Enable = 1


class UserConfig(JsonDataMixin):
    def __init__(
        self,
        icloud_username: str,
        icloud_password: str,
        target_type: int = TargetType.SFTP,
        sftp_host: str = None,
        sftp_port: int = None,
        sftp_username: str = None,
        sftp_password: str = None,
        sftp_dir: str = None,
        reindex_enable: int = ReindexEnable.Disable,
        sftp_home: str = None,
        admin_url_prefix: str = None,
        notify_type: int = NotifyType.NONE,
        slack_token: str = None,
        slack_channel: str = None,
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_user: str = None,
        smtp_password: str = None,
        msg_from: str = None,
        msg_to: str = None,
        scheduler_enable: int = SchedulerEnable.Disable,
        scheduler_crontab: str = None,
        scheduler_last_day_cnt: int = None,
    ):
        self.icloud_username = icloud_username
        self.icloud_password = icloud_password

        self.target_type = target_type

        self.sftp_host = sftp_host
        self.sftp_port = sftp_port
        self.sftp_username = sftp_username
        self.sftp_password = sftp_password
        self.sftp_dir = sftp_dir
        self.reindex_enable = reindex_enable
        self.sftp_home = sftp_home

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

        self.scheduler_enable = scheduler_enable
        self.scheduler_crontab = scheduler_crontab
        self.scheduler_last_day_cnt = scheduler_last_day_cnt
