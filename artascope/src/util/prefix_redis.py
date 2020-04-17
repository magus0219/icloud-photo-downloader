#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/22
import redis
import functools


class PrefixRedis(object):
    """Redis client add prefix in front of key auto.

    """

    __support_functions__ = [
        "get",
        "set",
        "setex",
        "delete",
        "incr",
        "expire",
        "hset",
        "hget",
        "setnx",
        "hsetnx",
        "hgetall",
        "hmset",
        "hmget",
        "hincrby",
        "sadd",
        "spop",
        "scard",
        "smembers",
        "srem",
        "zadd",
        "zrange",
        "zscore",
        "zrangebyscore",
        "zrank",
        "lpush",
        "lrange",
    ]

    def __init__(self, prefix, **config):
        super(PrefixRedis, self).__init__()
        self._prefix = prefix + ":{}"
        self._r = redis.StrictRedis(**config)

    def __getattr__(self, key):
        if key not in self.__support_functions__:
            raise AttributeError("Prefix Redis does not have {} function".format(key))
        return self.prefix_wrapper(getattr(self._r, key))

    def prefix_wrapper(self, func):
        @functools.wraps(func)
        def wrapper(key, *args, **kwargs):
            return func(self._prefix.format(key), *args, **kwargs)

        return wrapper
