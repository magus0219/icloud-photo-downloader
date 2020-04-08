#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/30
from artascope.src.model.user_config import UserConfig
from artascope.src.lib.user_config_manager import ucm
from artascope.src.lib.user_status_manager import usm


class TestUserConfigManager:
    def test_save(self):
        uc = UserConfig("username", "password")
        ucm.save(uc)
        assert usm.exist_user("username") is True
        obj = ucm.load("username")
        assert obj == uc
