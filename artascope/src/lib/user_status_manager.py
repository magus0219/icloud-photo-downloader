#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/28
import typing
from artascope.src.config import REDIS_CONFIG
from artascope.src.util.prefix_redis import PrefixRedis
from artascope.src.util.date_util import DateTimeUtil
from artascope.src.model.user_status import UserStatus


USER_STATUS_LIST_KEY = "list"


class UserStatusManager:
    def __init__(self, redis_config=REDIS_CONFIG):
        self._redis = PrefixRedis("user", **redis_config)

    def add_user(self, username: str) -> None:
        if self._redis.zrank(USER_STATUS_LIST_KEY, username) is not None:
            pass
        else:
            self._redis.zadd(
                USER_STATUS_LIST_KEY,
                {username: int(DateTimeUtil.get_now().timestamp())},
            )

    def get_user(self, username: str) -> typing.Union[UserStatus, None]:
        if self.exist_user(username):
            created_ts = int(self._redis.zscore(USER_STATUS_LIST_KEY, username))
            return UserStatus(username, created_ts)
        else:
            return None

    def exist_user(self, username: str) -> bool:
        rlt = self._redis.zrank(USER_STATUS_LIST_KEY, username)
        return True if rlt is not None else False

    def get_all_user(self) -> typing.Union[typing.List[UserStatus], None]:
        rlt = self._redis.zrange(USER_STATUS_LIST_KEY, 0, -1, withscores=True)
        if not rlt:
            return None
        else:
            users = []
            for username, created_ts in rlt:
                username = username.decode("utf8")
                users.append(UserStatus(username, created_ts))
            return users


usm = UserStatusManager()
