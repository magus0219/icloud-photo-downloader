#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/6
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
)
from artascope.src.lib.task_manager import (
    tm,
    TaskStatus,
    TaskStatusText,
    TaskRunType,
    TaskRunTypeText,
)
from artascope.src.lib.user_status_manager import usm
from artascope.src.lib.user_config_manager import ucm
from artascope.src.util.date_util import (
    DateTimeUtil,
    DateUtil,
)
from artascope.src.task.sync import sync


bp = Blueprint("task", __name__, url_prefix="/task")


@bp.route("/", defaults={"username": None})
@bp.route("/<username>/")
def get_task_list(username=None):
    tasks = tm.get_task_list(username)
    for task in tasks:
        if task.status == TaskStatus.RUNNING:
            if tm.check_fail(task.task_name):
                tm.fail_task(task.task_name)
                # not load again
                task.status = TaskStatus.FAIL

    return render_template(
        "task.html",
        tasks=tasks,
        username=username,
        task_status_text=TaskStatusText,
        task_run_type_text=TaskRunTypeText,
    )


@bp.route("/status/<task_name>/")
def get_task_status(task_name):
    tasks = tm.get_task_list()
    files = tm.get_file_status_list(task_name)
    return render_template(
        "task_status.html", task_name=task_name, tasks=tasks, files=files
    )


@bp.route("/run/<username>", methods=["GET", "POST"])
def run_task(username):
    if request.method == "GET":
        user = usm.get_user(username)
        return render_template("task_run.html", user=user,)
    elif request.method == "POST":
        data = request.form
        user_setting = ucm.load(username)

        run_type = int(data["run_type"])
        if run_type == TaskRunType.ALL:
            sync.delay(
                username=user_setting.icloud_username,
                password=user_setting.icloud_password,
            )
        elif run_type == TaskRunType.LAST:
            last = int(data["last_cnt"])
            sync.delay(
                username=user_setting.icloud_username,
                password=user_setting.icloud_password,
                last=last,
            )
        elif run_type == TaskRunType.DATE_RANGE:
            date_start = DateTimeUtil.get_datetime_from_date_str(
                data["date_start"]
            ).timestamp()
            date_end = DateTimeUtil.get_datetime_from_date_str(
                data["date_end"]
            ).timestamp()
            sync.delay(
                username=user_setting.icloud_username,
                password=user_setting.icloud_password,
                date_start=DateUtil.get_date_from_timestamp(date_start),
                date_end=DateUtil.get_date_from_timestamp(date_end),
            )

        return redirect(url_for("task.get_task_list", username=username))
