#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/1
import datetime
import json
from pyicloud.services.photos import (
    PhotoAsset,
    PhotoAlbum,
)
from artascope.src.patch.pyicloud import patch_photo_album
from artascope.src.util.date_util import DateUtil

MOCK_PHOTO_ASSET_DATA = [
    {
        "fields": {
            "assetDate": {
                "value": datetime.datetime(year=2020, month=1, day=1).timestamp() * 1000
            },
            "masterRef": {"value": {"recordName": "record1"}},
        }
    },
    {
        "fields": {
            "assetDate": {
                "value": datetime.datetime(year=2020, month=1, day=2).timestamp() * 1000
            },
            "masterRef": {"value": {"recordName": "record2"}},
        }
    },
    {
        "fields": {
            "assetDate": {
                "value": datetime.datetime(year=2020, month=1, day=3).timestamp() * 1000
            },
            "masterRef": {"value": {"recordName": "record3"}},
        }
    },
]


class MockResponse:
    def __init__(self, idx, direction):
        self.idx = int(idx)
        self.direction = direction

    def json(self):
        if self.idx < 0 or self.idx > len(MOCK_PHOTO_ASSET_DATA):
            return {"records": []}
        elif self.direction == "DESCENDING":
            return {"records": mock_data[self.idx * 2 :]}
        else:
            data = list(reversed(mock_data))
            return {"records": data[self.idx * 2 :]}


class MockPyiCloudSession:
    def post(self, url, data, headers):
        data = json.loads(data)
        idx = data[0]
        direction = data[1]
        return MockResponse(idx, direction)


class MockPyiCloudService:
    def __init__(self, username, password, client_id):
        self.username = username
        self.password = password
        self.client_id = client_id

        self._service_endpoint = "mock_endpoint"
        self.params = {}
        self.session = MockPyiCloudSession()


mock_data = []

for one in MOCK_PHOTO_ASSET_DATA:
    mock_data.append(
        {
            "recordType": "CPLMaster",
            "recordName": one["fields"]["masterRef"]["value"]["recordName"],
        }
    )
    mock_data.append({"recordType": "CPLAsset", **one})


def mock__len__(self):
    return len(MOCK_PHOTO_ASSET_DATA)


def mock_list_query_gen(
    self, offset: int, list_type: str, direction: str, query_filter=None
):
    if direction == "DESCENDING":
        return [len(MOCK_PHOTO_ASSET_DATA) - 1 - offset, direction]
    else:
        return [offset, direction]


