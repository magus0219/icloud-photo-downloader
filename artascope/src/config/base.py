#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/22
ENV = ""  # will be set auto as filename in __init__
DEBUG = True

SLACK_TOKEN = (
    "xoxp-788823341621-776039979922-783917865361-5c7a03623068530dd3307507b067b459"
)
REDIS_SLACK_MSG_EXPIRE = 3600

REDIS_CONFIG = {
    "host": "localhost",
    "port": 6379,
}

USER_PASSWORD_MAP = {"magus0219@gmail.com": "LiuNian871209"}

TARGET = {
    "hostname": "192.168.50.118",
    "port": 2224,
    "username": "magus0219",
    "password": "boena0219",
}
TARGET_DIR = "Drive/Moments/Mobile/Magicqin"

BATCH_CNT = 100

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
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": "DEBUG",
            # 'class': 'logging.handlers.TimedRotatingFileHandler',
            "class": "logging.FileHandler",
            "formatter": "verbose",
            "filename": "{name}.log".format(name="server"),
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
