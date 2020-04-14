#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/1
import datetime
import json
import pytest
from pyicloud.services.photos import (
    PhotoAsset,
    PhotoAlbum,
)
from artascope.src.patch.pyicloud import patch_photo_album
from artascope.src.util.date_util import DateUtil
from artascope.test.conftest import (
    DataException,
    CustomEncoder,
)

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


@pytest.fixture()
def mock_album(monkeypatch):
    patch_photo_album()

    def mock__len__(self):
        return len(MOCK_PHOTO_ASSET_DATA)

    def mock_list_query_gen(
        self, offset: int, list_type: str, direction: str, query_filter=None
    ):
        if direction == "DESCENDING":
            return [len(MOCK_PHOTO_ASSET_DATA) - 1 - offset, direction]
        else:
            return [offset, direction]

        # def mock_photo_data(self):
        #     for one in MOCK_PHOTO_ASSET_DATA:
        #         yield PhotoAsset(service={}, master_record={}, asset_record=one)
        #

    monkeypatch.setattr(PhotoAlbum, "__len__", mock__len__)
    monkeypatch.setattr(PhotoAlbum, "__list_query_gen_simple", mock_list_query_gen)
    monkeypatch.setattr(PhotoAlbum, "_list_query_gen", mock_list_query_gen)

    ab = PhotoAlbum(
        service=MockPyiCloudService(
            username="username", password="password", client_id="client_id"
        ),
        name="",
        list_type="",
        obj_type="",
        direction="DESCENDING",
    )
    return ab


class TestPatchPhotoAlbum:
    def test_get_photos_by_date_desc(self, mock_album):
        method = getattr(mock_album, "__get_photos_by_date")
        photos = [photo for photo in method()]
        assert len(photos) == len(MOCK_PHOTO_ASSET_DATA)
        assert (
            photos[0].id
            == MOCK_PHOTO_ASSET_DATA[0]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            photos[1].id
            == MOCK_PHOTO_ASSET_DATA[1]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            photos[2].id
            == MOCK_PHOTO_ASSET_DATA[2]["fields"]["masterRef"]["value"]["recordName"]
        )

    def test_get_photos_by_date_asc(self, mock_album):
        mock_album.direction = "ASCENDING"
        method = getattr(mock_album, "__get_photos_by_date")
        photos = [photo for photo in method()]
        assert len(photos) == len(MOCK_PHOTO_ASSET_DATA)
        assert (
            photos[0].id
            == MOCK_PHOTO_ASSET_DATA[2]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            photos[1].id
            == MOCK_PHOTO_ASSET_DATA[1]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            photos[2].id
            == MOCK_PHOTO_ASSET_DATA[0]["fields"]["masterRef"]["value"]["recordName"]
        )

    def test_get_offset_and_cnt(self, mock_album):
        method = getattr(mock_album, "__get_offset_and_cnt_by_date")
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

    def test_calculate_offset_and_cnt(self, mock_album, monkeypatch):
        def mock_get_offset_and_cnt_by_date(self, album_len, date_start, date_end):
            raise DataException(
                {
                    "album_len": album_len,
                    "date_start": date_start,
                    "date_end": date_end,
                }
            )

        monkeypatch.setattr(
            mock_album,
            "__get_offset_and_cnt_by_date",
            mock_get_offset_and_cnt_by_date.__get__(mock_album),
        )

        # without arguments
        offset, cnt = mock_album.calculate_offset_and_cnt()
        assert (offset, cnt) == (2, 3)
        # only date_start
        data = {
            "album_len": len(MOCK_PHOTO_ASSET_DATA),
            "date_start": DateUtil.get_today(),
            "date_end": DateUtil.get_tomorrow(),
        }
        with pytest.raises(DataException,) as exc_info:
            mock_album.calculate_offset_and_cnt(date_start=DateUtil.get_today())
        assert json.dumps(data, sort_keys=True, cls=CustomEncoder) in str(
            exc_info.value
        )

        # only date_start and date_end
        data = {
            "album_len": len(MOCK_PHOTO_ASSET_DATA),
            "date_start": DateUtil.get_date_from_str("20190101"),
            "date_end": DateUtil.get_date_from_str("20190201"),
        }
        with pytest.raises(DataException,) as exc_info:
            mock_album.calculate_offset_and_cnt(
                date_start=DateUtil.get_date_from_str("20190101"),
                date_end=DateUtil.get_date_from_str("20190201"),
            )
        assert json.dumps(data, sort_keys=True, cls=CustomEncoder) in str(
            exc_info.value
        )

        # only last
        offset, cnt = mock_album.calculate_offset_and_cnt(last=2)
        assert (offset, cnt) == (1, 2)

        # only last larger than album len
        offset, cnt = mock_album.calculate_offset_and_cnt(last=4)
        assert (offset, cnt) == (2, 3)

    def test_fetch_photos(self, mock_album):
        photos = [photo for photo in mock_album.fetch_photos(offset=1, cnt=2)]
        assert len(photos) == 2
        assert (
            photos[0].id
            == MOCK_PHOTO_ASSET_DATA[1]["fields"]["masterRef"]["value"]["recordName"]
        )
        assert (
            photos[1].id
            == MOCK_PHOTO_ASSET_DATA[2]["fields"]["masterRef"]["value"]["recordName"]
        )
