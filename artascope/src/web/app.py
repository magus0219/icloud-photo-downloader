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

    app.register_blueprint(user.bp)
    app.register_blueprint(task.bp)

    return app


# SLACK_USERNAME_MAP = {
#     "magus0219": "magus0219@gmail.com",
# }


# @app.route("/artascope/slack", methods=["POST"])
# def get_icloud_verify_code():
#     data = request.form
#     print(data)
#
#     slack_username = data["user_name"]
#     icloud_username = SLACK_USERNAME_MAP[slack_username]
#     icloud_password = USER_PASSWORD_MAP[icloud_username]
#
#     icloud_verify_code = None
#     if data["text"].split(" ")[0] == "verify":
#         icloud_verify_code = data["text"].split(" ")[1]
#
#     print(icloud_username, icloud_verify_code)
#     auth = AuthManager(icloud_username, icloud_password)
#     auth.receive_captcha(icloud_verify_code)
#
#     current_task = tm.get_current_task_name(icloud_username)
#     task = tm.load_task(task_name=current_task)
#
#     print(task)
#
#     sync.delay(
#         task.task_name,
#         icloud_username,
#         icloud_password,
#         task.last,
#         DateUtil.get_date_from_timestamp(task.date_start) if task.date_start else None,
#         DateUtil.get_date_from_timestamp(task.date_end) if task.date_end else None,
#     )
#
#     return {}
