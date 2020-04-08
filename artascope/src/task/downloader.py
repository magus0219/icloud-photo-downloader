#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/3
import os
import socket
import typing
import tempfile

from pathlib import Path
from artascope.src.celery_app import app as celery_app
from requests.exceptions import ConnectionError
from pyicloud.exceptions import (
    PyiCloudAPIResponseException,
    PyiCloudServiceNotActivatedException,
)
from pyicloud.services.photos import PhotoAsset
from artascope.src.config import (
    DEBUG,
    API_FILE_DOWNLOAD_CHUNK_SIZE,
    SECONDS_WAIT_FOR_API_LIMIT,
    SECONDS_WAIT_AFTER_SEND_CAPTCHA,
)
from artascope.src.lib.auth_manager import LoginStatus
from artascope.src.util import get_logger
from artascope.src.lib.task_manager import tm
from artascope.src.patch.pyicloud import patch_photo_asset
from artascope.src.lib.auth_manager import AuthManager
from artascope.src.task.post_action.sftp import upload_to_sftp
from artascope.src.exception import NeedLoginAgainException, ApiLimitException
from artascope.src.util.context_manager import api_exception_handler

logger = get_logger("server")

tempdir = Path(tempfile.gettempdir()) / "artascope"


def get_file_size(filepath: Path) -> int:
    try:
        size = os.stat(str(filepath)).st_size
    except Exception as e:
        size = 0
    return size


def download_file(photo: PhotoAsset, filepath: Path, file_size: int) -> None:
    """Download file from pyicloud photo service, support resume broken download process

    :param photo:
    :param filepath:
    :param file_size:
    :return:
    """
    size_downloaded = get_file_size(filepath)

    while size_downloaded < file_size:
        try:
            photo._service.session.headers["Range"] = "bytes=%d-" % size_downloaded
            download = photo.download(timeout=30)
            has_downloaded = size_downloaded
            with open(str(filepath), "ab") as opened_file:
                for content in download.iter_content(
                    chunk_size=API_FILE_DOWNLOAD_CHUNK_SIZE
                ):
                    opened_file.write(content)
                    has_downloaded += len(content)
                    tm.update_file_status(photo, has_downloaded / file_size * 100)
                    logger.debug(
                        "{percent:5.2f}% {cnt:d} B".format(
                            percent=has_downloaded / file_size * 100, cnt=has_downloaded
                        )
                    )
        except (ConnectionError, socket.timeout) as e:
            pass
        except PyiCloudAPIResponseException as e:
            if DEBUG:
                logger.exception(e)
            if "Gone (410)" in str(e):
                logger.info("Gone（410）happened.")
                raise NeedLoginAgainException()
            if "Invalid global session" in str(e):
                raise NeedLoginAgainException()
            elif "private db access disabled for this account" in str(e):
                raise ApiLimitException()
            else:
                raise
        except Exception as e:
            raise
        finally:
            size_downloaded = get_file_size(filepath)
            if "Range" in photo._service.session.headers:
                del photo._service.session.headers["Range"]


@celery_app.task(
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_backoff_max=900,
    retry_kwargs={"max_retries": 10},
)
def download_photo(
    task_name: str, username: str, batch: typing.List[PhotoAsset],
):
    """Workload of downloading one photo

    :param task_name:
    :param username:
    :param batch:
    :return:
    """
    patch_photo_asset()

    am = AuthManager(username)
    with api_exception_handler(am) as api:
        if isinstance(api, Exception):
            raise api
        photo_service = api.photos
        for photo in batch:
            photo._service = photo_service

            logger.info(
                "start download photo {name}:{size}".format(
                    name=photo.filename, size=str(photo.size)
                )
            )

            if not tempdir.exists():
                os.mkdir(tempdir)
            filename = "{ts}_{filename}".format(
                filename=photo.filename, ts=int(photo.created.timestamp())
            )
            filepath = tempdir / filename

            download_file(photo, filepath, photo.size)
            logger.info("download photo {name} done.".format(name=filename))

            upload_to_sftp.delay(
                username=username,
                src_filepath=str(filepath),
                filename=photo.filename,
                created_dt=photo.created,
            )
            tm.finish_file_status(task_name, photo)
            task = tm.load_task(task_name=task_name)
            if task.cnt_done == task.cnt_total:
                tm.finish_task(task_name)


