#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/16
REDIS_CONFIG = {
    "host": "redis",
    "port": 6379,
    "db": 0,
}

API_FILE_DOWNLOAD_CHUNK_SIZE = 8192 * 2

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
    },
    "loggers": {
        "server": {"handlers": ["console"], "level": "INFO", "propagate": False,},
    },
}
