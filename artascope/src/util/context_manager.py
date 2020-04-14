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
    UnableToSendCaptchaException,
    LoginTimeoutException,
)
from artascope.src.util.date_util import DateTimeUtil
from artascope.src.util import get_logger
from artascope.src.lib.auth_manager import LoginStatus
from artascope.src.config import (
    SECONDS_WAIT_AFTER_LOGIN_FAIL,
    SECONDS_WAIT_FOR_API_LIMIT,
    SECONDS_WAIT_LOGIN,
)


logger = get_logger("server")


@contextmanager
def api_exception_handler(auth: AuthManager):
    try:
        start_ts = DateTimeUtil.get_now()
        api = auth.login()
        while not api:
            logger.info("login fail:{}".format(str(auth.get_login_status())))
            status = auth.get_login_status()
            if status == LoginStatus.CAPTCHA_SENT:
                # wait user to enter captcha
                logger.info("wait for user to enter captcha")
            elif status == LoginStatus.CAPTCHA_WRONG:
                logger.info("receive wrong captcha")

            now_ts = DateTimeUtil.get_now()
            if (now_ts - start_ts).seconds > SECONDS_WAIT_LOGIN:
                yield None
            time.sleep(SECONDS_WAIT_AFTER_LOGIN_FAIL)
            api = auth.login()
        else:
            yield api
    except LoginTimeoutException as e:
        logger.info("login timeout")
        raise
    except UnableToSendCaptchaException as e:
        logger.info("something is wrong")
        raise
    except NeedLoginAgainException as e:
        logger.info("need login again")
        auth.prepare_to_login_again()
        raise
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
