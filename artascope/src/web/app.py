#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/23
from types import FunctionType
from flask import (
    Flask,
    redirect,
    url_for,
)
import artascope.src.web.lib.filter as module_filter
from artascope.src.web.lib.content_processor import inject_version


def index():
    return redirect(url_for("task.get_task_list"))


def create_app():
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

    # register blueprint
    app.register_blueprint(user.bp)
    app.register_blueprint(task.bp)
    app.register_blueprint(scheduler.bp)

    # register index
    app.add_url_rule("/", "index", index)
    # register context processor
    app.context_processor(inject_version)
    return app
