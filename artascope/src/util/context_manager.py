#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/4
import time
from contextlib import contextmanager
from artascope.src.lib.auth_manager import AuthManager
from pyicloud.exceptions import (
    PyiCloudAPIResponseException,
    PyiCloudServiceNotActivatedException,
)
from artascope.src.exception import (
    NeedLoginAgainException,
    ApiLimitException,
    NeedWaitForCaptchaException,
)
from artascope.src.util import get_logger
from artascope.src.lib.auth_manager import LoginStatus
from artascope.src.config import (
    SECONDS_WAIT_AFTER_SEND_CAPTCHA,
    SECONDS_WAIT_FOR_API_LIMIT,
)


logger = get_logger("server")


@contextmanager
def api_exception_handler(auth: AuthManager):
    try:
        api = auth.login()
        if api:
            yield api
        else:
            # this state end with CAPTCHA_SENT
            logger.info("login fail:{}".format(str(auth.get_login_status())))
            if auth.get_login_status() == LoginStatus.CAPTCHA_SENT:
                # wait user to enter captcha
                time.sleep(SECONDS_WAIT_AFTER_SEND_CAPTCHA)
            yield NeedWaitForCaptchaException()
    except NeedWaitForCaptchaException as e:
        return
    except NeedLoginAgainException as e:
        logger.info("need login again")
        auth.set_login_status(LoginStatus.NEED_LOGIN_AGAIN)
        auth.login()
        return
    except PyiCloudServiceNotActivatedException as e:
        logger.info("index not finished, try after 10 minutes")
        time.sleep(SECONDS_WAIT_FOR_API_LIMIT)
        raise
    except ApiLimitException as e:
        logger.info("need slow down in download_file")
        time.sleep(SECONDS_WAIT_FOR_API_LIMIT)
        raise
    except PyiCloudAPIResponseException as e:
        auth.check_login_status()
        logger.exception(e)
        raise
    except Exception as e:
        auth.check_login_status()
        logger.exception(e)
        raise
