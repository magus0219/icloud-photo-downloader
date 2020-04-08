#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/31
import base64
import pytest
import datetime
from pyicloud.services.photos import PhotoAsset
from celery.result import AsyncResult
from artascope.src.lib.task_manager import (
    TaskRunType,
    TaskStatus,
    tm,
)
from artascope.src.model.task import TaskInfo
from artascope.src.util.date_util import DateTimeUtil
from artascope.src.exception import (
    TaskNotExisted,
    FileStatusNotExisted,
)


@pytest.fixture()
def photo_asset():
    master_record = {
        "recordName": "test_record",
        "fields": {
            "filenameEnc": {"value": base64.b64encode("test".encode("utf8"))},
            "resOriginalRes": {"value": {"size": 128}},
        },
    }
    return PhotoAsset({}, master_record, {})


@pytest.fixture()
def photo_asset2():
    master_record = {
        "recordName": "test_record2",
        "fields": {
            "filenameEnc": {"value": base64.b64encode("test2".encode("utf8"))},
            "resOriginalRes": {"value": {"size": 258}},
        },
    }
    return PhotoAsset({}, master_record, {})


class TestTaskManager:
    def test_get_celery_task_id(self, monkeypatch):
        assert tm.get_celery_task_id("task_name") is None

        tm.attach_celery_task_id("task_name", "task_id1")
        tm.attach_celery_task_id("task_name", "task_id2")

        assert tm.get_celery_task_id("task_name") == ["task_id2", "task_id1"]

    def test_celery_task_fail(self, monkeypatch):
        def mock_fail(self):
            if self.id == "task_id2":
                return False
            return True

        tm.attach_celery_task_id("task_name", "task_id1")
        tm.attach_celery_task_id("task_name", "task_id2")

        monkeypatch.setattr(AsyncResult, "failed", mock_fail)
        assert tm.check_fail("task_name") is True

    def test_celery_task_success(self, monkeypatch):
        def mock_fail(self):
            return False

        tm.attach_celery_task_id("task_name", "task_id1")
        tm.attach_celery_task_id("task_name", "task_id2")

        monkeypatch.setattr(AsyncResult, "failed", mock_fail)
        assert tm.check_fail("task_name") is False

    def test_load_not_exist_task(self):
        with pytest.raises(TaskNotExisted, match="unknown not existed"):
            tm.load_task("unknown")

    def test_update_task_total(self):
        tm.add_task(
            task_name="test_name", username="test_username", run_type=TaskRunType.ALL
        )
        tm.update_task_total(task_name="test_name", total=100)
        assert tm.load_task(task_name="test_name").cnt_total == 100

    def test_finish_task(self):
        tm.add_task(
            task_name="test_name", username="test_username", run_type=TaskRunType.ALL
        )
        tm.finish_task(task_name="test_name")
        assert tm.load_task(task_name="test_name").status == TaskStatus.SUCCESS
        assert tm.get_current_task_name(username="test_username") is None

    def test_fail_task(self):
        tm.add_task(
            task_name="test_name", username="test_username", run_type=TaskRunType.ALL
        )
        tm.fail_task(task_name="test_name")
        assert tm.load_task(task_name="test_name").status == TaskStatus.FAIL
        assert tm.get_current_task_name(username="test_username") is None

    def test_add_task(self, monkeypatch):
        dt = datetime.datetime(year=2000, month=1, day=1)

        def mock_get_now():
            return dt

        monkeypatch.setattr(DateTimeUtil, "get_now", mock_get_now)
        task = TaskInfo(
            task_name="test_name",
            created_dt=int(dt.timestamp()),
            username="test_username",
            run_type=TaskRunType.ALL,
            status=TaskStatus.RUNNING,
        )
        tm.add_task(
            task_name=task.task_name, username=task.username, run_type=task.run_type
        )

        assert tm.load_task(task.task_name) == task
        assert tm.get_task_list(username=task.username)[0] == task
        assert tm.get_task_list()[0] == task
        assert len(tm.get_task_list()) == 1

        assert tm.get_current_task_name(username=task.username) == task.task_name

    def test_add_file_status(self, photo_asset):
        tm.add_file_status("task_name", photo_asset)

        file_loaded = tm.load_file_status(photo_asset.id)
        assert file_loaded.file_id == photo_asset.id
        assert file_loaded.filename == photo_asset.filename
        assert file_loaded.size == photo_asset.size

    def test_load_not_existed_file_status(self):
        with pytest.raises(FileStatusNotExisted, match="unknown not existed"):
            tm.load_file_status("unknown")

    def test_update_file_status(self, photo_asset):
        tm.add_file_status("task_name", photo_asset)
        tm.update_file_status(photo_asset, 99)
        file_loaded = tm.load_file_status(photo_asset.id)
        assert file_loaded.status == 99

    def test_finish_file_status(self, photo_asset):
        tm.add_task(
            task_name="task_name", username="username", run_type=TaskRunType.ALL,
        )
        tm.add_file_status("task_name", photo_asset)
        tm.finish_file_status("task_name", photo_asset)
        file_loaded = tm.load_file_status(photo_asset.id)
        assert file_loaded.status == 100
        assert tm.load_task("task_name").cnt_done == 1

    def test_get_file_status_list(self, photo_asset, photo_asset2):
        tm.add_file_status("task_name", photo_asset)
        tm.add_file_status("task_name", photo_asset2)

        fs_list = tm.get_file_status_list("task_name")
        assert len(fs_list) == 2
        assert fs_list[1].file_id == photo_asset2.id
        assert fs_list[1].filename == photo_asset2.filename
        assert fs_list[1].size == photo_asset2.size
