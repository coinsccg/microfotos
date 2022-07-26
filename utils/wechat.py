# -*- coding: utf-8 -*-
"""
@Time: 2020-11-13 16:12:11
@File: wechat
@Auth: money
"""
import os
import uuid
import requests
import json
import time
import xmltodict  # pip install xmltodict
from urllib.parse import urlencode
import base64, hashlib
from Crypto.Cipher import AES
from hashlib import md5


class AESCipher():
    """
    Usage:
        c = AESCipher('password').encrypt('message')
        m = AESCipher('password').decrypt(c)
    Tested under Python 3 and PyCrypto 2.6.1.
    """

    def __init__(self, key):
        self.key = hashlib.md5(key.encode('utf8')).hexdigest()

        # Padding for the input string --not
        # related to encryption itself.
        self.BLOCK_SIZE = 32  # Bytes
        self.pad = lambda s: s + (self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE) * \
                             chr(self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE)
        self.unpad = lambda s: s[:-ord(s[len(s) - 1:])]

    # 加密
    def encrypt(self, raw):
        raw = self.pad(raw)
        cipher = AES.new(self.key, AES.MODE_ECB)
        return base64.b64encode(cipher.encrypt(raw))

    # 解密
    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        cipher = AES.new(self.key, AES.MODE_ECB)
        return self.unpad(cipher.decrypt(enc)).decode('utf8')


