#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/26
import pytest
import datetime
from pyicloud.exceptions import (
    PyiCloudServiceNotActivatedException,
    PyiCloudAPIResponseException,
)
from artascope.src.lib.auth_manager import (
    LoginStatus,
    AuthManager,
)
from artascope.src.config import SECONDS_WAIT_FOR_API_LIMIT
from artascope.src.util.context_manager import (
    task_exception_handler,
    api_exception_handler,
)
from artascope.src.exception import (
    LoginTimeout,
    UnableToSendCaptcha,
    NeedLoginAgain,
    ApiLimitExceed,
    Gone,
)
from artascope.src.util.date_util import DateTimeUtil


class TestContextManager:
    def test_login_timeout(self, set_user, mock_login_captcha_wrong):
        am = AuthManager(username="username")

        with pytest.raises(LoginTimeout):
            with task_exception_handler(am) as api:
                assert api is None
                raise LoginTimeout()

        assert am.get_login_status() == LoginStatus.CAPTCHA_WRONG

    def test_unable_send_captcha(self, set_user, mock_login):
        am = AuthManager(username="username")
        with pytest.raises(UnableToSendCaptcha):
            with task_exception_handler(am) as api:
                assert api is not None
                raise UnableToSendCaptcha()

        assert am.get_login_status() == LoginStatus.NEED_LOGIN_AGAIN
        assert am._icloud_api is None

    def test_need_login_again(self, set_user, mock_login):
        am = AuthManager(username="username")
        with pytest.raises(NeedLoginAgain):
            with task_exception_handler(am) as api:
                assert api is not None
                raise NeedLoginAgain()

        assert am.get_login_status() == LoginStatus.NEED_LOGIN_AGAIN
        assert am._icloud_api is None

    def test_service_not_active(self, set_user, mock_login):
        am = AuthManager(username="username")

        start_ts = DateTimeUtil.get_now()
        with pytest.raises(PyiCloudServiceNotActivatedException):
            with task_exception_handler(am) as api:
                assert api is not None
                raise PyiCloudServiceNotActivatedException("reason")

        now_ts = DateTimeUtil.get_now()
        assert (now_ts - start_ts) / datetime.timedelta(
            milliseconds=1
        ) >= SECONDS_WAIT_FOR_API_LIMIT * 1000

    def test_api_limit(self, set_user, mock_login):
        am = AuthManager(username="username")

        start_ts = DateTimeUtil.get_now()
        with pytest.raises(ApiLimitExceed):
            with task_exception_handler(am) as api:
                assert api is not None
                raise ApiLimitExceed()

        now_ts = DateTimeUtil.get_now()
        assert (now_ts - start_ts) / datetime.timedelta(
            milliseconds=1
        ) >= SECONDS_WAIT_FOR_API_LIMIT * 1000

    def test_pyicloud_exception(self, set_user, mock_login):
        am = AuthManager(username="username")

        with pytest.raises(PyiCloudAPIResponseException):
            with task_exception_handler(am) as api:
                assert api is not None
                raise PyiCloudAPIResponseException("abc")

        assert am.get_login_status() == LoginStatus.NEED_LOGIN_AGAIN

    def test_pyicloud_exception(self, set_user, mock_login):
        am = AuthManager(username="username")

        with pytest.raises(Exception):
            with task_exception_handler(am) as api:
                assert api is not None
                raise Exception("abc")

        assert am.get_login_status() == LoginStatus.NEED_LOGIN_AGAIN

    @pytest.mark.parametrize(
        "inner,outer",
        [
            (PyiCloudAPIResponseException("Gone (410)"), Gone),
            (PyiCloudAPIResponseException("Invalid global session"), NeedLoginAgain),
            (
                PyiCloudAPIResponseException(
                    "private db access disabled for this account"
                ),
                ApiLimitExceed,
            ),
            (PyiCloudAPIResponseException("other"), PyiCloudAPIResponseException),
        ],
    )
    def test_generate_custom_exception(self, inner, outer):
        with pytest.raises(outer):
            with api_exception_handler():
                raise inner
