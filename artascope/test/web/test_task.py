#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/6
import pytest
import datetime
import sys
import json
from artascope.src.model.user_config import UserConfig
from artascope.src.lib.user_config_manager import ucm
from artascope.src.lib.task_manager import (
    tm,
    TaskRunType,
)
from artascope.src.util.date_util import DateTimeUtil
from artascope.test.conftest import DataException


@pytest.mark.web
class TestTask:
    def test_task_without_content(self, client):
        response = client.get("/task", follow_redirects=True)
        assert b"Task List" in response.data  # test jumbotron

    def test_task_with_all_task(self, client):
        uc = UserConfig("username", "password")
        ucm.save(uc)

        tm.add_task(
            task_name="task_name", username="username", run_type=TaskRunType.ALL
        )
        tm.update_task_total(task_name="task_name", total=100)

        response = client.get("/task/username", follow_redirects=True)
        # test jumbotron
        assert b"Task List" in response.data
        assert b"of username" in response.data

        # test info
        assert b"<td>1</td>" in response.data
        assert (
            b'<td><a href="/task/status/task_name">task_name</a></td>' in response.data
        )
        assert b"<td>All</td>" in response.data
        assert b"<td>Running</td>" in response.data
        assert b"<td>0 / 100</td>" in response.data

    def test_task_with_last_task(self, client):
        uc = UserConfig("username", "password")
        ucm.save(uc)

        tm.add_task(
            task_name="task_name",
            username="username",
            run_type=TaskRunType.LAST,
            last=200,
        )
        tm.update_task_total(task_name="task_name", total=100)

        response = client.get("/task/username", follow_redirects=True)
        # test jumbotron
        assert b"Task List" in response.data
        assert b"of username" in response.data

        # test info
        assert b"<td>1</td>" in response.data
        assert (
            b'<td><a href="/task/status/task_name">task_name</a></td>' in response.data
        )
        assert b"<td>Last</td>" in response.data
        assert b"<td>Running</td>" in response.data
        assert b"<td>0 / 100</td>" in response.data
        assert b"<td>200</td>" in response.data

    def test_task_with_date_range_task(self, client):
        uc = UserConfig("username", "password")
        ucm.save(uc)

        tm.add_task(
            task_name="task_name",
            username="username",
            run_type=TaskRunType.DATE_RANGE,
            date_start=int(
                DateTimeUtil.get_datetime_from_date_str("20200101").timestamp()
            ),
            date_end=int(
                DateTimeUtil.get_datetime_from_date_str("20200102").timestamp()
            ),
        )

        tm.update_task_total(task_name="task_name", total=100)

        response = client.get("/task/username", follow_redirects=True)

        # test jumbotron
        assert b"Task List" in response.data
        assert b"of username" in response.data

        # test info
        assert b"<td>1</td>" in response.data
        assert (
            b'<td><a href="/task/status/task_name">task_name</a></td>' in response.data
        )
        assert b"<td>Date Range</td>" in response.data
        assert b"<td>Running</td>" in response.data
        assert b"<td>0 / 100</td>" in response.data
        assert b"<td>2020-01-01 00:00:00 - 2020-01-02 00:00:00</td>" in response.data

    def test_task_fail(self, client, monkeypatch):
        def mock_check_fail(self, task_name):
            return True

        monkeypatch.setattr(tm, "check_fail", mock_check_fail.__get__(tm))

        uc = UserConfig("username", "password")
        ucm.save(uc)

        tm.add_task(
            task_name="task_name", username="username", run_type=TaskRunType.ALL
        )

        response = client.get("/task/username", follow_redirects=True)
        assert b"Fail" in response.data
        assert tm.get_current_task_name(username="username") is None

    def test_task_status(self, client, photos):
        uc = UserConfig("username", "password")
        ucm.save(uc)

        tm.add_task(
            task_name="task_name", username="username", run_type=TaskRunType.ALL
        )

        for photo in photos:
            tm.add_file_status(task_name="task_name", file=photo)

        tm.update_file_status(photos[0], 98.92)
        response = client.get("/task/status/task_name", follow_redirects=True)
        assert b"Task Status" in response.data
        for photo in photos:
            assert photo.id.encode() in response.data

        assert b"98.92%" in response.data

    def test_task_run_get(self, client):
        uc = UserConfig("username", "password")
        ucm.save(uc)

        response = client.get("/task/run/username", follow_redirects=True)

        # test jumbotron
        assert b"Run task" in response.data
        assert (
            b'<input class="form-check-input" type="radio" name="run_type" id="type_all" value=1 checked>'
            in response.data
        )

    def test_task_run_post(self, client, monkeypatch):
        uc = UserConfig("username", "password")
        ucm.save(uc)

        data = {"run_type": "1"}

        response = client.post("/task/run/username", data=data, follow_redirects=True)
        # test jumbotron
        assert b"Task List" in response.data
        assert b"of username" in response.data

    def test_task_run_post_all(self, client, monkeypatch):
        uc = UserConfig("username", "password")
        ucm.save(uc)

        data = {"run_type": "1"}

        class MockSync:
            def delay(
                self,
                username: str,
                password: str,
                last: int = None,
                date_start: datetime.date = None,
                date_end: datetime.date = None,
            ):
                raise DataException(
                    {"last": last, "date_start": date_start, "date_end": date_end}
                )

        monkeypatch.setattr(
            sys.modules["artascope.src.web.task"], "sync", MockSync(),
        )

        sync_params = {"last": None, "date_start": None, "date_end": None}
        with pytest.raises(
            DataException, match=json.dumps(sync_params, sort_keys=True)
        ):
            response = client.post(
                "/task/run/username", data=data, follow_redirects=True
            )

    def test_task_run_post_last(self, client, monkeypatch):
        uc = UserConfig("username", "password")
        ucm.save(uc)

        data = {"run_type": "2", "last_cnt": "200"}

        class MockSync:
            def delay(
                self,
                username: str,
                password: str,
                last: int = None,
                date_start: datetime.date = None,
                date_end: datetime.date = None,
            ):
                print(last, date_start, date_end)
                raise DataException(
                    {"last": last, "date_start": date_start, "date_end": date_end}
                )

        monkeypatch.setattr(
            sys.modules["artascope.src.web.task"], "sync", MockSync(),
        )

        sync_params = {"last": 200, "date_start": None, "date_end": None}
        with pytest.raises(
            DataException, match=json.dumps(sync_params, sort_keys=True)
        ):
            response = client.post(
                "/task/run/username", data=data, follow_redirects=True
            )

    def test_task_run_post_date_range(self, client, monkeypatch):
        uc = UserConfig("username", "password")
        ucm.save(uc)

        data = {"run_type": "3", "date_start": "20200101", "date_end": "20200102"}

        class MockSync:
            def delay(
                self,
                username: str,
                password: str,
                last: int = None,
                date_start: datetime.date = None,
                date_end: datetime.date = None,
            ):
                print(last, date_start, date_end)
                raise DataException(
                    {"last": last, "date_start": date_start, "date_end": date_end}
                )

        monkeypatch.setattr(
            sys.modules["artascope.src.web.task"], "sync", MockSync(),
        )

        sync_params = {
            "last": None,
            "date_start": DateTimeUtil.get_datetime_from_date_str(
                data["date_start"]
            ).timestamp(),
            "date_end": DateTimeUtil.get_datetime_from_date_str(
                data["date_end"]
            ).timestamp(),
        }
        with pytest.raises(
            DataException, match=json.dumps(sync_params, sort_keys=True)
        ):
            response = client.post(
                "/task/run/username", data=data, follow_redirects=True
            )