class TestPatchPhotoAlbum:
    def test_get_photos_by_date_desc(self, monkeypatch):
        patch_photo_album()

        ab = PhotoAlbum(
            service=MockPyiCloudService(
                username="username", password="password", client_id="client_id"
            ),
            name="",
            list_type="",
            obj_type="",
            direction="DESCENDING",
        )
        monkeypatch.setattr(PhotoAlbum, "__len__", mock__len__.__get__(ab))
        monkeypatch.setattr(
            ab, "__list_query_gen_simple", mock_list_query_gen.__get__(ab)
        )
        method = getattr(ab, "__get_photos_by_date")
        data = [one for one in method()]
        assert len(data) == 3
        assert (
            data[0].id
            == MOCK_PHOTO_ASSET_DATA[0]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            data[1].id
            == MOCK_PHOTO_ASSET_DATA[1]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            data[2].id
            == MOCK_PHOTO_ASSET_DATA[2]["fields"]["masterRef"]["value"]["recordName"]
        )

    def test_get_photos_by_date_asc(self, monkeypatch):
        patch_photo_album()
        abc = PhotoAlbum(
            service=MockPyiCloudService(
                username="username", password="password", client_id="client_id"
            ),
            name="",
            list_type="",
            obj_type="",
            direction="ASCENDING",
        )
        monkeypatch.setattr(PhotoAlbum, "__len__", mock__len__.__get__(abc))
        monkeypatch.setattr(
            abc, "__list_query_gen_simple", mock_list_query_gen.__get__(abc)
        )
        method = getattr(abc, "__get_photos_by_date")
        data = [one for one in method()]
        assert len(data) == 3
        assert (
            data[0].id
            == MOCK_PHOTO_ASSET_DATA[2]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            data[1].id
            == MOCK_PHOTO_ASSET_DATA[1]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            data[2].id
            == MOCK_PHOTO_ASSET_DATA[0]["fields"]["masterRef"]["value"]["recordName"]
        )

    def test_get_offset_and_cnt(self, monkeypatch):
        patch_photo_album()

        def mock_photo_data(self):
            for one in MOCK_PHOTO_ASSET_DATA:
                yield PhotoAsset(service={}, master_record={}, asset_record=one)

        monkeypatch.setattr(PhotoAlbum, "__get_photos_by_date", mock_photo_data)

        ab = PhotoAlbum(service={}, name="", list_type="", obj_type="", direction="")

        method = getattr(ab, "__get_offset_and_cnt_by_desc")
        assert method(
            album_len=3,
            date_start=datetime.date(year=2019, month=12, day=30),
            date_end=datetime.date(year=2019, month=12, day=31),
        ) == (0, 0)
        assert method(
            album_len=3,
            date_start=datetime.date(year=2020, month=1, day=4),
            date_end=datetime.date(year=2020, month=1, day=6),
        ) == (0, 0)

        assert method(
            album_len=3,
            date_start=datetime.date(year=2020, month=1, day=1),
            date_end=datetime.date(year=2020, month=1, day=2),
        ) == (2, 2)

        assert method(
            album_len=3,
            date_start=datetime.date(year=2019, month=12, day=31),
            date_end=datetime.date(year=2020, month=1, day=2),
        ) == (2, 2)

        assert method(
            album_len=3,
            date_start=datetime.date(year=2020, month=1, day=2),
            date_end=datetime.date(year=2020, month=1, day=4),
        ) == (1, 2)

    def test_fetch_photos(self, monkeypatch):
        patch_photo_album()

        ab = PhotoAlbum(
            service=MockPyiCloudService(
                username="username", password="password", client_id="client_id"
            ),
            name="",
            list_type="",
            obj_type="",
            direction="",
        )
        monkeypatch.setattr(ab, "_list_query_gen", mock_list_query_gen.__get__(ab))

        data = [one for one in ab.fetch_photos(album_len=len(MOCK_PHOTO_ASSET_DATA))]
        assert len(data) == 3
        assert (
            data[0].id
            == MOCK_PHOTO_ASSET_DATA[0]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            data[1].id
            == MOCK_PHOTO_ASSET_DATA[1]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            data[2].id
            == MOCK_PHOTO_ASSET_DATA[2]["fields"]["masterRef"]["value"]["recordName"]
        )

    def test_fetch_photos_without_len(self, monkeypatch):
        patch_photo_album()
        ab = PhotoAlbum(
            service=MockPyiCloudService(
                username="username", password="password", client_id="client_id"
            ),
            name="",
            list_type="",
            obj_type="",
            direction="",
        )

        monkeypatch.setattr(ab, "_list_query_gen", mock_list_query_gen.__get__(ab))
        monkeypatch.setattr(PhotoAlbum, "__len__", mock__len__.__get__(ab))

        data = [one for one in ab.fetch_photos()]
        assert len(data) == 3
        assert (
            data[0].id
            == MOCK_PHOTO_ASSET_DATA[0]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            data[1].id
            == MOCK_PHOTO_ASSET_DATA[1]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            data[2].id
            == MOCK_PHOTO_ASSET_DATA[2]["fields"]["masterRef"]["value"]["recordName"]
        )

    def test_fetch_photos_with_last(self, monkeypatch):
        patch_photo_album()

        ab = PhotoAlbum(
            service=MockPyiCloudService(
                username="username", password="password", client_id="client_id"
            ),
            name="",
            list_type="",
            obj_type="",
            direction="",
        )
        monkeypatch.setattr(ab, "_list_query_gen", mock_list_query_gen.__get__(ab))

        data = [
            one for one in ab.fetch_photos(album_len=len(MOCK_PHOTO_ASSET_DATA), last=2)
        ]
        assert len(data) == 2
        assert (
            data[0].id
            == MOCK_PHOTO_ASSET_DATA[1]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            data[1].id
            == MOCK_PHOTO_ASSET_DATA[2]["fields"]["masterRef"]["value"]["recordName"]
        )

    def test_fetch_photos_with_last_larger_than_len(self, monkeypatch):
        patch_photo_album()

        ab = PhotoAlbum(
            service=MockPyiCloudService(
                username="username", password="password", client_id="client_id"
            ),
            name="",
            list_type="",
            obj_type="",
            direction="",
        )
        monkeypatch.setattr(ab, "_list_query_gen", mock_list_query_gen.__get__(ab))

        data = [
            one for one in ab.fetch_photos(album_len=len(MOCK_PHOTO_ASSET_DATA), last=4)
        ]
        assert len(data) == 3
        assert (
            data[0].id
            == MOCK_PHOTO_ASSET_DATA[0]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            data[1].id
            == MOCK_PHOTO_ASSET_DATA[1]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            data[2].id
            == MOCK_PHOTO_ASSET_DATA[2]["fields"]["masterRef"]["value"]["recordName"]
        )

    def test_fetch_photos_with_date_filter(self, monkeypatch):
        patch_photo_album()

        def mock_photo_data(self):
            for one in MOCK_PHOTO_ASSET_DATA:
                yield PhotoAsset(service={}, master_record={}, asset_record=one)

        monkeypatch.setattr(PhotoAlbum, "__get_photos_by_date", mock_photo_data)

        ab = PhotoAlbum(
            service=MockPyiCloudService(
                username="username", password="password", client_id="client_id"
            ),
            name="",
            list_type="",
            obj_type="",
            direction="",
        )
        monkeypatch.setattr(ab, "_list_query_gen", mock_list_query_gen.__get__(ab))

        data = [
            one
            for one in ab.fetch_photos(
                album_len=len(MOCK_PHOTO_ASSET_DATA),
                date_start=datetime.date(year=2020, month=1, day=1),
                date_end=datetime.date(year=2020, month=1, day=2),
            )
        ]

        assert len(data) == 2
        assert (
            data[0].id
            == MOCK_PHOTO_ASSET_DATA[0]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            data[1].id
            == MOCK_PHOTO_ASSET_DATA[1]["fields"]["masterRef"]["value"]["recordName"]
        )

    def test_fetch_photos_with_date_filter_with_no_end(self, monkeypatch):
        patch_photo_album()

        def mock_photo_data(self):
            for one in MOCK_PHOTO_ASSET_DATA:
                yield PhotoAsset(service={}, master_record={}, asset_record=one)

        @classmethod
        def mock_get_tomorrow(cls):
            return datetime.date(year=2020, month=1, day=2)

        monkeypatch.setattr(PhotoAlbum, "__get_photos_by_date", mock_photo_data)

        ab = PhotoAlbum(
            service=MockPyiCloudService(
                username="username", password="password", client_id="client_id"
            ),
            name="",
            list_type="",
            obj_type="",
            direction="",
        )
        monkeypatch.setattr(ab, "_list_query_gen", mock_list_query_gen.__get__(ab))
        monkeypatch.setattr(
            DateUtil, "get_tomorrow", mock_get_tomorrow.__get__(DateUtil)
        )

        data = [
            one
            for one in ab.fetch_photos(
                album_len=len(MOCK_PHOTO_ASSET_DATA),
                date_start=datetime.date(year=2020, month=1, day=1),
            )
        ]

        assert len(data) == 2
        assert (
            data[0].id
            == MOCK_PHOTO_ASSET_DATA[0]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            data[1].id
            == MOCK_PHOTO_ASSET_DATA[1]["fields"]["masterRef"]["value"]["recordName"]
        )
