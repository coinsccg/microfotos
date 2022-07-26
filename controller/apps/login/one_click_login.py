# -*- coding: utf-8 -*-
"""
@Time: 2021/2/19 10:22
@Auth: money
@File: one_click_login.py
"""
import base64
import requests

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5


class OneClickLogin(object):
    """
    极光一键登录
    """

    url = "https://api.verification.jpush.cn/v1/web/loginTokenVerify"
    appKey = "bc6e5ed17de51b44d3530f87"
    masterSecret = "e7f7a02a7baba7bcc8b3d9d9"

    def __init__(self, loginToken):
        self.loginToken = loginToken

    def loginTokenVerifyAPI(self):
        authorization = base64.b64encode("{}:{}".format(self.appKey, self.masterSecret).encode("utf-8")).decode()
        headers = {
            "Authorization": "Basic {}".format(authorization)
        }
        json = {
            "loginToken": self.loginToken
        }
        res = requests.post(self.url, json=json, headers=headers).json()
        return res["code"], res["content"], res["phone"]

    def rsaDecode(self, encrypted):
        """
        :param encrypted: 登录认证接口返回的手机加密结果
        """
        PREFIX = "-----BEGIN RSA PRIVATE KEY-----"
        SUFFIX = "-----END RSA PRIVATE KEY-----"
        publicKey = """MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDJ/xW4uQWjpEKEUtb6e6KBXL+kaJKp9nvYVv4JGuHpN87N6lLQSe+FoCsgFvIWYJ6NlI/P5jwjyBGRBo686yLIJOZK00rLJaEkUC1jBwD8hb/Cx4smkZXApLM431eDMBnRuiSbVC8kcQm+suBbWd5LSitTsrK+dCSvKaryhs4U/QIDAQAB"""
        privateKey = """MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAMn/Fbi5BaOkQoRS1vp7ooFcv6Rokqn2e9hW/gka4ek3zs3qUtBJ74WgKyAW8hZgno2Uj8/mPCPIEZEGjrzrIsgk5krTSssloSRQLWMHAPyFv8LHiyaRlcCkszjfV4MwGdG6JJtULyRxCb6y4FtZ3ktKK1Oysr50JK8pqvKGzhT9AgMBAAECgYAqJUj489HTZPBj/4zPUoCDkUCDIzaGs+D/MJdseulr6bMCj8ObpfGN5e9ZkLAOLzalv7uJ2zXtGU9g/QdHL6Bf1v/s1VzJzJ9mOx8xz0bO5zjLUaKuCpqg3y9U50Lfq64EW3qLjNDib0ANWY6lKpps9jjavfl4eBZa+fwbAGWr2QJBAPRLUR5yUnVhd6twRzaTOeZ3GwTZeVRGcWAIJhCNXIwHu6sHlhC74jzF+XN1BIsJ3jZuWWTp4OCtwF3yGq5arPMCQQDTrOn0xLeRHGMFKoAnSSMmiOXe9rpu1bQbSiGMoahCYwm2UX8w3sW9cqz95MEWDfwPn3RQ7QcIuLz9Y5qKl/JPAkEA0M7DwmNzKdOqpwXsSLCkz+HEXWvJcghYBf5REtrRXPuLJE/yq9D8Onf5lP9TZ8iCgEHn9QKXbVP2VhaHSbpFkwJAG4gF9fwQFCOpDWb1vCZbGAv+Of3FSd0py9LcgjoUdG4FOV1oOab/+SANOAikxIWVH0MSEeSCYbQFgL+Pvi79KQJBAI23VimZUB1eShDmHiOYP5pmRWNU18wLKTQXm9jBOOIumOSei5dI6SqDT3r6fMDuNE4G+gZ3IMSq8Rr0iAfr4cc="""

        key = "{}\n{}\n{}".format(PREFIX, privateKey, SUFFIX)
        cipher = PKCS1_v1_5.new(RSA.import_key(key))
        res = cipher.decrypt(base64.b64decode(encrypted.encode()), None).decode()
        return res

    def main(self):
        code, msg, phone = self.loginTokenVerifyAPI()
        if code == 8000:
            return self.rsaDecode(phone)
        return None


if __name__ == '__main__':
    demo = OneClickLogin("qygTsh2TEueN3PYeAocrPRj1dH+9AR8Inrf6/zAlwgodsNvkSnFFL5/UfxTW4jJv0zfk2qKaoejezPQGScxH4uVlguFGeEE0HylCDW9q07YwFaEoo3a51FqFpQC/OChTBkr5SOHNgfg6UtnIV2e/Anl3pkk6vjeB5PbKuOc4CqyiHsbphbdXS/DuTJ/24HwBiv/0eGaSFEqhueHBenM9lpVZ/2d1X0F86mxGl+w+iY2nK8qFh1vTNtdBk4H0I3cGuF1yGrVMATDS/7rSLUgJ+Q7o456Qrl1DP+i5PtD67aJVrkF8LpexBes/xXX59dS/budA1stkUQKsMlMSYd0NAju6qZ5OLo0G7Hv69aBnbFxu2m8XcMWmt9kHYxkPcccbvQuYPSUx7ODCIqJerIP0bg+/6rLt+rw+d/bjyinqTtbfvtH0xveG8VX7/tF0B4Iit7o3SKq2O+v3EouisZyA+w==")
    demo.main()
