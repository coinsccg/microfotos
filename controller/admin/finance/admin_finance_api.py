# -*- coding: utf-8 -*-
"""
@Time: 2020/07/25 15:07:38
@File: admin_finance_api
@Auth: money
"""
import time
import datetime

from flask import request
from flask import Response

from middleware.auth import response
from constant import constant
from utils.util import ExportExcle
from utils.util import generate_uid
from utils.alipay import AliPayCustomTradeAppPay
from utils.wechat import WechatPay
from initialize import log
from initialize import client
from dao.admin.finance import orders
from dao.admin.finance import withdrawal
from dao.admin.finance import recharge
from dao.admin.finance import withdrawal_audit


def get_order_list(delta_time=30):
    """
    订单列表页
    :param delta_time: 允许查询的最大区间30天
    """
    data = {}
    try:
        # 参数
        num = request.args.get("num")
        page = request.args.get("page")
        content = request.args.get("content")
        category = request.args.get("category")  # order订单号，account账号
        state = request.args.get("state")  # -1订单作废，0正常，1未付款，2已付款，3已退款，4订单退款中，5退款失败， 10全部
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        start_time = start_time + " 00:00:00"
        end_time = end_time + " 23:59:59"
        timeArray1 = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        timeArray2 = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        start_time = int(time.mktime(timeArray1.timetuple()) * 1000)
        end_time = int(time.mktime(timeArray2.timetuple()) * 1000)

        # 参数校验
        error = None
        if not num:
            error = "num is required"
        elif not page:
            error = "page is required"
        elif int(page) < 1 or int(num) < 1:
            error = "page or num invalid"
        elif category not in ["account", "order"]:
            error = "category invalid"
        elif state not in ["1", "2", "3", "4", "5", "10", "-1"]:
            error = "state invalid"
        elif not start_time:
            error = "start_time is required"
        elif not end_time:
            error = "end_time is required"

        if error:
            return response(msg=error, code=1, status=400)

        if (int(end_time) - int(start_time)) // (24 * 3600 * 1000) > delta_time:
            return response(msg=f"最多可连续查询{delta_time}天以内的记录", code=1)

        # 更新订单状态
        err = orders.updateOrderState()
        if err is not None:
            raise Exception(err)

        # 订单列表
        orderList, err = orders.queryOrderList(state, category, content, start_time, end_time, page, num)
        if err is not None:
            raise Exception(err)

        # 总数
        totalNum, err = orders.queryOrderTotalNum(state, category, content, start_time, end_time)
        if err is not None:
            raise Exception(err)

        data["count"] = totalNum
        data["list"] = orderList
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_order_refund_first():
    try:
        userId = request.json.get("user_id")
        order = request.json.get("order")
        reason = request.json.get("reason")
        state = request.json.get("state")  # 1退款 0驳回

        # 参数校验
        error = None
        if not order:
            error = "order is required"
        elif state not in [1, 0]:
            error = "state invalid"
        elif not userId:
            error = "user_id is required"
        if error:
            return response(msg=error, code=1, status=400)

        if state == 1:
            # 确认退款
            amount, payMethod, error = orders.queryRefundAmount(order)
            if error:
                raise Exception(error)
            error = orders.refundFollowUpoperation(order, userId, amount, payMethod=payMethod)
            if error:
                raise Exception(error)
        else:
            # 给用户发送退款驳回消息
            error = orders.rejectRefundSendMessage(userId, reason, order)
            if error:
                raise Exception(error)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 暂时不用
def putOrderRefund():
    """订单退款"""
    try:
        # 参数
        userId = request.json.get("user_id")
        order = request.json.get("order")
        reason = request.json.get("reason")
        state = request.json.get("state")  # 1退款 0驳回

        # 参数校验
        error = None
        if not order:
            error = "order is required"
        elif state not in [1, 0]:
            error = "state invalid"
        elif not userId:
            error = "user_id is required"
        if error:
            return response(msg=error, code=1, status=400)

        if state == 1:
            # 向第三方发起退款请求
            error = orders.sendRefundRequest(order, userId)
            if error:
                raise Exception(error)
        else:
            # 给用户发送退款驳回消息
            error = orders.rejectRefundSendMessage(order, reason, order)
            if error:
                raise Exception(error)

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


