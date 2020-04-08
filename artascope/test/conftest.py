#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/4
import pytest
import redis
import datetime
import base64
from pyicloud.services.photos import PhotoAsset
from artascope.src.config import (
    REDIS_CONFIG,
    TIMEZONE,
)
from artascope.src.lib.task_manager import (
    tm,
    TaskRunType,
)

MOCK_PHOTO_ASSET_DATA = [
    {
        "master": {
            "recordName": "record1",
            "fields": {
                "filenameEnc": {"value": base64.b64encode("filename1".encode("utf8"))},
                "resOriginalRes": {"value": {"size": 258}},
            },
        },
        "asset": {
            "fields": {
                "assetDate": {
                    "value": datetime.datetime(year=2020, month=1, day=1).timestamp()
                    * 1000
                },
                "masterRef": {"value": {"recordName": "record1"}},
            }
        },
    },
    {
        "master": {
            "recordName": "record2",
            "fields": {
                "filenameEnc": {"value": base64.b64encode("filename2".encode("utf8"))},
                "resOriginalRes": {"value": {"size": 258}},
            },
        },
        "asset": {
            "fields": {
                "assetDate": {
                    "value": datetime.datetime(year=2020, month=1, day=2).timestamp()
                    * 1000
                },
                "masterRef": {"value": {"recordName": "record2"}},
            }
        },
    },
    {
        "master": {
            "recordName": "record3",
            "fields": {
                "filenameEnc": {"value": base64.b64encode("filename3".encode("utf8"))},
                "resOriginalRes": {"value": {"size": 258}},
            },
        },
        "asset": {
            "fields": {
                "assetDate": {
                    "value": datetime.datetime(year=2020, month=1, day=3).timestamp()
                    * 1000
                },
                "masterRef": {"value": {"recordName": "record3"}},
            }
        },
    },
]


@pytest.fixture()
def photos():
    tm.add_task(task_name="task_name", username="username", run_type=TaskRunType.ALL)
    tm.update_task_total(task_name="task_name", total=len(MOCK_PHOTO_ASSET_DATA))
    photos = []
    for one in MOCK_PHOTO_ASSET_DATA:
        photo = PhotoAsset(
            service={}, master_record=one["master"], asset_record=one["asset"]
        )
        photos.append(photo)
        tm.add_file_status(task_name="task_name", file=photo)
    return photos


def pytest_runtest_setup():
    redis_client = redis.StrictRedis(**REDIS_CONFIG)
    redis_client.flushdb()
    print("clean up redis")


@pytest.fixture(scope="session")
def celery_config():
    return {
        "timezone": TIMEZONE,
        "result_expires": 3600,
        "task_serializer": "pickle",
        "result_serializer": "pickle",
        "accept_content": ["json", "pickle"],
    }


@pytest.fixture(scope="session")
def celery_includes():
    return [
        "artascope.src.task.sync",
    ]
