#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/22
import os
import tempfile
import datetime
import paramiko
import pytz
from typing import List
from pyicloud.services.photos import PhotoAsset
from artascope.src.celery_app import app as celery_app
from artascope.src.lib.auth import Auth
from artascope.src.util import get_logger
from artascope.src.util.date_util import DateUtil
from artascope.src.config import (
    TARGET,
    TARGET_DIR,
    BATCH_CNT,
)
from artascope.src.lib.watcher import Watcher
from artascope.src.util.latch import Latch
from artascope.src.patch.pyicloud import (
    patch_photo_album,
    patch_photo_asset,
)

logger = get_logger("server.sync")

tz_shanghai = pytz.timezone("Asia/Shanghai")

artascope_tempdir = tempfile.gettempdir() + os.sep + "artascope"
logger.info("tempdir:{}".format(artascope_tempdir))


def get_file_size(filename: str):
    try:
        size = os.stat(filename).st_size
    except Exception as e:
        size = 0
    return size


def modify_meta(
    sftp_client: paramiko.sftp_client,
    filepath: str,
    filename: str,
    created_dt: datetime.datetime,
):
    file_type = filename.split(".")[-1].lower()
    created_dt = created_dt.timestamp()

    if file_type in ("png", "jpg", "jepg"):
        sftp_client.utime(filepath, (created_dt, created_dt))


def download_file(task_name: str, photo: PhotoAsset, filename: str, file_size: int):
    watcher = Watcher()
    size_downloaded = get_file_size(filename)
    latch = Latch("api", 10)

    while size_downloaded < file_size:
        try:
            photo._service.session.headers["Range"] = "bytes=%d-" % size_downloaded
            logger.debug("headers {}".format(str(photo._service.session.headers)))
            latch.lock()
            download = photo.download(timeout=30)
            has_downloaded = size_downloaded
            with open(filename, "ab") as opened_file:
                for content in download.iter_content(chunk_size=8192):
                    opened_file.write(content)
                    has_downloaded += len(content)
                    watcher.update_file_status(
                        task_name, photo, has_downloaded / file_size * 100
                    )
                    logger.debug(
                        "{percent:5.2f}% {cnt:d} B".format(
                            percent=has_downloaded / file_size * 100, cnt=has_downloaded
                        )
                    )
        except TimeoutError as e:
            logger.exception(e)
        except Exception as e:
            raise
        finally:
            size_downloaded = get_file_size(filename)


@celery_app.task(autoretry_for=(Exception,), retry_backoff=True)
def download_photo(
    task_name: str, batch: List[PhotoAsset], username: str, password: str
):
    auth = Auth(username, password)
    icloud_api = auth.login()
    photo_service = icloud_api.photos
    watcher = Watcher()
    try:
        for photo in batch:
            photo._service = photo_service

            logger.info(
                "start download photo {name}:{size}".format(
                    name=photo.filename, size=str(photo.size)
                )
            )

            if not os.path.exists(artascope_tempdir):
                os.mkdir(artascope_tempdir)
            filename = artascope_tempdir + os.sep + photo.filename

            download_file(task_name, photo, filename, photo.size)
            logger.info("download photo {name} done.".format(name=photo.filename))
            if "Range" in photo._service.session.headers:
                del photo._service.session.headers["Range"]
            logger.debug(
                "headers removed {}".format(str(photo._service.session.headers))
            )

            upload_to_server.delay(
                filepath=filename,
                filename=photo.filename,
                created_dt=photo.created.astimezone(tz_shanghai),
            )
            watcher.finish_file_status(task_name, photo)
    except Exception as e:
        auth.check_login_status()
        logger.exception(e)
        patch_photo_asset()
        raise


@celery_app.task(
    autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5}
)
def upload_to_server(filepath: str, filename: str, created_dt: datetime.datetime):
    ssh_client = paramiko.client.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy)
    ssh_client.connect(**TARGET)

    sftp_client = ssh_client.open_sftp()
    sftp_client.chdir(TARGET_DIR)

    date_folder = DateUtil.get_str_from_date(created_dt)
    if date_folder not in sftp_client.listdir():
        sftp_client.mkdir(date_folder)

    target_filepath = date_folder + "/" + filename
    logger.info("target position:{}".format(target_filepath))
    try:
        sftp_client.remove(target_filepath)
    except FileNotFoundError as e:
        pass
    sftp_client.put(filepath, target_filepath)
    modify_meta(sftp_client, target_filepath, filename, created_dt)

    os.remove(filepath)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def sync(self, username: str, password: str):
    auth = Auth(username, password)
    watcher = Watcher()
    try:
        icloud_api = auth.login()
        if icloud_api:
            logger.info("login success")

            patch_photo_asset()
            patch_photo_album()

            album_all = icloud_api.photos.all
            album_all.direction = "DESCENDING"
            logger.info("album direction:{}".format(album_all.direction))

            album_len = len(album_all)
            task_name = self.request.id
            logger.info("album_len:{}".format(str(album_len)))
            watcher.add_task(task_name, album_len)

            cnt = 0
            photos = [photo for photo in album_all.fetch_photos(album_len)]
            logger.info("get photos meta data done.")
            batch = []
            for photo in photos:
                watcher.add_file_status(task_name, photo)
                logger.debug(
                    "{}:{}".format(
                        photo.filename, photo.created.astimezone(tz_shanghai)
                    )
                )
                batch.append(photo)

                if len(batch) == BATCH_CNT:
                    download_photo.delay(task_name, batch, username, password)
                    batch = []
                cnt += 1

            download_photo.delay(task_name, batch, username, password)
            logger.info("Need download {} photos".format(str(cnt)))
        else:
            logger.info("login fail:{}".format(str(auth.get_login_status())))

    except Exception as e:
        auth.check_login_status()
        logger.exception(e)
        raise


# pyicloud.exceptions.PyiCloudAPIResponseException: Invalid global session
# ERROR/ForkPoolWorker-3] Socket exception: Connection reset by peer (54)
# pyicloud.exceptions.PyiCloudAPIResponseException: Gone (410)