# 舍弃 支付宝退款没有回调
def alipayRefundCallback():
    """支付宝退款回调"""
    try:
        alipayResParam = request.form.to_dict()

        # 验签
        isValid, err = AliPayCustomTradeAppPay.alipy_trade_app_pay_response(alipayResParam)
        if not isValid:
            log.error(err)
            return Response("failure")

        # 退款后续操作
        out_trade_no = alipayResParam["out_trade_no"]
        total_amount = alipayResParam["total_amount"]
        tmp = list(client["order"].find({"order": out_trade_no, "state": 4}))
        if not tmp:
            log.error("out_trade_no is not exists")
            return Response("failure")

        userId = tmp[0]["user_id"]
        error = orders.refundFollowUpoperation(out_trade_no, userId, total_amount)
        if error:
            log.error(f"{out_trade_no} alipay refund success follow operation failed")
        return Response("success")
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def wechatRefundCallback():
    """微信退款回调"""
    try:
        out_trade_no, total_fee = WechatPay.verify_refund_callback(request.data)
        xml_data = WechatPay.generate_xml_data({"return_code": "FAIL", "return_msg": "验证失败"})
        if not all([out_trade_no, total_fee]):
            return Response(xml_data)

        tmp = list(client["order"].find({"order": out_trade_no, "state": 4}))
        if not tmp:
            log.error("out_trade_no is not exists")
            return Response(xml_data)

        userId = tmp[0]["user_id"]
        error = orders.refundFollowUpoperation(out_trade_no, userId, float(total_fee) / 100)
        if error:
            log.error(f"{out_trade_no} wechat refund success follow operation failed")
        xmlData = WechatPay.generate_xml_data({"return_code": "SUCCESS", "return_msg": "OK"})
        return Response(xmlData)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_order_detail():
    """
    订单详情
    :param domain: 域名
    """
    data = {}
    try:
        # 参数
        order = request.args.get('order')
        user_id = request.args.get('user_id')  # 买家id

        # 参数校验
        error = None
        if not order:
            error = "order is required"
        elif not user_id:
            error = "userId is required"
        if error:
            return response(msg=error, code=1, status=400)

        # 商品信息
        dataList, orderInfo, amount, count, error = orders.orderDetail(order)
        if error is not None:
            raise Exception(error)

        # 用户信息
        userInfo, error = orders.userInfo(user_id)
        if error is not None:
            raise Exception(error)
        data["user_info"] = userInfo
        data["works_list"] = dataList
        orderInfo["count"] = count
        orderInfo["amount"] = amount
        data["order_info"] = orderInfo
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_withdrawal_records(delta_time=30):
    """
    提现记录
    :param delta_time: 允许查询的最大区间30天
    """
    data = {}
    try:
        # 参数
        num = request.args.get("num")
        page = request.args.get("page")
        content = request.args.get("content")
        category = request.args.get("category")  # order订单号，account账号
        state = request.args.get("state")  # 1驳回，2已完成
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        start_time = start_time + " 00:00:00"
        end_time = end_time + " 23:59:59"
        timeArray1 = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        timeArray2 = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        start_time = int(time.mktime(timeArray1.timetuple()) * 1000)
        end_time = int(time.mktime(timeArray2.timetuple()) * 1000)

        # 参数校验
        error = None
        if not num:
            error = "num is required"
        elif not page:
            error = "page is required"
        elif int(page) < 1 or int(num) < 1:
            error = "page or num invalid"
        elif category not in ["account", "order"]:
            error = "category invalid"
        elif state not in ["0", "2"]:
            error = "state invalid"
        elif not start_time:
            error = "start_time invalid"
        elif not end_time:
            error = "end_time invalid"
        if error:
            return response(msg=error, code=1, status=400)

        if (int(end_time) - int(start_time)) // (24 * 3600 * 1000) > delta_time:
            return response(msg=f"最多可连续查询{delta_time}天以内的记录", code=1)

        # 提现列表
        dataList, error = withdrawal.queryWithdrawalList(category, content, state, start_time, end_time, page, num)
        if error is not None:
            raise Exception(error)

        # 总数
        totalNum, error = withdrawal.queryWithdrawalTotalNum(category, content, state, start_time, end_time)
        if error is not None:
            raise Exception(error)

        data["count"] = totalNum
        data["list"] = dataList
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_recharge_channel():
    """充值全部渠道"""
    try:
        # 查询
        return response(data=["支付宝", "微信"])
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_order_recharge(delta_time=30):
    """
    充值记录
    :param delta_time: 允许查询的最大区间30天
    """
    data = {}
    try:
        # 参数
        num = request.args.get("num")
        page = request.args.get("page")
        content = request.args.get("content")
        category = request.args.get("category")  # order订单号，account充值账号，trade交易号
        state = request.args.get("state")  # 0未支付，1已支付完成, 2全部
        channel = request.args.get("channel")  # 支付宝/微信 全部default
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        start_time = start_time + " 00:00:00"
        end_time = end_time + " 23:59:59"
        timeArray1 = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        timeArray2 = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        start_time = int(time.mktime(timeArray1.timetuple()) * 1000)
        end_time = int(time.mktime(timeArray2.timetuple()) * 1000)

        # 参数校验
        error = None
        if not num:
            error = "num is required"
        elif not page:
            error = "page is required"
        elif int(page) < 1 or int(num) < 1:
            error = "page or num invalid"
        elif category not in ["account", "order", "trade"]:
            error = "category invalid"
        elif state not in ["2", "1", "0"]:
            error = "state invalid"
        elif channel not in ["支付宝", "微信", "default"]:
            error = "channel invalid"
        if error:
            return response(msg=error, code=1, status=400)

        if (int(end_time) - int(start_time)) // (24 * 3600 * 1000) > delta_time:
            return response(msg=f"最多可连续查询{delta_time}天以内的记录", code=1)

        # 充值订单列表
        dataList, error = recharge.queryRechargeList(category, content, state, start_time, end_time, page, num, channel)
        if error is not None:
            raise Exception(error)

        # 总数
        totalNum, error = recharge.queryRechargeTotalNum(category, content, state, start_time, end_time, channel)
        if error is not None:
            raise Exception(error)

        data["count"] = totalNum
        data["list"] = dataList
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_withdrawal_records_audit(delta_time=30):
    """
    提现审核列表
    :param delta_time: 允许查询的最大区间30天
    """
    data = {}
    try:
        # 参数
        num = request.args.get("num")
        page = request.args.get("page")
        content = request.args.get("content")
        category = request.args.get("category")  # order订单号，account申请账号
        channel = request.args.get("channel")  # 全部传default, 其余对应传，如支付宝
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        start_time = start_time + " 00:00:00"
        end_time = end_time + " 23:59:59"
        timeArray1 = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        timeArray2 = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        start_time = int(time.mktime(timeArray1.timetuple()) * 1000)
        end_time = int(time.mktime(timeArray2.timetuple()) * 1000)

        # 参数校验
        error = None
        if not num:
            error = "num is required"
        elif not page:
            error = "page is required"
        elif int(page) < 1 or int(num) < 1:
            error = "page or num invalid"
        elif category not in ["account", "order", "trade"]:
            error = "category invalid"
        elif not start_time:
            error = "start_time is required"
        elif not end_time:
            error = "end_time is required"
        elif not channel:
            error = "channel is required"
        if error:
            return response(msg=error, code=1, status=400)

        if (int(end_time) - int(start_time)) // (24 * 3600 * 1000) > delta_time:
            return response(msg=f"最多可连续查询{delta_time}天以内的记录", code=1)

        # 提现审核列表
        dataList, error = withdrawal_audit.queryWithdrawalAuditList(category, content, start_time, end_time, channel,
                                                                    page, num)
        if error is not None:
            raise Exception(error)
        # 总数
        totalNum, error = withdrawal_audit.queryWithdrawalAuditTotalNum(category, content, start_time, end_time,
                                                                        channel)
        if error is not None:
            raise Exception(error)

        data["count"] = totalNum
        data["list"] = dataList
        return response(data=data)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def put_withdrawal_records_state():
    """
    提现审核接口
    """
    try:
        # 参数
        order_list = request.json.get("order_list")  # array
        state = request.json.get("state")  # 完成传2 驳回传0

        # 参数校验
        error = None
        if not order_list:
            error = "order_list is required"
        if state not in [0, 2]:
            error = "state invalid"
        if error:
            return response(msg=error, code=1, status=400)

        # 审核
        error = withdrawal_audit.withdrawalAudit(order_list, state)
        if error is not None:
            raise Exception(error)

        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_withdrawal_records_export(delta_time=30, domain=constant.DOMAIN):
    """
    提现记录导出
    :param delta_time: 允许查询的最大区间30天
    """
    try:
        # 参数
        content = request.args.get("content")
        category = request.args.get("category")  # order订单号，account账号
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        state = request.args.get("state")  # 1驳回，2已完成
        start_time = start_time + " 00:00:00"
        end_time = end_time + " 23:59:59"
        timeArray1 = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        timeArray2 = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        start_time = int(time.mktime(timeArray1.timetuple()) * 1000)
        end_time = int(time.mktime(timeArray2.timetuple()) * 1000)

        # 参数校验
        error = None
        if category not in ["account", "order"]:
            error = "category invalid"
        elif state not in ["1", "2"]:
            error = "state invalid"
        elif not start_time:
            error = "start_time is required"
        elif not end_time:
            error = "end_time is required"
        if error:
            return response(msg=error, code=1, status=400)

        if (int(end_time) - int(start_time)) // (24 * 3600 * 1000) > delta_time:
            return response(msg=f"最多可连续查询{delta_time}天以内的记录", code=1)

        # 提现记录列表
        dataList, error = withdrawal.queryWithdrawalListExport(category, content, state, start_time, end_time)
        if error is not None:
            raise Exception(error)

        temp = {
            "order": "提现单号",
            "create_time": "申请时间",
            "amount": "提现金额",
            "account": "申请账号",
            "state": "订单状态",
            "channel": "提现渠道",
            "trade_id": "支付号码",
            "trade_name": "支付姓名",
        }
        export = ExportExcle(temp, "提现记录")
        if not dataList:
            dataList = [{
                "order": "",
                "create_time": "",
                "amount": "",
                "account": "",
                "state": "",
                "channel": "",
                "trade_id": "",
                "trade_name": "",
            }]
        path = export.export_excle(dataList, "export", "order")
        return response(data=domain + path)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_order_recharge_export(delta_time=30, domain=constant.DOMAIN):
    """
    充值记录导出
    :param delta_time: 允许查询的最大区间30天
    :param domain: 域名
    """
    data = {}
    try:
        # 参数
        content = request.args.get("content")
        category = request.args.get("category")  # order订单号，account充值账号，trade交易号
        state = request.args.get("state")  # 0未支付，1已支付完成, 2全部
        channel = request.args.get("channel")  # 支付宝/微信 全部default
        start_time = request.args.get("start_time")
        end_time = request.args.get("end_time")
        start_time = start_time + " 00:00:00"
        end_time = end_time + " 23:59:59"
        timeArray1 = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        timeArray2 = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        start_time = int(time.mktime(timeArray1.timetuple()) * 1000)
        end_time = int(time.mktime(timeArray2.timetuple()) * 1000)

        # 参数校验
        error = None
        if category not in ["account", "order", "trade"]:
            error = "category invalid"
        elif state not in ["2", "1", "0"]:
            error = "state invalid"
        elif not start_time:
            error = "start_time is required"
        elif not end_time:
            error = "end_time is required"
        elif channel not in ["支付宝", "微信", "default"]:
            error = "channel invalid"
        if error:
            return response(msg=error, code=1, status=400)

        if (int(end_time) - int(start_time)) // (24 * 3600 * 1000) > delta_time:
            return response(msg=f"最多可连续查询{delta_time}天以内的记录", code=1)

        # 充值记录列表
        dataList, error = recharge.rechargeListExport(category, content, state, start_time, end_time, channel)
        if error is not None:
            raise Exception(error)

        temp = {
            "order": "充值单号",
            "create_time": "充值时间",
            "amount": "充值金额",
            "account": "充值账号",
            "state": "订单状态",
            "channel": "充值渠道",
            "trade_id": "支付交易号",
        }
        if not dataList:
            dataList = {
                "order": "",
                "create_time": "",
                "amount": "",
                "account": "",
                "state": "",
                "channel": "",
                "trade_id": "",
            }
        export = ExportExcle(temp, "充值记录")
        path = export.export_excle(dataList, "export", "order")
        return response(data=domain + path)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_withdrawal_records_audit_export(delta_time=30, domain=constant.DOMAIN):
    """
    提现审核列表导出
    :param delta_time: 允许查询的最大区间30天
    :param domain: 域名
    """
    data = {}
    try:
        # 参数
        order_list = request.json.get("order_list")
        content = request.json.get("content")
        category = request.json.get("category")  # order订单号，account申请账号
        channel = request.json.get("channel")  # 全部传default, 其余对应传，如支付宝
        start_time = request.json.get("start_time")
        end_time = request.json.get("end_time")
        start_time = start_time + " 00:00:00"
        end_time = end_time + " 23:59:59"
        timeArray1 = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        timeArray2 = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        start_time = int(time.mktime(timeArray1.timetuple()) * 1000)
        end_time = int(time.mktime(timeArray2.timetuple()) * 1000)

        # 参数校验
        error = None
        if category not in ["account", "order", "trade"]:
            error = "category invalid"
        elif not start_time:
            error = "start_time is required"
        elif not end_time:
            error = "end_time is required"
        elif not channel:
            error = "channel is required"
        if error:
            return response(msg=error, code=1, status=400)

        if (int(end_time) - int(start_time)) // (24 * 3600 * 1000) > delta_time:
            return response(msg=f"最多可连续查询{delta_time}天以内的记录", code=1)

        # 提现审核列表
        dataList, error = withdrawal_audit.withdrawalAuditListExport(category, content, order_list, start_time,
                                                                     end_time, channel)
        if error is not None:
            raise Exception(error)

        temp = {
            "order": "提现单号",
            "create_time": "申请时间",
            "amount": "提现金额",
            "account": "申请账号",
            "channel": "提现渠道",
            "trade_id": "支付号码",
            "trade_name": "支付姓名",
        }
        if not dataList:
            dataList = [{
                "order": "",
                "create_time": "",
                "amount": "",
                "account": "",
                "channel": "",
                "trade_id": "",
                "trade_name": "",
            }]
        export = ExportExcle(temp, "申请提现记录")
        path = export.export_excle(dataList, "export", "order")
        return response(data=domain + path)
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def post_withdrawal_bank():
    """可提现银行"""
    try:
        bank = request.json.get("bank")

        # 参数校验
        error = None
        if not bank:
            error = "请输入可提现银行"
        elif not isinstance(bank, str):
            error = "请输入正确的银行"
        if error:
            return response(msg=error, code=1)

        client["bank"].update({}, {"$set": {"state": -1}}, multi=True)

        bank_list = bank.split("、")
        for i in bank_list:
            cond = dict()
            cond["uid"] = generate_uid(24)
            cond["ico_url"] = ""
            cond["fees"] = 0.01
            cond["state"] = 1
            cond["name"] = i
            client["bank"].insert(cond)
        return response()
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s." % str(e), code=1, status=500)


def get_bank_list():
    """银行列表"""
    try:
        cursor = client["bank"].find({"state": 1}, {"_id": 0, "name": 1})
        return response(data=[doc["name"] for doc in cursor])
    except Exception as e:
        log.error(e)
        return response(msg="Internal Server Error: %s" % str(e), code=1, status=500)

