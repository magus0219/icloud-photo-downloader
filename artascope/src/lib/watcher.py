#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/25
from artascope.src.util.prefix_redis import PrefixRedis
from artascope.src.config import REDIS_CONFIG
from artascope.src.util import get_logger
from artascope.src.util.date_util import DateTimeUtil

logger = get_logger("server.watcher")


class TaskInfo:
    def __init__(self, task_name: str, created_dt: int, cnt_total: int, cnt_done: int):
        self.task_name = task_name
        self.created_dt = created_dt
        self.cnt_total = cnt_total
        self.cnt_done = cnt_done


class FileStatus:
    def __init__(self, file_id, filename, size, created_ts, status):
        self.file_id = file_id
        self.filename = filename
        self.size = size
        self.created_ts = created_ts
        self.status = status


class Watcher:
    def __init__(self, redis_config=REDIS_CONFIG):
        self._redis_config = redis_config
        self._redis_client = PrefixRedis("watcher", **self._redis_config)

    def add_task(self, task_name, cnt_total):
        self._redis_client.zadd(
            "taskname", {task_name: int(DateTimeUtil.get_now().timestamp())}
        )
        self._redis_client.hmset(
            "taskinfo:{}".format(task_name), {"cnt_total": cnt_total, "cnt_done": 0}
        )

    def get_task_list(self):
        rlt = self._redis_client.zrange("taskname", 0, -1, withscores=True)
        task_list = []

        for task_name, created_ts in rlt:
            task_name = task_name.decode("utf8")
            info = self._redis_client.hgetall("taskinfo:{}".format(task_name))
            info = {k.decode("utf8"): v.decode("utf8") for k, v in info.items()}
            task_list.append(
                TaskInfo(
                    task_name,
                    int(created_ts),
                    int(info["cnt_total"]),
                    int(info["cnt_done"]),
                )
            )
        return task_list

    def add_file_status(self, task_name, file):
        self._redis_client.zadd(
            "fs:{}".format(task_name), {file.id: file.created.timestamp()}
        )
        self._redis_client.hmset(
            "fs:info:{}:{}".format(task_name, file.id),
            {"status": 0, "name": file.filename, "size": file.size},
        )

    def update_file_status(self, task_name, file, status: float):
        self._redis_client.hmset(
            "fs:info:{}:{}".format(task_name, file.id), {"status": status}
        )

    def finish_file_status(self, task_name, file):
        self._redis_client.hmset(
            "fs:info:{}:{}".format(task_name, file.id), {"status": 100}
        )
        self._redis_client.hincrby("taskinfo:{}".format(task_name), "cnt_done")

    def get_file_status(self, task_name):
        rlt = []
        files = self._redis_client.zrange(
            "fs:{}".format(task_name), 0, -1, withscores=True
        )
        for file_id, created_ts in files:
            file_id = file_id.decode("utf8")
            file_info = self._redis_client.hgetall(
                "fs:info:{}:{}".format(task_name, file_id)
            )
            file_info = {
                k.decode("utf8"): v.decode("utf8") for k, v in file_info.items()
            }

            rlt.append(
                FileStatus(
                    file_id,
                    file_info["name"],
                    int(file_info["size"]),
                    int(created_ts),
                    float(file_info["status"]),
                )
            )

        return rlt
