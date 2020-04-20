#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/30
import pytest
import sys
import tempfile
import json
import http.cookiejar as cookielib
from collections import namedtuple
from pathlib import Path
import pyicloud
from pyicloud.exceptions import PyiCloudAPIResponseException
from artascope.src.exception import (
    UserConfigNotExisted,
    InvalidLoginStatus,
    APINotExisted,
    MissiCloudLoginCookie,
    UnableToSendCaptcha,
)
import artascope.src.lib.auth_manager as auth_manager
from artascope.src.lib.auth_manager import (
    AuthManager,
    LoginStatus,
)
from artascope.src.lib.user_config_manager import ucm
from artascope.src.model.user_config import (
    UserConfig,
    NotifyType,
)
from artascope.test.conftest import DataException


@pytest.fixture()
def am() -> AuthManager:
    uc = UserConfig("username", "password")
    ucm.save(uc)
    return AuthManager(username="username")


@pytest.fixture()
def prepare_cookie_file() -> None:
    with open(Path(tempfile.gettempdir()) / "test_cookie", "w") as f:
        f.write(
            'Set-Cookie3: X-APPLE-WEBAUTH-HSA-TRUST-K3YK2TVYKD-6HH1VSP3AQAD9K58=""v=1:t=BQ==BST_IAAAAAAABLwIAAAAAF6LMq8RDmdzLmljbG91ZC5hdXRovQAJWyxlyRSJGCebu2GAUY3NPYxl4HYHuluB7fhMgT55QNtwdbt5AN3MP1wkPIjva6lAHH7cEJ0fxhokwubjciFGeHijihK_b_tmigi9Q3UkWGE0ZzTu9NUhGTOrn9VB-VnY56i5DC6faNa3ebirFEtq1YJ6mg~~""; path="/"; domain=".icloud.com"; path_spec; domain_dot; secure; expires="2020-07-05 13:46:23Z"; HttpOnly=None; version=0\nSet-Cookie3: X_APPLE_WEB_KB-K3YK2TVYKD-6HH1VSP3AQAD9K58=""v=1:t=BA==BST_IAAAAAAABLwIAAAAAF6LMmURDmdzLmljbG91ZC5hdXRovQBLuBmVRPdPJjDqhBhiaOO3DrLp_A5wYaaEoSNFeHwBBsEEWbE9_p-strpA8GErq5r8i85S6jnJSa03eql9tX7ez7c9HWCl08j07UPBkJHe_6iruJ6XciVw8WMe-s_tL6zgLzIiW7QgLeZ8g2O5jAPf-oQtnw~~""; path="/"; domain=".icloud.com"; path_spec; domain_dot; secure; expires="2020-06-05 13:45:10Z"; HttpOnly=None; version=0'
        )


COOKIE = namedtuple("Cookie", ["name", "path", "domain"])

TEMP_FILE_PATH = Path(tempfile.gettempdir()) / "test_cookie"


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

        self.session = MockPyiCloudSession()

    @property
    def trusted_devices(self):
        return [
            {
                "deviceType": "SMS",
                "areaCode": "",
                "phoneNumber": "13801753980",
                "deviceId": "1",
            }
        ]

    def send_verification_code(self, device):
        return True

    def validate_verification_code(self, device, code):
        return True

    def authenticate(self):
        return True

    def requires_2sa(self):
        return True

    def _get_cookiejar_path(self):
        return TEMP_FILE_PATH


class MockCeleryTask:
    def delay(self, token, channel, msg):
        raise DataException({"msg": msg})


