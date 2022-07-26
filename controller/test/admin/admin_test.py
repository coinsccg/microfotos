# -*- coding: utf-8 -*-
"""
@Time: 2021/1/25 9:42
@Auth: money
@File: admin_test.py
"""
import unittest
import json

from manage import app


class AdminTest(unittest.TestCase):
    """后台单元测试"""

    def setUp(self) -> None:
        app.testing = True
        self.client = app.test_client()

    def test_admin_list(self):
        data = {
            "page": 1, "num": 50, "category": "account", "content": 1, "group": "default",
            "start_time": "2020-11-30", "end_time": "2020-12-31", "sort_way": 1
        }
        resp = self.client.get("/api/v1/admin/user/audit/filter", data=data)

        # resp = json.loads(resp.data)
        self.assertEqual(resp.get("code"), 0)

    def test_forbidden_user(self):
        """
        用户禁言接口
        """
        data = {
            "user_id": "eb34f363db78b67abb829fd7beb9672d", "day_num": 1
        }
        headers = {
            "Content-Type": "application/json",
            "token": "eyJtZDVfdG9rZW4iOiAiMDEwNjEzZjVmZGMxZWJjMGEyMTA0MzA5N2FmZjAxZGIiLCAidGltZXN0YW1wIjogMTYwNjIwNzM3MjA0OH0=",
            "permission_id": "127",
            "module_id": "008"
        }
        resp = self.client.post("/api/v1/admin/user/forbidden", data=data, headers=headers)
        print(resp.status_code)
        print(resp.data)
        self.assertEqual(resp.get("code"), 0)

    def tearDown(self) -> None:
        pass


if __name__ == '__main__':
    unittest.main()
