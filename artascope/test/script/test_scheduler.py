#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/17
import pytest
import datetime
import sys
import json
import time
from artascope.src.script.scheduler import (
    extract_cron_expression,
    CRON_ELEMENTS,
    trigger_sync_task,
    update_user_job,
    scheduler,
    start,
)
from artascope.src.model.user_config import (
    UserConfig,
    SchedulerEnable,
)
from artascope.src.lib.user_config_manager import ucm
from artascope.src.lib.scheduler_manager import sm
from artascope.src.util.date_util import DateUtil
from artascope.test.conftest import (
    DataException,
    CustomEncoder,
)


@pytest.fixture()
def set_user_enable():
    uc = UserConfig(
        icloud_username="username",
        icloud_password="password",
        scheduler_enable=SchedulerEnable.Enable,
        scheduler_last_day_cnt=2,
        scheduler_crontab="0 1 * * *",
    )
    ucm.save(uc)


@pytest.fixture()
def set_user_disable():
    uc = UserConfig(
        icloud_username="username",
        icloud_password="password",
        scheduler_enable=SchedulerEnable.Disable,
        scheduler_last_day_cnt=2,
    )
    ucm.save(uc)


class TestScheduler:
    def test_extract_cron_expression(self):
        expr = "11 * */2 1 3"
        rlt = extract_cron_expression(expr)

        for idx, one in enumerate(CRON_ELEMENTS):
            assert one in rlt
            assert rlt[one] == expr.split(" ")[idx]

    def test_trigger_sync_task_without_user(self):
        assert trigger_sync_task(username="not_existed") is False

    def test_trigger_sync_task_disable_scheduler(self, set_user_disable):
        assert trigger_sync_task(username="username") is False

    def test_trigger_sync_task_enable_scheduler(self, set_user_enable, monkeypatch):
        class MockSync:
            def delay(
                self,
                username: str,
                password: str,
                last: int = None,
                date_start: datetime.date = None,
                date_end: datetime.date = None,
            ):
                raise DataException(
                    {"last": last, "date_start": date_start, "date_end": date_end}
                )

        monkeypatch.setattr(
            sys.modules["artascope.src.script.scheduler"], "sync", MockSync(),
        )

        sync_params = {
            "last": None,
            "date_start": DateUtil.get_today() - datetime.timedelta(days=2),
            "date_end": None,
        }
        with pytest.raises(
            DataException,
            match=json.dumps(sync_params, sort_keys=True, cls=CustomEncoder),
        ):
            assert trigger_sync_task(username="username") is False

    def test_update_user_job_not_existed(self):
        assert update_user_job(username="not_existed") is None
        assert sm.get_job_id(username="not_existed") is None

    def test_update_user_job_disable_scheduler(self, set_user_disable):
        assert update_user_job(username="username") is None
        assert sm.get_job_id(username="not_existed") is None

    def test_update_user_job_enable_scheduler(self, set_user_enable):
        job_id = update_user_job(username="username")
        assert sm.get_job_id(username="username") == job_id

    def test_start_no_user(self, monkeypatch):
        def mock_start(self):
            return True

        monkeypatch.setattr(scheduler, "start", mock_start.__get__(scheduler))

        def mock_time_sleep(seconds):
            raise DataException({"msg": "sleep"})

        monkeypatch.setattr(time, "sleep", mock_time_sleep)

        data = {"msg": "sleep"}
        with pytest.raises(DataException, match=json.dumps(data, sort_keys=True)):
            assert start()

    def test_start_user_exception(self, monkeypatch, set_user_enable):
        def mock_start(self):
            return True

        monkeypatch.setattr(scheduler, "start", mock_start.__get__(scheduler))

        def mock_time_sleep(seconds):
            raise DataException({"msg": "sleep"})

        monkeypatch.setattr(time, "sleep", mock_time_sleep)

        def mock_update_user_job(username):
            raise Exception({"error"})

        monkeypatch.setattr(
            sys.modules["artascope.src.script.scheduler"],
            "update_user_job",
            mock_update_user_job,
        )

        sm.add_user("username")

        data = {"msg": "sleep"}
        with pytest.raises(DataException, match=json.dumps(data, sort_keys=True)):
            assert start()
        assert sm.get_user_cnt() == 1
