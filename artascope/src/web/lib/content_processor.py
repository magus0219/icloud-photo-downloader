#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/26
from pathlib import Path


def inject_version():
    print(__file__)
    with open(Path(__file__).parent / "../../../../.project_version") as f:
        ver_str = f.read()
    return {"version": ver_str}
