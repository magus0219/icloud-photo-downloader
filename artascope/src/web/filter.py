#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/25
import datetime


def unixtime_to_str(val, format_str="%Y-%m-%d %H:%M:%S"):
    return datetime.datetime.fromtimestamp(val).strftime(format_str)
