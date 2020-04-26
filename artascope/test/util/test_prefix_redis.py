#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/26
import pytest
from artascope.src.util.prefix_redis import PrefixRedis


@pytest.fixture()
def client():
    return PrefixRedis("test")


class TestPrefixRedis:
    def test_prefix(self, client):
        client.set("key", "val")
        assert client.get("key").decode("utf8") == "val"

    def test_unsupport_cmd(self, client):
        with pytest.raises(AttributeError, match="cmdcmd"):
            client.cmdcmd()
