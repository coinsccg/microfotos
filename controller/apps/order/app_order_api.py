# -*- coding: utf-8 -*-
"""
@File: app_order_api
@Time: 2020-07-14
@Author: money 
"""
import random
import time
import hashlib
from flask import request
from flask import g
from flask import Response

from middleware.auth import response
from utils.alipay import AliPayCustomTradeAppPay
from utils.wechat import WechatPay
from initialize import log
from initialize import client
from dao.app.order import orders
from dao.app.order import recharge
from dao.app.order import car


def post_verify_pic_isbuy():
    """校验订单中的图片是否已经购买"""
    try:

        user_id = g.user_data["user_id"]
        order = request.json.get("order")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not order:
            error = "Order is required."

        if error:
            return response(msg=error, code=1, status=400)

        # 校验订单中的图片是否已购买
        deltaAmount, excludeAmount, error = orders.verifyPicIsBuy(order)
        if error:
            raise Exception(error)

        # 查询订单信息
        dataList, error = orders.queryOrderInfo(user_id, order)
        if error:
            raise Exception(error)

        data = {}
        data["delta_amount"] = deltaAmount
        data["exclude_amount"] = excludeAmount
        data["works_item"] = dataList
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_add_car():
    """加入购物车"""
    try:

        user_id = g.user_data["user_id"]
        works_id = request.json.get("works_id")
        spec = request.json.get("spec")
        is_buy = request.json.get("is_buy")  # true购买 false加入购物车

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not works_id:
            error = "WorksID is required."
        elif spec not in ["S", "M", "L", "扩大授权"]:
            error = "Spec invalid."
        elif is_buy not in [True, False]:
            error = "IsBuy invalid."

        if error:
            return response(msg=error, code=1, status=400)

        # 作品信息
        picId, title, priceId, error = car.queryWorksInfo(works_id)
        if error:
            raise Exception(error)

        # 图片路径
        picURL, thumbURL, price, currency, priceUnit, error = car.queryPicInfo(picId, priceId, spec, works_id, user_id,
                                                                               is_buy)
        if error:
            raise Exception(error)

        # 插入订单
        order = str(int(time.time() * 1000)) + str(random.randint(1001, 9999))
        error = car.insertOrder(user_id, works_id, title, picURL, spec, currency, priceUnit, thumbURL, price, is_buy,
                                picId, order)
        if error:
            raise Exception(error)

        return response(data=order if is_buy else None)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_order_detail():
    """
    订单详情
    """
    try:

        user_id = g.user_data["user_id"]
        order = request.args.get("order")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not order:
            error = "Order is required."

        if error:
            return response(msg=error, code=1, status=400)

        # 订单详情
        orderInfo, error = orders.queryOrderDetail(user_id, order)
        if error:
            raise Exception(error)

        return response(data=orderInfo)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s.", code=1, status=500)


