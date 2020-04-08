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
from artascope.src.util.slack_sender import send_message
from artascope.src.util import get_logger
from artascope.src.patch.pyicloud import patch_session
from artascope.src.lib.user_config_manager import ucm
from artascope.src.model.user_config import NotifyType
from artascope.src.exception import (
    UserConfigNotExisted,
    APINotExisted,
    MissiCloudLoginCookie,
    InvalidLoginStatus,
)


class LoginStatus:
    SUCCESS = 1
    NOT_LOGIN = 2
    NEED_LOGIN_AGAIN = 3
    CAPTCHA_RECEIVED = 4
    CAPTCHA_SENT = 5


LoginStatusText = {
    LoginStatus.SUCCESS: "Success",
    LoginStatus.NOT_LOGIN: "Not Login",
    LoginStatus.NEED_LOGIN_AGAIN: "Need login again",
    LoginStatus.CAPTCHA_SENT: "Captcha Sent",
    LoginStatus.CAPTCHA_RECEIVED: "Captcha Pass",
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
            self.set_login_status(LoginStatus.NEED_LOGIN_AGAIN)

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

    def send_captcha(self, notify_type=None) -> None:
        if self.get_login_status() not in (
            LoginStatus.NOT_LOGIN,
            LoginStatus.NEED_LOGIN_AGAIN,
        ):
            raise InvalidLoginStatus("need VERIFY_CODE_NEED")
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
        if notify_type == NotifyType.SLACK:
            user_setting = ucm.load(self._username)
            send_message.delay(
                msg="Goto {url_prefix}/user/captcha/<username> to enter your icloud HSA captcha!".format(
                    url_prefix=user_setting.admin_url_prefix, username=self._username
                ),
            )

    def clear_hsa_trust_cookie(self) -> None:
        """Remove X-APPLE-WEBAUTH-HSA-TRUST cookie
        :return:
        """
        cookiejar_path = Path(self._icloud_api._get_cookiejar_path())

        if cookiejar_path.exists():
            contents = []
            with open(cookiejar_path, "r") as f:
                line = f.readline()
                while line:
                    if "X-APPLE-WEBAUTH-HSA-TRUST" not in line:
                        contents.append(line)
                    line = f.readline()

            with open(cookiejar_path, "w") as f:
                for line in contents:
                    f.write(line)

        logger.info("remove Cookie X-APPLE-WEBAUTH-HSA-TRUST done")

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
        # if not self._icloud_api:
        patch_session()
        self._icloud_api = pyicloud.PyiCloudService(
            self._username, self._password, client_id=self.get_client_id()
        )
        status = self.get_login_status()

        logger.info("in login:{}".format(str(status)))

        if status == LoginStatus.SUCCESS:
            return self._icloud_api
        elif status == LoginStatus.NOT_LOGIN:
            self.send_captcha()
            return None
        elif status == LoginStatus.NEED_LOGIN_AGAIN:
            if not self.find_hsa_trust_cookie() and self.find_hsa_login_cookie():
                self.send_captcha()
                return None
            else:
                return self._icloud_api
        elif status == LoginStatus.CAPTCHA_SENT:
            return None
        elif status == LoginStatus.CAPTCHA_RECEIVED:
            device = self.get_trust_device()
            code = self.get_captcha()
            rlt = self._icloud_api.validate_verification_code(device, code)
            logger.debug("validate_verification_code:{}".format(str(rlt)))
            self.set_login_status(LoginStatus.SUCCESS)
            return self._icloud_api

    # def __getstate__(self):
    #     state = self.__dict__.copy()
    #     # Remove the unpicklable entries.
    #     del state["_redis"]
    #     if "_icloud_api" in state:
    #         del state["_icloud_api"]
    #     return state
    #
    # def __setstate__(self, state):
    #     self.__dict__.update(state)
    #     self._redis = PrefixRedis("auth", **self._redis_config)


# after Authentication:<LWPCookieJar[<Cookie X-APPLE-WEBAUTH-HSA-LOGIN="v=2:t=Gw==BST_IAAAAAAABLwIAAAAAF6MNuMRDmdzLmljbG91ZC5hdXRovQDwC0mgBaGO70DEsMJA5FOM8rSa2TfmZRhosC5NfJ71X3ViKwXtnToVbJlUa9H8pBnby97krThU-pQcMA9Km3QUa1309EDoSXN7SRmNCph7EKFNPTWjSPzqa9cMFPt-VU2Z7pGVxWN6_u68pkFJQEe2qgIdkA~~" for .icloud.com/>, <Cookie X-APPLE-WEBAUTH-LOGIN="v=1:t=Gw==BST_IAAAAAAABLwIAAAAAF6MNuMRDmdzLmljbG91ZC5hdXRovQDwC0mgBaGO70DEsMJA5FOM8rSa2TfmZRhosC5NfJ71X3ViKwXtnToVbJlUa9H8pBnby97krThU-pQcMA9Km3QUa1309EDoSXN7SRmNCph7EB_5ILA51LWXvRTf-BoorpOzL4R-rAFKjOF7kqP71QOkEapoZA~~" for .icloud.com/>, <Cookie X-APPLE-WEBAUTH-USER="v=1:s=0:d=556903187" for .icloud.com/>, <Cookie X-APPLE-WEBAUTH-VALIDATE="v=1:t=Gw==BST_IAAAAAAABLwIAAAAAF6MNuMRDmdzLmljbG91ZC5hdXRovQDwC0mgBaGO70DEsMJA5FOM8rSa2TfmZRhosC5NfJ71X3ViKwXtnToVbJlUa9H8pBnby97krThU-pQcMA9Km3QUa1309EDoSXN7SRmNCph7ENSUC9hWPez96SiTU49YOCVGPfWDoa9IGmOQOqtLd8d20XKVew~~" for .icloud.com/>, <Cookie X-Apple-GCBD-Cookie=1 for .icloud.com/>, <Cookie X_APPLE_WEB_KB-K3YK2TVYKD-6HH1VSP3AQAD9K58="v=1:t=Gw==BST_IAAAAAAABLwIAAAAAF6MNuMRDmdzLmljbG91ZC5hdXRovQDwC0mgBaGO70DEsMJA5FOM8rSa2TfmZRhosC5NfJ71X3ViKwXtnToVbJlUa9H8pBnby97krThU-pQcMA9Km3QUa1309EDoSXN7SRmNCph7EIYA8tvzZ8Lj87qecGKK6S1_zKoGyS-ftRsHGjnM0mR2jueAaA~~" for .icloud.com/>]>
# after
# Authentication: < LWPCookieJar[ < Cookie
# X - APPLE - WEBAUTH - HSA - TRUST - K3YK2TVYKD - 6
# HH1VSP3AQAD9K58 = "v=1:t=HA==BST_IAAAAAAABLwIAAAAAF6MNzIRDmdzLmljbG91ZC5hdXRovQBwQrAHUvkjudTIWhdAjs4JVOW1is1DxCKbTx57uwJCuTNLacRo94P8-KNRaEgIZWcGeb5o-Ox4dQ8gsdvpwmsC1bNbOHfXvG6yZhtHROSiBrgSkzdb12jqyaNVDUBs6M6uT9I2eUFa5Y_unyznbO1Cfhb5mA~~"
# for .icloud.com / >, < Cookie X-APPLE-WEBAUTH-LOGIN="v=1:t=HA==BST_IAAAAAAABLwIAAAAAF6MNz0RDmdzLmljbG91ZC5hdXRovQDt3XVyzLZrs0HXuQ_NxzOf7P5Awastto2n0AeGVyR9D1gwr978yJbvX_K54xGSnGlLrcRJ3fzkH536F7X_ZanTRjB9_rD6dPr3ATvVwFl6D3ks3_esOYKhoPoS56tVn8661clcIHqQhXoSIkTnim71NA4dPg~~" for.icloud.com / >, < Cookie X-APPLE-WEBAUTH-PCS-Cloudkit="TGlzdEFwcGw6MTpBcHBsOjE6Ab5KLfgYWBS+MGoKmA8nnms5D/7CLhWs4zwZwpcP4OqDyZPDvRaVBuEKp9x7DuLrL1VSPU8k2CpopalhZkHqQ19eEQnVh2zosnGeq2SH5NmzTTnbPX73mosuBeE7ioBmaLK0jeCrP9ldyd+btlXpp0bqgMGivX55e7tDtIjcqd/57eOBCrAvXQ==" for.icloud.com / >, < Cookie X-APPLE-WEBAUTH-PCS-Documents="TGlzdEFwcGw6MTpBcHBsOjE6AbU8xSTlEvQsOkrN8Lhmc/5H1AT8a3moryHwfJYlsAIEK1qLJIhZdYy2lzzd23opDjQ9JKiKxhPZptSbQpFxmJt0CU6h9PdmvsRVkcdC/UOA8v7C5SErsDZtBLBb+g8HHRil4lLVLPBUTpb46B4nlG2gAx+zKbcCpzRkolQdEF6wG9yE8yPyaw==" for.icloud.com / >, < Cookie X-APPLE-WEBAUTH-PCS-Mail="TGlzdEFwcGw6MTpBcHBsOjE6AUp9CrOi41GTgFE34Dyp0d/bhcceZWrCkZeRjoqmfYIOna57tFywDk0srx8Kt9hXjUaJkTLHqJ7o7f27LaEp25Ox8z1FIHtZulgv3i27Bkz3Un+/mXUPRx7T7fKQ7mzbJSc6+vD6zU+UIeK9MJ8DUcCpvu7mJtU88BSCsNqWL5/hgoAecvLa/A==" for.icloud.com / >, < Cookie X-APPLE-WEBAUTH-PCS-News="TGlzdEFwcGw6MTpBcHBsOjE6AfMVi+LJOEZsTS0fNIr4DwkuYaEKP8oo8ROkUMOQwaXMJCt3XGr15xaqniI+8jjII51DeJasFQASLRiwhyrMVK43E8Pnm3eLsyE6lW6mm+K8RF98XYqMCbaZfrq1M1y1WJjIP2LxeAt9POfgMt6knrjFGG/80RxEg/DZnFF6XyamXCl823bKkA==" for.icloud.com / >, < Cookie X-APPLE-WEBAUTH-PCS-Notes="TGlzdEFwcGw6MTpBcHBsOjE6ASDdU98UtVx1c+U3kEkMZ7yNVZ9d6Z0nRTcZ0wp0dGQ/dbNvPPDv52AJ3suV1C7Tl4zIHKtmqW0YY6TXmjmuZNLhvysQnVyIFEsADfKoBZPITw6FOTRb6FjYEVusGvTlUAYt+5lMM6Ysh5kVzqxPDzv3f7SE3lEEKhCpe3vQZ49+HllHraZsOw==" for.icloud.com / >, < Cookie X-APPLE-WEBAUTH-PCS-Photos="TGlzdEFwcGw6MTpBcHBsOjE6AR2VVZInTOI5+/AgxKBqXDPW04ccUHexEw7Q05YtBEIhVeFGe6A/zWX4dxS3K4PnPzuN6NsOGbnpuX8FTY6xiLhtspYsM3wqpMERp2rKDd49rLCmAiiO7PVPvWSmxXGl3B9W0ocmXZQqfh5EtY8w2oMLFcaA8/Yhbj3I5Bv8N9MAeLLzAUtbhw==" for.icloud.com / >, < Cookie X-APPLE-WEBAUTH-PCS-Safari="TGlzdEFwcGw6MTpBcHBsOjE6Ab0U2QUtgNLAib2sRndqu8owzbM8lMKDg4PVD23nnYWUJTIS7Ev1OMJ0K3ESgIlJfkT+lh82+kvwS5tZQbD7DGzpjWQyh0P/G7bv0SR1IDDGM9pA0Pj/UZEMep2rChuX/V/BcJS53PPNegyBv0DtYGIQtibfnANlfHMaVPx6HsjKI4W3IZ1O1Q==" for.icloud.com / >, < Cookie X-APPLE-WEBAUTH-PCS-Sharing="TGlzdEFwcGw6MTpBcHBsOjE6AZeJu/5OhffQsx5E+wHshVMhBl2Uqu/vvH2bYpL+lqh71pYqu0CjmpiBNFgEL90a0W5qno+xbjOnHolnKQ7XzmYeW2FtqCYDAKywPaBrcLkl0lYKfDokbJ+nOjC5W+9QWG4RTObWk2URkFFJ4GzLcXQhpnPxF6EquHrwjgDlL0MykUZwIu5Inw==" for.icloud.com / >, < Cookie X-APPLE-WEBAUTH-TOKEN="v=2:t=HA==BST_IAAAAAAABLwIAAAAAF6MNz0RDmdzLmljbG91ZC5hdXRovQDt3XVyzLZrs0HXuQ_NxzOf7P5Awastto2n0AeGVyR9D1gwr978yJbvX_K54xGSnGlLrcRJ3fzkH536F7X_ZanTRjB9_rD6dPr3ATvVwFl6D9emyFeRzT0fo0Mp5K0r35u86pauv8AJDnvNqnGAq-anZOruqg~~" for.icloud.com / >, < Cookie X-APPLE-WEBAUTH-USER="v=1:s=0:d=556903187" for.icloud.com / >, < Cookie X-APPLE-WEBAUTH-VALIDATE="v=1:t=HA==BST_IAAAAAAABLwIAAAAAF6MNz0RDmdzLmljbG91ZC5hdXRovQDt3XVyzLZrs0HXuQ_NxzOf7P5Awastto2n0AeGVyR9D1gwr978yJbvX_K54xGSnGlLrcRJ3fzkH536F7X_ZanTRjB9_rD6dPr3ATvVwFl6D5U0KyI3eucSnd5q6Yqi11JA5fHVb_RsoOtwW6_q5QYnOtcnjg~~" for.icloud.com / >, < Cookie X-Apple-GCBD-Cookie=1 for.icloud.com / >, < Cookie X_APPLE_WEB_KB-K3YK2TVYKD-6HH1VSP3AQAD9K58="v=1:t=Gw==BST_IAAAAAAABLwIAAAAAF6MNuMRDmdzLmljbG91ZC5hdXRovQDwC0mgBaGO70DEsMJA5FOM8rSa2TfmZRhosC5NfJ71X3ViKwXtnToVbJlUa9H8pBnby97krThU-pQcMA9Km3QUa1309EDoSXN7SRmNCph7EIYA8tvzZ8Lj87qecGKK6S1_zKoGyS-ftRsHGjnM0mR2jueAaA~~" for.icloud.com / >] >