class TestAuthManager:
    def test_init_auth_manager_with_password(self):
        am = AuthManager(username="username", password="password")
        assert getattr(am, "_password") == "password"

    def test_init_auth_manager_without_password(self):
        uc = UserConfig("username", "password2")
        ucm.save(uc)
        am = AuthManager(username="username")
        assert getattr(am, "_password") == "password2"

    def test_init_auth_manager_without_user_config(self):
        with pytest.raises(UserConfigNotExisted, match="username not existed"):
            am = AuthManager(username="username")

    def test_get_client_id(self, am):
        client_id = am.get_client_id()
        assert am.get_client_id() == client_id

    def test_login_status(self, am):
        assert am.get_login_status() is LoginStatus.NOT_LOGIN
        am.set_login_status(LoginStatus.CAPTCHA_RECEIVED)
        assert am.get_login_status() == LoginStatus.CAPTCHA_RECEIVED

    def test_trust_device(self, am):
        assert am.get_trust_device() is None
        am.set_trust_device(
            {
                "deviceType": "SMS",
                "areaCode": "",
                "phoneNumber": "13801753980",
                "deviceId": "1",
            }
        )
        assert am.get_trust_device() == {
            "deviceType": "SMS",
            "areaCode": "",
            "phoneNumber": "13801753980",
            "deviceId": "1",
        }

    def test_get_captcha_without_set(self, am):
        assert am.get_captcha() is None

    def test_send_captcha_with_invalid_login_status(self, am):
        am.set_login_status(LoginStatus.CAPTCHA_RECEIVED)
        with pytest.raises(
            InvalidLoginStatus,
            match="need NOT_LOGIN or NEED_LOGIN_AGAIN or CAPTCHA_WRONG",
        ):
            am.send_captcha()

    def test_send_captcha_without_login(self, am):
        am.set_login_status(LoginStatus.NEED_LOGIN_AGAIN)
        with pytest.raises(APINotExisted):
            am.send_captcha()

    def test_send_captcha_without_hsa_login_cookie(self, am, monkeypatch):
        am._icloud_api = MockPyiCloudService(
            username="username", password="password", client_id="client_id"
        )

        @property
        def mock_trusted_devices(self):
            raise PyiCloudAPIResponseException("Miss X-APPLE-WEBAUTH-HSA-LOGIN")

        monkeypatch.setattr(
            MockPyiCloudService, "trusted_devices", mock_trusted_devices
        )
        with pytest.raises(MissiCloudLoginCookie):
            am.send_captcha()

    def test_send_captcha_raise_api_exception(self, am, monkeypatch):
        am._icloud_api = MockPyiCloudService(
            username="username", password="password", client_id="client_id"
        )

        @property
        def mock_trusted_devices(self):
            raise PyiCloudAPIResponseException("something wrong")

        monkeypatch.setattr(
            MockPyiCloudService, "trusted_devices", mock_trusted_devices
        )
        with pytest.raises(PyiCloudAPIResponseException, match="something wrong"):
            am.send_captcha()

    def test_send_captcha_notify_slack(self, am, monkeypatch):
        uc = UserConfig(
            icloud_username="username",
            icloud_password="password",
            notify_type=NotifyType.SLACK,
            slack_token="abcd",
            slack_channel="dev",
            admin_url_prefix="test_url",
        )
        ucm.save(uc)
        am._icloud_api = MockPyiCloudService(
            username="username", password="password", client_id="client_id"
        )
        monkeypatch.setattr(
            sys.modules["artascope.src.lib.msg_manager"],
            "send_slack_message",
            MockCeleryTask(),
        )

        data = {
            "msg": "Goto {url_prefix}/user/captcha/username to enter your icloud HSA captcha!".format(
                url_prefix=uc.admin_url_prefix, username="username"
            )
        }
        with pytest.raises(DataException,) as exc_info:
            am.send_captcha()
        assert json.dumps(data, sort_keys=True) in str(exc_info.value)

        assert am.get_login_status() == LoginStatus.CAPTCHA_SENT

    def test_login(self, am, monkeypatch):
        assert am.get_login_status() is LoginStatus.NOT_LOGIN
        monkeypatch.setattr(pyicloud, "PyiCloudService", MockPyiCloudService)

        api = am.login()
        assert api is None
        assert am.get_login_status() == LoginStatus.CAPTCHA_SENT

        api = am.login()
        assert api is None
        assert am.get_login_status() == LoginStatus.CAPTCHA_SENT

        am.receive_captcha("captcha")
        assert am.get_login_status() == LoginStatus.CAPTCHA_RECEIVED

        api = am.login()
        assert api is not None
        assert am.get_login_status() == LoginStatus.SUCCESS

        api2 = am.login()
        assert api2 == api

    def test_login_after_need_login_again(self, am, monkeypatch):
        monkeypatch.setattr(pyicloud, "PyiCloudService", MockPyiCloudService)
        am.set_login_status(LoginStatus.NEED_LOGIN_AGAIN)

        api = am.login()
        assert api is None
        assert am.get_login_status() == LoginStatus.CAPTCHA_SENT

    def test_login_after_need_login_again_fail(self, am, monkeypatch):
        def mock_find_hsa_trust_cookie(self):
            return True

        monkeypatch.setattr(
            am, "find_hsa_trust_cookie", mock_find_hsa_trust_cookie.__get__(am)
        )
        monkeypatch.setattr(pyicloud, "PyiCloudService", MockPyiCloudService)
        am.set_login_status(LoginStatus.NEED_LOGIN_AGAIN)

        with pytest.raises(UnableToSendCaptcha,):
            api = am.login()
        assert am.get_login_status() == LoginStatus.NEED_LOGIN_AGAIN

    def test_login_after_need_login_again_fail2(self, am, monkeypatch):
        def mock_find_hsa_login_cookie(self):
            return False

        monkeypatch.setattr(
            am, "find_hsa_login_cookie", mock_find_hsa_login_cookie.__get__(am)
        )
        monkeypatch.setattr(pyicloud, "PyiCloudService", MockPyiCloudService)

        with pytest.raises(UnableToSendCaptcha,):
            api = am.login()
        assert am.get_login_status() == LoginStatus.NOT_LOGIN

    def test_check_login_status(self, am, monkeypatch):
        monkeypatch.setattr(pyicloud, "PyiCloudService", MockPyiCloudService)

        api = am.login()
        am.check_login_status()
        assert am.get_login_status() == LoginStatus.NEED_LOGIN_AGAIN

    def test_clear_hsa_trust_cookie(self, am, prepare_cookie_file):
        am._icloud_api = MockPyiCloudService(
            username="username", password="password", client_id="client_id"
        )

        am.clear_hsa_trust_cookie()
        assert (
            open(am._icloud_api._get_cookiejar_path(), "r").read()
            == 'Set-Cookie3: X_APPLE_WEB_KB-K3YK2TVYKD-6HH1VSP3AQAD9K58=""v=1:t=BA==BST_IAAAAAAABLwIAAAAAF6LMmURDmdzLmljbG91ZC5hdXRovQBLuBmVRPdPJjDqhBhiaOO3DrLp_A5wYaaEoSNFeHwBBsEEWbE9_p-strpA8GErq5r8i85S6jnJSa03eql9tX7ez7c9HWCl08j07UPBkJHe_6iruJ6XciVw8WMe-s_tL6zgLzIiW7QgLeZ8g2O5jAPf-oQtnw~~""; path="/"; domain=".icloud.com"; path_spec; domain_dot; secure; expires="2020-06-05 13:45:10Z"; HttpOnly=None; version=0'
        )

    def test_validate_captcha_fail(self, am, monkeypatch):
        def mock_validate_verification_code(self, device, code):
            return False

        monkeypatch.setattr(
            MockPyiCloudService,
            "validate_verification_code",
            mock_validate_verification_code,
        )
        monkeypatch.setattr(pyicloud, "PyiCloudService", MockPyiCloudService)

        am.set_login_status(LoginStatus.CAPTCHA_RECEIVED)
        api = am.login()
        assert api is None
        assert am.get_login_status() == LoginStatus.CAPTCHA_WRONG

    def test_prepare_to_login_again(self, am, prepare_cookie_file, monkeypatch):
        monkeypatch.setattr(pyicloud, "PyiCloudService", MockPyiCloudService)
        am.set_login_status(LoginStatus.SUCCESS)
        api = am.login()
        assert api is not None

        am.prepare_to_login_again()
        assert am._icloud_api is None
        assert am.get_login_status() == LoginStatus.NEED_LOGIN_AGAIN
        assert (
            open(TEMP_FILE_PATH, "r").read()
            == 'Set-Cookie3: X_APPLE_WEB_KB-K3YK2TVYKD-6HH1VSP3AQAD9K58=""v=1:t=BA==BST_IAAAAAAABLwIAAAAAF6LMmURDmdzLmljbG91ZC5hdXRovQBLuBmVRPdPJjDqhBhiaOO3DrLp_A5wYaaEoSNFeHwBBsEEWbE9_p-strpA8GErq5r8i85S6jnJSa03eql9tX7ez7c9HWCl08j07UPBkJHe_6iruJ6XciVw8WMe-s_tL6zgLzIiW7QgLeZ8g2O5jAPf-oQtnw~~""; path="/"; domain=".icloud.com"; path_spec; domain_dot; secure; expires="2020-06-05 13:45:10Z"; HttpOnly=None; version=0'
        )
