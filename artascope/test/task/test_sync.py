#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/4
import datetime
import base64
import pytest
import sys
from pyicloud.exceptions import PyiCloudAPIResponseException
from pyicloud.services.photos import (
    PhotoAsset,
    PhotoAlbum,
)
from artascope.src.lib.task_manager import (
    tm,
    TaskRunType,
)
from artascope.src.lib.auth_manager import AuthManager
from artascope.src.lib.user_config_manager import ucm
from artascope.src.model.user_config import UserConfig
from artascope.src.util import get_logger
from artascope.src.task.sync import (
    sync,
    decide_run_type,
)
from artascope.src.exception import (
    NeedLoginAgainException,
    ApiLimitException,
)
from artascope.src.util.date_util import DateUtil
from artascope.test.conftest import MOCK_PHOTO_ASSET_DATA

logger = get_logger("test")


@pytest.fixture()
def set_user():
    uc = UserConfig(icloud_username="username", icloud_password="password",)
    ucm.save(uc)


class MockPhotoService:
    @property
    def all(self):
        return PhotoAlbum(
            service=self,
            name="all",
            list_type=None,
            obj_type=None,
            direction="DESCENDING",
        )


class MockPyiCloudService:
    def __init__(self, username, password, client_id):
        self.username = username
        self.password = password
        self.client_id = client_id

        self._service_endpoint = "mock_endpoint"
        self.params = {}
        self.session = {}

    @property
    def photos(self):
        return MockPhotoService()

    def authenticate(self):
        return True


class TestSync:
    def test_decide_run_type(self):
        assert decide_run_type() == TaskRunType.ALL
        assert decide_run_type(last=100) == TaskRunType.LAST
        assert decide_run_type(
            date_start=DateUtil.get_today(), date_end=DateUtil.get_today()
        )

    def test_sync(self, photos, set_user, monkeypatch, celery_app, celery_worker):
        def mock_login(self):
            return MockPyiCloudService(
                username="username", password="password", client_id="client_id"
            )

        monkeypatch.setattr(AuthManager, "login", mock_login)

        def mock_len(self):
            return len(MOCK_PHOTO_ASSET_DATA)

        monkeypatch.setattr(PhotoAlbum, "__len__", mock_len)

        def mock_fetch_photos(self, album_len, last, date_start, date_end):
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
        assert tm.load_task(task_name).cnt_total == len(MOCK_PHOTO_ASSET_DATA)

    def test_sync_with_need_login_again(self, monkeypatch):
        def mock_login(self):
            return MockPyiCloudService(
                username="username", password="password", client_id="client_id"
            )

        monkeypatch.setattr(AuthManager, "login", mock_login)

        def mock_len(self):
            return len(MOCK_PHOTO_ASSET_DATA)

        monkeypatch.setattr(PhotoAlbum, "__len__", mock_len)

        def mock_fetch_photos(self, album_len, last, date_start, date_end):
            raise PyiCloudAPIResponseException("Invalid global session")

        monkeypatch.setattr(
            sys.modules["artascope.src.patch.pyicloud"],
            "fetch_photos",
            mock_fetch_photos,
        )

        sync.apply(
            kwargs={"username": "username", "password": "password"},
            task_id="mock_test_id",
            throw=True,
        )

    def test_sync_with_api_limit(self, monkeypatch):
        def mock_login(self):
            return MockPyiCloudService(
                username="username", password="password", client_id="client_id"
            )

        monkeypatch.setattr(AuthManager, "login", mock_login)

        def mock_len(self):
            return len(MOCK_PHOTO_ASSET_DATA)

        monkeypatch.setattr(PhotoAlbum, "__len__", mock_len)

        def mock_fetch_photos(self, album_len, last, date_start, date_end):
            raise PyiCloudAPIResponseException(
                "private db access disabled for this account"
            )

        monkeypatch.setattr(
            sys.modules["artascope.src.patch.pyicloud"],
            "fetch_photos",
            mock_fetch_photos,
        )

        with pytest.raises(ApiLimitException):
            sync.apply(
                kwargs={"username": "username", "password": "password"},
                task_id="mock_test_id",
                throw=True,
            )

    def test_sync_with_api_exception(self, monkeypatch):
        def mock_login(self):
            return MockPyiCloudService(
                username="username", password="password", client_id="client_id"
            )

        monkeypatch.setattr(AuthManager, "login", mock_login)

        def mock_len(self):
            return len(MOCK_PHOTO_ASSET_DATA)

        monkeypatch.setattr(PhotoAlbum, "__len__", mock_len)

        def mock_fetch_photos(self, album_len, last, date_start, date_end):
            raise PyiCloudAPIResponseException("foo")

        monkeypatch.setattr(
            sys.modules["artascope.src.patch.pyicloud"],
            "fetch_photos",
            mock_fetch_photos,
        )

        with pytest.raises(PyiCloudAPIResponseException, match="foo"):
            sync.apply(
                kwargs={"username": "username", "password": "password"},
                task_id="mock_test_id",
                throw=True,
            )

    def test_sync_with_other_exception(self, monkeypatch):
        def mock_login(self):
            return MockPyiCloudService(
                username="username", password="password", client_id="client_id"
            )

        monkeypatch.setattr(AuthManager, "login", mock_login)

        def mock_len(self):
            return len(MOCK_PHOTO_ASSET_DATA)

        monkeypatch.setattr(PhotoAlbum, "__len__", mock_len)

        def mock_fetch_photos(self, album_len, last, date_start, date_end):
            raise Exception("foo")

        monkeypatch.setattr(
            sys.modules["artascope.src.patch.pyicloud"],
            "fetch_photos",
            mock_fetch_photos,
        )

        with pytest.raises(Exception, match="foo"):
            sync.apply(
                kwargs={"username": "username", "password": "password"},
                task_id="mock_test_id",
                throw=True,
            )
