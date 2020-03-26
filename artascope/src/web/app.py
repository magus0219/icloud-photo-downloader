#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/3/23
from types import FunctionType
from flask import (
    Flask,
    request,
    render_template,
)
from artascope.src.lib.auth import (
    Auth,
    LoginStatus,
)
from artascope.src.config import USER_PASSWORD_MAP
from artascope.src.main import sync
from artascope.src.lib.watcher import Watcher
import artascope.src.web.filter as module_filter


app = Flask(__name__)
app.jinja_env.filters.update(
    {
        key: val
        for key, val in module_filter.__dict__.items()
        if isinstance(val, FunctionType)
    }
)

SLACK_USERNAME_MAP = {"magus0219": "magus0219@gmail.com"}


@app.route("/artascope/slack", methods=["POST"])
def get_icloud_verify_code():
    data = request.form
    print(data)

    slack_username = data["user_name"]
    icloud_username = SLACK_USERNAME_MAP[slack_username]
    icloud_password = USER_PASSWORD_MAP[icloud_username]

    icloud_verify_code = None
    if data["text"].split(" ")[0] == "verify":
        icloud_verify_code = data["text"].split(" ")[1]

    print(icloud_username, icloud_verify_code)
    auth = Auth(icloud_username, icloud_password)
    auth.set_verify_code(icloud_verify_code)
    auth.set_login_status(LoginStatus.VERIFY_CODE_RECEIVED)

    sync.delay(icloud_username, icloud_password)

    return {}


@app.route("/tasklist")
def get_task_list():
    watcher = Watcher()
    tasks = watcher.get_task_list()
    return render_template("task_list.html", tasks=tasks) if tasks else "data not ready"


@app.route("/filestatus/<task_name>")
def get_file_status(task_name):
    watcher = Watcher()
    tasks = watcher.get_task_list()
    files = watcher.get_file_status(task_name)
    return render_template(
        "file_status.html", task_name=task_name, tasks=tasks, files=files
    )
