#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/30
import pytest
from artascope.src.model.user_status import UserStatus
from artascope.src.exception import UserConfigNotExisted


class TestUserStatus:
    def test_init_user_status(self):
        us = UserStatus("username", 1300000000)
        assert us.current_task is None
        with pytest.raises(UserConfigNotExisted, match="username not existed"):
            assert us.login_status is None
