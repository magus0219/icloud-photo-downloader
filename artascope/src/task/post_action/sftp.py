#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/3
import datetime
import paramiko
import os
from pathlib import Path
from artascope.src.celery_app import app as celery_app
from artascope.src.util.date_util import DateUtil
from artascope.src.lib.user_config_manager import ucm
from artascope.src.util import get_logger

logger = get_logger("server")


def modify_meta(
    sftp_client: paramiko.sftp_client, filepath: str, created_dt: datetime.datetime,
):
    """Change access and modified times of photo, software like Synology Moments will need it

    :param sftp_client:
    :param filepath:
    :param created_dt:
    :return:
    """
    created_dt = created_dt.timestamp()
    sftp_client.utime(filepath, (created_dt, created_dt))


@celery_app.task(
    autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 5}
)
def upload_to_sftp(
    username: str, src_filepath: str, filename: str, created_dt: datetime.datetime
) -> None:
    """Upload one photo to sftp

    :param username:
    :param src_filepath:
    :param filename:
    :param created_dt:
    :return:
    """
    user_setting = ucm.load(username)

    logger.info(
        "host:{host}, port:{port}".format(
            host=user_setting.sftp_host, port=user_setting.sftp_port
        )
    )

    ssh_client = paramiko.client.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy)
    try:
        ssh_client.connect(
            hostname=user_setting.sftp_host,
            port=user_setting.sftp_port,
            username=user_setting.sftp_username,
            password=user_setting.sftp_password,
        )

        sftp_client = ssh_client.open_sftp()
        try:
            sftp_client.chdir(user_setting.sftp_dir)
        except FileNotFoundError:
            for part in Path(user_setting.sftp_dir).parts:
                try:
                    sftp_client.mkdir(part)
                    sftp_client.chdir(part)
                except OSError:
                    sftp_client.chdir(part)
                    pass

        date_folder = DateUtil.get_str_from_date(created_dt)
        if date_folder not in sftp_client.listdir():
            sftp_client.mkdir(date_folder)

        tgt_filepath = Path(date_folder) / filename
        logger.debug("target position:{}".format(str(tgt_filepath)))
        try:
            sftp_client.remove(str(tgt_filepath))
        except (FileNotFoundError, PermissionError, OSError) as e:
            pass
        sftp_client.put(src_filepath, str(tgt_filepath))
        modify_meta(sftp_client, str(tgt_filepath), created_dt)

        os.remove(src_filepath)
    except Exception as e:
        logger.exception(e)
        raise
    finally:
        ssh_client.close()
