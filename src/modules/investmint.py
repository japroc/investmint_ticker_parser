#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import calendar
import datetime
import json
import re
import requests
import html


class Currency:
    RUB = "RUB"
    USD = "USD"


def parse_float(value):
    val = value.strip().replace(",", ".").replace("&nbsp;", "").replace("\\xa0", "").replace("\xa0", "")
    return float(val) if val else None

def parse_currency(currency_):
    if not currency_:
        return None
    currency = currency_.strip()
    currencies = {
        "₽": Currency.RUB,
        "$": Currency.USD,
    }
    currency_ords = {
        8381: Currency.RUB,
        36: Currency.USD,
    }
    res = currencies.get(currency)
    if not res:
        res = currency_ords.get(ord(currency), currency)
    return res

def parse_date(day_and_month_, year_):
    day_and_month = day_and_month_.strip().split(" ")
    day = int(day_and_month[0])
    month = parse_month(day_and_month[1])
    year = int(year_)
    date = Date(day, month, year)
    return date

def parse_month(month):
    monthes = {
        "янв": 1,
        "января": 1,
        "фев": 2,
        "февраля": 2,
        "мар": 3,
        "марта": 3,
        "апр": 4,
        "апреля": 4,
        "мая": 5,
        "июн": 6,
        "июня": 6,
        "июл": 7,
        "июля": 7,
        "авг": 8,
        "августа": 8,
        "сен": 9,
        "сентября": 9,
        "окт": 10,
        "октября": 10,
        "ноя": 11,
        "ноября": 11,
        "дек": 12,
        "декабря": 12,
    }
    return monthes.get(month)

def parse_divs_table(divs_table):
    future_divs = list()
    previous_divs = list()

    future_divs_regex = re.compile(r"""<tr class="(.*?)">.*?<td class="text-nowrap">(.*?)<.*?>(.*?)</span></td><td class="text-nowrap">(.*?)<span.*?>(.*?)</span></td><td class="text-nowrap text-right">(.*?)(?:&nbsp;)?<small class="text-muted">(.*?)</small></td><td class="text-right">(.*?)<small class="text-muted">%</small></td><td></td></tr>""")
    previous_divs_regex = re.compile(r"""<tr class="(.*?)">.*?<td class="text-nowrap">(.*?)<.*?>(.*?)</span></td><td class="text-nowrap">(.*?)<span.*?>(.*?)</span></td><td class="text-nowrap text-right">(.*?)(?:&nbsp;)?<small class="text-muted">(.*?)</small></td><td class="text-right">(.*?)<small class="text-muted">%</small></td><td class="text-right">(.*?)(?:&nbsp;)?<""")

    lookup_for_future_divs = True

    prev_line_start_idx = divs_table.find("<tr")
    while True:
        line_start_idx = divs_table.find("<tr", prev_line_start_idx+1)
        if line_start_idx == -1:
            break

        line_end_idx = divs_table.find("</tr>", line_start_idx)
        line = divs_table[line_start_idx:line_end_idx+5]

        if lookup_for_future_divs:
            m = re.search(future_divs_regex, line)
            if not m:
                lookup_for_future_divs = False

        if not lookup_for_future_divs:
            m = re.search(previous_divs_regex, line)
            if not m:
                break

        div_info = DivInfo()
        div_info.verified = "green-bg" in m.group(1) or "gray-bg" not in m.group(1)
        div_info.buy_till_date = parse_date(m.group(2), m.group(3))
        div_info.registry_close_date = parse_date(m.group(4), m.group(5))
        div_info.dividend = parse_float(m.group(6))
        div_info.currency = parse_currency(m.group(7))
        div_info.div_yield = parse_float(m.group(8))

        if lookup_for_future_divs:
            future_divs.append(div_info)
        else:
            div_info.close_price = parse_float(m.group(9))
            previous_divs.append(div_info)

        prev_line_start_idx = line_start_idx

    return future_divs, previous_divs

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

    # def __repr__(self):
    #     return json.dumps(self.json(), indent=4)


class DivInfo:
    def __init__(self):
        self.verified = None
        self.buy_till_date = None
        self.registry_close_date = None
        self.dividend = None
        self.currency = None
        self.div_yield = None
        self.close_price = None

    def json(self):
        buy_till_date = self.buy_till_date.json() if isinstance(self.buy_till_date, Date) else self.buy_till_date
        registry_close_date = self.registry_close_date.json() if isinstance(self.registry_close_date, Date) else self.registry_close_date
        return {
            "verified": self.verified,
            "buy_till_date": buy_till_date,
            "registry_close_date": registry_close_date,
            "dividend": self.dividend,
            "currency": self.currency,
            "div_yield": self.div_yield,
            "close_price": self.close_price,
        }

    # def __repr__(self):
    #     return json.dumps(self.json(), indent=4)


