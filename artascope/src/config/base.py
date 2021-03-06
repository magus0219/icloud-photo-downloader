#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/22
ENV = ""  # will be set auto as filepath in __init__
DEBUG = True

REDIS_SLACK_MSG_EXPIRE = 3600

REDIS_CONFIG = {
    "host": "localhost",
    "port": 6379,
    "db": 0,
}

BATCH_CNT = 200

API_FILE_DOWNLOAD_CHUNK_SIZE = 8192
API_LATCH_LIMIT_PER_MINUTE = 6
API_PAGE_SIZE = 200

SECONDS_WAIT_FOR_API_LIMIT = 1800
SECONDS_WAIT_AFTER_LOGIN_FAIL = 60
SECONDS_WAIT_LOGIN = 60 * 15

SECONDS_SLEEP_SCHEDULER = 30

TZ = "Asia/Shanghai"

LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "generic": {
            "format": "%(asctime)s [%(process)d] [%(levelname)s] %(name)s: %(message)s",
        },
        "verbose": {
            "format": "[%(process)s][%(thread)d][%(levelname)s][%(module)s][%(lineno)d]%(asctime)s %(name)s:%(message)s"
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "DEBUG",
            # 'class': 'logging.handlers.TimedRotatingFileHandler',
            "class": "logging.FileHandler",
            "formatter": "verbose",
            "filename": "server.log",
            # 'when': 'D',
            # 'backupCount': 7,
            "encoding": "utf8",
        },
    },
    "loggers": {
        "server": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}
