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
from artascope.src.lib.user_status_manager import usm
from artascope.src.lib.user_config_manager import ucm
from artascope.src.lib.auth_manager import (
    AuthManager,
    LoginStatusText,
)
from artascope.src.model.user_config import (
    TargetType,
    UserConfig,
    NotifyType,
)
from artascope.src.lib.task_manager import tm
from artascope.src.task.sync import sync
from artascope.src.util.date_util import DateUtil


bp = Blueprint("user", __name__, url_prefix="/user")


@bp.route("/")
def user():
    users = usm.get_all_user()
    return render_template(
        "user.html", users=users if users else [], login_status_text=LoginStatusText,
    )


@bp.route("/edit/", defaults={"username": None}, methods=["GET", "POST"])
@bp.route("/edit/<username>", methods=["GET", "POST"])
def user_edit(username=None):
    if request.method == "GET":
        if not username:
            return render_template("user_edit.html", user_setting=None,)
        else:
            user_setting = ucm.load(username)
            return render_template("user_edit.html", user_setting=user_setting,)
    elif request.method == "POST":
        data = request.form
        user_setting = ucm.load(data["account_username"])
        if not user_setting:
            user_setting = UserConfig(
                data["account_username"], data["account_password"]
            )

        for key, value in user_setting.__dict__.items():
            if key in data and data[key] not in ("None", ""):
                if key in ("target_type", "notify_type", "sftp_port", "smtp_port"):
                    setattr(user_setting, key, int(data[key]))
                else:
                    setattr(user_setting, key, data[key])
        ucm.save(user_setting)
        return redirect(url_for("user.user"))


@bp.route("/captcha/<username>", methods=["GET", "POST"])
def captcha(username):
    if request.method == "GET":
        user = usm.get_user(username)
        return render_template("captcha.html", user=user,)
    elif request.method == "POST":
        data = request.form

        auth = AuthManager(username)
        auth.receive_captcha(data["captcha"])

        return redirect(url_for("task.get_task_list", username=username))
