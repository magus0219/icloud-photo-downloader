#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/22
import typing
from pyicloud import PyiCloudService
from artascope.src.util.prefix_redis import PrefixRedis
from artascope.src.config import REDIS_CONFIG
from artascope.src.util.slack_sender import send_message
from artascope.src.util import get_logger


class LoginStatus:
    SUCCESS = 0
    VERIFY_CODE_NEED = 1
    VERIFY_CODE_RECEIVED = 2
    VERIFY_CODE_SENT = 3


LOGIN_STATUS_KEY = "ls"
LOGIN_VERIFY_CODE_KEY = "lvck"

logger = get_logger("server.auth")


class Auth:
    def __init__(self, username, password, redis_config=REDIS_CONFIG):
        self._redis_config = redis_config
        self._redis = PrefixRedis("auth", **self._redis_config)
        # self._latch = Latch('icouldapi', 3)
        self._username = username
        self._password = password
        self._icloud_api = None

    def set_login_status(self, status: int):
        assert status in (
            LoginStatus.SUCCESS,
            LoginStatus.VERIFY_CODE_NEED,
            LoginStatus.VERIFY_CODE_RECEIVED,
            LoginStatus.VERIFY_CODE_SENT,
        )
        self._redis.set(
            "{username}:{key}".format(username=self._username, key=LOGIN_STATUS_KEY),
            status,
        )

    def get_login_status(self):
        rlt = self._redis.get(
            "{username}:{key}".format(username=self._username, key=LOGIN_STATUS_KEY)
        )
        logger.info(
            "get_login_status:key:{}:{}:{}".format(
                "auth", self._username, LOGIN_STATUS_KEY
            )
        )
        logger.info("get_login_status:{}".format(str(rlt)))
        if rlt:
            return int(rlt.decode("utf8"))
        return None

    def set_verify_code(self, code: str):
        self._redis.set(
            "{username}:{key}".format(
                username=self._username, key=LOGIN_VERIFY_CODE_KEY
            ),
            code,
        )

    def get_verify_code(self):
        rlt = self._redis.get(
            "{username}:{key}".format(
                username=self._username, key=LOGIN_VERIFY_CODE_KEY
            )
        )
        if rlt:
            return rlt.decode("utf8")
        return None

    def check_login_status(self):
        logger.info("before check:{}".format(self.get_login_status()))
        if not self._icloud_api or self._icloud_api.requires_2sa:
            self.set_login_status(LoginStatus.VERIFY_CODE_NEED)

    def send_verify_code(self):
        device = self._icloud_api.trusted_devices[0]
        # self._latch.lock()
        rlt = self._icloud_api.send_verification_code(device)
        logger.debug("send_verification_code:{}".format(str(rlt)))
        send_message.delay(
            msg="Hey~ artascope need icloud verify code!",
            callback=self.set_login_status,
            callback_params={"status": LoginStatus.VERIFY_CODE_SENT},
        )

    def login(self) -> typing.Union[None, PyiCloudService]:
        # self._latch.lock()
        self._icloud_api = PyiCloudService(self._username, self._password)
        status = self.get_login_status()

        logger.debug("login status:{}".format(str(status)))
        if status == LoginStatus.SUCCESS:
            return self._icloud_api
        elif status is None or status == LoginStatus.VERIFY_CODE_NEED:
            self.send_verify_code()
            return None
        elif status == LoginStatus.VERIFY_CODE_SENT:
            return None
        elif status == LoginStatus.VERIFY_CODE_RECEIVED:
            device = self._icloud_api.trusted_devices[0]
            code = self.get_verify_code()
            # self._latch.lock()
            rlt = self._icloud_api.validate_verification_code(device, code)
            logger.debug("validate_verification_code:{}".format(str(rlt)))
            self.set_login_status(LoginStatus.SUCCESS)
            return self._icloud_api

    def __getstate__(self):
        state = self.__dict__.copy()
        # Remove the unpicklable entries.
        del state["_redis"]
        if "_icloud_api" in state:
            del state["_icloud_api"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._redis = PrefixRedis("auth", **self._redis_config)
