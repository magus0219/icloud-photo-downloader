#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/22
import typing
import uuid
import json
import pyicloud
from pathlib import Path
from pyicloud.exceptions import PyiCloudAPIResponseException
from artascope.src.util.prefix_redis import PrefixRedis
from artascope.src.config import REDIS_CONFIG
from artascope.src.lib.msg_manager import MsgManager
from artascope.src.util import get_logger
from artascope.src.patch.pyicloud import patch_session
from artascope.src.lib.user_config_manager import ucm
from artascope.src.exception import (
    UserConfigNotExisted,
    APINotExisted,
    MissiCloudLoginCookie,
    InvalidLoginStatus,
    UnableToSendCaptcha,
)


class LoginStatus:
    SUCCESS = 1
    NOT_LOGIN = 2
    NEED_LOGIN_AGAIN = 3
    CAPTCHA_RECEIVED = 4
    CAPTCHA_SENT = 5
    CAPTCHA_WRONG = 6


LoginStatusText = {
    LoginStatus.SUCCESS: "Success",
    LoginStatus.NOT_LOGIN: "Not Login",
    LoginStatus.NEED_LOGIN_AGAIN: "Need login again",
    LoginStatus.CAPTCHA_SENT: "Captcha Sent",
    LoginStatus.CAPTCHA_RECEIVED: "Captcha Received",
    LoginStatus.CAPTCHA_WRONG: "Captcha Fail",
}


LOGIN_STATUS_KEY = "ls"
LOGIN_VERIFY_CODE_KEY = "lvck"
LOGIN_CLIENT_ID_KEY = "cid"
LOGIN_TRUST_DEVICE_KEY = "device"

logger = get_logger("server.auth")


