#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/16
import smtplib
from email.message import EmailMessage
from typing import List
from artascope.src.celery_app import app as celery_app


@celery_app.task(autoretry_for=(Exception,), retry_kwargs={"max_retries": 5})
def send_message(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    msg_from: str,
    msg_to: List[str],
    msg: str,
) -> None:
    with smtplib.SMTP_SSL(smtp_host, smtp_port) as smtp:
        smtp.login(smtp_user, smtp_password)
        email_msg = EmailMessage()
        email_msg.set_content(msg.split("\n")[-1])

        email_msg["Subject"] = msg.split("\n")[0]
        email_msg["From"] = msg_from
        email_msg["To"] = msg_to

        smtp.send_message(email_msg)


# send_message('mail.magicqin.com', 465, 'magus0219', 'boena0219', 'admin@magicqin.com', ['magus0219@gmail.com'], 'test\ntest')