def get_user_car_list():
    """
    获取用户购物车列表
    """
    try:
        # 参数
        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)

        # 购物车列表
        dataList, error = car.carList(user_id)
        if error:
            raise Exception(error)
        return response(data=dataList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s.", code=1, status=500)


def delete_user_car_goods():
    """删除购物车商品"""
    try:

        user_id = g.user_data["user_id"]
        uid_list = request.json.get("uid_list")  # array

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not uid_list:
            error = "UIDList is required."

        if error:
            return response(msg=error, code=1, status=400)

        client["order"].update({"uid": {"$in": uid_list}}, {"$set": {"state": -2}}, multi=True)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s.", code=1, status=500)


def post_car_generate_order():
    """
    购物车合并订单
    """
    try:

        user_id = g.user_data["user_id"]
        uid_list = request.json.get("uid_list")  # array

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not uid_list:
            error = "UIDList is required."

        if error:
            return response(msg=error, code=1, status=400)

        order = str(int(time.time() * 1000)) + str(random.randint(1001, 9999))

        # 合并购物车
        error = car.carMergeOrder(uid_list, order)
        if error:
            raise Exception(error)

        # 返回订单信息
        orderInfo, error = car.queryOrderDetail(user_id, order)
        if error:
            raise Exception(error)

        return response(data=orderInfo)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s.", code=1, status=500)


def get_user_order_list():
    """
    用户订单列表
    """
    try:

        user_id = g.user_data["user_id"]
        is_complete = request.args.get("is_complete")  # true完成 false待付款
        page = request.args.get("page")
        num = request.args.get("num")

        error = None
        if not user_id:
            error = "UserID is required."
        elif not (str.isdecimal(page) and str.isdecimal(num)):
            error = "Page or num invalid."
        elif int(num) < 1 or int(page) < 1:
            error = "Page or num invalid."
        elif is_complete not in ("true", "false"):
            error = "IsComplete invalid."

        if error:
            return response(msg=error, code=1, status=400)

        # 更新订单状态 支付超时更新状态
        error = orders.updateOrderState(user_id)
        if error:
            raise Exception(error)

        # 查询订单列表
        dataList, error = orders.queryOrderList(user_id, is_complete, page, num)
        if error:
            raise Exception(error)

        return response(data=dataList)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s.", code=1, status=500)


def get_not_complete_order_count():
    """未付款的订单数"""
    try:

        user_id = g.user_data["user_id"]
        if not user_id:
            return response(msg="Bad Request: User not logged in.", code=1, status=400)

        # 查询未支付的订单数
        count, error = orders.queryUnpaidOrderNum(user_id)
        if error:
            raise Exception(error)

        return response(data=count)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s.", code=1, status=500)


def put_cancel_order():
    """取消订单"""
    try:

        user_id = g.user_data["user_id"]
        order_id = request.json.get("order_id")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not order_id:
            error = "OrderID is required."
        if error:
            return response(msg=error, code=1, status=400)

        error = orders.updateCancelOrder(order_id, user_id)
        if error:
            raise Exception(error)

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s.", code=1, status=500)


def post_order_payment_param():
    """生成支付请求参数"""
    request_param = ""
    try:

        user_id = g.user_data["user_id"]
        order = request.json.get("order")
        pay_method = request.json.get("channel")  # 余额 支付宝 微信

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif not order:
            error = "Order is required."
        elif pay_method not in ["微信", "支付宝", "余额"]:
            error = "PayMethod invalid."

        if error:
            return response(msg=error, code=1, status=400)

        # 交易金额查询
        goodId, totalAmount, balance, error = orders.queryOrderTotalAmount(order, user_id)
        if error:
            raise Exception(error)

        # 交易记录
        trade_id = str(int(time.time() * 1000)) + str(random.randint(1001, 9999))
        error = orders.tradeRecords(trade_id, goodId, order, totalAmount, pay_method)
        if error:
            raise Exception(error)

        # 余额支付
        if pay_method == "余额":
            trade_data = {"trade_id": trade_id, "balance": balance, "trade_amount": totalAmount}
            import json
            trade_str = json.dumps(trade_data)
            request_param = trade_str

        # 支付宝支付
        if pay_method == "支付宝":
            alipay = AliPayCustomTradeAppPay(str(order), str(totalAmount), subject="图片购买")
            request_param = alipay.alipy_trade_app_pay_request()

        # 微信支付
        if pay_method == "微信":
            wechatpay = WechatPay(order, int(totalAmount * 100))
            prepay_id = wechatpay.wechat_payment_request()
            if not prepay_id:
                return response(msg="请求微信失败", code=1)
            request_param = wechatpay.generate_app_call_data(prepay_id)

        return response(data=request_param)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_alipay_callback_verify():
    """支付宝回调验证"""
    try:
        alipay_resp_param = request.form.to_dict()

        # 验签
        is_valid, err = AliPayCustomTradeAppPay.alipy_trade_app_pay_response(alipay_resp_param)
        if not is_valid:
            log.error(err)
            return Response("failure")

        out_trade_no = alipay_resp_param["out_trade_no"]
        total_amount = alipay_resp_param["total_amount"]
        dataList = list(client["order"].find({"order": out_trade_no, "state": 1}))
        if not dataList:
            log.error("out_trade_no is not exists")
            return Response("failure")

        user_id = dataList[0]["user_id"]
        error = orders.orderPaySuccessFollowOperation(out_trade_no, user_id, dataList)
        if error:
            log.error(f"{out_trade_no} alipay pay success follow operation failed")

        return Response("success")
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_wechat_callback_verify():
    """微信支付回调验证"""
    try:
        data = request.data
        out_trade_no, total_fee, _ = WechatPay.verify_wechat_call_back(data)
        xml_data = WechatPay.generate_xml_data({"return_code": "FAIL", "return_msg": "验证失败"})
        if not all([out_trade_no, total_fee]):
            return Response(xml_data)

        dataList = list(client["order"].find({"order": out_trade_no, "state": 1}))
        if not dataList:
            log.error("out_trade_no is not exists")
            return Response(xml_data)

        user_id = dataList[0]["user_id"]
        error = orders.orderPaySuccessFollowOperation(out_trade_no, user_id, dataList)
        if error:
            log.error(f"{out_trade_no} wechat pay success follow operation failed")

        xmlData = WechatPay.generate_xml_data({"return_code": "SUCCESS", "return_msg": "OK"})
        return Response(xmlData)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_balance_payment():
    """余额支付"""
    try:

        user_id = g.user_data["user_id"]
        trade_id = request.json.get("trade_id")
        # password = request.json.get("password")

        # 校验
        error = None
        if not user_id:
            error = "user not logged in"
        elif not trade_id:
            error = "trade_id is required"
        if error:
            return response(msg=error, code=1, status=400)

        # if not password:
        #     return response(msg="请输入密码", code=1)

        # 校验密码
        # passwordMd5 = hashlib.md5(str(password).encode("utf-8")).hexdigest()
        # balance, error = orders.verifyBlancePayPassword(user_id, passwordMd5)
        # if error:
        #     return response(msg=str(error), code=1)

        # 获取交易金额及订单号
        trade_amount, order, error = orders.queryTradeAmountAndOrder(trade_id)
        if error:
            raise Exception(error)

        # 自己不能购买自己的商品
        dataList, error = orders.judgeIsOwnWorks(order, user_id, trade_amount)
        if error:
            return response(msg=str(error), code=1)

        error = orders.orderPaySuccessFollowOperation(order, user_id, dataList, trade_amount)
        if error:
            raise Exception("balance pay success follow operation failed: {}".format(error))

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_balance_recharge():
    """余额充值"""
    request_param = ""
    try:

        user_id = g.user_data["user_id"]
        channel = request.json.get("channel")  # 支付宝 微信
        total_amount = request.json.get("total_amount")

        # 校验
        error = None
        if not user_id:
            error = "User not logged in."
        elif channel not in ["微信", "支付宝", "余额"]:
            error = "Channel invalid."
        elif not total_amount:
            error = "TotalAmount is required."
        elif total_amount < 0 or type(total_amount) != float:
            error = "TotalAmount invalid."

        if error:
            return response(msg=error, code=1, status=400)

        # 创建订单、交易记录
        order = trade_id = str(int(time.time() * 1000)) + str(random.randint(1001, 9999))

        # 交易记录
        error = recharge.tradeRecords(channel, total_amount, trade_id)
        if error:
            raise Exception(error)

        # 创建充值订单
        error = recharge.createRechargeOrder(order, user_id, channel, total_amount)
        if error:
            raise Exception(error)

        # 支付宝支付
        if channel == "支付宝":
            alipay = AliPayCustomTradeAppPay(str(order), str(total_amount), subject="余额充值", type="recharge")
            request_param = alipay.alipy_trade_app_pay_request()

        # 微信支付
        if channel == "微信":
            wechatPay = WechatPay(order, int(total_amount * 100), type="recharge")
            prepay_id = wechatPay.wechat_payment_request()
            if not prepay_id:
                return response(msg="请求微信失败", code=1)
            request_param = wechatPay.generate_app_call_data(prepay_id)

        return response(data=request_param)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_top_up_alipay_callback_verify():
    """余额充值支付宝回调验证"""
    try:
        alipay_resp_param = request.form.to_dict()

        # 验签
        is_valid, err = AliPayCustomTradeAppPay.alipy_trade_app_pay_response(alipay_resp_param)
        if not is_valid:
            log.error(err)
            return Response("failure")

        # 校验订单号
        out_trade_no = alipay_resp_param["out_trade_no"]
        total_amount = alipay_resp_param["total_amount"]
        doc = client["recharge_records"].find_one({"order": out_trade_no})
        if not doc:
            return Response("failure")
        if str(doc.get("amount")) != total_amount:
            return Response("failure")

        # 充值成功后的记录操作
        user_id = doc.get("user_id")
        recharge.rechargeSuccessFollowOperation(out_trade_no, total_amount, user_id, "支付宝")

        return Response("success")
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_top_up_wechat_callback_verify():
    """余额充值微信回调验证"""
    try:
        out_trade_no, total_fee, _ = WechatPay.verify_wechat_call_back(request.data)
        xml_data = WechatPay.generate_xml_data({"return_code": "FAIL", "return_msg": "验证失败"})
        if not all([out_trade_no, total_fee]):
            return Response(xml_data)

        # 校验
        doc = client["recharge_records"].find_one({"order": out_trade_no})
        if not doc:
            return Response(xml_data)
        if doc.get("amount") != float(total_fee) / 100:
            return Response(xml_data)

        # 充值成功后的记录操作
        user_id = doc.get("user_id")
        recharge.rechargeSuccessFollowOperation(out_trade_no, float(total_fee) / 100, user_id, "微信")

        xml_data = WechatPay.generate_xml_data({"return_code": "SUCCESS", "return_msg": "OK"})
        return Response(xml_data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def postOrderRefund():
    """订单退款申请"""
    try:
        order = request.json.get("order")
        explain = request.json.get("explain")

        # 参数校验
        error = None
        if not order:
            error = "order is required"
        elif not explain:
            error = "explain is required"
        if error:
            return response(msg=error, code=1, status=400)
        if len(explain) > 200:
            return response(msg="退款说明最多200字")

        # 判断订单状态是否为已支付状态
        isState, error = orders.queryOrderState(order)
        if error:
            raise Exception(error)
        if not isState:
            return response(msg="order invalid", code=1, status=400)

        # 提交退款申请
        error = orders.updateOrderRefund(order, explain)
        if error:
            raise Exception(error)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def verifyPassword():
    try:
        user_id = g.user_data["user_id"]
        # 检查用户是否绑定手机、登录密码
        userOne, error = orders.getUser(user_id)
        if error is not None:
            raise Exception(error)
        if not any([userOne.get("password"), userOne.get("mobile")]):
            return response(data=2, code=0)
        elif not userOne.get("password"):
            return response(data=1, code=0)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)
