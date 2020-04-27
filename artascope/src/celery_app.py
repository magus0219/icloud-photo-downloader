#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/22
from celery import Celery
from celery.schedules import crontab
from artascope.src.config import (
    REDIS_CONFIG,
    TZ,
)
from artascope.src.util import get_logger

logger = get_logger("server.celery")

app = Celery(
    "artascope",
    broker="redis://{host}:{port}/{db}".format(**REDIS_CONFIG),
    backend="redis://{host}:{port}/{db}".format(**REDIS_CONFIG),
    include=[
        "artascope.src.util.slack_sender",
        "artascope.src.util.email_sender",
        "artascope.src.task.downloader",
        "artascope.src.task.post_action.sftp",
        "artascope.src.task.sync",
    ],
)

# Optional configuration, see the application user guide.
app.conf.update(
    timezone=TZ,
    result_expires=3600,
    task_serializer="pickle",
    result_serializer="pickle",
    accept_content=["json", "pickle"],
    task_routes={
        "artascope.src.task.post_action.sftp.*": {"queue": "upload"},
        "artascope.src.util.slack_sender.*": {"queue": "msg"},
        "artascope.src.util.email_sender.*": {"queue": "msg"},
    },
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_transport_options={"visibility_timeout": 864000},
)

app.conf.beat_schedule = {
    "download-after-midnight": {
        "task": "artascope.src.task.sync",
        "schedule": crontab(hour=16, minute=30),
        "kwargs": {},
    }
}
