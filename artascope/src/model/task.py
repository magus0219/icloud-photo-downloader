#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/30
from artascope.src.model.mixin import JsonDataMixin


class FileStatus(JsonDataMixin):
    def __init__(self, file_id, filename, size, created_ts, status=0):
        self.file_id = file_id
        self.filename = filename
        self.size = size
        self.created_ts = created_ts
        self.status = status


class TaskStatus:
    RUNNING = 1
    FAIL = 2
    SUCCESS = 3


TaskStatusText = {
    TaskStatus.RUNNING: "Running",
    TaskStatus.FAIL: "Fail",
    TaskStatus.SUCCESS: "Success",
}


class TaskRunType:
    ALL = 1
    LAST = 2
    DATE_RANGE = 3


TaskRunTypeText = {
    TaskRunType.ALL: "All",
    TaskRunType.LAST: "Last",
    TaskRunType.DATE_RANGE: "Date Range",
}


class TaskInfo(JsonDataMixin):
    def __init__(
        self,
        task_name: str,
        status: int,
        created_dt: int,
        username: str,
        run_type: int,
        cnt_total: int = 0,
        cnt_done: int = 0,
        last: int = None,
        date_start: int = None,
        date_end: int = None,
    ):
        self.task_name = task_name
        self.status = status
        self.created_dt = created_dt
        self.cnt_total = cnt_total
        self.cnt_done = cnt_done
        self.username = username
        self.run_type = run_type
        self.last = last
        self.date_start = date_start
        self.date_end = date_end
