# -*- coding: utf-8 -*-
"""
@Time: 2021/1/22 16:34
@Auth: money
@File: comm.py
"""
import time
import datetime


def strDateToTimestamp(start, end):
    start_time, end_time, deltaDay = 0, 0, 0
    if start != "0" and end != "0":
        start_time = start + " 00:00:00"
        end_time = end + " 23:59:59"
        timeArray1 = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        timeArray2 = datetime.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        start_time = int(time.mktime(timeArray1.timetuple()) * 1000)
        end_time = int(time.mktime(timeArray2.timetuple()) * 1000)

        deltaDay = (int(end_time) - int(start_time)) // (24 * 3600 * 1000)
    return start_time, end_time, deltaDay