class AuthManager:
    def __init__(self, username, password=None, redis_config=REDIS_CONFIG):
        self._redis_config = redis_config
        self._redis = PrefixRedis("auth", **self._redis_config)
        self._username = username

        if not password:
            uc = ucm.load(username)
            if not uc:
                raise UserConfigNotExisted("{} not existed".format(username))
            password = uc.icloud_password
        self._password = password

        self._icloud_api = None

    def get_client_id(self) -> str:
        """Cache or generate client id

        :return:
        """
        client_id = self._redis.get(
            "{key}:{username}".format(username=self._username, key=LOGIN_CLIENT_ID_KEY)
        )
        if not client_id:
            client_id = str(uuid.uuid1()).upper()
            self._redis.set(
                "{key}:{username}".format(
                    username=self._username, key=LOGIN_CLIENT_ID_KEY
                ),
                client_id,
            )
        else:
            client_id = client_id.decode("utf8")

        logger.debug("client id:{}".format(client_id))
        return client_id

    def set_login_status(self, status: int) -> None:
        assert status in (
            LoginStatus.SUCCESS,
            LoginStatus.NEED_LOGIN_AGAIN,
            LoginStatus.CAPTCHA_RECEIVED,
            LoginStatus.CAPTCHA_SENT,
            LoginStatus.CAPTCHA_WRONG,
        )
        self._redis.set(
            "{key}:{username}".format(username=self._username, key=LOGIN_STATUS_KEY),
            status,
        )
        logger.info("set_login_status:{}".format(str(status)))

    def get_login_status(self) -> typing.Union[int, None]:
        rlt = self._redis.get(
            "{key}:{username}".format(username=self._username, key=LOGIN_STATUS_KEY)
        )
        logger.debug("get_login_status:{}".format(str(rlt)))
        if rlt:
            return int(rlt.decode("utf8"))
        return LoginStatus.NOT_LOGIN

    def check_login_status(self) -> None:
        if not self._icloud_api or self._icloud_api.requires_2sa:
            logger.info("check_login_status:{}".format(str(self._icloud_api)))
            if self._icloud_api:
                logger.info(
                    "check_login_status:{}".format(str(self._icloud_api.requires_2sa))
                )
            self.prepare_to_login_again()

    def set_trust_device(self, device: dict) -> None:
        self._redis.set(
            "{key}:{username}".format(
                username=self._username, key=LOGIN_TRUST_DEVICE_KEY
            ),
            json.dumps(device),
        )

    def get_trust_device(self) -> typing.Union[None, str]:
        rlt = self._redis.get(
            "{key}:{username}".format(
                username=self._username, key=LOGIN_TRUST_DEVICE_KEY
            )
        )

        if rlt:
            return json.loads(rlt)
        else:
            return None

    def set_captcha(self, code: str) -> None:
        self._redis.set(
            "{key}:{username}".format(
                username=self._username, key=LOGIN_VERIFY_CODE_KEY
            ),
            code,
        )

    def get_captcha(self) -> typing.Union[None, str]:
        rlt = self._redis.get(
            "{key}:{username}".format(
                username=self._username, key=LOGIN_VERIFY_CODE_KEY
            )
        )
        if rlt:
            return rlt.decode("utf8")
        return None

    def receive_captcha(self, captcha: str):
        self.set_captcha(captcha)
        self.set_login_status(LoginStatus.CAPTCHA_RECEIVED)

    def send_captcha(self) -> None:
        if self.get_login_status() not in (
            LoginStatus.NOT_LOGIN,
            LoginStatus.NEED_LOGIN_AGAIN,
            LoginStatus.CAPTCHA_WRONG,
        ):
            raise InvalidLoginStatus(
                "need NOT_LOGIN or NEED_LOGIN_AGAIN or CAPTCHA_WRONG"
            )
        if not self._icloud_api:
            raise APINotExisted("icloud api not init.")
        device = self.get_trust_device()
        if not device:
            try:
                # this icloud api need Cookie X-APPLE-WEBAUTH-HSA-LOGIN but not Cookie X-APPLE-WEBAUTH-HSA-TRUST
                # which means HSA passed
                device = self._icloud_api.trusted_devices[0]
                logger.info(str(device))
                self.set_trust_device(device)
            except PyiCloudAPIResponseException as e:
                if "X-APPLE-WEBAUTH-HSA-LOGIN" in str(e):
                    raise MissiCloudLoginCookie()
                else:
                    raise
        rlt = self._icloud_api.send_verification_code(device)
        logger.debug("send_verification_code:{}".format(str(rlt)))
        self.set_login_status(LoginStatus.CAPTCHA_SENT)

        user_setting = ucm.load(self._username)
        MsgManager.send_message(
            username=self._username,
            msg="Goto {url_prefix}/user/captcha/{username} to enter your icloud HSA captcha!".format(
                url_prefix=user_setting.admin_url_prefix, username=self._username
            ),
        )

    def prepare_to_login_again(self) -> None:
        self.set_login_status(LoginStatus.NEED_LOGIN_AGAIN)
        self.clear_hsa_trust_cookie()
        self._icloud_api = None

    def clear_hsa_trust_cookie(self) -> None:
        """remove Cookies but X_APPLE_WEB_KB done
        :return:
        """
        cookiejar_path = Path(self._icloud_api._get_cookiejar_path())

        if cookiejar_path.exists():
            contents = []
            with open(cookiejar_path, "r") as f:
                line = f.readline()
                while line:
                    if "X_APPLE_WEB_KB" in line:
                        contents.append(line)
                    line = f.readline()

            with open(cookiejar_path, "w") as f:
                for line in contents:
                    f.write(line)

        logger.info("remove Cookies but X_APPLE_WEB_KB done")

    def find_hsa_trust_cookie(self) -> bool:
        for one in self._icloud_api.session.cookies:
            if one.name.startswith("X-APPLE-WEBAUTH-HSA-TRUST"):
                return True
        return False

    def find_hsa_login_cookie(self) -> bool:
        for one in self._icloud_api.session.cookies:
            if one.name.startswith("X-APPLE-WEBAUTH-HSA-LOGIN"):
                return True
        return False

    def login(self) -> typing.Union[None, pyicloud.PyiCloudService]:
        patch_session()
        if not self._icloud_api:
            self._icloud_api = pyicloud.PyiCloudService(
                self._username, self._password, client_id=self.get_client_id()
            )
        status = self.get_login_status()

        logger.info("in login:{}".format(str(status)))

        if status == LoginStatus.SUCCESS:
            return self._icloud_api
        elif status == LoginStatus.NOT_LOGIN:
            if not self.find_hsa_trust_cookie() and self.find_hsa_login_cookie():
                self.send_captcha()
                return None
            else:
                raise UnableToSendCaptcha()
        elif status == LoginStatus.NEED_LOGIN_AGAIN:
            if not self.find_hsa_trust_cookie() and self.find_hsa_login_cookie():
                self.send_captcha()
                return None
            else:
                raise UnableToSendCaptcha()
        elif status == LoginStatus.CAPTCHA_SENT:
            return None
        elif status == LoginStatus.CAPTCHA_RECEIVED:
            device = self.get_trust_device()
            code = self.get_captcha()

            success = self._icloud_api.validate_verification_code(device, code)
            logger.debug("validate_verification_code:{}".format(str(success)))
            if success:
                self.set_login_status(LoginStatus.SUCCESS)
                return self._icloud_api
            else:
                self.set_login_status(LoginStatus.CAPTCHA_WRONG)
                return None
