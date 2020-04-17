#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/17
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
)
from artascope.src.lib.scheduler_manager import sm

bp = Blueprint("scheduler", __name__, url_prefix="/scheduler")


@bp.route("/")
def scheduler():
    job_info = sm.get_job_info()
    return render_template("scheduler.html", job_info=job_info if job_info else [],)
