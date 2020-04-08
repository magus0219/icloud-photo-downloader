#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/22
from celery import Celery
from celery.schedules import crontab
from artascope.src.config import (
    REDIS_CONFIG,
    TIMEZONE,
)
from artascope.src.util import get_logger

logger = get_logger("server.celery")

app = Celery(
    "artascope",
    broker="redis://{host}:{port}".format(**REDIS_CONFIG),
    backend="redis://{host}:{port}".format(**REDIS_CONFIG),
    include=[
        "artascope.src.util.slack_sender",
        "artascope.src.task.downloader",
        "artascope.src.task.post_action.sftp",
        "artascope.src.task.sync",
    ],
)

# Optional configuration, see the application user guide.
app.conf.update(
    timezone=TIMEZONE,
    result_expires=3600,
    task_serializer="pickle",
    result_serializer="pickle",
    accept_content=["json", "pickle"],
)

app.conf.beat_schedule = {
    "add-every-monday-morning": {
        "task": "bugsbunny.src.etl.job.future_update_info",
        "schedule": crontab(hour=20, minute=22),
        "args": (),
    }
}
