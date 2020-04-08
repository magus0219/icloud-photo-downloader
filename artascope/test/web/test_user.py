#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Created by magus0219[magus0219@gmail.com] on 2020/4/6
import pytest
from artascope.src.lib.user_config_manager import ucm
from artascope.src.model.user_config import UserConfig
from artascope.src.lib.auth_manager import (
    LoginStatusText,
    LoginStatus,
)
from artascope.src.lib.auth_manager import AuthManager
from artascope.src.lib.task_manager import (
    tm,
    TaskRunType,
)

MOCK_NEW_USER = {
    "account_username": "account_name",
    "account_password": "account_password",
    "admin_url_prefix": "http://127.0.0.1:5000",
    "target": "1",
    "sftp_host": "198.168.50.118",
    "sftp_port": "2222",
    "sftp_username": "someone",
    "sftp_password": "someone",
    "sftp_dir": "/home",
    "notify_type": "1",
    "slack_token": "abcdefg",
    "slack_channel": "dev",
}


@pytest.fixture
def response(client):
    response = client.post("/user/edit/", data=MOCK_NEW_USER, follow_redirects=True)
    return response


@pytest.mark.web
class TestUser:
    def test_user_without_content(self, client):
        response = client.get("/user", follow_redirects=True)
        assert b"User List" in response.data  # test jumbotron

    def test_user_with_content(self, client):
        uc = UserConfig("username", "password")
        ucm.save(uc)

        tm.add_task(
            task_name="task_name", username="username", run_type=TaskRunType.ALL
        )

        response = client.get("/user", follow_redirects=True)
        # test info
        assert b"User List" in response.data  # test jumbotron
        assert b"<td>1</td>" in response.data
        assert b"<td>username</td>" in response.data
        # test current task
        assert (
            "<td>{}</td>".format(tm.get_current_task_name(username="username")).encode()
            in response.data
        )
        assert LoginStatusText[LoginStatus.NOT_LOGIN].encode() in response.data

        # test link
        assert b'href="/task/username"' in response.data
        assert b'href="/task/run/username"' in response.data
        assert b'href="/user/edit/username"' in response.data
        assert b'href="/user/captcha/username"' in response.data

    def test_user_edit_get_without_user(self, client):
        response = client.get("/user/edit/")
        assert b"Edit User Setting" in response.data  # test jumbotron
        assert b"Add one user to download photos" in response.data  # test jumbotron

        # test default radio choice
        assert (
            b'<input class="form-check-input" type="radio" name="target" id="targetSFTP" value=1 checked>'
            in response.data
        )
        assert (
            b'<input class="form-check-input" type="radio" name="notify_type" id="None" value=0 checked>'
            in response.data
        )

    def test_user_edit_add_new_user(self, client, response):
        # test info
        assert b"User List" in response.data  # test jumbotron
        assert b"<td>1</td>" in response.data
        assert b"<td>account_name</td>" in response.data
        assert LoginStatusText[LoginStatus.NOT_LOGIN].encode() in response.data

        # test link
        assert b'href="/task/account_name"' in response.data
        assert b'href="/task/run/account_name"' in response.data
        assert b'href="/user/edit/account_name"' in response.data
        assert b'href="/user/captcha/account_name"' in response.data

    def test_user_edit_get_exsited_user(self, client, response):
        response = client.get("/user/edit/{}".format(MOCK_NEW_USER["account_username"]))
        assert b"Edit User Setting" in response.data  # test jumbotron
        assert (
            "of {}".format(MOCK_NEW_USER["account_username"]).encode() in response.data
        )  # test jumbotron

        # test info
        assert (
            '<input type="email" class="form-control" id="inputEmail" name="account_username" value="{}"'.format(
                MOCK_NEW_USER["account_username"]
            ).encode()
            in response.data
        )
        assert (
            '<input type="text" class="form-control" id="inputPassword" name="account_password" value="{}"'.format(
                MOCK_NEW_USER["account_password"]
            ).encode()
            in response.data
        )
        assert (
            '<input type="text" class="form-control" id="adminURLPrefix" name="admin_url_prefix" value="{}"'.format(
                MOCK_NEW_USER["admin_url_prefix"]
            ).encode()
            in response.data
        )
        assert (
            b'<input class="form-check-input" type="radio" name="target" id="targetSFTP" value=1 checked>'
            in response.data
        )
        assert (
            '<input type="text" class="form-control" id="SFTPHost" name="sftp_host" value="{}"'.format(
                MOCK_NEW_USER["sftp_host"]
            ).encode()
            in response.data
        )
        assert (
            '<input type="text" class="form-control" id="SFTPPort" name="sftp_port" value="{}"'.format(
                MOCK_NEW_USER["sftp_port"]
            ).encode()
            in response.data
        )
        assert (
            '<input type="text" class="form-control" id="SFTPUsername" name="sftp_username" value="{}"'.format(
                MOCK_NEW_USER["sftp_username"]
            ).encode()
            in response.data
        )
        assert (
            '<input type="text" class="form-control" id="SFTPPassword" name="sftp_password" value="{}"'.format(
                MOCK_NEW_USER["sftp_password"]
            ).encode()
            in response.data
        )
        assert (
            '<input type="text" class="form-control" id="SFTPDir" name="sftp_dir" value="{}"'.format(
                MOCK_NEW_USER["sftp_dir"]
            ).encode()
            in response.data
        )
        assert (
            b'<input class="form-check-input" type="radio" name="notify_type" id="Slack" value=1 checked>'
            in response.data
        )
        assert (
            '<input type="text" class="form-control" id="slackToken" name="slack_token" value="{}"'.format(
                MOCK_NEW_USER["slack_token"]
            ).encode()
            in response.data
        )
        assert (
            '<input type="text" class="form-control" id="slackChannel" name="slack_channel" value="{}"'.format(
                MOCK_NEW_USER["slack_channel"]
            ).encode()
            in response.data
        )

    def test_user_captcha_get(self, client, response):
        response = client.get(
            "/user/captcha/{}".format(MOCK_NEW_USER["account_username"])
        )

        # test info
        assert b"Captcha" in response.data  # test jumbotron
        assert (
            "enter captcha of {}".format(MOCK_NEW_USER["account_username"]).encode()
            in response.data
        )

    def test_user_captcha_post_without_current_task(self, client, response):
        data = {"captcha": "abcd"}
        response = client.post(
            "/user/captcha/{}".format(MOCK_NEW_USER["account_username"]),
            data=data,
            follow_redirects=True,
        )

        # test info
        assert b"Task List" in response.data  # test jumbotron
        assert (
            "of {}".format(MOCK_NEW_USER["account_username"]).encode() in response.data
        )

        assert (
            AuthManager(username=MOCK_NEW_USER["account_username"]).get_login_status()
            == LoginStatus.CAPTCHA_RECEIVED
        )

    def test_user_captcha_post_with_current_task(self, client, response):
        tm.add_task(
            task_name="task_name",
            username=MOCK_NEW_USER["account_username"],
            run_type=TaskRunType.ALL,
        )

        data = {"captcha": "abcd"}
        response = client.post(
            "/user/captcha/{}".format(MOCK_NEW_USER["account_username"]),
            data=data,
            follow_redirects=True,
        )

        # test info
        assert b"Task List" in response.data  # test jumbotron
        assert (
            "of {}".format(MOCK_NEW_USER["account_username"]).encode() in response.data
        )

        assert (
            AuthManager(username=MOCK_NEW_USER["account_username"]).get_login_status()
            == LoginStatus.CAPTCHA_RECEIVED
        )

        # TODO how to check sync is called
