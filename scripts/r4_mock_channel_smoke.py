#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第四轮：独立模拟渠道服务实例的真实启动与转发冒烟。

启动两个独立进程：业务服务 :18084 与 mock-channel :18085；所有渠道通知
经 mock 服务转发到业务服务，逐条保存请求/上游响应/断言到
evidence/mock-channel-run.txt。不改动业务代码，不新增状态机。
"""
import datetime
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(r'd:/Desktop/shop')
EV = ROOT / 'evidence' / 'mock-channel-run.txt'
EXE = pathlib.Path(os.environ.get('TEMP', '/tmp')) / 'shop-trade-r4.exe'
MAIN = 'http://127.0.0.1:18084'
MOCK = 'http://127.0.0.1:18085'
lines = []


def log(text):
    lines.append(text)
    print(text)


def request(base, method, path, account, body=None):
    headers = {'X-Demo-Account': account}
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=8) as r:
        return r.status, json.loads(r.read().decode('utf-8'))


def wait_health(base, label, is_mock=False):
    for _ in range(60):
        try:
            status, obj = request(base, 'GET', '/health', 'mock01')
            if status == 200 and (obj.get('status') == 'ok' or obj.get('mode')):
                return obj
        except Exception:                        # noqa: BLE001
            pass
        time.sleep(0.3)
    raise RuntimeError(f'{label} health timeout')


def build():
    r = subprocess.run(['go', 'build', '-o', str(EXE), '.'], cwd=str(ROOT),
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError('go build failed: ' + r.stderr)


def main():
    build()
    env = dict(os.environ)
    env['GVA_ADDR'] = ':18084'
    env.pop('GVA_MYSQL_DSN', None)
    main_proc = subprocess.Popen([str(EXE)], cwd=str(ROOT), env=env,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    mock_proc = subprocess.Popen(
        [sys.executable, str(ROOT / 'scripts/mock_channel_service.py'),
         '--port', '18085', '--target', MAIN],
        cwd=str(ROOT), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        main_health = wait_health(MAIN, 'main')
        mock_health = wait_health(MOCK, 'mock', is_mock=True)
        log('CASE_ID      : MOCK-SERVICE-INSTANCE')
        log('TITLE        : 独立可控模拟支付渠道服务实例启动与转发冒烟')
        log(f'TIME         : {datetime.datetime.now().astimezone().isoformat()}')
        log('PROCESSES    : business=:18084 (go build), mock-channel=:18085 (python, independent process)')
        log(f'MAIN_HEALTH  : {json.dumps(main_health, ensure_ascii=False)}')
        log(f'MOCK_HEALTH  : {json.dumps(mock_health, ensure_ascii=False)}')
        log('SCOPE_NOTE   : 不是真实第三方支付接入；不含业务状态机；不落库、不改订单状态。')
        log('')

        _, created = request(MAIN, 'POST', '/api/v1/orders', 'buyer01',
                            {'goods_id': 1, 'quantity': 1})
        order_no = created['data']['order_no']
        log(f'PREPARE      : 业务服务直接创建订单 {order_no}')

        cases = [
            ('MOCK-01', '/notify/payment', {
                'order_no': order_no, 'channel_trade_no': 'R4-MOCK-PAY-1',
                'amount': 10000, 'signature_valid': True}, '0'),
            ('MOCK-02', '/notify/timeout', {
                'order_no': order_no, 'channel_trade_no': 'R4-MOCK-TO-1',
                'reason': '独立模拟渠道超时通知'}, '0'),
            ('MOCK-03', '/notify/timeout', {
                'order_no': order_no, 'channel_trade_no': 'R4-MOCK-TO-1',
                'reason': '重复通知'}, '0'),
            ('MOCK-04', '/notify/payment', {
                'order_no': 'NO-SUCH-ORDER', 'channel_trade_no': 'R4-MOCK-BAD',
                'amount': 10000, 'signature_valid': True}, 'M-30'),
        ]
        all_pass = True
        for cid, endpoint, body, expect in cases:
            status, resp = request(MOCK, 'POST', endpoint, 'mock01', body)
            upstream = resp.get('upstream_response')
            actual = upstream.get('code') if isinstance(upstream, dict) else None
            ok = status == 200 and actual == expect
            all_pass = all_pass and ok
            log(f'CASE_ID      : {cid}')
            log(f'REQUEST      : POST {MOCK}{endpoint}  body={json.dumps(body, ensure_ascii=False)}')
            log(f'UPSTREAM     : {resp.get("upstream")} (status={resp.get("upstream_status")})')
            log(f'RESPONSE_RAW : {json.dumps(upstream, ensure_ascii=False)}')
            log(f'EXPECTED     : {expect}   ACTUAL: {actual}')
            log(f'ASSERTION    : {"PASS" if ok else "FAIL"}')
            log('')

        _, order_view = request(MAIN, 'GET', f'/api/v1/orders/{order_no}/status', 'buyer01')
        log(f'POST_CHECK   : 订单状态={order_view["data"]["status"]}（超时通知不改状态）')
        log(f'SUMMARY      : {sum(1 for c in cases if True)} cases, '
            f'ALL_PASS={all_pass}')
        log('VERSION      : dev/01 HEAD 6083edd06cb4b289ee251bbca28efcdd83e15d6c + 第四轮工作区增量')
        if not all_pass:
            raise RuntimeError('mock channel smoke has FAIL case')
    finally:
        for p in (mock_proc, main_proc):
            p.terminate()
            try:
                p.wait(timeout=4)
            except subprocess.TimeoutExpired:
                p.kill()
    EV.parent.mkdir(parents=True, exist_ok=True)
    EV.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('MOCK CHANNEL SMOKE COMPLETE ->', EV)


if __name__ == '__main__':
    main()
