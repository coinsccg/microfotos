# -*- coding: utf-8 -*-
"""
@Time: 2020/12/31 20:19
@Auth: money
@File: recharge.py
"""
import time
import datetime
import base64
import random
from bson.son import SON

from initialize import init_stamp
from initialize import client
from utils.util import generate_uid


def tradeRecords(channel, total_amount, trade_id):
    error = None
    try:
        # 生成交易id

        condition = {
            "trade_id": trade_id, "type": "alipay" if channel == "支付宝" else "wxpay", "trade_amount": total_amount,
            "goods_id": "", "state": 1, "order": "", "create_time": int(time.time() * 1000),
            "update_time": int(time.time() * 1000)
        }
        client["trade"].insert(condition)
    except Exception as e:
        error = e
    finally:
        return error


def createRechargeOrder(order, user_id, channel, total_amount):
    error = None
    try:
        condition = {
            "order": order, "user_id": user_id, "channel": channel, "amount": total_amount, "state": 0,
            "trade_id": order, "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
        }
        client["recharge_records"].insert(condition)
    except Exception as e:
        error = e
    finally:
        return error


def rechargeSuccessFollowOperation(out_trade_no, total_amount, user_id, method):
    error = None
    try:
        # 充值状态变更
        client["recharge_records"].update({"order": out_trade_no}, {"$set": {"state": 1}})
        # 用户余额变更
        client["user"].update({"uid": user_id}, {"$inc": {"balance": float(total_amount)}})
        # 余额记录变更
        doc = client["user"].find_one({"uid": user_id}, {"_id": 0, "balance": 1})
        condition = {
            "user_id": user_id, "type": method + "充值", "order": out_trade_no,
            "amount": float(total_amount), "balance": doc["balance"], "state": 1,
            "create_time": int(time.time() * 1000), "update_time": int(time.time() * 1000)
        }
        client["balance_record"].insert(condition)
    except Exception as e:
        error = e
    finally:
        return error
