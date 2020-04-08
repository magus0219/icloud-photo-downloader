#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/3
import pytest
import json
from pyicloud.base import PyiCloudSession
from artascope.src.patch.pyicloud import patch_session


class DataException(Exception):
    def __init__(self, data: dict):
        self.data = data

    def __str__(self):
        print("aha", json.dumps(self.data, sort_keys=True).encode())
        return json.dumps(self.data, sort_keys=True)


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

        print("hah", json.dumps(data, sort_keys=True).encode())
        with pytest.raises(DataException,) as excinfo:
            api.session.get("url", data="abc")

        assert json.dumps(data, sort_keys=True) in str(excinfo.value)
        data = {"args": ["POST", "url"], "kwargs": {"data": "abc", "json": None}}

        with pytest.raises(DataException,) as excinfo:
            api.session.post("url", data="abc")
        assert json.dumps(data, sort_keys=True) in str(excinfo.value)
