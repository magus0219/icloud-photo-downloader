#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/3
import tempfile
import os
import pytest
import socket
import sys
import http.cookiejar as cookielib
from collections import namedtuple
from pathlib import Path
import pyicloud
from pyicloud.services.photos import PhotoAsset
from requests.exceptions import ConnectionError
from pyicloud.exceptions import (
    PyiCloudAPIResponseException,
    PyiCloudServiceNotActivatedException,
)
from artascope.src.lib.auth_manager import (
    AuthManager,
    LoginStatus,
)
from artascope.src.task.downloader import (
    download_file,
    download_photo,
    tempdir,
)
from artascope.src.lib.task_manager import (
    tm,
    TaskStatus,
)
from artascope.src.lib.user_config_manager import ucm
from artascope.src.model.user_config import UserConfig
from artascope.src.exception import (
    NeedLoginAgainException,
    ApiLimitException,
    NeedWaitForCaptchaException,
)
from artascope.src.util import get_logger


logger = get_logger("test")


class MockPyicloudSession:
    def __init__(self):
        self.headers = {}


class MockPyicloudService:
    def __init__(self):
        self.session = MockPyicloudSession()


def mock_update_file_status(self, photo, status):
    return True


temp_dir = tempfile.gettempdir()
temp_file = Path(temp_dir) / "testsrc"
tgt_filepath = Path(temp_dir) / "tgt_test"
file_size = 3 * 1024


@pytest.fixture()
def prepare_photo():

    if temp_file.exists():
        Path.unlink(temp_file)
    with open(temp_file, "w") as f:
        f.write("abc" * 1024)

    if tgt_filepath.exists():
        Path.unlink(tgt_filepath)

    yield PhotoAsset(service=MockPyicloudService(), master_record={}, asset_record={})

    Path.unlink(temp_file)
    Path.unlink(tgt_filepath)


COOKIE = namedtuple("Cookie", ["name", "path", "domain"])


class MockPyiCloudSession:
    def __init__(self):
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
        return {}

    def authenticate(self):
        return True

    def _get_cookiejar_path(self):
        return Path(tempfile.gettempdir()) / "test_cookie"


@pytest.fixture()
def set_not_existed_tempdir(monkeypatch):
    tempdir = Path(tempfile.gettempdir()) / "really_not_existed"
    monkeypatch.setattr(
        sys.modules["artascope.src.task.downloader"], "tempdir", tempdir
    )
    yield
    if tempdir.exists():
        Path.rmdir(tempdir)


@pytest.fixture()
def set_user():
    uc = UserConfig(icloud_username="username", icloud_password="password",)
    ucm.save(uc)


