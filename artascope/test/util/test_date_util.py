#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/26
import datetime
from artascope.src.util.date_util import (
    DateUtil,
    DateTimeUtil,
)


class TestDateUtil:
    def test_get_date_from_str(self):
        assert DateUtil.get_date_from_str("20200101") == datetime.date(
            year=2020, month=1, day=1
        )

    def test_get_today(self):
        assert DateUtil.get_today() == datetime.date.today()

    def test_get_yesterday(self):
        assert DateUtil.get_yesterday() == datetime.date.today() - datetime.timedelta(
            days=1
        )

    def test_get_str_from_date(self):
        assert (
            DateUtil.get_str_from_date(datetime.date(year=2020, month=1, day=1))
            == "2020-01-01"
        )

    def test_get_tomorrow(self):
        assert DateUtil.get_tomorrow() == datetime.date.today() + datetime.timedelta(
            days=1
        )

    def test_get_date_from_timestamp(self):
        assert DateUtil.get_date_from_timestamp(
            datetime.datetime(year=2020, month=1, day=1).timestamp()
        ) == datetime.date(year=2020, month=1, day=1)

    def test_get_datetime_from_str(self):
        assert DateTimeUtil.get_datetime_from_str(
            "2020-01-01 01:01:01"
        ) == datetime.datetime(year=2020, month=1, day=1, hour=1, minute=1, second=1)

    def test_get_datetime_from_date_str(self):
        assert DateTimeUtil.get_datetime_from_date_str("20200101") == datetime.datetime(
            year=2020, month=1, day=1, hour=0, minute=0, second=0
        )

    def test_get_str_from_datetime(self):
        assert (
            DateTimeUtil.get_str_from_datetime(
                datetime.datetime(year=2020, month=1, day=1, hour=0, minute=0, second=0)
            )
            == "2020-01-01 00:00:00"
        )

    def test_get_datetime_from_timestamp(self):
        assert DateTimeUtil.get_datetime_from_timestamp(
            datetime.datetime(year=2020, month=1, day=1).timestamp()
        ) == datetime.datetime(year=2020, month=1, day=1, hour=0, minute=0, second=0)

    def test_get_datetime_from_date(self):
        assert DateTimeUtil.get_datetime_from_date(
            datetime.date(year=2020, month=1, day=1)
        ) == datetime.datetime(year=2020, month=1, day=1, hour=0, minute=0, second=0)
