#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import calendar
import datetime
import re
import requests

def parse_date(day, month, year):
    months = {
        "Jan": 1,
        "Feb": 2,
        "Mar": 3,
        "Apr": 4,
        "May": 5,
        "Jun": 6,
        "Jul": 7,
        "Aug": 8,
        "Sep": 9,
        "Oct": 10,
        "Nov": 11,
        "Dec": 12,
    }

    return Date(int(day), months.get(month), int(year))


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


class DivInfo:
    def __init__(self):
        self.ex_div_date = None
        self.dividend = None
        self.pay_date = None
        self.div_yield = None

    def json(self):
        ex_div_date = self.ex_div_date.json() if isinstance(self.ex_div_date, Date) else self.ex_div_date
        pay_date = self.pay_date.json() if isinstance(self.pay_date, Date) else self.pay_date
        return {
            "dividend": self.dividend,
            "div_yield": self.div_yield,
            "ex_div_date": ex_div_date,
            "pay_date": pay_date,
        }


class TickerInfo:
    def __init__(self):
        self.price = None
        self.name = None
        self.industry = None
        self.sector = None
        self.currency = None
        self.pe = None
        self.next_earnings_date = None
        self.all_divs = list()

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
        next_earnings_date = self.next_earnings_date.json() if isinstance(self.next_earnings_date, Date) else self.next_earnings_date
        all_divs = list(map(lambda x: x.json(), self.all_divs))
        if len(self.all_divs) >= 2:
            date1 = self.all_divs[0].ex_div_date.date
            date2 = self.all_divs[1].ex_div_date.date
            div_period = self.eval_div_period(date1, date2)
        else:
            div_period = None
        return {
            "price": self.price,
            "name": self.name,
            "industry": self.industry,
            "sector": self.sector,
            "currency": self.currency,
            "pe": self.pe,
            "all_divs": all_divs,
            "div_period": div_period,
            "next_earnings_date": next_earnings_date,
        }


def get_ticker_info(ticker_):
    ticker = ticker_.lower()
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0"
    headers = {
        "User-Agent": user_agent, 
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Connection": "close",
    }
    url = "https://uk.investing.com/search/service/searchTopBar"

    data = "search_text={}".format(ticker.lower())
    r = requests.post(url, data=data, headers=headers, timeout=3)
    json_data = r.json()
    quotes = json_data["quotes"]
    quotes = list(filter(lambda x:x.get("symbol") == ticker.upper(), quotes))

    if not quotes and ticker_.endswith("p"):
        ticker = ticker[:-1]
        data = "search_text={}".format(ticker)
        r = requests.post(url, data=data, headers=headers, timeout=3)
        json_data = r.json()
        quotes = json_data["quotes"]
        quotes = list(filter(lambda x:x.get("symbol") == ticker.upper() + "_p", quotes))

    if not quotes:
        return None

    exchanges = {
        "Moscow": 4, 
        "NASDAQ": 3, 
        "NYSE": 2,
        "London": 1,
    }
    quotes = list(filter(lambda x: x.get("exchange") in exchanges.keys(), quotes))
    quotes = sorted(quotes, key=lambda x: exchanges.get(x.get("exchange"), 0), reverse=True)
    quote = quotes[0]
    link = "https://uk.investing.com{}".format(quote["link"])

    ticker_info = TickerInfo()

    r2 = requests.get(link, headers=headers, timeout=3)
    text = r2.text
    m = re.search("""<input type="text" class="newInput inputTextBox alertValue" placeholder="([^"]*)""", text)
    if m:
        ticker_info.price = float(m.group(1).replace(",", ""))

    m = re.search(r"""<h1 class="float_lang_base_1 relativeAttr"\s*dir="ltr" itemprop="name">(.*?)</h1>""", text)
    if m:
        ticker_info.name = m.group(1).strip()

    m = re.search(r"""<div>Industry<a.*?>(.*?)</a></div>""", text)
    if m:
        ticker_info.industry = m.group(1).strip()

    m = re.search(r"""<div>Sector<a.*?>(.*?)</a></div>""", text)
    if m:
        ticker_info.sector = m.group(1).strip()

    m = re.search(r"""Currency in <span class='bold'>(.*?)</span>""", text)
    if m:
        ticker_info.currency = m.group(1).strip()

    m = re.search(r"""Next Earnings Date.*?>([^\s]*) (\d*), (\d*)</a>""", text)
    if m:
        ticker_info.next_earnings_date = parse_date(m.group(2), m.group(1), m.group(3))

    m = re.search(r"""class="float_lang_base_1">P/E Ratio</span><span class="float_lang_base_2 bold">(.*?)</span""", text)
    if m:
        if m.group(1) == "N/A":
            ticker_info.pe = None
        else:
            ticker_info.pe = float(m.group(1))

    all_divs = list()

    m = re.search(r"""<li><a href="(.*?)" class="arial_12 bold">Dividends</a></li>""", text)
    if m:
        dividend_link = "https://uk.investing.com{}".format(m.group(1))

        r3 = requests.get(dividend_link, headers=headers, timeout=3)
        text3 = r3.text

        div_table_start_idx = text3.find("""<th class="first left">Ex-Dividend Date<span sort_default class="headerSortDefault"></span></th>""")
        div_table_finish_idx = text3.find("""</table>""", div_table_start_idx)
        div_table = text3[div_table_start_idx:div_table_finish_idx]

        regex  = r"""<tr event_timestamp=".*?">.*?">([^\s]*) (\d*), (\d*)</td>\s*"""
        regex += r"""<td>(.*?)</td>.*?"""
        regex += r"""<td data-value=".*?">([^\s]*) (\d*), (\d*)</td>\s*"""
        regex += r"""<td>(.*?)%</td>"""

        all_divs_info = re.findall(regex, div_table, re.S)

        for div_info in all_divs_info:
            di = DivInfo()
            di.ex_div_date = parse_date(div_info[1], div_info[0], div_info[2])
            di.dividend = float(div_info[3])
            di.pay_date = parse_date(div_info[5], div_info[4], div_info[6])
            di.div_yield = float(div_info[7])
            all_divs.append(di)

    ticker_info.all_divs = all_divs

    return ticker_info.json()
