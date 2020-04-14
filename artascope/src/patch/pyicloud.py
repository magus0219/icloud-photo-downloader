#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/25
import sys
import json as jsonlib
import datetime
from future.moves.urllib.parse import urlencode
from pyicloud.services.photos import (
    PhotoAsset,
    PhotoAlbum,
)
from pyicloud.base import PyiCloudService
from artascope.src.util.latch import Latch
from artascope.src.util import get_logger
from artascope.src.util.date_util import DateUtil
from artascope.src.config import API_LATCH_LIMIT_PER_MINUTE


logger = get_logger("server.patch")


def photo_asset_get_state(self) -> None:
    """Remove stateful attribute _service to adapt pickle module

    :param self:
    :return:
    """
    state = self.__dict__.copy()
    if "_service" in state:
        del state["_service"]
    return state


def patch_photo_asset() -> None:
    """Patch PhotoAsset class to adapt pickle module

    :return:
    """
    setattr(PhotoAsset, "__getstate__", photo_asset_get_state)


def __list_query_gen_simple(
    self, offset: int, list_type: str, direction: str, query_filter=None
) -> dict:
    """A method to get simple info of photos to support date filter function

    :param self:
    :param offset:
    :param list_type:
    :param direction:
    :param query_filter:
    :return:
    """
    query = {
        u"query": {
            u"filterBy": [
                {
                    u"fieldName": u"startRank",
                    u"fieldValue": {u"type": u"INT64", u"value": offset},
                    u"comparator": u"EQUALS",
                },
                {
                    u"fieldName": u"direction",
                    u"fieldValue": {u"type": u"STRING", u"value": direction},
                    u"comparator": u"EQUALS",
                },
            ],
            u"recordType": list_type,
        },
        u"resultsLimit": self.page_size * 2,
        u"desiredKeys": [
            u"assetDate",
            u"recordName",
            u"recordType",
            u"recordChangeTag",
            u"masterRef",
        ],
        u"zoneID": {u"zoneName": u"PrimarySync"},
    }

    if query_filter:
        query["query"]["filterBy"].extend(query_filter)

    return query


def __get_photos_by_date(self):
    """Prefetch all photo data to filter date

    :param self:
    :return:
    """
    if self.direction == "DESCENDING":
        offset = len(self) - 1
    else:
        offset = 0

    while True:
        url = ("%s/records/query?" % self.service._service_endpoint) + urlencode(
            self.service.params
        )
        request = self.service.session.post(
            url,
            data=jsonlib.dumps(
                self.__list_query_gen_simple(
                    offset, self.list_type, self.direction, self.query_filter
                )
            ),
            headers={"Content-type": "text/plain"},
        )
        response = request.json()

        asset_records = {}
        master_records = []
        for rec in response["records"]:
            if rec["recordType"] == "CPLAsset":
                master_id = rec["fields"]["masterRef"]["value"]["recordName"]
                asset_records[master_id] = rec
            elif rec["recordType"] == "CPLMaster":
                master_records.append(rec)

        master_records_len = len(master_records)
        if master_records_len:
            if self.direction == "DESCENDING":
                offset = offset - master_records_len
            else:
                offset = offset + master_records_len

            for master_record in master_records:
                record_name = master_record["recordName"]
                yield PhotoAsset(
                    self.service, master_record, asset_records[record_name]
                )
        else:
            break


def __get_offset_and_cnt_by_date(
    self, album_len, date_start: datetime.date, date_end: datetime.date
) -> (int, int):
    """Get idx and cnt of date query
    Use DESCENDING as api direction so index of the first item is len-1

    :param self:
    :param album_len: len of album
    :param date_start: start date of query
    :param date_end: end date of query(include)
    :return: (offset, cnt)
    """
    idx_first = None
    idx_last = None

    idx = 0
    for photo in self.__get_photos_by_date():
        asset_date = DateUtil.get_date_from_timestamp(
            photo._asset_record["fields"]["assetDate"]["value"] // 1000
        )
        logger.debug(
            "{}:assetDate:{}".format(idx, DateUtil.get_str_from_date(asset_date))
        )
        if asset_date > date_end:
            if idx_first is not None and idx_last is None:
                idx_last = idx - 1
                break

        elif asset_date >= date_start:
            if idx_first is None:
                idx_first = idx
            idx += 1
            continue

        else:
            idx += 1

    if idx_first is None:
        return 0, 0
    elif idx_last is None:
        idx_last = album_len - 1

    logger.debug(
        "album_len:{}, idx_first:{}, idx_last:{}".format(album_len, idx_first, idx_last)
    )
    return album_len - 1 - idx_first, idx_last - idx_first + 1


