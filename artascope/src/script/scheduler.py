#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/17
import pytz
import datetime
import typing
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from artascope.src.lib.scheduler_manager import sm
from artascope.src.config import (
    REDIS_CONFIG,
    TIMEZONE,
    SECONDS_SLEEP_SCHEDULER,
)
from artascope.src.task.sync import sync
from artascope.src.lib.user_config_manager import ucm
from artascope.src.model.user_config import SchedulerEnable
from artascope.src.util.date_util import DateUtil
from artascope.src.util import get_logger

logger = get_logger("server.scheduler")

tz = pytz.timezone(TIMEZONE)

jobstores = {"default": RedisJobStore(**REDIS_CONFIG)}
executors = {
    "default": ThreadPoolExecutor(5),
}
job_defaults = {"coalesce": False, "max_instances": 3}
scheduler = BackgroundScheduler(
    jobstores=jobstores, executors=executors, job_defaults=job_defaults, timezone=tz,
)

CRON_ELEMENTS = ["minute", "hour", "day", "month", "day_of_week"]


def trigger_sync_task(username: str) -> bool:
    """Workload function scheduler triggered

    :param username:
    :param last:
    :return:
    """
    try:
        user_setting = ucm.load(username)

        if user_setting and user_setting.scheduler_enable == SchedulerEnable.Enable:
            date_start = DateUtil.get_today() - datetime.timedelta(
                days=user_setting.scheduler_last_day_cnt
            )
            sync.delay(
                username=user_setting.icloud_username,
                password=user_setting.icloud_password,
                date_start=date_start,
            )
            logger.info("trigger sync task of {username}".format(username=username))
            return True
        else:
            return False
    except Exception as e:
        logger.exception(e)
        raise


def extract_cron_expression(expr: str) -> dict:
    """Extract elements from cron expression to form param dict

    :param expr:
    :return:
    """
    return dict(zip(CRON_ELEMENTS, expr.split(" ")))


def update_user_job(username: str) -> typing.Union[None, str]:
    """Remove job of user then add new one

    Restrict: Each User has only one scheduler job

    :param username:
    :return:
    """
    existed_job_id = sm.get_job_id(username=username)
    if existed_job_id:
        scheduler.remove_job(existed_job_id)
        sm.del_job(username=username)

    user_setting = ucm.load(username)
    if user_setting and user_setting.scheduler_enable == SchedulerEnable.Enable:
        trigger = CronTrigger(
            **extract_cron_expression(user_setting.scheduler_crontab), timezone=tz
        )
        job = scheduler.add_job(
            func=trigger_sync_task, trigger=trigger, kwargs={"username": username,}
        )
        sm.add_job(username, job.id)
        return job.id
    else:
        return None


def export_job_info():
    sm.save_job_info(scheduler)


def start():
    scheduler.start()

    fail_user = []
    while True:
        username = sm.get_one_user()
        while username:
            try:
                update_user_job(username)
                export_job_info()
                logger.info("handle {username} done".format(username=username))
            except Exception as e:
                fail_user.append(username)
                logger.info("handle {username} fail".format(username=username))
            username = sm.get_one_user()
        else:
            for one_fail in fail_user:
                sm.add_user(one_fail)
            fail_user = []
            time.sleep(SECONDS_SLEEP_SCHEDULER)
            export_job_info()
            logger.debug("sleep done...")


if __name__ == "__main__":  # pragma: no cover
    logger.info("Scheduler start...")
    start()
