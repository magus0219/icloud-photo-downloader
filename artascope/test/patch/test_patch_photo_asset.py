#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/1
import pickle
from pyicloud.services.photos import PhotoAsset
from artascope.src.patch.pyicloud import patch_photo_asset


class TestPicklePhotoAsset:
    def test_pickle_photo_asset(self):
        patch_photo_asset()
        asset = PhotoAsset(service={}, master_record={}, asset_record={})
        data = pickle.dumps(asset)
        obj = pickle.loads(data)
        assert getattr(obj, "service", None) is None
