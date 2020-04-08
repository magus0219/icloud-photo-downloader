#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/30
import datetime
from artascope.src.lib.user_status_manager import usm


class TestUserStatusManager:
    def test_add_user(self):
        usm.add_user(username="username")

        us = usm.get_user(username="username")
        assert (
            us.username == "username"
            and type(us.created_ts) == int
            and us.created_ts < datetime.datetime.now().timestamp()
        )

    def test_add_existed_user(self):
        usm.add_user(username="username")
        usm.add_user(username="username")

        us_list = usm.get_all_user()
        assert len(us_list) == 1

    def test_get_user(self):
        assert usm.get_user("not_exist") is None

        usm.add_user(username="username")
        assert usm.get_user("username").username == "username"

    def test_exist_user(self):
        assert usm.exist_user("not_exist") is False

        usm.add_user(username="username")
        assert usm.exist_user("username") is True

    def test_get_all_user(self):
        assert usm.get_all_user() is None

        usm.add_user(username="username1")
        usm.add_user(username="username2")

        us_list = usm.get_all_user()
        assert us_list[0].username == "username1"
        assert us_list[1].username == "username2"
        assert len(us_list) == 2

    def test_add_dup_user(self):
        usm.add_user(username="username")
        usm.add_user(username="username")
        us_list = usm.get_all_user()
        assert len(us_list) == 1
