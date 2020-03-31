#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import calendar
import datetime
import re
import requests


class Date:
    def __init__(self, day=None, month=None, year=None):
        self.day = day
        self.month = month
        self.year = year

    @property
    def timestamp(self):
        return calendar.timegm(self.date.timetuple())

    @property
    def date(self):
        return datetime.date(self.year, self.month, self.day)

    def json(self):
        return {
            "day": self.day,
            "month": self.month,
            "year": self.year,
            "timestamp": self.timestamp,
        }


class Coupon:
    def __init__(self, date, coupon, coupon_yield):
        self.date = date
        self.coupon = coupon
        self.coupon_yield = coupon_yield

    def json(self):
        return {
            "date": self.date.json(),
            "coupon": self.coupon,
            "coupon_yield": self.coupon_yield,
        }


class BondInfo:
    def __init__(self):
        self.name = None
        self.isin = None
        self.publish_date = None
        self.close_date = None
        self.nominal = None
        self.currency = None
        self.coupon_yield = None
        self.next_coupon = None
        self.nkd = None
        self.coupon_period = None
        self.status = None
        self.all_coupons = None

    def eval_days_to_close(self):
        if not self.close_date:
            return None
        now = datetime.datetime.utcnow()
        now_date = datetime.date(now.year, now.month, now.day)
        close_date = datetime.date(self.close_date.year, self.close_date.month, self.close_date.day)
        td = close_date - now_date
        return td.days

    def json(self):
        publish_date = self.publish_date.json() if isinstance(self.publish_date, Date) else self.publish_date
        close_date = self.close_date.json() if isinstance(self.close_date, Date) else self.close_date
        all_coupons = list(map(lambda x: x.json(), self.all_coupons))
        return {
            "name": self.name,
            "isin": self.isin,
            "nominal": self.nominal,
            "currency": self.currency,
            "coupon_yield": self.coupon_yield,
            "next_coupon": self.next_coupon,
            "nkd": self.nkd,
            "coupon_period": self.coupon_period,
            "status": self.status,
            "publish_date": publish_date,
            "close_date": close_date,
            "days_to_close": self.eval_days_to_close(),
            "all_coupons": all_coupons,
        }


def parse_coupon_by_isin(isin):
    r = requests.get("https://smart-lab.ru/q/bonds/{}/".format(isin))
    text = r.text

    if r.status_code != 200:
        return None

    bond_info = BondInfo()

    m = re.search(r"""<td><abbr title="Краткое наименование ценной бумаги">Название</abbr></td>\s*?<td>(.*?)</td>""", text)
    if m:
        bond_info.name = m.group(1)

    m = re.search(r"""<td><abbr title="ISIN">ISIN</abbr></td>\s*?<td>(.*?)</td>""", text)
    if m:
        bond_info.isin = m.group(1)

    m = re.search(r"""<td><abbr title="Дата размещения, дд.мм.гг">Дата размещения</abbr></td>\s*?<td>(\d+)-(\d+)-(\d+)</td>""", text)
    if m:
        bond_info.publish_date = Date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    m = re.search(r"""<td><abbr title="Дата погашения, дд.мм.гг">Дата погашения</abbr></td>\s*?<td>(\d+)-(\d+)-(\d+)</td>""", text)
    if m:
        bond_info.close_date = Date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    m = re.search(r""">Номинал</abbr></td>\s*<td>(.*?)</td>""", text)
    if m:
        bond_info.nominal = int(m.group(1))

    m = re.search(r"""<td><abbr title="Валюта номинала">Валюта</abbr></td>\s*?<td>(.*?)</td>""", text)
    if m:
        bond_info.currency = "RUB" if m.group(1) == "руб" else None

    m = re.search(r""">Дох\. купона, годовых от ном</abbr></td>\s*<td(?:\s+class="up")?>(.*?)%</td>""", text)
    if m:
        bond_info.coupon_yield = float(m.group(1))

    m = re.search(r"""<abbr title="Величина купона">Купон, руб&nbsp;&nbsp;&nbsp;\(\?\)</abbr></a></td>\s*?<td>(.*?)\s""", text)
    if m:
        bond_info.next_coupon = float(m.group(1))

    m = re.search(r"""<abbr title="Накопленный купонный доход">НКД&nbsp;&nbsp;&nbsp;\(\?\)</abbr></a></td>\s*?<td>(.*?)\s""", text)
    if m:
        bond_info.nkd = float(m.group(1))

    m = re.search(r"""<td><abbr title="Длительность купона">Выплата купона, дн</abbr></td>\s*?<td>(.*?)</td>""", text)
    if m:
        bond_info.coupon_period = int(m.group(1))

    m = re.search(r"""<td><abbr title="Статус">Статус</abbr></td>\s*?<td>(.*?)</td>""", text)
    if m:
        bond_info.status = m.group(1)

    calendar_start_idx = text.find("""<h2 style="margin-top: 2em">Календарь выплаты купонов по облигации""")
    all_couponds_table_start_idx = text.find("""<table class="simple-little-table bond" cellspacing="0">""", calendar_start_idx)
    all_couponds_table_stop_idx = text.find("""</table>""", all_couponds_table_start_idx)
    all_couponds_table = text[all_couponds_table_start_idx:all_couponds_table_stop_idx]

    all_coupons = list()
    all_coupons_parts = re.findall(r"""<tr>\s*<td>\d+</td>\s*<td>(\d+)-(\d+)-(\d+)\s*</td>\s*<td>([0-9\.]*)</td>\s*<td>([\d+\.]*)%.*?</tr>""", all_couponds_table, re.S)
    for coupon_parts in all_coupons_parts:
        all_coupons.append(Coupon(
            date=Date(int(coupon_parts[0]), int(coupon_parts[1]), int(coupon_parts[2])),
            coupon=float(coupon_parts[3]),
            coupon_yield=float(coupon_parts[4])
        ))
    bond_info.all_coupons = all_coupons

    return bond_info.json()
