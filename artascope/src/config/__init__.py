#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/22
import os
import sys
import importlib
from artascope.src.config.base import *

env = os.environ["ARTASCOPE_ENV"] if "ARTASCOPE_ENV" in os.environ else "dev"

if env:
    config_module = importlib.import_module("artascope.src.config.{}".format(env))
    for name in dir(config_module):
        if not name.startswith("__"):
            setattr(sys.modules[__name__], name, getattr(config_module, name))

        if name in os.environ:
            setattr(sys.modules[__name__], name, os.environ[name])

    setattr(sys.modules[__name__], "ENV", env)
