# -*- coding: utf-8 -*-
"""
@Time: 2020-11-13 16:12:11
@File: alipay
@Auth: money
"""
import rsa
import base64
import datetime
import json
from urllib.parse import urlencode
from urllib.parse import quote_plus

import requests


class AliPayCustomTradeAppPay:
    """
    自定义支付宝APP支付接入
    

    :param out_trade_no: 商户订单号
    :param total_amount: 订单总额
    :param body: 商品描述
    :param subject: 订单标题
    :param type: pay 支付 recharge 充值
    """

    # 应用ID
    APP_ID = "2021002102695407"

    # 支付接口名称
    METHOD = "alipay.trade.app.pay"

    # 退款接口名称
    REFUNDMETHOD = "alipay.trade.refund"

    # 编码
    CHARSET = "utf-8"

    # 加密类型
    SIGN_TYPE = "RSA2"

    # 版本
    VERSION = "1.0"

    # 支付宝请求地址
    SERVER_URL = "https://openapi.alipay.com/gateway.do"  # 沙箱地址："https://openapi.alipaydev.com/gateway.do"

    # 支付宝回调地址
    PAY_NOTIFY_URL = "http://m.microfotos.cn/api/v1/alipay/callback"
    RECHARGE_NOTIFY_URL = "http://m.microfotos.cn/api/v1/recharge/alipay/callback"
    REFUND_NOTIFY_URL = "http://m.microfotos.cn/api/v1/refund/alipay/callback"

    # 支付宝公钥
    ALIPAY_PUBLIC = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtsFyrKIVIoVsw+N+15ENV6WPc7hbxu1+WYQSReqRkswK+S6KEg619jFOEdJl02McBJoRWl0q8v/xK7hl0uAJBgzdJ0s/Q5LT+KwfEDDfZrPf0iDQyAMtBtwsYnmCtvguCgKkeArxVC9I/OaIM0BNphi/dwcR3Qg+GaDYeFKvfRlBekwPSaLetu+VeBZKFGINpVRASB93xmv/1AG3UdlgDgvNVOw5fbq5YE82fHb1Bp+zr4TU3o+YKjN2P53iOYZRx5lp2CbfeWizVilvzrBuLxoHn9RPw5rKqzQrAGLCwTVJzqODrx6uzY7uupt+5UzyqIoiP8oMbJL3V9ib8weACQIDAQAB"

    # 商户RSA2私钥
    APP_PRIVATE_KEY = "MIIEpAIBAAKCAQEAnSMt9TA1ObaiSyrg+bEnqKpGgx1hujTVHFRLPWR61me3WoMhebdBdszZP0HeC1/5cdstZ7i0H0kuCiD2ZsMBrQf/7q0Jzu9A8e6UCyGM2JKSBi9soNV5yr7Dojtk3emONQJbbOdT11IHvrPc4dQOhX/CsfJXJrP1FEoBwNhoEWB0BZVMvxWZWqK3O5rnaVtEKFBeb3L5EIefDZVS1nMUpGVHb1nD2FM2+0fGmwXQhFiGI7iDTkqXeyxeVVklS2m+AhvRhGHxQLfw7rMQ1MImczuvfRV635yfJ2a4lj9oNquGnU3tOlujNuDwKAdZONajLm7VMoTC/7erBT9bd0wERwIDAQABAoIBAAlKgjYkIpGGBfSR1XmOCv1DDCZGf3fGFe+14DkCDu1Mdp/obvtGZZ2DoTjHSTy88P/VaMrgNe4/onRA3LDYyOmVNoHDQ3gz11A2vhQmaLCJgg7RkQe1d50QSHr4Lg+c9qaVvBglWWS62fBhrCbCJhWopzdkT9je/Re1BIOFiCm2xYi33D1S7cJ+cAKIWxTjLjOtlS8J3LsiQcvvPYtPIL4vY5TJbfph7FEmqlPmrcVsSRja1bKQqGYfULGPk/r1RV+D8UoP02E9lgEM82VQRPvibGfSkw8AqW5efTQgo3FYs6NDLWmr3NvXENgq6w9GnJUF1dtNNmoBgLFBGqA/b4kCgYEA0L09sDcdhgkSRNnxnMqm3oRH+UJrCjvvgxKm+kjpk7Mo1wSyMBw7OFL+7JYTAkS0gLVHV2SoXzBR6CmAi7U0eTG09wDIihTkCBGAs4kasJyI6SL/jhiKAxw4AARkbeFPWhQtOLbfbfWegMjlyzSNQa/SRvE1gv3BK07q04WbS20CgYEAwLcKUZoPQjJNfXt35pUKvMoIvBNlGWBSSKCNZcuo0JhvyWTXF89kHvVAO0uBQy0SpRmep0tzpZPfoHXz2U23/RUFnpffmbTIIkxR+teI6zmi1YfNuWhJ4HwGpeYZG13fcfjJ+9+PmJHMEXp/WfHxQpm8ifOt34n+xuE4Mn/bagMCgYEArRkxbc7Wyc79+mCtjvMym/YgZWChuTPos84k8ArEv/njVSOMzH6s0VFqGzF8g/YLpWwuxBcx1PYSBi9cbP6QjCwfQHHC21blnpc9HiUFIA4/Lu4Z9HD/CgM9oS4DRmeAUVfIBG8KK3pyvaNbhD6JIT63ZqMiWAUsSkjATTZPiKUCgYAPEgFPklGhJpfiuTYOJRea3d3C/21Hh73Hii6kiEGiVllfkXA0n3Y/6YPlXykznKG5oYBDquXXS/IP9Ullc+twciVnWo8U0QtZi0hZ6mL9qhsuwZj358znLivC63SJLFUd74u0E66CCty/fSnaWc45HBafXxv4wCzZVqFzaYY6CwKBgQCjaWPzw2RWCT9WL4E/JbK9gJFUlRSZjk8u70YEMobo1e/gsyiHBLfKsP2YVbbHTC4YOspdw1Qy3YNTdTeXRBYmBRXm+/an0d2ZQE6uQwOsEqjXLZLTzRjIDHe2HthcFDkfLKwfXYiHauNbIiRwdqVMwxbCMRubNFvoGUoIqUoexQ=="

    # 商户RSA2公钥
    APP_PUBLICE_KEY = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAt8QcIn+hbP0+XMJje8nsT3q6qXmsforaBC7G+1WEZ9mlucffzQ6QleXWhWZD6Awy2Wtr7bUsR0rOcEraSJNx2BQ4g9na6TgF6XsjP8zhJDe88pu8eO93sIqbauc+W4Q9EN1Z64g0lA/CJnCpfso2c4YR/AJqWm2Jj1JQ09gEHN6cVA8R1gPgiK53qo/LN9Dy69vLapghKmlrDhCC6xtrDzd8QbHuZBhRFeTMxanScFcyiMRxje/MqD61KzC2Xo52a2pi/64KRhLMiZNtTkeKCzZVBhND6fC9U5esB3fb1QiEJMRh+vjrpoFvGalAmFqP/ObsWIVbF999ym+izxbaWwIDAQAB"

    def __init__(self, out_trade_no, total_amount, body="微图支付", subject="图购买", type="pay"):
        # 支付
        self.order_info = {
            "body": body,  # 商品描述
            "out_trade_no": out_trade_no,  # 商户订单号
            "product_code": "QUICK_MSECURITY_PAY",  # 产品码 默认QUICK_MSECURITY_PAY
            "subject": subject,  # 订单标题
            "timeout_express": "90m",
            "total_amount": total_amount  # 订单总额
        }
        # 退款
        self.refund = {
            "out_trade_no": out_trade_no, # 商户订单号
            "refund_amount": total_amount # 退款金额
        }
        self.public_param = {
            "app_id": self.APP_ID,  # 应用ID
            "biz_content": "",
            "charset": self.CHARSET,  # 编码
            "format": "json",  # 格式
            "method": self.METHOD,  # 接口名称
            "notify_url": self.PAY_NOTIFY_URL if type == "pay" else self.RECHARGE_NOTIFY_URL,  # 回调地址
            "sign_type": self.SIGN_TYPE,  # 加密类型
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # 时间
            "version": self.VERSION,  # 接口版本
        }

    def genreate_sign(self, params):
        """
        生成SHA-256签名
        :param params: 参与签名的内容
        :return 签名
        """
        # # 生成公钥和私钥
        # public_key, private_key  = rsa.newkeys(2048) # 1024为SHA-1 2048为SHA-256
        # PRIVATE_KEY = private_key.save_pkcs1()
        # PUBLICE_KEY = public_key.save_pkcs1()
        private_key = "-----BEGIN RSA PRIVATE KEY-----\n" \
                      + self.APP_PRIVATE_KEY \
                      + "\n-----END RSA PRIVATE KEY-----"
        private_key = rsa.PrivateKey.load_pkcs1(private_key)
        params = params.encode("utf-8")
        sign = rsa.sign(params, private_key, "SHA-256")
        b64_sign = base64.b64encode(sign)
        b64_sign = str(b64_sign, encoding=self.CHARSET)
        return b64_sign

    @staticmethod
    def generate_str(params):
        """
        字典生成字符串s
        :param params: 字典参数
        :return 返回字符串
        """
        str = "&".join(["%s=%s" % (k, v) for k, v in sorted(params.items())])
        return str

    @staticmethod
    def url_encode(params, charset):
        """
        url编码
        :param params: 加密参数
        :param charset: 编码
        :return
        """

        query_string = ""
        for (k, v) in params.items():
            value = v
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            value = quote_plus(value, encoding=charset)
            query_string += ("&" + k + "=" + value)
        query_string = query_string[1:]
        return query_string

    def alipy_trade_app_pay_request(self):
        """
        支付请求参数
        """

        self.public_param["biz_content"] = json.dumps(self.order_info, separators=(',', ':'), ensure_ascii=False)
        sign_str = AliPayCustomTradeAppPay.generate_str(self.public_param)

        # 签名
        self.public_param["sign"] = self.genreate_sign(sign_str)
        # 拼接URL
        request_param = urlencode(self.public_param, encoding=self.CHARSET)
        # request_param = AliPayCustomTradeAppPay.url_encode(self.public_param, self.CHARSET)
        return request_param

    def refund_trade_app_pay_request(self):
        """
        退款请求
        """
        self.public_param["method"] = self.REFUNDMETHOD
        self.public_param["notify_url"] = self.REFUND_NOTIFY_URL
        self.public_param["biz_content"] = json.dumps(self.refund, separators=(',', ':'), ensure_ascii=False)
        sign_str = AliPayCustomTradeAppPay.generate_str(self.public_param)

        # 签名
        self.public_param["sign"] = self.genreate_sign(sign_str)
        # 拼接URL
        request_param = urlencode(self.public_param, encoding=self.CHARSET)
        # request_param = AliPayCustomTradeAppPay.url_encode(self.public_param, self.CHARSET)

        # 发送请求
        res = requests.post(self.SERVER_URL, params=request_param).json()
        if res["alipay_trade_refund_response"]["code"] == '10000':
            return True, res["alipay_trade_refund_response"]
        else:
            return False, res["alipay_trade_refund_response"]["sub_msg"]

    @staticmethod
    def alipy_trade_app_pay_response(param_dict: dict):
        """
        支付宝回调验签
        :param param_dict: 支付宝回调参数
        :return
        """

        # 回调sign
        sign = param_dict["sign"]
        call_sign = base64.b64decode(sign)

        # 除sign、sign_type参数外，其余参数皆是待验签参数
        param_dict.pop("sign_type")
        param_dict.pop("sign")

        param_str = AliPayCustomTradeAppPay.generate_str(param_dict)
        content = param_str.encode("utf-8")
        alipay_public_key = "-----BEGIN PUBLIC KEY-----\n" \
                            + AliPayCustomTradeAppPay.ALIPAY_PUBLIC \
                            + "\n-----END PUBLIC KEY-----"
        public_key = rsa.PublicKey.load_pkcs1_openssl_pem(alipay_public_key)

        try:
            rsa.verify(content, call_sign, public_key)
            return True, None
        except Exception as e:
            return False, e