# normal
# [2020-04-07 21:55:42,378: DEBUG/ForkPoolWorker-1] GET https://cvws.icloud-content.com/B/Abv37U_7aI2OUshfP8wio7uyH7H_ASZfb9tzkbTY7puNXEcZmE-App6r/${f}?o=AhovPwGCpUimsEYxvO6y8LLWZe1fsluNtiDb-jl7MKES&v=1&x=3&a=CAogKqJpxNBgwa6Y_zSIRgKsq-ajZpLU9JNwh5RxxGv6G3ISHRCmrtmllS4Ypou1p5UuIgEAUgSyH7H_WgSApp6r&e=1586267768&k=fNvhFtIaC-bdvCTKrEeeHg&fl=&r=617a0944-5466-4e0f-94a7-78b81f8c41c4-1&ckc=com.apple.photos.cloud&ckz=PrimarySync&y=1&p=69&s=eV21EQJL4n-My-Hx0Bym0zkt98M
# [2020-04-07 21:55:43,099: DEBUG/ForkPoolWorker-1] https://cvws.icloud-content.com:443 "GET /B/Abv37U_7aI2OUshfP8wio7uyH7H_ASZfb9tzkbTY7puNXEcZmE-App6r/$%7Bf%7D?o=AhovPwGCpUimsEYxvO6y8LLWZe1fsluNtiDb-jl7MKES&v=1&x=3&a=CAogKqJpxNBgwa6Y_zSIRgKsq-ajZpLU9JNwh5RxxGv6G3ISHRCmrtmllS4Ypou1p5UuIgEAUgSyH7H_WgSApp6r&e=1586267768&k=fNvhFtIaC-bdvCTKrEeeHg&fl=&r=617a0944-5466-4e0f-94a7-78b81f8c41c4-1&ckc=com.apple.photos.cloud&ckz=PrimarySync&y=1&p=69&s=eV21EQJL4n-My-Hx0Bym0zkt98M HTTP/1.1" 200 12560287
# 410 after 1 hour
# [2020-04-07 21:58:19,544: DEBUG/ForkPoolWorker-1] GET https://cvws.icloud-content.com/B/AS-uPA19alOCkx-z5bxmy-aUbYwzATaGuaasjapoF-8SUz9mn0FRvCUl/${f}?o=AnrEySPlMmdojcaEHqaX54WQX8Wfq2un-FHsC0C0S_I3&v=1&x=3&a=CAogEkMHIbPp49a6cvxmBgNVENjixhJwugjwCAPof3c2x4MSHRCyrtmllS4Ysou1p5UuIgEAUgSUbYwzWgRRvCUl&e=1586267768&k=MAh32XQOuDVPahLkJKrfXA&fl=&r=617a0944-5466-4e0f-94a7-78b81f8c41c4-1&ckc=com.apple.photos.cloud&ckz=PrimarySync&y=1&p=69&s=rb-IWdZn9HGwJjG6aKVAg7_IA4U
# [2020-04-07 21:58:19,588: DEBUG/ForkPoolWorker-1]
# https://cvws.icloud-content.com:443 "GET /B/AS-uPA19alOCkx-z5bxmy-aUbYwzATaGuaasjapoF-8SUz9mn0FRvCUl/$%7Bf%7D?o=AnrEySPlMmdojcaEHqaX54WQX8Wfq2un-FHsC0C0S_I3&v=1&x=3&a=CAogEkMHIbPp49a6cvxmBgNVENjixhJwugjwCAPof3c2x4MSHRCyrtmllS4Ysou1p5UuIgEAUgSUbYwzWgRRvCUl&e=1586267768&k=MAh32XQOuDVPahLkJKrfXA&fl=&r=617a0944-5466-4e0f-94a7-78b81f8c41c4-1&ckc=com.apple.photos.cloud&ckz=PrimarySync&y=1&p=69&s=rb-IWdZn9HGwJjG6aKVAg7_IA4U HTTP/1.1" 410 4
# relogin
# https://cvws.icloud-content.com:443 "GET /B/AVLWpmdZ_GqkbNDFXP6Pbc2f3CXlAXN7o2zVO76Ae92fBpibprIrsLn6/$%7Bf%7D?o=Ah2Be1wsEnrIvY_767PGDcJ1sv899Y6_7zIN62CZQSAb&v=1&x=3&a=CAogwxWK3PEufEf82KEeT8LH95N1Clv_4MwVjVDZed9wcF4SHRD2z9qllS4Y9qy2p5UuIgEAUgSf3CXlWgQrsLn6&e=1586267788&k=KI44KjSqLmxLXXWJRK-1uw&fl=&r=0814c8ed-53fe-46ed-899d-01e2aa9ae771-1&ckc=com.apple.photos.cloud&ckz=PrimarySync&y=1&p=69&s=i3mpaYERz4yyPS7FLQH9GDugnBY HTTP/1.1" 410 4
