#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/26
import urllib.parse
from apscheduler.triggers.cron import CronTrigger
from artascope.src.script.scheduler import (
    scheduler,
    extract_cron_expression,
)

from artascope.src.lib.scheduler_manager import sm


class TestScheduler:
    def test_get(self, client):
        def mock_task(abc):
            return True

        scheduler.add_job(
            func=mock_task,
            trigger=CronTrigger(**extract_cron_expression("0 */4 * * *")),
            kwargs={"abc": 10},
        )

        sm.save_job_info(scheduler)

        response = client.get("/scheduler", follow_redirects=True,)
        assert b"mock_task" in response.data
