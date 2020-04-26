#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/23
class TestConfig:
    def test_config_base(self):
        from artascope.src.config import TIMEZONE
        from artascope.src.config.base import TIMEZONE as TIMEZONE_BASE

        assert TIMEZONE == TIMEZONE_BASE

    def test_config_overwrite_by_file(self):
        import os
        import importlib
        from artascope.src.config import SECONDS_WAIT_FOR_API_LIMIT

        env = os.environ["ARTASCOPE_ENV"]
        config_module_test = importlib.import_module(
            "artascope.src.config.{}".format(env)
        )
        assert SECONDS_WAIT_FOR_API_LIMIT == getattr(
            config_module_test, "SECONDS_WAIT_FOR_API_LIMIT"
        )

    def test_config_overwrite_by_env(self):
        import os
        import sys
        import importlib

        os.environ["SECONDS_WAIT_FOR_API_LIMIT"] = "-1"
        importlib.reload(sys.modules["artascope.src.config"])
        from artascope.src.config import SECONDS_WAIT_FOR_API_LIMIT

        assert SECONDS_WAIT_FOR_API_LIMIT == "-1"
