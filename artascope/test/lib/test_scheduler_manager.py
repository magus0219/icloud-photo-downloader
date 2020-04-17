#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/17
from apscheduler.triggers.cron import CronTrigger
from artascope.src.lib.scheduler_manager import sm
from artascope.src.script.scheduler import (
    scheduler,
    extract_cron_expression,
)


class TestSchedulerManager:
    def test_get_user_cnt(self):
        assert sm.get_user_cnt() == 0

    def test_get_users_black(self):
        assert sm.get_one_user() is None

    def test_add_user(self):
        sm.add_user("username")
        assert sm.get_one_user() == "username"
        assert sm.get_one_user() is None

    def test_add_multi_user(self):
        sm.add_user("username1")
        sm.add_user("username2")
        assert sm.get_user_cnt() == 2

        one = sm.get_one_user()
        assert one is not None
        assert one in ["username1", "username2"]
        assert sm.get_user_cnt() == 1

    def test_get_job_id_not_existed_user(self):
        assert sm.get_job_id(username="not_existed") is None

    def test_add_job(self):
        sm.add_job("username", "jobid")
        assert sm.get_job_id(username="username") == "jobid"

    def test_del_job(self):
        sm.add_job("username", "jobid")
        assert sm.get_job_id(username="username") == "jobid"
        sm.del_job("username")

    def test_get_job_info_without_info(self):
        assert sm.get_job_info() is None

    def test_save_job_info(self):
        def mock_task(abc):
            return True

        scheduler.add_job(
            func=mock_task,
            trigger=CronTrigger(**extract_cron_expression("0 */4 * * *")),
            kwargs={"abc": 10},
        )

        sm.save_job_info(scheduler)

        assert sm.get_job_info() == [
            "TestSchedulerManager.test_save_job_info.<locals>.mock_task (trigger: cron[month='*', day='*', day_of_week='*', hour='*/4', minute='0'], pending) kwargs:{'abc': 10}"
        ]
