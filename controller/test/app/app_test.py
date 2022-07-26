# -*- coding: utf-8 -*-
"""
@Time: 2021/1/23 16:49
@Auth: money
@File: app_test.py
"""
import unittest
import json

from manage import app


class AppTest(unittest.TestCase):
    """app单元测试"""

    def setUp(self) -> None:
        app.testing = True
        self.client = app.test_client()

    def test_app_list(self):
        data = {
            "page": 1, "num": 50, "category": "account", "content": 1, "group": "default",
            "start_time": "2020-11-30", "end_time": "2020-12-31", "sort_way": 1
        }
        resp = self.client.get("/api/v1/admin/user/audit/filter", data=data)
        resp = json.loads(resp.data)
        self.assertEqual(resp.get("code"), 0)

    def test_user_permission(self):
        data = {
            "page": 1, "num": 50, "category": "account", "content": 1, "group": "default",
            "start_time": "2020-11-30", "end_time": "2020-12-31", "sort_way": 1
        }
        headers = {"Content-Type": "application/json",
                   "token": "eyJtZDVfdG9rZW4iOiAiMDEwNjEzZjVmZGMxZWJjMGEyMTA0MzA5N2FmZjAxZGIiLCAidGltZXN0YW1wIjogMTYxMTUzOTQ3MDQ3OH0="}
        resp = self.client.get("/api/v1/user/info", data=data, headers=headers)
        resp = json.loads(resp.data)
        self.assertEqual(0, resp.get("code"))

    def tearDown(self) -> None:
        pass


if __name__ == '__main__':
    unittest.main()
