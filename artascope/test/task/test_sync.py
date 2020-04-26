#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/4
import pytest
import sys
from pyicloud.exceptions import PyiCloudAPIResponseException
from artascope.src.lib.task_manager import (
    tm,
    TaskRunType,
    TaskStatus,
)
from artascope.src.util import get_logger
from artascope.src.task.sync import (
    sync,
    decide_run_type,
)
from artascope.src.exception import (
    NeedLoginAgain,
    ApiLimitExceed,
    LoginTimeout,
)
from artascope.src.util.date_util import DateUtil
from artascope.test.conftest import MOCK_PHOTO_DATA

logger = get_logger("test")


@pytest.fixture()
def mock_calculate_offset_and_cnt(monkeypatch):
    def mock_calculate_offset_and_cnt(self, last=None, date_start=None, date_end=None):
        return len(MOCK_PHOTO_DATA) - 1, len(MOCK_PHOTO_DATA)

    monkeypatch.setattr(
        sys.modules["artascope.src.patch.pyicloud"],
        "calculate_offset_and_cnt",
        mock_calculate_offset_and_cnt,
    )


@pytest.fixture()
def mock_calculate_offset_and_cnt_no_photo(monkeypatch):
    def mock_calculate_offset_and_cnt(self, last=None, date_start=None, date_end=None):
        return 0, 0

    monkeypatch.setattr(
        sys.modules["artascope.src.patch.pyicloud"],
        "calculate_offset_and_cnt",
        mock_calculate_offset_and_cnt,
    )


class TestSync:
    def test_decide_run_type(self):
        assert decide_run_type() == TaskRunType.ALL
        assert decide_run_type(last=100) == TaskRunType.LAST
        assert decide_run_type(
            date_start=DateUtil.get_today(), date_end=DateUtil.get_today()
        )

    def test_sync(
        self,
        photos,
        set_user,
        monkeypatch,
        mock_login,
        mock_calculate_offset_and_cnt,
        celery_app,
        celery_worker,
    ):
        def mock_fetch_photos(self, offset, cnt):
            return photos

        monkeypatch.setattr(
            sys.modules["artascope.src.patch.pyicloud"],
            "fetch_photos",
            mock_fetch_photos,
        )

        task_name = celery_app.send_task(
            "artascope.src.task.sync.sync",
            kwargs={"username": "username", "password": "password"},
        ).get(10)

        assert len(tm.get_celery_task_id(task_name)) == 3
        assert tm.load_task(task_name).cnt_total == len(MOCK_PHOTO_DATA)

    def test_sync_with_need_login_again(
        self, monkeypatch, mock_login, mock_calculate_offset_and_cnt
    ):
        def mock_fetch_photos(self, offset, cnt):
            raise PyiCloudAPIResponseException("Invalid global session")

        monkeypatch.setattr(
            sys.modules["artascope.src.patch.pyicloud"],
            "fetch_photos",
            mock_fetch_photos,
        )

        with pytest.raises(NeedLoginAgain):
            sync.apply(
                kwargs={"username": "username", "password": "password"}, throw=True,
            )

    def test_sync_with_api_limit(
        self, monkeypatch, mock_login, mock_calculate_offset_and_cnt
    ):
        def mock_fetch_photos(self, offset, cnt):
            raise PyiCloudAPIResponseException(
                "private db access disabled for this account"
            )

        monkeypatch.setattr(
            sys.modules["artascope.src.patch.pyicloud"],
            "fetch_photos",
            mock_fetch_photos,
        )

        with pytest.raises(ApiLimitExceed):
            sync.apply(
                kwargs={"username": "username", "password": "password"}, throw=True,
            )

    def test_sync_with_api_exception(
        self, monkeypatch, mock_login, mock_calculate_offset_and_cnt
    ):
        def mock_fetch_photos(self, offset, cnt):
            raise PyiCloudAPIResponseException("foo")

        monkeypatch.setattr(
            sys.modules["artascope.src.patch.pyicloud"],
            "fetch_photos",
            mock_fetch_photos,
        )

        with pytest.raises(PyiCloudAPIResponseException, match="foo"):
            sync.apply(
                kwargs={"username": "username", "password": "password"}, throw=True,
            )

    def test_sync_with_other_exception(
        self, monkeypatch, mock_login, mock_calculate_offset_and_cnt
    ):
        def mock_fetch_photos(self, offset, cnt):
            raise Exception("foo")

        monkeypatch.setattr(
            sys.modules["artascope.src.patch.pyicloud"],
            "fetch_photos",
            mock_fetch_photos,
        )

        with pytest.raises(Exception, match="foo"):
            sync.apply(
                kwargs={"username": "username", "password": "password"}, throw=True,
            )

    def test_sync_with_login_timeout(self, mock_login_captcha_wrong):
        with pytest.raises(LoginTimeout,):
            sync.apply(
                kwargs={"username": "username", "password": "password"}, throw=True,
            )

    def test_no_photo_need_download(
        self,
        monkeypatch,
        mock_login,
        mock_calculate_offset_and_cnt_no_photo,
        celery_app,
        celery_worker,
    ):
        def mock_fetch_photos(self, offset, cnt):
            return []

        monkeypatch.setattr(
            sys.modules["artascope.src.patch.pyicloud"],
            "fetch_photos",
            mock_fetch_photos,
        )

        task_name = celery_app.send_task(
            "artascope.src.task.sync.sync",
            kwargs={"username": "username", "password": "password"},
        ).get(10)

        assert tm.load_task(task_name=task_name).status == TaskStatus.SUCCESS
        assert tm.get_current_task_name("username") is None