class TickerInfo:
    def __init__(self):
        self.name = None
        self.sector = None
        self.isin = None
        self.price = None
        self.currency = None
        self.dividend = None
        self.div_yield = None
        self.buy_till_date = None
        self.ex_div_date = None
        self.registry_close_date = None
        self.div_pay_date = None
        self.future_divs = None
        self.previous_divs = None

    def eval_div_period(self, d2, d1):
        if not d2 or not d1:
            return None

        td = d2 - d1
        td_days = td.days

        if td_days > 50 and td_days < 130:
            return 3
        elif td_days > 150 and td_days < 220:
            return 6
        elif td_days > 300 and td_days < 410:
            return 12
        else:
            return None

    def json(self):
        buy_till_date = self.buy_till_date.json() if isinstance(self.buy_till_date, Date) else self.buy_till_date
        ex_div_date = self.ex_div_date.json() if isinstance(self.ex_div_date, Date) else self.ex_div_date
        registry_close_date = self.registry_close_date.json() if isinstance(self.registry_close_date, Date) else self.registry_close_date
        div_pay_date = self.div_pay_date.json() if isinstance(self.div_pay_date, Date) else self.div_pay_date
        future_divs = list(map(lambda x: x.json(), self.future_divs))
        previous_divs = list(map(lambda x: x.json(), self.previous_divs))
        future_div = future_divs[-1] if future_divs else None
        previous_div = previous_divs[0] if previous_divs else None
        if self.future_divs and self.previous_divs:
            next_date = self.future_divs[-1].registry_close_date.date
            prev_date = self.previous_divs[0].registry_close_date.date
            div_period = self.eval_div_period(next_date, prev_date)
        elif len(self.previous_divs) >= 2:
            date1 = self.previous_divs[0].registry_close_date.date
            date2 = self.previous_divs[1].registry_close_date.date
            div_period = self.eval_div_period(date1, date2)
        else:
            div_period = None

        if self.currency:
            currency = self.currency
        elif self.future_divs:
            currency = self.future_divs[-1].currency
        elif self.previous_divs:
            currency = self.previous_divs[0].currency
        elif self.isin and self.isin.startswith("RU"):
            currency = Currency.RUB
        else:
            currency = Currency.USD
        return {
            "name": self.name,
            "sector": self.sector,
            "isin": self.isin,
            "price": self.price,
            "currency": currency,
            "dividend": self.dividend,
            "div_yield": self.div_yield,
            "buy_till_date": buy_till_date,
            "ex_div_date": ex_div_date,
            "registry_close_date": registry_close_date,
            "div_pay_date": div_pay_date,
            "future_divs": future_divs,
            "previous_divs": previous_divs,
            "future_div": future_div,
            "previous_div": previous_div,
            "div_period": div_period,
        }

    # def __repr__(self):
    #     return json.dumps(self.json(), indent=4)


def parse_ticker(ticker):
    r = requests.get("https://investmint.ru/{}/".format(ticker.lower()))
    text = r.text

    if r.status_code != 200:
        return None

    ticket_info = TickerInfo()

    # m = re.search(r"""<h2 class="mb-1">Утверждённые ближайшие дивиденды на одну акцию (.*?) сегодня</h2>""", text)
    m = re.search(r"""<div class="ml-3"><h1 class="mb-2">Дивиденды (.*?) \d{4}</h1>""", text)
    if m:
        ticket_info.name = html.unescape(m.group(1))

    m = re.search(r"""<div class="smallcaps">Сектор</div><p>(.*?)</p>""", text)
    if m:
        ticket_info.sector = m.group(1)

    m = re.search(r"""<div class="smallcaps">ISIN</div><p>(.*?)</p>""", text)
    if m:
        ticket_info.isin = m.group(1)

    m = re.search(r"""<div class="smallcaps">Курс акций</div><div class="d-flex align-items-center text-nowrap"><div class="num200 mr-2">(.*?)(?:</div>|<small class="text-muted">(.*?)</small></div>)""", text)
    if m:
        ticket_info.price = parse_float(m.group(1))
        ticket_info.currency = parse_currency(m.group(2))

    m = re.search(r"""><div class="smallcaps mb-1">Дивиденд</div><div class="d-flex align-items-center"><div class="num200">([\d,]*)""", text)
    if m:
        ticket_info.dividend = parse_float(m.group(1))

    m = re.search(r"""<div class="smallcaps">Доходность</div><div class="num200">(.*?)<small class="text-muted">%</small""", text)
    if m:
        ticket_info.div_yield = parse_float(m.group(1))

    m = re.search(r"""<div class="eventname smallcaps">Купить до.*?</small>(.*?)<small class="text-muted">(.*?)</small>""", text)
    if m:
        ticket_info.buy_till_date = parse_date(m.group(1), m.group(2))

    m = re.search(r"""<div class="eventname smallcaps">Экс-дивидендная дата.*?</small>(.*?)<small class="text-muted">(.*?)</small>""", text)
    if m:
        ticket_info.ex_div_date = parse_date(m.group(1), m.group(2))

    m = re.search(r"""<div class="eventname smallcaps">Закрытие реестра.*?</small>(.*?)<small class="text-muted">(.*?)</small>""", text)
    if m:
        ticket_info.registry_close_date = parse_date(m.group(1), m.group(2))

    m = re.search(r"""<div class="eventname smallcaps">Дата выплаты.*?</small>(.*?)<small class="text-muted">(.*?)</small>""", text)
    if m:
        ticket_info.div_pay_date = parse_date(m.group(1), m.group(2))

    divs_table_start_idx = text.find("""<table class="table table-hover">""")
    divs_table_end_idx = text.find("""</table>""", divs_table_start_idx)
    divs_table = text[divs_table_start_idx:divs_table_end_idx]

    ticket_info.future_divs, ticket_info.previous_divs = parse_divs_table(divs_table)

    return ticket_info.json()