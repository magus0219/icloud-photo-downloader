#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/3
REDIS_CONFIG = {
    "host": "localhost",
    "port": 6379,
    "db": 1,
}

API_LATCH_LIMIT_PER_MINUTE = 30

API_FILE_DOWNLOAD_CHUNK_SIZE = 4

SECONDS_WAIT_AFTER_SEND_CAPTCHA = 1
SECONDS_WAIT_FOR_API_LIMIT = 1

BATCH_CNT = 2

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
            "filename": "dev.log",
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