class AlipayOfficialTradeAppPay:
    """
    基于官方SDK接入支付宝APP支付
    
    """

    # 支付宝应用ID
    APP_ID = "2021002102695407"

    # 支付宝支付地址
    SERVER_URL = "https://openapi.alipay.com/gateway.do"

    # 支付宝回调地址
    NOTIFY_URL = "http://wt.test.frp.jethro.fun:8080/api/v1/alipay/callback"

    # 支付宝公钥
    ALIPAY_PUBLIC_KEY = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAtsFyrKIVIoVsw+N+15ENV6WPc7hbxu1+WYQSReqRkswK+S6KEg619jFOEdJl02McBJoRWl0q8v/xK7hl0uAJBgzdJ0s/Q5LT+KwfEDDfZrPf0iDQyAMtBtwsYnmCtvguCgKkeArxVC9I/OaIM0BNphi/dwcR3Qg+GaDYeFKvfRlBekwPSaLetu+VeBZKFGINpVRASB93xmv/1AG3UdlgDgvNVOw5fbq5YE82fHb1Bp+zr4TU3o+YKjN2P53iOYZRx5lp2CbfeWizVilvzrBuLxoHn9RPw5rKqzQrAGLCwTVJzqODrx6uzY7uupt+5UzyqIoiP8oMbJL3V9ib8weACQIDAQAB"

    # 商户RSA2私钥
    APP_PRIVATE_KEY = "MIIEpAIBAAKCAQEAnSMt9TA1ObaiSyrg+bEnqKpGgx1hujTVHFRLPWR61me3WoMhebdBdszZP0HeC1/5cdstZ7i0H0kuCiD2ZsMBrQf/7q0Jzu9A8e6UCyGM2JKSBi9soNV5yr7Dojtk3emONQJbbOdT11IHvrPc4dQOhX/CsfJXJrP1FEoBwNhoEWB0BZVMvxWZWqK3O5rnaVtEKFBeb3L5EIefDZVS1nMUpGVHb1nD2FM2+0fGmwXQhFiGI7iDTkqXeyxeVVklS2m+AhvRhGHxQLfw7rMQ1MImczuvfRV635yfJ2a4lj9oNquGnU3tOlujNuDwKAdZONajLm7VMoTC/7erBT9bd0wERwIDAQABAoIBAAlKgjYkIpGGBfSR1XmOCv1DDCZGf3fGFe+14DkCDu1Mdp/obvtGZZ2DoTjHSTy88P/VaMrgNe4/onRA3LDYyOmVNoHDQ3gz11A2vhQmaLCJgg7RkQe1d50QSHr4Lg+c9qaVvBglWWS62fBhrCbCJhWopzdkT9je/Re1BIOFiCm2xYi33D1S7cJ+cAKIWxTjLjOtlS8J3LsiQcvvPYtPIL4vY5TJbfph7FEmqlPmrcVsSRja1bKQqGYfULGPk/r1RV+D8UoP02E9lgEM82VQRPvibGfSkw8AqW5efTQgo3FYs6NDLWmr3NvXENgq6w9GnJUF1dtNNmoBgLFBGqA/b4kCgYEA0L09sDcdhgkSRNnxnMqm3oRH+UJrCjvvgxKm+kjpk7Mo1wSyMBw7OFL+7JYTAkS0gLVHV2SoXzBR6CmAi7U0eTG09wDIihTkCBGAs4kasJyI6SL/jhiKAxw4AARkbeFPWhQtOLbfbfWegMjlyzSNQa/SRvE1gv3BK07q04WbS20CgYEAwLcKUZoPQjJNfXt35pUKvMoIvBNlGWBSSKCNZcuo0JhvyWTXF89kHvVAO0uBQy0SpRmep0tzpZPfoHXz2U23/RUFnpffmbTIIkxR+teI6zmi1YfNuWhJ4HwGpeYZG13fcfjJ+9+PmJHMEXp/WfHxQpm8ifOt34n+xuE4Mn/bagMCgYEArRkxbc7Wyc79+mCtjvMym/YgZWChuTPos84k8ArEv/njVSOMzH6s0VFqGzF8g/YLpWwuxBcx1PYSBi9cbP6QjCwfQHHC21blnpc9HiUFIA4/Lu4Z9HD/CgM9oS4DRmeAUVfIBG8KK3pyvaNbhD6JIT63ZqMiWAUsSkjATTZPiKUCgYAPEgFPklGhJpfiuTYOJRea3d3C/21Hh73Hii6kiEGiVllfkXA0n3Y/6YPlXykznKG5oYBDquXXS/IP9Ullc+twciVnWo8U0QtZi0hZ6mL9qhsuwZj358znLivC63SJLFUd74u0E66CCty/fSnaWc45HBafXxv4wCzZVqFzaYY6CwKBgQCjaWPzw2RWCT9WL4E/JbK9gJFUlRSZjk8u70YEMobo1e/gsyiHBLfKsP2YVbbHTC4YOspdw1Qy3YNTdTeXRBYmBRXm+/an0d2ZQE6uQwOsEqjXLZLTzRjIDHe2HthcFDkfLKwfXYiHauNbIiRwdqVMwxbCMRubNFvoGUoIqUoexQ=="

    # 商户RSA2公钥
    APP_PUBLICE_KEY = "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAt8QcIn+hbP0+XMJje8nsT3q6qXmsforaBC7G+1WEZ9mlucffzQ6QleXWhWZD6Awy2Wtr7bUsR0rOcEraSJNx2BQ4g9na6TgF6XsjP8zhJDe88pu8eO93sIqbauc+W4Q9EN1Z64g0lA/CJnCpfso2c4YR/AJqWm2Jj1JQ09gEHN6cVA8R1gPgiK53qo/LN9Dy69vLapghKmlrDhCC6xtrDzd8QbHuZBhRFeTMxanScFcyiMRxje/MqD61KzC2Xo52a2pi/64KRhLMiZNtTkeKCzZVBhND6fC9U5esB3fb1QiEJMRh+vjrpoFvGalAmFqP/ObsWIVbF999ym+izxbaWwIDAQAB"

    @staticmethod
    def alipy_trade_app_pay_request(out_trade_no, total_amount, body="微图支付", subject="图片购买"):
        """
        支付请求参数
        :param out_trade_no: 商户订单号
        :param total_amount: 订单总金额
        :param body: 商品描述
        :param subject: 订单标题
        :return
        """

        from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
        from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
        from alipay.aop.api.domain.AlipayTradeAppPayModel import AlipayTradeAppPayModel
        from alipay.aop.api.request.AlipayTradeAppPayRequest import AlipayTradeAppPayRequest

        # 初始化请求对象
        alipay_client_config = AlipayClientConfig()
        alipay_client_config.app_id = AlipayOfficialTradeAppPay.APP_ID
        alipay_client_config.alipay_public_key = AlipayOfficialTradeAppPay.ALIPAY_PUBLIC_KEY
        alipay_client_config.app_private_key = AlipayOfficialTradeAppPay.APP_PRIVATE_KEY
        alipay_client_config.server_url = AlipayOfficialTradeAppPay.SERVER_URL

        client = DefaultAlipayClient(alipay_client_config=alipay_client_config, logger=None)

        # 构造请求对象
        model = AlipayTradeAppPayModel()
        model.timeout_express = "90m"
        model.total_amount = total_amount
        model.product_code = "QUICK_MSECURITY_PAY"
        model.body = body
        model.subject = subject
        model.out_trade_no = out_trade_no
        request = AlipayTradeAppPayRequest(biz_model=model)
        request.notify_url = AlipayOfficialTradeAppPay.NOTIFY_URL
        params = client.sdk_execute(request)

        # print(params)

        return params

    @staticmethod
    def alipy_trade_app_pay_response(param_dict: dict):
        """
        支付宝回调验签
        :param param_dict: 请求参数
        :return
        """

        # 回调sign
        sign = param_dict["sign"]
        call_sign = base64.b64decode(sign)

        # 除sign、sign_type参数外，其余参数皆是待验签参数
        param_dict.pop("sign_type")
        param_dict.pop("sign")

        param_str = AlipayOfficialTradeAppPay.generate_str(param_dict)
        resp_str = param_str.encode("utf-8")

        alipay_public_key = "-----BEGIN PUBLIC KEY-----\n" \
                            + AlipayOfficialTradeAppPay.ALIPAY_PUBLIC_KEY \
                            + "\n-----END PUBLIC KEY-----"
        public_key = rsa.PublicKey.load_pkcs1_openssl_pem(alipay_public_key)

        try:
            rest = rsa.verify(resp_str, call_sign, public_key)
            return True, None
        except Exception as e:
            return False, e

    @staticmethod
    def generate_str(param):
        """
        字典生成字符串
        :param param: 字典参数
        :return 返回字符串
        """
        str = "&".join(["%s=%s" % (k, v) for k, v in sorted(param.items())])
        return str


if __name__ == '__main__':
    # demo = AlipayOfficialTradeAppPay()
    # print(AlipayOfficialTradeAppPay.alipy_trade_app_pay_request("1254121254125", "0.01"))
    demo = AliPayCustomTradeAppPay("16093108311419421", "0.01")
    demo.refund_trade_app_pay_request()