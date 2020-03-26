#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/22
import logging.config
from artascope.src.config import LOG_CONFIG


def get_logger(name):
    logging.config.dictConfig(LOG_CONFIG)
    return logging.getLogger(name)
