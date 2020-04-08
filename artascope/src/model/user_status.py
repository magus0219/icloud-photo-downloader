#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/30
import typing
from artascope.src.lib.task_manager import tm
from artascope.src.lib.auth_manager import AuthManager


class UserStatus:
    def __init__(self, username: str, created_ts: int):
        self.username = username
        self.created_ts = created_ts

    @property
    def current_task(self) -> typing.Union[str, None]:
        return tm.get_current_task_name(self.username)

    @property
    def login_status(self) -> typing.Union[int, None]:
        return AuthManager(self.username).get_login_status()
