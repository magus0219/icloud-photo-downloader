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

        user_setting.icloud_password = data["account_password"]
        user_setting.admin_url_prefix = data["admin_url_prefix"]

        if int(data["target"]) == TargetType.SFTP:
            user_setting.set_target_sftp(
                host=data["sftp_host"],
                port=int(data["sftp_port"]),
                username=data["sftp_username"],
                password=data["sftp_password"],
                sftp_dir=data["sftp_dir"],
            )

        if int(data["notify_type"]) == NotifyType.SLACK:
            user_setting.set_nofity_slack(
                slack_token=data["slack_token"], slack_channel=data["slack_channel"]
            )
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
