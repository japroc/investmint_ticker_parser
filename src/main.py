#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import traceback

from flask import Flask
from flask import jsonify

from modules.investing_stock import get_ticker_info
from modules.investmint import parse_ticker
from modules.smartlab_bonds import parse_coupon_by_isin


app = Flask(__name__)


@app.route('/investing/<ticker>')
def get_investing_ticker(ticker):
    try:
        ticker_info = get_ticker_info(ticker)
        if ticker_info:
            resp = {"success": True, "result": ticker_info}
        else:
            resp = {"success": False, "error": "Ticker Not Found"}
    except Exception as e:
        traceback.print_exc()
        resp = {"success": False, "error": "{}".format(e)}
    finally:
        return jsonify(resp)


@app.route('/investmint/<ticker>')
def parse_investmint_ticker(ticker):
    try:
        ticker_info = parse_ticker(ticker)
        if ticker_info:
            resp = {"success": True, "result": ticker_info}
        else:
            resp = {"success": False, "error": "Ticker Not Found"}
    except Exception as e:
        traceback.print_exc()
        resp = {"success": False, "error": "{}".format(e)}
    finally:
        return jsonify(resp)


@app.route('/smartlab/coupon/<isin>')
def parse_smartlab_coupon(isin):
    try:
        coupon_info = parse_coupon_by_isin(isin)
        if coupon_info:
            resp = {"success": True, "result": coupon_info}
        else:
            resp = {"success": False, "error": "ISIN Not Found"}
    except Exception as e:
        traceback.print_exc()
        resp = {"success": False, "error": "{}".format(e)}
    finally:
        return jsonify(resp)


@app.route('/ping')
def ping():
    return "pong"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000)
