#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/3
import tempfile
import paramiko
import os
import shutil
import datetime
import pytest
from pathlib import Path
from artascope.src.model.user_config import UserConfig
from artascope.src.lib.user_config_manager import ucm
from artascope.src.task.post_action.sftp import upload_to_sftp
from artascope.src.util.date_util import DateUtil


class MockSSHClient:
    def set_missing_host_key_policy(self, policy):
        pass

    def connect(self, hostname, port, username, password):
        pass

    def open_sftp(self):
        return MockSFTPClient()


class MockSFTPClient:
    def __init__(self):
        self.pwd = Path()

    def chdir(self, to_dir):
        if (self.pwd / to_dir).exists() is False:
            raise FileNotFoundError
        self.pwd = self.pwd / Path(to_dir)
        print("chdir", self.pwd)

    def listdir(self):
        print(self.pwd)
        return [x.stem for x in Path(self.pwd).iterdir() if x.is_dir()]

    def mkdir(self, folder):
        print("make", self.pwd / folder)
        os.mkdir(self.pwd / folder)

    def remove(self, filepath):
        os.remove(self.pwd / filepath)

    def put(self, src_filepath, tgt_filepath):
        shutil.copy(src_filepath, self.pwd / tgt_filepath)

    def utime(self, filepath, times):
        os.utime(self.pwd / filepath, times)


@pytest.fixture(
    params=[
        Path(tempfile.gettempdir()),
        Path(tempfile.gettempdir()) / "not_existed/not_existed",
    ]
)
def tgt_tempdir(request):
    if (Path(tempfile.gettempdir()) / "not_existed/not_existed").exists():
        shutil.rmtree(Path(tempfile.gettempdir()) / "not_existed/not_existed")
    return request.param


class TestSFTP:
    def test_upload_to_sftp(self, tgt_tempdir, monkeypatch):
        uc = UserConfig(icloud_username="username", icloud_password="password",)
        uc.set_target_sftp(
            host="127.0.0.1",
            port=1000,
            username="sftp_username",
            password="sftp_password",
            sftp_dir=str(tgt_tempdir),
        )
        ucm.save(uc)

        monkeypatch.setattr(paramiko.client, "SSHClient", MockSSHClient)

        filename = "testfile.jpg"
        src_filepath = Path(tempfile.gettempdir()) / filename
        created_date = datetime.datetime(year=2019, month=12, day=31)
        with open(src_filepath, "w") as f:
            f.write("testfile")

        upload_to_sftp(
            username="username",
            src_filepath=str(src_filepath),
            filename=filename,
            created_dt=created_date,
        )

        tgt_filepath = tgt_tempdir / DateUtil.get_str_from_date(created_date) / filename
        assert Path.exists(tgt_filepath) is True
        assert Path.exists(src_filepath) is False
        assert Path.stat(tgt_filepath).st_atime == created_date.timestamp()
        assert Path.stat(tgt_filepath).st_mtime == created_date.timestamp()