class WechatPay(object):
    """移动端微信支付"""

    # 应用ID
    APP_ID = "wx8a0f5700af95662d"

    # 商户号
    MCH_ID = "1604919345"

    # 加密类型
    SIGN_TYPE = "MD5"

    # 微信商户平台设置的密钥
    SECRET_KEY = "DGz8tO6Pr1hSxp0PT20u8WrX987ufAwB"  # 微信商户平台(pay.weixin.qq.com)-->账户设置-->API安全-->密钥设置

    # 商户服务器IP
    SPBILL_CREATE_IP = "101.132.136.180"

    # 微信统一下单URL
    UNIFIED_ORDER_URL = "https://api.mch.weixin.qq.com/pay/unifiedorder"

    # 微信统一退款URL
    UNIFIED_REFUND_URL = " https://api.mch.weixin.qq.com/secapi/pay/refund"

    # 回调地址
    recharge = "http://m.microfotos.cn/api/v1/recharge/wechat/callback"
    buy = "http://m.microfotos.cn/api/v1/wechat/callback"
    refund = "http://m.microfotos.cn/api/v1/refund/wechat/callback"

    def __init__(self, out_trade_no, total_fee, body="微图支付", type="buy"):
        """
        初始化配置
        :param out_trade_no: 商户订单号
        :param total_fee: 总金额
        :param body: 订单描述
        :return
        """
        self.order_info = {
            "appid": self.APP_ID,  # 应用ID
            "mch_id": self.MCH_ID,  # 商户号
            "device_info": "WEB",  # 设备号 默认传WEB
            "nonce_str": "",  # 随机字符串
            "sign_type": self.SIGN_TYPE,  # 加密类型
            "body": body,  # 商品描述
            "out_trade_no": str(out_trade_no),  # 商户订单号
            "total_fee": total_fee,  # 总金额 单位分
            "spbill_create_ip": self.SPBILL_CREATE_IP,  # 商户服务器IP
            "notify_url": self.buy if type == "buy" else self.recharge,  # 支付结果回调地址
            "trade_type": "APP"  # 交易类型 默认传APP
        }

    def generate_nonce_str(self):
        """
        生成随机字符串
        :return 返回随机字符串
        """
        nonce_str = str(uuid.uuid4()).replace("-", "")
        return nonce_str

    @staticmethod
    def generate_xml_data(json_data):
        """
        生成xml格式数据
        :param json_data: json格式数据
        :return 返回xml格式数据
        """
        xml_data = xmltodict.unparse({"xml": json_data}, pretty=True, full_document=False).encode("utf-8")
        return xml_data

    @staticmethod
    def generate_sign(params):
        """
        生成md5签名
        :param params: 向微信支付发送的请求参数
        :return 返回签名
        """
        if "sign" in params:
            params.pop("sign")
        src = "&".join(["%s=%s" % (k, v) for k, v in sorted(params.items())]) + "&key=%s" % WechatPay.SECRET_KEY
        sign = md5(src.encode("utf-8")).hexdigest().upper()
        return sign

    def wechat_payment_request(self):
        """
        请求统一下单接口
        """
        # 生成xml数据
        self.order_info["nonce_str"] = self.generate_nonce_str()
        self.order_info["sign"] = WechatPay.generate_sign(self.order_info)
        xml_data = WechatPay.generate_xml_data(self.order_info)
        # 向微信支付发送请求
        context = {}
        resp = requests.post(self.UNIFIED_ORDER_URL, data=xml_data, headers={"Content-Type": "application/xml"})
        if resp.status_code == 200:
            rest = json.loads(json.dumps(xmltodict.parse(resp.content)))
            if rest["xml"]["return_code"] == "SUCCESS":  # 请求成功SUCCESS，请求失败FAIL
                prepay_id = rest["xml"]["prepay_id"]
                return prepay_id
            else:
                err_code = rest["xml"]["return_code"]  # 错误码FAIL
                err_msg = rest["xml"]["return_msg"]
                return False
        return False

    def generate_app_call_data(self, prepay_id):
        """
        客户端APP请求所需参数
        :param prepay_id: 预支付交易标识
        :return 返回app请求微信的参数
        """
        app_request_info = {
            "appid": self.APP_ID,  # 应用ID
            "partnerid": self.MCH_ID,  # 商户号
            "prepayid": prepay_id,  # 预交易标识
            "package": "Sign=WXPay",  # 扩展字段 默认WXPay
            "noncestr": self.generate_nonce_str(),  # 随机字符串
            "timestamp": str(int(time.time()))  # 时间戳 秒级
        }
        app_request_info["sign"] = WechatPay.generate_sign(app_request_info)

        return json.dumps(app_request_info)

    @staticmethod
    def verify_wechat_call_back(request_body):
        """
        校验微信支付回调参数
        :param request_body: 微信回调请求体数据
        :return: 返回校验微信支付回调通知的结果
        """
        # xml to dict
        dict_params = dict(xmltodict.parse(request_body, process_namespaces=True)["xml"])
        # 校验返回码
        return_code = dict_params.get("return_code")
        if return_code == "SUCCESS":
            # 校验签名
            if "sign" not in dict_params:
                return False, False, False
            backcall_sign = dict_params["sign"]
            sign = WechatPay.generate_sign(dict_params)
            if sign == backcall_sign:
                return dict_params["out_trade_no"], dict_params["total_fee"], dict_params["transaction_id"]
            else:
                return False, False, False
        else:
            return False, False, False

    def wechat_refund_request(self, out_refund_no, refund_fee):
        """
        请求统一退款接口
        :param out_refund_no: 商户退款单号
        :param refund_fee: 申请退款金额
        """
        # 生成xml数据
        self.order_info["out_refund_no"] = out_refund_no
        self.order_info["refund_fee"] = refund_fee
        self.order_info["notify_url"] = self.refund
        self.order_info["nonce_str"] = self.generate_nonce_str()
        self.order_info["sign"] = WechatPay.generate_sign(self.order_info)
        xml_data = WechatPay.generate_xml_data(self.order_info)
        # 微信退款需要证书
        sshKeysPath = os.path.join(os.path.dirname(os.path.dirname(__file__)), "utils", "ssh_keys")
        wechatCert = os.path.join(sshKeysPath, "wechat_cert.pem")
        wechatKey = os.path.join(sshKeysPath, "wechat_key.pem")

        # 向微信支付发送https请求
        resp = requests.post(self.UNIFIED_REFUND_URL, data=xml_data, headers={"Content-Type": "application/xml"},
                             cert=(wechatCert, wechatKey), verify=True)
        # rest =xmltodict.parse(resp.content)
        print(resp.text)
        if resp.status_code == 200:
            rest = json.loads(json.dumps(xmltodict.parse(resp.content)))
            print(rest)
            if rest["xml"]["return_code"] == "SUCCESS":  # 请求成功SUCCESS，请求失败FAIL
                return True
            else:
                return False
        return False

    @staticmethod
    def verify_refund_callback(request_body):
        """
        校验微信退款回调参数
        :param request_body: 微信退款回调请求体数据
        :return:
        """
        # xml to dict
        resParam = dict(xmltodict.parse(request_body, process_namespaces=True)["xml"])
        # 校验返回码
        returnCode = resParam.get("return_code")
        if returnCode == "SUCCESS":
            # 校验签名
            if "req_info" not in resParam:
                return False, False, False
            callBack = resParam["req_info"]
            # 解密
            aes = AESCipher(WechatPay.SECRET_KEY)
            decryptRest = json.loads(aes.decrypt(callBack))
            if decryptRest["refund_status"] == "SUCCESS":
                return decryptRest["out_trade_no"], decryptRest["total_fee"]
            else:
                return False, False
        else:
            return False, False


if __name__ == "__main__":
    # demo = WechatPay("20200701412141241", 0.01)
    # demo.wechat_payment_request()

    # pwd = 'your key'
    # msg = "your return_xml's 'req_info'"
    # print(AESCipher(pwd).encrypt(msg))
    # print(AESCipher(pwd).decrypt(msg))
    demo = WechatPay("16093097024612524", "100")
    demo.wechat_refund_request("16093097024612524", "100")
