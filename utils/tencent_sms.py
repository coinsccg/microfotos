# -*- coding: utf-8 -*-
"""
@Time: 2020-11-13 16:12:11
@File: tencent_sms
@Auth: money
"""
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.sms.v20190711 import sms_client, models
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile


def tencent_sms(mobile: str, sms_code: str):
    """
    基于腾讯云SDK接入腾讯云发送短信接口
    :param mobile: 手机
    :param sms_code: 短信验证码

    """

    try:

        # 基础配置 "SecretId" "SecretKey"
        cred = credential.Credential("AKIDumLhpf9QLzSGo7vMolSrwkJbhhRuJF7k", "VlxtYTDixuhSwB992f16wXrvmWzB5lAI")

        # 实例化一个http选项，可选的，没有特殊需求可以跳过。
        httpProfile = HttpProfile()
        httpProfile.reqMethod = "POST"  # post请求(默认为post请求)
        httpProfile.reqTimeout = 30  # 请求超时时间，单位为秒(默认60秒)
        httpProfile.endpoint = "sms.tencentcloudapi.com"  # 指定接入地域域名(默认就近接入)

        # 实例化一个客户端配置对象，可以指定超时时间等配置
        clientProfile = ClientProfile()
        clientProfile.signMethod = "TC3-HMAC-SHA256"  # 指定签名算法
        clientProfile.language = "en-US"
        clientProfile.httpProfile = httpProfile

        # 实例化要请求产品(以sms为例)的client对象
        # 第二个参数是地域信息，可以直接填写字符串ap-guangzhou，或者引用预设的常量
        client = sms_client.SmsClient(cred, "ap-guangzhou", clientProfile)

        # 实例化一个请求对象
        req = models.SendSmsRequest()

        # 短信应用ID
        req.SmsSdkAppid = "1400408658"
        # 短信签名
        req.Sign = "微图"
        # 短信码号扩展号: 默认未开通
        req.ExtendCode = ""
        # 用户的 session 内容: 可以携带用户侧 ID 等上下文信息，server 会原样返回
        req.SessionContext = "1111144"
        # 国际/港澳台短信 senderid: 国内短信填空，默认未开通
        req.SenderId = ""
        # 下发手机号码，采用 e.164 标准，+[国家或地区码][手机号]
        req.PhoneNumberSet = ["+86" + mobile]
        # 模板ID
        req.TemplateID = "603553"
        # 模板参数: 若无模板参数，则设置为空
        req.TemplateParamSet = [sms_code]

        # 发送
        resp = client.SendSms(req)

        # 输出json格式的字符串回包
        # print(resp.to_json_string(indent=2))

        return True, None
    except TencentCloudSDKException as err:
        return False, err


if __name__ == "__main__":
    tencent_sms("17725021250", "12345")
