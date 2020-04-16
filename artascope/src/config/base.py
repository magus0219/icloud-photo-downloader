#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/22
ENV = ""  # will be set auto as filepath in __init__
DEBUG = True

SLACK_TOKEN = (
    "xoxp-788823341621-776039979922-783917865361-5c7a03623068530dd3307507b067b459"
)
REDIS_SLACK_MSG_EXPIRE = 3600

REDIS_CONFIG = {
    "host": "localhost",
    "port": 6379,
    "db": 0,
}

USER_PASSWORD_MAP = {"magus0219@gmail.com": "LiuNian871209"}

TARGET = {
    "hostname": "192.168.50.118",
    "port": 2224,
    "username": "magus0219",
    "password": "boena0219",
}
TARGET_DIR = "Drive/Moments/Mobile/iphone"

BATCH_CNT = 200

API_FILE_DOWNLOAD_CHUNK_SIZE = 8192
API_LATCH_LIMIT_PER_MINUTE = 6
API_PAGE_SIZE = 200

SECONDS_WAIT_FOR_API_LIMIT = 600
SECONDS_WAIT_AFTER_LOGIN_FAIL = 60
SECONDS_WAIT_LOGIN = 60 * 15

TIMEZONE = "Asia/Shanghai"

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
