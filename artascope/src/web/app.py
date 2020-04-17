#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/23
import uuid
import copy
from types import FunctionType
from flask import (
    Flask,
    request,
    render_template,
    redirect,
    url_for,
)
import artascope.src.web.filter as module_filter


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    app.jinja_env.filters.update(
        {
            key: val
            for key, val in module_filter.__dict__.items()
            if isinstance(val, FunctionType)
        }
    )

    from . import user
    from . import task
    from . import scheduler

    app.register_blueprint(user.bp)
    app.register_blueprint(task.bp)
    app.register_blueprint(scheduler.bp)

    return app
