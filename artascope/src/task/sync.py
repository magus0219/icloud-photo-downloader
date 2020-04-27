#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/4
import datetime
import uuid
import pytz
from artascope.src.celery_app import app as celery_app
from artascope.src.lib.auth_manager import AuthManager
from artascope.src.util import get_logger
from artascope.src.config import (
    BATCH_CNT,
    API_PAGE_SIZE,
    TIMEZONE,
)
from artascope.src.lib.task_manager import (
    tm,
    TaskRunType,
)
from artascope.src.task.downloader import download_photo
from artascope.src.patch.pyicloud import (
    patch_photo_album,
    patch_photo_asset,
)
from artascope.src.exception import LoginTimeout
from artascope.src.util.context_manager import (
    task_exception_handler,
    api_exception_handler,
)
from artascope.src.util.date_util import DateTimeUtil

logger = get_logger("server")

tz = pytz.timezone(TIMEZONE)


def decide_run_type(
    last=None, date_start: datetime.date = None, date_end: datetime.date = None
):
    if last is None and date_start is None and date_end is None:
        return TaskRunType.ALL
    elif last is not None:
        return TaskRunType.LAST
    elif date_start is not None:
        return TaskRunType.DATE_RANGE


def get_task_name(
    username: str,
    last: int = None,
    date_start: datetime.date = None,
    date_end: datetime.date = None,
):
    task_name = tm.get_current_task_name(username=username)
    if not task_name:
        task_name = uuid.uuid4().hex
        tm.add_task(
            task_name=task_name,
            username=username,
            run_type=decide_run_type(last, date_start, date_end),
            last=last,
            date_start=int(DateTimeUtil.get_datetime_from_date(date_start).timestamp())
            if date_start
            else None,
            date_end=int(DateTimeUtil.get_datetime_from_date(date_end).timestamp())
            if date_end
            else None,
        )
    return task_name


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def sync(
    self,
    username: str,
    password: str,
    last: int = None,
    date_start: datetime.date = None,
    date_end: datetime.date = None,
) -> str:
    logger.info("handle celery task:{}".format(self.request.id))
    task_name = get_task_name(
        username=username, last=last, date_start=date_start, date_end=date_end
    )
    tm.attach_celery_task_id(task_name, self.request.id)
    am = AuthManager(username, password)
    with task_exception_handler(am) as api:
        if not api:
            raise LoginTimeout()

        patch_photo_asset()
        patch_photo_album()

        with api_exception_handler():
            album_all = api.photos.all
            album_all.direction = "DESCENDING"
            album_all.page_size = API_PAGE_SIZE

            offset, cnt = album_all.calculate_offset_and_cnt(
                last=last, date_start=date_start, date_end=date_end
            )

            photos = [photo for photo in album_all.fetch_photos(offset=offset, cnt=cnt)]

        assert len(photos) == cnt
        tm.update_task_total(task_name, cnt)
        logger.info("get photos meta data done.")

        if cnt == 0:
            # nothing to do
            tm.finish_task(task_name)

        else:
            batch = []
            for photo in photos:
                tm.add_file_status(task_name, photo)
                logger.debug(
                    "{}:{}".format(photo.filename, photo.created.astimezone(tz))
                )
                batch.append(photo)

                if len(batch) == BATCH_CNT:
                    rlt = download_photo.delay(
                        task_name, username, batch, offset, BATCH_CNT
                    )
                    tm.attach_celery_task_id(task_name, rlt.id)
                    batch = []
                    offset -= BATCH_CNT

            if len(batch):
                rlt = download_photo.delay(
                    task_name, username, batch, offset, len(batch)
                )
                tm.attach_celery_task_id(task_name, rlt.id)
        logger.info("Need download {} photos".format(cnt))

        return task_name