class TestDownloader:
    def test_download_file(self, prepare_photo, monkeypatch):
        photo = prepare_photo

        def download(class_instance, timeout=None):
            class downloader:
                def iter_content(self, chunk_size):
                    offset = int(
                        class_instance._service.session.headers["Range"]
                        .split("=")[1]
                        .split("-")[0]
                    )
                    with open(temp_file, "rb") as f:
                        f.seek(offset)
                        content = f.read(chunk_size)
                        while content:
                            yield content
                            content = f.read(chunk_size)
                            offset += len(content)

            return downloader()

        monkeypatch.setattr(photo, "download", download.__get__(photo))
        monkeypatch.setattr(
            tm, "update_file_status", mock_update_file_status.__get__(tm)
        )

        download_file(photo=photo, filepath=tgt_filepath, file_size=file_size)
        assert os.stat(tgt_filepath).st_size == file_size
        assert open(tgt_filepath).read() == "abc" * 1024
        assert "Range" not in photo._service.session.headers

    def test_download_file_connection_error(self, prepare_photo, monkeypatch):
        photo = prepare_photo

        def download(class_instance, timeout=None):
            class downloader:
                def iter_content(self, chunk_size):
                    offset = int(
                        class_instance._service.session.headers["Range"]
                        .split("=")[1]
                        .split("-")[0]
                    )
                    with open(temp_file, "rb") as f:
                        f.seek(offset)
                        content = f.read(chunk_size)
                        while content:
                            yield content
                            content = f.read(chunk_size)
                            offset += len(content)

                            if offset > 100:
                                raise ConnectionError

            return downloader()

        monkeypatch.setattr(photo, "download", download.__get__(photo))
        monkeypatch.setattr(
            tm, "update_file_status", mock_update_file_status.__get__(tm)
        )

        download_file(photo=photo, filepath=tgt_filepath, file_size=file_size)
        assert os.stat(tgt_filepath).st_size == file_size
        assert open(tgt_filepath).read() == "abc" * 1024
        assert "Range" not in photo._service.session.headers

    def test_download_file_socket_error(self, prepare_photo, monkeypatch):
        photo = prepare_photo

        def download(class_instance, timeout=None):
            class downloader:
                def iter_content(self, chunk_size):
                    offset = int(
                        class_instance._service.session.headers["Range"]
                        .split("=")[1]
                        .split("-")[0]
                    )
                    with open(temp_file, "rb") as f:
                        f.seek(offset)
                        content = f.read(chunk_size)
                        while content:
                            yield content
                            content = f.read(chunk_size)
                            offset += len(content)

                            if offset > 100:
                                raise socket.timeout

            return downloader()

        monkeypatch.setattr(photo, "download", download.__get__(photo))
        monkeypatch.setattr(
            tm, "update_file_status", mock_update_file_status.__get__(tm)
        )

        download_file(photo=photo, filepath=tgt_filepath, file_size=file_size)
        assert os.stat(tgt_filepath).st_size == file_size
        assert open(tgt_filepath).read() == "abc" * 1024
        assert "Range" not in photo._service.session.headers

    def test_download_file_invalid_global_session(self, prepare_photo, monkeypatch):
        photo = prepare_photo

        def download(class_instance, timeout=None):
            class downloader:
                def iter_content(self, chunk_size):
                    offset = int(
                        class_instance._service.session.headers["Range"]
                        .split("=")[1]
                        .split("-")[0]
                    )
                    with open(temp_file, "rb") as f:
                        f.seek(offset)
                        content = f.read(chunk_size)
                        while content:
                            yield content
                            content = f.read(chunk_size)
                            offset += len(content)

                            if offset > 100:
                                raise PyiCloudAPIResponseException(
                                    "Invalid global session"
                                )

            return downloader()

        monkeypatch.setattr(photo, "download", download.__get__(photo))
        monkeypatch.setattr(
            tm, "update_file_status", mock_update_file_status.__get__(tm)
        )

        with pytest.raises(NeedLoginAgainException):
            download_file(photo=photo, filepath=tgt_filepath, file_size=file_size)
        assert "Range" not in photo._service.session.headers

    def test_download_file_rate_limit(self, prepare_photo, monkeypatch):
        photo = prepare_photo

        def download(class_instance, timeout=None):
            class downloader:
                def iter_content(self, chunk_size):
                    offset = int(
                        class_instance._service.session.headers["Range"]
                        .split("=")[1]
                        .split("-")[0]
                    )
                    with open(temp_file, "rb") as f:
                        f.seek(offset)
                        content = f.read(chunk_size)
                        while content:
                            yield content
                            content = f.read(chunk_size)
                            offset += len(content)

                            if offset > 100:
                                raise PyiCloudAPIResponseException(
                                    "private db access disabled for this account"
                                )

            return downloader()

        monkeypatch.setattr(photo, "download", download.__get__(photo))
        monkeypatch.setattr(
            tm, "update_file_status", mock_update_file_status.__get__(tm)
        )

        with pytest.raises(ApiLimitException):
            download_file(photo=photo, filepath=tgt_filepath, file_size=file_size)
        assert "Range" not in photo._service.session.headers

    def test_download_file_other_error(self, prepare_photo, monkeypatch):
        photo = prepare_photo

        def download(class_instance, timeout=None):
            class downloader:
                def iter_content(self, chunk_size):
                    offset = int(
                        class_instance._service.session.headers["Range"]
                        .split("=")[1]
                        .split("-")[0]
                    )
                    with open(temp_file, "rb") as f:
                        f.seek(offset)
                        content = f.read(chunk_size)
                        while content:
                            yield content
                            content = f.read(chunk_size)
                            offset += len(content)

                            if offset > 100:
                                raise PyiCloudAPIResponseException("foo")

            return downloader()

        monkeypatch.setattr(photo, "download", download.__get__(photo))
        monkeypatch.setattr(
            tm, "update_file_status", mock_update_file_status.__get__(tm)
        )

        with pytest.raises(PyiCloudAPIResponseException, match="foo"):
            download_file(photo=photo, filepath=tgt_filepath, file_size=file_size)
        assert "Range" not in photo._service.session.headers

    def test_download_photo(
        self, monkeypatch, set_not_existed_tempdir, photos, set_user
    ):
        def mock_login(self):
            return MockPyiCloudService(
                username="username", password="password", client_id="client_id"
            )

        monkeypatch.setattr(AuthManager, "login", mock_login)

        def mock_download_file(photo, filepath, size):
            return True

        monkeypatch.setattr(
            sys.modules["artascope.src.task.downloader"],
            "download_file",
            mock_download_file,
        )

        download_photo(task_name="task_name", username="username", batch=photos)
        assert tm.load_task(task_name="task_name").status == TaskStatus.SUCCESS
        for photo in photos:
            assert tm.load_file_status(photo.id).status == 100

    def test_download_photo_src_path(self, monkeypatch, photos, set_user):
        def mock_login(self):
            return MockPyiCloudService(
                username="username", password="password", client_id="client_id"
            )

        monkeypatch.setattr(AuthManager, "login", mock_login)

        def mock_download_file(photo, filepath, size):
            raise Exception(str(filepath))

        monkeypatch.setattr(
            sys.modules["artascope.src.task.downloader"],
            "download_file",
            mock_download_file,
        )

        filename = "{ts}_{filename}".format(
            filename=photos[0].filename, ts=int(photos[0].created.timestamp())
        )

        with pytest.raises(Exception, match=str(tempdir / filename)):
            download_photo(
                task_name="task_name", username="username", batch=[photos[0]]
            )

    def test_download_photo_upload_path(self, monkeypatch, photos, set_user):
        def mock_login(self):
            return MockPyiCloudService(
                username="username", password="password", client_id="client_id"
            )

        monkeypatch.setattr(AuthManager, "login", mock_login)

        def mock_download_file(photo, filepath, size):
            return True

        monkeypatch.setattr(
            sys.modules["artascope.src.task.downloader"],
            "download_file",
            mock_download_file,
        )

        class MockUploadToSFTPTask:
            def delay(self, username, src_filepath, filename, created_dt):
                raise Exception(filename)

        monkeypatch.setattr(
            sys.modules["artascope.src.task.downloader"],
            "upload_to_sftp",
            MockUploadToSFTPTask(),
        )

        with pytest.raises(Exception, match=photos[0].filename):
            download_photo(
                task_name="task_name", username="username", batch=[photos[0]]
            )

    def test_download_photo_without_login(
        self, monkeypatch, set_not_existed_tempdir, photos, set_user
    ):
        def mock_login(self):
            return None

        monkeypatch.setattr(AuthManager, "login", mock_login)

        AuthManager(username="username", password="password").set_login_status(
            LoginStatus.CAPTCHA_SENT
        )

        download_photo(task_name="task_name", username="username", batch=photos)

    def test_download_photo_need_login_again(self, monkeypatch, photos, set_user):
        monkeypatch.setattr(pyicloud, "PyiCloudService", MockPyiCloudService)

        def mock_send_captcha(self):
            self.set_login_status(LoginStatus.CAPTCHA_SENT)
            return True

        auth_manager = AuthManager(username="username", password="password")
        monkeypatch.setattr(
            AuthManager, "send_captcha", mock_send_captcha.__get__(auth_manager)
        )

        def mock_download_file(photo, filepath, size):
            raise NeedLoginAgainException()

        monkeypatch.setattr(
            sys.modules["artascope.src.task.downloader"],
            "download_file",
            mock_download_file,
        )

        auth_manager.set_login_status(LoginStatus.SUCCESS)

        download_photo(task_name="task_name", username="username", batch=photos)

        assert auth_manager.get_login_status() == LoginStatus.CAPTCHA_SENT

    def test_download_photo_api_limit(self, monkeypatch, photos, set_user):
        monkeypatch.setattr(pyicloud, "PyiCloudService", MockPyiCloudService)

        auth_manager = AuthManager(username="username", password="password")

        def mock_download_file(photo, filepath, size):
            raise ApiLimitException()

        monkeypatch.setattr(
            sys.modules["artascope.src.task.downloader"],
            "download_file",
            mock_download_file,
        )

        auth_manager.set_login_status(LoginStatus.SUCCESS)

        with pytest.raises(ApiLimitException):
            download_photo(task_name="task_name", username="username", batch=photos)

        assert auth_manager.get_login_status() == LoginStatus.SUCCESS

    def test_download_photo_api_not_index(self, monkeypatch, photos, set_user):
        monkeypatch.setattr(pyicloud, "PyiCloudService", MockPyiCloudService)

        auth_manager = AuthManager(username="username", password="password")

        def mock_download_file(photo, filepath, size):
            raise PyiCloudServiceNotActivatedException("index not finish")

        monkeypatch.setattr(
            sys.modules["artascope.src.task.downloader"],
            "download_file",
            mock_download_file,
        )

        auth_manager.set_login_status(LoginStatus.SUCCESS)

        with pytest.raises(
            PyiCloudServiceNotActivatedException, match="index not finish"
        ):
            download_photo(task_name="task_name", username="username", batch=photos)

        assert auth_manager.get_login_status() == LoginStatus.SUCCESS

    def test_download_photo_api_exception(self, monkeypatch, photos, set_user):
        monkeypatch.setattr(pyicloud, "PyiCloudService", MockPyiCloudService)

        def mock_check_login_status(self):
            return

        auth_manager = AuthManager(username="username", password="password")
        monkeypatch.setattr(
            AuthManager,
            "check_login_status",
            mock_check_login_status.__get__(auth_manager),
        )

        def mock_download_file(photo, filepath, size):
            raise PyiCloudAPIResponseException("foo")

        monkeypatch.setattr(
            sys.modules["artascope.src.task.downloader"],
            "download_file",
            mock_download_file,
        )

        auth_manager.set_login_status(LoginStatus.SUCCESS)

        with pytest.raises(PyiCloudAPIResponseException, match="foo"):
            download_photo(task_name="task_name", username="username", batch=photos)

        assert auth_manager.get_login_status() == LoginStatus.SUCCESS

    def test_download_photo_exception(self, monkeypatch, photos, set_user):
        monkeypatch.setattr(pyicloud, "PyiCloudService", MockPyiCloudService)

        def mock_check_login_status(self):
            return

        auth_manager = AuthManager(username="username", password="password")
        monkeypatch.setattr(
            AuthManager,
            "check_login_status",
            mock_check_login_status.__get__(auth_manager),
        )

        def mock_download_file(photo, filepath, size):
            raise Exception("foo")

        monkeypatch.setattr(
            sys.modules["artascope.src.task.downloader"],
            "download_file",
            mock_download_file,
        )

        auth_manager.set_login_status(LoginStatus.SUCCESS)

        with pytest.raises(Exception, match="foo"):
            download_photo(task_name="task_name", username="username", batch=photos)

        assert auth_manager.get_login_status() == LoginStatus.SUCCESS
