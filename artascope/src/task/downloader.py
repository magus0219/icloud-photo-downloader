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
    API_PAGE_SIZE,
)
from artascope.src.lib.auth_manager import LoginStatus
from artascope.src.util import get_logger
from artascope.src.lib.task_manager import tm
from artascope.src.patch.pyicloud import (
    patch_photo_asset,
    patch_photo_album,
)
from artascope.src.lib.auth_manager import AuthManager
from artascope.src.task.post_action.sftp import upload_to_sftp
from artascope.src.exception import (
    NeedLoginAgainException,
    ApiLimitException,
    GoneException,
    LoginTimeoutException,
)
from artascope.src.util.context_manager import (
    task_exception_handler,
    api_exception_handler,
)

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
        with api_exception_handler():
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
    task_name: str, username: str, batch: typing.List[PhotoAsset], offset: int, cnt: int
):
    """Workload of downloading one photo

    :param task_name:
    :param username:
    :param batch:
    :param offset:
    :param cnt:
    :return:
    """
    patch_photo_asset()
    patch_photo_album()

    am = AuthManager(username)
    with task_exception_handler(am) as api:
        if not api:
            raise LoginTimeoutException()

        photo_service = api.photos
        album_all = api.photos.all
        album_all.direction = "DESCENDING"
        album_all.page_size = API_PAGE_SIZE

        idx = 0
        while batch:
            try:
                for photo in batch:
                    fs = tm.load_file_status(photo.id)
                    # download file really needed
                    if fs.done is False:
                        photo._service = photo_service

                        logger.info(
                            "start download photo {name}:{size}".format(
                                name=photo.filename, size=str(photo.size)
                            )
                        )

                        if not tempdir.exists():
                            os.mkdir(tempdir)
                        filename = "{ts}_{filename}".format(
                            filename=photo.id, ts=int(photo.created.timestamp())
                        )
                        filepath = tempdir / filename

                        download_file(photo, filepath, photo.size)
                        logger.info("download photo {name} done.".format(name=filename))

                        upload_to_sftp.delay(
                            username=username,
                            src_filepath=str(filepath),
                            filename=photo.id,
                            created_dt=photo.created,
                        )
                        tm.finish_file_status(task_name, photo)
                        task = tm.load_task(task_name=task_name)
                        if task.cnt_done == task.cnt_total:
                            tm.finish_task(task_name)
                    else:
                        pass
                    idx += 1
                return
            except GoneException as e:
                offset -= idx
                cnt -= idx
                fetch_done = False
                while not fetch_done:
                    with api_exception_handler():
                        batch = album_all.fetch_photos(offset=offset, cnt=cnt)
                        fetch_done = True
                idx = 0
