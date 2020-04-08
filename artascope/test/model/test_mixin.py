#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/30
from artascope.src.model.mixin import JsonDataMixin


class DataModel(JsonDataMixin):
    def __init__(self, a: str, b: int, c: dict):
        self.a = a
        self.b = b
        self.c = c


class TestJsonDataMixin:
    def test_serialize(self):
        model = DataModel(a="abc", b=10, c={"text": 10.0})

        json_str = model.extract_to_json()
        obj = DataModel.load_by_json(json_str)
        assert obj == model

        model2 = DataModel(a="abcd", b=10, c={"text": 10.0})

        assert obj != model2
