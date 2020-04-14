#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/3
import pytest
import json
from pyicloud.base import PyiCloudSession
from artascope.src.patch.pyicloud import patch_session
from artascope.test.conftest import DataException


class MockPyiCloudService:
    def __init__(self):
        self.session = PyiCloudSession(self)


class TestPyiCloudSession:
    def test_session_method(self, monkeypatch):
        def mock_request(self, *args, **kwargs):
            raise DataException({"args": args, "kwargs": kwargs})

        monkeypatch.setattr(PyiCloudSession, "request", mock_request)

        patch_session()
        api = MockPyiCloudService()

        data = {"args": ["GET", "url"], "kwargs": {"data": "abc", "json": None}}

        with pytest.raises(DataException,) as exc_info:
            api.session.get("url", data="abc")

        assert json.dumps(data, sort_keys=True) in str(exc_info.value)
        data = {"args": ["POST", "url"], "kwargs": {"data": "abc", "json": None}}

        with pytest.raises(DataException,) as exc_info:
            api.session.post("url", data="abc")
        assert json.dumps(data, sort_keys=True) in str(exc_info.value)
