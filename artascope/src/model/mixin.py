#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/30
import json


class JsonDataMixin:
    def extract_to_json(self):
        data = {}
        for key, value in self.__dict__.items():
            data[key] = getattr(self, key)
        return json.dumps(data)

    @classmethod
    def load_by_json(cls, json_str: str):
        data = json.loads(json_str)
        obj = cls(**data)
        return obj

    def __eq__(self, other):
        for key, value in self.__dict__.items():
            if key not in other.__dict__ or getattr(self, key) != getattr(other, key):
                return False
        return True
