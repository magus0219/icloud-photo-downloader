#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/3
import tempfile
import paramiko
import os
import sys
import shutil
import datetime
import pytest
import json
from pathlib import Path
from artascope.src.model.user_config import UserConfig
from artascope.src.lib.user_config_manager import ucm
from artascope.src.task.post_action.sftp import upload_to_sftp
from artascope.src.util.date_util import DateUtil
from artascope.test.conftest import (
    DataException,
    CustomEncoder,
)


class MockSSHClient:
    def set_missing_host_key_policy(self, policy):
        pass

    def connect(self, hostname, port, username, password):
        pass

    def open_sftp(self):
        return MockSFTPClient()

    def close(self):
        return True

    def exec_command(self, cmd):
        raise DataException({"cmd": cmd})


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


@pytest.fixture()
def mock_user(tgt_tempdir):
    uc = UserConfig(
        icloud_username="username",
        icloud_password="password",
        sftp_host="127.0.0.1",
        sftp_port=1000,
        sftp_username="sftp_username",
        sftp_password="sftp_password",
        sftp_dir=str(tgt_tempdir),
    )
    ucm.save(uc)


@pytest.fixture()
def mock_user_reindex(tgt_tempdir):
    uc = UserConfig(
        icloud_username="username",
        icloud_password="password",
        sftp_host="127.0.0.1",
        sftp_port=1000,
        sftp_username="sftp_username",
        sftp_password="sftp_password",
        sftp_dir=str(tgt_tempdir),
        reindex_enable=1,
        sftp_home="/sftp_home",
    )
    ucm.save(uc)


class TestSFTP:
    def test_upload_to_sftp(self, mock_user, tgt_tempdir, monkeypatch):
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

    def test_connect_error(self, mock_user, tgt_tempdir, monkeypatch):
        def mock_connect_error(self, hostname, port, username, password):
            raise DataException({})

        monkeypatch.setattr(MockSSHClient, "connect", mock_connect_error)
        monkeypatch.setattr(paramiko.client, "SSHClient", MockSSHClient)

        filename = "testfile.jpg"
        src_filepath = Path(tempfile.gettempdir()) / filename
        created_date = datetime.datetime(year=2019, month=12, day=31)
        with pytest.raises(DataException,):
            upload_to_sftp(
                username="username",
                src_filepath=str(src_filepath),
                filename=filename,
                created_dt=created_date,
            )

    def test_reindex(self, mock_user_reindex, tgt_tempdir, monkeypatch):
        class MockLogger:
            def info(self, msg):
                return True

            def debug(self, msg):
                return True

            def exception(self, e):
                raise e

        monkeypatch.setattr(
            sys.modules["artascope.src.task.post_action.sftp"], "logger", MockLogger()
        )
        monkeypatch.setattr(paramiko.client, "SSHClient", MockSSHClient)

        filename = "testfile.jpg"
        src_filepath = Path(tempfile.gettempdir()) / filename
        created_date = datetime.datetime(year=2019, month=12, day=31)
        with open(src_filepath, "w") as f:
            f.write("testfile")

        data = {
            "cmd": "/var/packages/SynologyMoments/target/usr/bin/synophoto-bin-index-tool -t reindex -i {path}".format(
                path=str(Path("/home") / tgt_tempdir / "2019-12-31")
            )
        }
        with pytest.raises(DataException,) as exc_info:
            upload_to_sftp(
                username="username",
                src_filepath=str(src_filepath),
                filename=filename,
                created_dt=created_date,
            )
        assert json.dumps(data, sort_keys=True, cls=CustomEncoder) in str(
            exc_info.value
        )