def calculate_offset_and_cnt(
    self,
    album_len=None,
    last=None,
    date_start: datetime.date = None,
    date_end: datetime.date = None,
):
    """A method to calculate offset and cnt from input

    :param self:
    :param album_len: len of album
    :param last: start date of query
    :param date_start: start date of query
    :param date_end: end date of query(include)
    :return:
    """
    if not album_len:
        album_len = len(self)
        logger.info("album_len:{}".format(str(album_len)))

    if date_start:
        if not date_end:
            date_end = DateUtil.get_tomorrow()

        offset, cnt = self.__get_offset_and_cnt_by_date(album_len, date_start, date_end)

    elif last:
        if last > album_len:
            last = album_len
        offset = last - 1
        cnt = last
    else:
        offset = album_len - 1
        cnt = album_len

    logger.info("offset:{}, cnt:{}".format(offset, cnt))
    return offset, cnt


def fetch_photos(
    self, offset: int, cnt: int,
):
    """Fetch photos using offset and cnt

    Photos are sorted by date in ascending order, and the idx is reverted.
    For example:
    item    idx
    0       3
    1       2
    2       1
    3       0

    :param self:
    :param offset:
    :param cnt:
    :return:
    """
    while cnt:
        url = ("%s/records/query?" % self.service._service_endpoint) + urlencode(
            self.service.params
        )
        request = self.service.session.post(
            url,
            data=jsonlib.dumps(
                self._list_query_gen(
                    offset, self.list_type, "DESCENDING", self.query_filter
                )
            ),
            headers={"Content-type": "text/plain"},
        )
        response = request.json()

        asset_records = {}
        master_records = []
        for rec in response["records"]:
            if rec["recordType"] == "CPLAsset":
                master_id = rec["fields"]["masterRef"]["value"]["recordName"]
                asset_records[master_id] = rec
            elif rec["recordType"] == "CPLMaster":
                master_records.append(rec)

        master_records_len = len(master_records)
        if master_records_len:
            offset = offset - master_records_len

            for master_record in master_records:
                record_name = master_record["recordName"]
                if cnt:
                    yield PhotoAsset(
                        self.service, master_record, asset_records[record_name]
                    )
                    cnt -= 1
                else:
                    break
        else:
            break


def patch_photo_album():
    setattr(PhotoAlbum, "fetch_photos", fetch_photos)
    setattr(PhotoAlbum, "calculate_offset_and_cnt", calculate_offset_and_cnt)
    setattr(PhotoAlbum, "__list_query_gen_simple", __list_query_gen_simple)
    setattr(PhotoAlbum, "__get_photos_by_date", __get_photos_by_date)
    setattr(PhotoAlbum, "__get_offset_and_cnt_by_date", __get_offset_and_cnt_by_date)


latch = Latch("api", API_LATCH_LIMIT_PER_MINUTE)


def get(self, url, data=None, json=None, **kwargs):
    latch.lock()
    return self.request("GET", url, data=data, json=json, **kwargs)


def post(self, url, data=None, json=None, **kwargs):
    latch.lock()

    if url == "https://setup.icloud.com/setup/ws/1/login":
        data = jsonlib.loads(data)
        data.update({"extended_login": True})
        data = jsonlib.dumps(data)
        logger.debug("modify json data:{}".format(data))
    return self.request("POST", url, data=data, json=json, **kwargs)


def patch_session():
    setattr(getattr(sys.modules["pyicloud.base"], "PyiCloudSession"), "post", post)
    setattr(getattr(sys.modules["pyicloud.base"], "PyiCloudSession"), "get", get)


# https://cvws.icloud-content.com/B/AZtBH0pCybo2VLI56JDiN2tYEsIzAV9WGhMjvVqSkoAPCgIZRFsU1zPJ/${f}?o=AlavBsN-b8QRWKfWOwjPE3bm8ahl7XccMIQmelZ7Yk_g&v=1&x=3&a=CAogSWogKPkr3Qie1Y7PWeNDQYjUBDTDCtZFoCO7SP3DCJcSHRDzq4y6li4Y84jou5YuIgEAUgRYEsIzWgQU1zPJ&e=1586578982&k=MozOm9oGk56EQbrrzAYzBg&fl=&r=db863a97-55f8-45f8-ae53-049924b61988-1&ckc=com.apple.photos.cloud&ckz=PrimarySync&y=1&p=69&s=0azouzetjrZFQQkmupdat2aA2XM
# https://cvws.icloud-content.com/B/AZtBH0pCybo2VLI56JDiN2tYEsIzAV9WGhMjvVqSkoAPCgIZRFsU1zPJ/${f}?o=AqCwrrDt_0hya30XIaca1GcSTX10pgVL46wo0Wlclts8&v=1&x=3&a=CAoghtALcWJwegM-oG34De1uLqeh9QnQxEt4_AWu1p4eSWwSHRDsjKa8li4Y7OmBvpYuIgEAUgRYEsIzWgQU1zPJ&e=1586583598&k=MozOm9oGk56EQbrrzAYzBg&fl=&r=ac781fa5-1f95-40c4-8d2c-670fc74b95b2-1&ckc=com.apple.photos.cloud&ckz=PrimarySync&y=1&p=69&s=vUczMzSTJHTb4sS58kXh8Pcu3A8
