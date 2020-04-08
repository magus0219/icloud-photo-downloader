#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/28
from artascope.src.model.user_config import UserConfig
from artascope.src.config import REDIS_CONFIG
from artascope.src.util.prefix_redis import PrefixRedis


class UserConfigManager:
    def __init__(self, redis_config=REDIS_CONFIG):
        self._redis = PrefixRedis("setting", **redis_config)

    def save(self, config: UserConfig):
        from artascope.src.lib.user_status_manager import usm

        if not usm.exist_user(config.icloud_username):
            usm.add_user(config.icloud_username)
        self._redis.set(
            "{username}".format(username=config.icloud_username),
            config.extract_to_json(),
        )

    def load(self, username: str):
        rlt = self._redis.get("{username}".format(username=username))

        if not rlt:
            return None
        else:
            return UserConfig.load_by_json(rlt)


ucm = UserConfigManager()
