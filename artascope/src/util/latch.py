#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/23
import math
import time
from artascope.src.util.prefix_redis import PrefixRedis
from artascope.src.util import get_logger
from artascope.src.config import REDIS_CONFIG

logger = get_logger("server.latch")


class Latch:
    def __init__(self, latch_name: str, limit_per_min: int, redis_config=REDIS_CONFIG):
        self.latch_name = latch_name
        self.limit_per_min = limit_per_min
        self.expire = math.floor(60 / self.limit_per_min)
        self._redis_config = redis_config
        self._redis = PrefixRedis("latch", **self._redis_config)

    def lock(self):
        rlt = self._redis.set(self.latch_name, "lock", ex=self.expire, nx=True)
        logger.debug("lock:{}".format(str(rlt)))
        while not rlt:
            time.sleep(1)
            rlt = self._redis.set(self.latch_name, "lock", ex=self.expire, nx=True)
            logger.debug("lock:{}".format(str(rlt)))

    def __getstate__(self):
        state = self.__dict__.copy()
        # Remove the unpicklable entries.
        del state["_redis"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self._redis = PrefixRedis("latch", **self._redis_config)
