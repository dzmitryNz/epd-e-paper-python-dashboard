#!/usr/bin/python
# -*- coding:utf-8 -*-
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.sensor_service import parse_sensor_text, fetch_sensor_data
from services.solopool_service import fetch_solopool_data
from services.nano3stats_service import parse_jsonp, fetch_nano3stats_data


class FakeResponse:
    def __init__(self, text='', json_data=None, status=200):
        self.text = text
        self._json = json_data
        self.status_code = status

    def json(self):
        return self._json

    def raise_for_status(self):
        pass


class TestSensorService(unittest.TestCase):
    def test_parse_sensor_text(self):
        parsed = parse_sensor_text('dsw1:12.5;dsw2:ERR;bmpp:998')
        self.assertEqual(parsed, {'dsw1': '12.5', 'dsw2': 'ERR', 'bmpp': '998'})

    def test_fetch_sensor_data_keeps_all_values(self):
        """Last key must not be clobbered to None (regression)."""
        config = {'services': {'wifiiot_sensors_1': {
            'url': 'http://x/sensors',
            'responseType': 'text',
            'data': {
                'dsw1': {'path': 'dsw1', 'type': 'float', 'round': 2},
                'dsw2': {'path': 'dsw2', 'type': 'float', 'round': 2},
            },
        }}}
        with mock.patch('services.sensor_service.requests.get',
                        return_value=FakeResponse(text='dsw1:12.5;dsw2:7.25')):
            data = fetch_sensor_data(config, 'wifiiot_sensors_1')
        self.assertEqual(data, {'dsw1': 12.5, 'dsw2': 7.25})


class TestSolopoolService(unittest.TestCase):
    def test_fetch_solopool_data(self):
        config = {'services': {'solopool': {'url': 'http://pool/api'}}}
        payload = {'hashrate': 5.1e12, 'luck': 88, 'stats': {'blocksFound': 2}}
        with mock.patch('services.solopool_service.requests.get',
                        return_value=FakeResponse(json_data=payload)):
            data = fetch_solopool_data(config)
        self.assertEqual(data, {'hashrate': 5.1e12, 'luck': 88, 'blocks': 2})

    def test_no_url_returns_none(self):
        self.assertIsNone(fetch_solopool_data({'services': {}}))


class TestNano3statsService(unittest.TestCase):
    def test_parse_jsonp_with_trailing_commas(self):
        text = 'dashboardCallback({"workingmode": "1", "power": "120",});'
        parsed = parse_jsonp(text)
        self.assertEqual(parsed['workingmode'], '1')
        self.assertEqual(parsed['power'], '120')

    def test_parse_jsonp_bad_format_returns_none(self):
        self.assertIsNone(parse_jsonp('<html>error</html>'))

    def test_fetch_passes_auth_cookie(self):
        config = {'services': {'nano3stats': {
            'url': 'http://miner/get_dashboard.cgi',
            'authCookie': 'abc123',
        }}}
        text = 'dashboardCallback({"workingmode":"2","workingstatus":"1","power":"95"});'
        with mock.patch('services.nano3stats_service.requests.get',
                        return_value=FakeResponse(text=text)) as m:
            data = fetch_nano3stats_data(config)
        self.assertEqual(data, {'workingmode': '2', 'workingstatus': '1', 'power': '95'})
        self.assertEqual(m.call_args.kwargs.get('cookies'), {'auth': 'abc123'})


if __name__ == '__main__':
    unittest.main()
