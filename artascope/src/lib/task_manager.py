#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/25
import typing
from celery.result import AsyncResult
from pyicloud.services.photos import PhotoAsset
from artascope.src.util.prefix_redis import PrefixRedis
from artascope.src.config import REDIS_CONFIG
from artascope.src.util import get_logger
from artascope.src.util.date_util import DateTimeUtil
from artascope.src.lib.msg_manager import MsgManager
from artascope.src.model.task import *
from artascope.src.exception import (
    TaskNotExisted,
    FileStatusNotExisted,
)

logger = get_logger("server.task")


CELERY_TASK_KEY = "celery_task"
TASK_LIST_KEY = "task"
TASK_BY_USER_KEY = "task_by_user"
TASK_INFO_KEY = "task_info"
TASK_CURRENT_KEY = "current"
FILE_LIST_KEY = "file"
FILE_INFO_KEY = "file_info"


class TaskManager:
    def __init__(self, redis_config=REDIS_CONFIG):
        self._redis_config = redis_config
        self._redis = PrefixRedis("task", **self._redis_config)

    def attach_celery_task_id(self, task_name: str, celery_task_id: str) -> None:
        self._redis.lpush(
            "{key}:{task_name}".format(key=CELERY_TASK_KEY, task_name=task_name),
            celery_task_id,
        )

    def get_celery_task_id(
        self, task_name: str
    ) -> typing.Union[None, typing.List[str]]:
        rlt = self._redis.lrange(
            "{key}:{task_name}".format(key=CELERY_TASK_KEY, task_name=task_name), 0, -1
        )
        if rlt:
            return [one.decode("utf8") for one in rlt]
        else:
            return None

    def check_fail(self, task_name: str) -> bool:
        tasks = self._redis.lrange(
            "{key}:{task_name}".format(key=CELERY_TASK_KEY, task_name=task_name), 0, -1
        )
        for one_task_id in tasks:
            one_task_id = one_task_id.decode("utf8")
            from artascope.src.celery_app import app

            if AsyncResult(one_task_id, backend=app.backend).failed():
                return True
        return False

    def load_task(self, task_name: str) -> typing.Union[TaskNotExisted, TaskInfo]:
        json_str = self._redis.get(
            "{key}:{task_name}".format(key=TASK_INFO_KEY, task_name=task_name)
        )
        if not json_str:
            raise (
                TaskNotExisted("{task_name} not existed".format(task_name=task_name))
            )
        else:
            task_info = TaskInfo.load_by_json(json_str)
            return task_info

    def save_task(self, task: TaskInfo) -> None:
        self._redis.set(
            "{key}:{task_name}".format(key=TASK_INFO_KEY, task_name=task.task_name),
            task.extract_to_json(),
        )

    def fail_task(self, task_name: str) -> None:
        task = self.load_task(task_name)
        task.status = TaskStatus.FAIL
        self.save_task(task)

        tasks = self._redis.lrange(
            "{key}:{task_name}".format(key=CELERY_TASK_KEY, task_name=task_name), 0, -1
        )

        if self.get_current_task_name(task.username) == task_name:
            self.clear_current_task_name(task.username)

        for one_task_id in tasks:
            one_task_id = one_task_id.decode("utf8")
            from artascope.src.celery_app import app

            AsyncResult(one_task_id, backend=app.backend).revoke(terminate=True)

        MsgManager.send_message(
            username=task.username,
            msg="Sync Task[{task_name}] of User [{user}] failed!\n{content}".format(
                task_name=task.task_name, user=task.username, content=str(task)
            ),
        )

    def update_task_total(self, task_name: str, total: int) -> None:
        task = self.load_task(task_name)
        task.cnt_total = total
        self.save_task(task)

    def incr_task_done(self, task_name: str) -> None:
        task = self.load_task(task_name)
        task.cnt_done += 1
        self.save_task(task)

    def finish_task(self, task_name: str) -> None:
        task = self.load_task(task_name)
        task.status = TaskStatus.SUCCESS
        self.save_task(task)
        self.clear_current_task_name(task.username)

        MsgManager.send_message(
            username=task.username,
            msg="Sync Task[{task_name}] of User [{user}] succeeded!\n{content}".format(
                task_name=task.task_name, user=task.username, content=str(task)
            ),
        )

    def clear_current_task_name(self, username: str) -> None:
        self._redis.delete(
            "{key}:{username}".format(key=TASK_CURRENT_KEY, username=username)
        )

    def set_current_task_name(self, username: str, task_name: str) -> None:
        self._redis.set(
            "{key}:{username}".format(key=TASK_CURRENT_KEY, username=username),
            task_name,
        )

    def get_current_task_name(self, username: str) -> typing.Union[None, str]:
        rlt = self._redis.get(
            "{key}:{username}".format(key=TASK_CURRENT_KEY, username=username)
        )
        if rlt:
            return rlt.decode("utf8")
        else:
            return None

    def add_task(
        self,
        task_name: str,
        username: str,
        run_type: int,
        last: int = None,
        date_start: int = None,
        date_end: int = None,
    ) -> None:
        now_timestamp = int(DateTimeUtil.get_now().timestamp())
        self._redis.zadd(TASK_LIST_KEY, {task_name: now_timestamp})
        self._redis.zadd(
            "{key}:{username}".format(key=TASK_BY_USER_KEY, username=username),
            {task_name: now_timestamp},
        )

        task = TaskInfo(
            task_name=task_name,
            status=TaskStatus.RUNNING,
            created_dt=now_timestamp,
            username=username,
            run_type=run_type,
            last=last,
            date_start=date_start,
            date_end=date_end,
        )
        self.save_task(task)
        self.set_current_task_name(username, task_name)

        MsgManager.send_message(
            username=task.username,
            msg="Sync Task[{task_name}] of User [{user}] started!\n{content}".format(
                task_name=task.task_name, user=task.username, content=str(task)
            ),
        )

    def get_task_list(self, username: str = None) -> typing.List[TaskInfo]:
        if not username:
            rlt = self._redis.zrange(TASK_LIST_KEY, 0, -1, withscores=True)
        else:
            rlt = self._redis.zrange(
                "{key}:{username}".format(key=TASK_BY_USER_KEY, username=username),
                0,
                -1,
                withscores=True,
            )

        task_list = []

        for task_name, created_ts in rlt:
            task_name = task_name.decode("utf8")
            task_str = self._redis.get(
                "{key}:{task_name}".format(key=TASK_INFO_KEY, task_name=task_name)
            )
            task_list.append(TaskInfo.load_by_json(task_str))
        return task_list

    def add_file_status(self, task_name: str, file: PhotoAsset):
        self._redis.zadd(
            "{key}:{task_name}".format(key=FILE_LIST_KEY, task_name=task_name),
            {file.id: file.created.timestamp()},
        )

        fs = FileStatus(
            file_id=file.id,
            filename=file.filename,
            size=file.size,
            created_ts=file.created.timestamp(),
        )
        self.save_file_status(fs)

    def save_file_status(self, file_status: FileStatus) -> None:
        self._redis.set(
            "{key}:{file_id}".format(key=FILE_INFO_KEY, file_id=file_status.file_id),
            file_status.extract_to_json(),
        )

    def load_file_status(
        self, file_id: str
    ) -> typing.Union[FileStatusNotExisted, FileStatus]:
        json_str = self._redis.get(
            "{key}:{file_id}".format(key=FILE_INFO_KEY, file_id=file_id)
        )
        if not json_str:
            raise (
                FileStatusNotExisted("{file_id} not existed".format(file_id=file_id))
            )
        else:
            fs = FileStatus.load_by_json(json_str)
            return fs

    def update_file_status(self, file: PhotoAsset, status: float) -> None:
        fs = self.load_file_status(file.id)
        fs.status = status
        self.save_file_status(fs)

    def finish_file_status(self, task_name: str, file: PhotoAsset) -> None:
        fs = self.load_file_status(file.id)
        fs.status = 100
        if fs.done is False:
            self.incr_task_done(task_name)
            fs.done = True
        self.save_file_status(fs)

    def get_file_status_list(self, task_name: str) -> typing.List[FileStatus]:
        rlt = []
        files = self._redis.zrange(
            "{key}:{task_name}".format(key=FILE_LIST_KEY, task_name=task_name),
            0,
            -1,
            withscores=True,
        )
        for file_id, created_ts in files:
            file_id = file_id.decode("utf8")
            rlt.append(self.load_file_status(file_id))

        return rlt


tm = TaskManager()
