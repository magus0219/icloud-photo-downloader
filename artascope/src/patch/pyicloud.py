#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/25
import json
import datetime
from future.moves.urllib.parse import urlencode
from pyicloud.services.photos import (
    PhotoAsset,
    PhotoAlbum,
)
from artascope.src.util import get_logger
from artascope.src.util.date_util import DateUtil


logger = get_logger("server.patch")


def photo_asset_get_state(self):
    state = self.__dict__.copy()
    if "_service" in state:
        del state["_service"]
    return state


def patch_photo_asset():
    setattr(PhotoAsset, "__getstate__", photo_asset_get_state)


def __list_query_gen_simple(self, offset, list_type, direction, query_filter=None):
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


def __get_date_info(self):
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
            data=json.dumps(
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


def __get_offset_and_cnt(
    self, album_len, date_start: datetime.date, date_end: datetime.date
):
    idx_first = None
    idx_last = None

    idx = 0
    for photo in self.__get_date_info():
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

    logger.info(
        "album_len:{}, idx_first:{}, idx_last:{}".format(album_len, idx_first, idx_last)
    )
    return album_len - 1 - idx_first, idx_last - idx_first + 1


def fetch_photos(
    self,
    album_len=None,
    last=None,
    date_start: datetime.date = None,
    date_end: datetime.date = None,
):
    if not album_len:
        album_len = len(self)
        logger.info("album_len:{}".format(str(album_len)))

    if date_start:
        if not date_end:
            date_end = DateUtil.get_tomorrow()

        offset, cnt = self.__get_offset_and_cnt(album_len, date_start, date_end)

    elif last:
        if last > album_len:
            last = album_len
        offset = last - 1
        cnt = last
    else:
        offset = album_len - 1
        cnt = album_len

    logger.info("offset:{}, cnt:{}".format(offset, cnt))

    while cnt:
        url = ("%s/records/query?" % self.service._service_endpoint) + urlencode(
            self.service.params
        )
        request = self.service.session.post(
            url,
            data=json.dumps(
                self._list_query_gen(
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
    setattr(PhotoAlbum, "__list_query_gen_simple", __list_query_gen_simple)
    setattr(PhotoAlbum, "__get_date_info", __get_date_info)
    setattr(PhotoAlbum, "__get_offset_and_cnt", __get_offset_and_cnt)
