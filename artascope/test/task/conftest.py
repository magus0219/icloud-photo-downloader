#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/14
import pytest
import tempfile
from pathlib import Path
import http.cookiejar as cookielib
from collections import namedtuple
from pyicloud.services.photos import (
    PhotoAsset,
    PhotoAlbum,
)
from artascope.src.lib.auth_manager import (
    AuthManager,
    LoginStatus,
)
from artascope.src.lib.user_config_manager import ucm
from artascope.src.model.user_config import UserConfig
from artascope.test.conftest import MOCK_PHOTO_DATA

COOKIE = namedtuple("Cookie", ["name", "path", "domain"])


class MockPhotoService:
    @property
    def all(self):
        ab = PhotoAlbum(
            service=self,
            name="all",
            list_type=None,
            obj_type=None,
            direction="DESCENDING",
        )
        return ab


class MockPyiCloudSession:
    def __init__(self):
        self.headers = {}
        self.cookies = cookielib.CookieJar()
        cookie = COOKIE(name="X-APPLE-WEBAUTH-HSA-LOGIN", path=".", domain="icloud.com")
        self.cookies.set_cookie(cookie)


class MockPyiCloudService:
    def __init__(self, username, password, client_id):
        self.username = username
        self.password = password
        self.client_id = client_id

        self._service_endpoint = "mock_endpoint"
        self.params = {}
        self.session = MockPyiCloudSession()

    @property
    def photos(self):
        return MockPhotoService()

    def authenticate(self):
        return True

    def _get_cookiejar_path(self):
        return Path(tempfile.gettempdir()) / "test_cookie"

    def requires_2sa(self):
        return True


@pytest.fixture()
def set_user():
    uc = UserConfig(icloud_username="username", icloud_password="password",)
    ucm.save(uc)


@pytest.fixture()
def mock_login(monkeypatch):
    def mock_login(self):
        self._icloud_api = MockPyiCloudService(
            username="username", password="password", client_id="client_id"
        )
        return self._icloud_api

    monkeypatch.setattr(AuthManager, "login", mock_login)
