#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/23
import datetime


class DateUtil:
    @classmethod
    def get_date_from_str(cls, date_str):
        return datetime.datetime.strptime(date_str, "%Y%m%d").date()

    @classmethod
    def get_today(cls):
        return datetime.date.today()

    @classmethod
    def get_yesterday(cls):
        return datetime.date.today() - datetime.timedelta(days=1)

    @classmethod
    def get_str_from_date(cls, date_obj):
        return date_obj.strftime("%Y-%m-%d")

    @classmethod
    def get_tomorrow(cls):
        return datetime.date.today() + datetime.timedelta(days=1)

    @classmethod
    def get_date_from_timestamp(cls, timestamp: int):
        return datetime.datetime.fromtimestamp(timestamp).date()


class DateTimeUtil:
    @classmethod
    def get_datetime_from_str(cls, date_str):
        return datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")

    @classmethod
    def get_datetime_from_date_str(cls, date_str):
        return datetime.datetime.strptime(date_str, "%Y%m%d")

    @classmethod
    def get_str_from_datetime(cls, datetime_obj):
        return datetime.datetime.strftime(datetime_obj, "%Y-%m-%d %H:%M:%S")

    @classmethod
    def get_now(cls):  # pragma: no cover
        return datetime.datetime.now()

    @classmethod
    def get_datetime_from_timestamp(cls, timestamp):
        return datetime.datetime.fromtimestamp(timestamp)

    @classmethod
    def get_datetime_from_date(cls, date):
        return datetime.datetime.fromordinal(date.toordinal())
