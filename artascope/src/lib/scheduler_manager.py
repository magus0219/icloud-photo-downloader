#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/17
import typing
from apscheduler.schedulers.background import BackgroundScheduler
from artascope.src.util.prefix_redis import PrefixRedis
from artascope.src.config import REDIS_CONFIG

CHANGE_USER_SET_KEY = "cus"
JOB_ID_KEY = "jid"
JOB_INFO_KEY = "jinfo"


class SchedulerManager:
    def __init__(self, redis_config=REDIS_CONFIG):
        self._redis_config = redis_config
        self._redis = PrefixRedis("schd", **self._redis_config)

    def add_user(self, username: str) -> None:
        self._redis.sadd("{key}".format(key=CHANGE_USER_SET_KEY), username)

    def get_one_user(self) -> typing.Union[str, None]:
        rlt = self._redis.spop("{key}".format(key=CHANGE_USER_SET_KEY))
        if rlt:
            return rlt.decode("utf8")
        else:
            return None

    def get_user_cnt(self) -> int:
        return self._redis.scard("{key}".format(key=CHANGE_USER_SET_KEY))

    def get_job_id(self, username: str) -> typing.Union[str, None]:
        rlt = self._redis.get(
            "{key}:{username}".format(key=JOB_ID_KEY, username=username)
        )
        if rlt:
            return rlt.decode("utf8")
        else:
            return None

    def del_job(self, username: str) -> None:
        self._redis.delete("{key}:{username}".format(key=JOB_ID_KEY, username=username))

    def add_job(self, username: str, job_id: str) -> None:
        self._redis.set(
            "{key}:{username}".format(key=JOB_ID_KEY, username=username), job_id
        )

    def save_job_info(self, schd: BackgroundScheduler) -> None:
        jobs = schd.get_jobs()
        info = "\n".join(
            [
                "{orignal_info} kwargs:{kwargs}".format(
                    orignal_info=str(job), kwargs=str(job.kwargs)
                )
                for job in jobs
            ]
        )
        self._redis.set("{key}".format(key=JOB_INFO_KEY), info)

    def get_job_info(self) -> typing.List[str]:
        rlt = self._redis.get("{key}".format(key=JOB_INFO_KEY))
        if rlt:
            return rlt.decode("utf8").split("\n")
        else:
            return None


sm = SchedulerManager()
