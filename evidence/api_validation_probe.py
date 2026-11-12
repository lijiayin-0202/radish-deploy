#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""接口入参校验与异常分支巡检脚本（真实 HTTP 探测）。

对全部 HTTP 接口逐个发送非法入参（缺失身份、非法 JSON、非法路径参数、非法业务入参），
记录真实响应；断言任何非法入参都不得返回 HTTP 500 / INTERNAL_ERROR 或非 JSON 响应。

用法：python -X utf8 evidence/api_validation_probe.py
输出：evidence/api_validation_probe.txt（UTF-8）
"""
import json
import os
import pathlib
import subprocess
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOG = ROOT / 'evidence/api_validation_probe.txt'
PORT = 18097
BASE = 'http://127.0.0.1:%d' % PORT
EXE = pathlib.Path(os.environ.get('TEMP', '/tmp')) / 'shop-trade-probe.exe'
LINES = []


def log(text=''):
    LINES.append(text)
    print(text)


def call(method, path, body, account, raw_json):
    url = BASE + path
    data = None
    headers = {}
    if account:
        headers['X-Demo-Account'] = account
    if body is not None:
        headers['Content-Type'] = 'application/json'
        data = b'NOT_JSON' if raw_json else json.dumps(body, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode('utf-8', 'replace')
    except Exception as exc:  # noqa: BLE001
        return -1, repr(exc)


def build_cases():
    """返回 (接口编号, 方法, 路径模板, 用例名, 身份, 路径参数, 请求体, 是否非法 JSON)"""
    c = []
    add = c.append
    add(('API-01', 'GET', '/api/v1/me', '缺失身份', None, {}, None, False))
    add(('API-02', 'GET', '/api/v1/goods', '缺失身份', None, {}, None, False))
    add(('API-02', 'GET', '/api/v1/goods', '未知身份', 'not-exists', {}, None, False))
    add(('API-03', 'GET', '/api/v1/admin/clock', '缺失身份', None, {}, None, False))
    add(('API-04', 'POST', '/api/v1/admin/clock', '缺失身份', None, {}, {}, False))
    add(('API-04', 'POST', '/api/v1/admin/clock', '非法 JSON', 'ops01', {}, 'NOT_JSON', True))
    add(('API-04', 'POST', '/api/v1/admin/clock', 'offset 越界', 'ops01', {}, {'offset_minutes': -1}, False))
    add(('API-05', 'POST', '/api/v1/orders', '缺失身份', None, {}, {}, False))
    add(('API-05', 'POST', '/api/v1/orders', '非法 JSON', 'buyer01', {}, 'NOT_JSON', True))
    add(('API-05', 'POST', '/api/v1/orders', 'quantity 非正', 'buyer01', {}, {'goods_id': 1, 'quantity': 0}, False))
    add(('API-05', 'POST', '/api/v1/orders', 'quantity 超限', 'buyer01', {}, {'goods_id': 1, 'quantity': 99}, False))
    add(('API-05', 'POST', '/api/v1/orders', 'goods_id 缺失', 'buyer01', {}, {'quantity': 1}, False))
    add(('API-06', 'GET', '/api/v1/orders/{order_no}', '缺失身份', None, {}, None, False))
    add(('API-06', 'GET', '/api/v1/orders/{order_no}', '订单号不存在', 'buyer01', {'order_no': 'NOT-EXIST-0001'}, None, False))
    add(('API-07', 'GET', '/api/v1/orders/{order_no}/status', '缺失身份', None, {}, None, False))
    add(('API-08', 'POST', '/api/v1/orders/{order_no}/cancel', '缺失身份', None, {}, {}, False))
    add(('API-08', 'POST', '/api/v1/orders/{order_no}/cancel', '订单号不存在', 'buyer01', {'order_no': 'NOT-EXIST-0001'}, {}, False))
    add(('API-09', 'POST', '/api/v1/payment/callback', '缺失身份', None, {}, {}, False))
    add(('API-09', 'POST', '/api/v1/payment/callback', '非法 JSON', 'mock01', {}, 'NOT_JSON', True))
    add(('API-09', 'POST', '/api/v1/payment/callback', '订单号为空', 'mock01', {}, {'order_no': '', 'channel_trade_no': 'T1', 'amount': 100}, False))
    add(('API-10', 'POST', '/api/v1/admin/orders/close-expired', '缺失身份', None, {}, {}, False))
    add(('API-10', 'POST', '/api/v1/admin/orders/close-expired', '非法 JSON', 'ops01', {}, 'NOT_JSON', True))
    add(('API-11', 'POST', '/api/v1/orders/{order_no}/refund/apply', '缺失身份', None, {}, {}, False))
    add(('API-11', 'POST', '/api/v1/orders/{order_no}/refund/apply', '订单号不存在', 'buyer01', {'order_no': 'NOT-EXIST-0001'}, {'reason': 'x'}, False))
    add(('API-12', 'POST', '/api/v1/orders/{order_no}/refund/reject', '缺失身份', None, {}, {}, False))
    add(('API-12', 'POST', '/api/v1/orders/{order_no}/refund/reject', '订单号不存在', 'cs01', {'order_no': 'NOT-EXIST-0001'}, {'remark': 'x'}, False))
    add(('API-13', 'POST', '/api/v1/orders/{order_no}/refund/approve', '缺失身份', None, {}, {}, False))
    add(('API-13', 'POST', '/api/v1/orders/{order_no}/refund/approve', '订单号不存在', 'cs01', {'order_no': 'NOT-EXIST-0001'}, {'remark': 'x'}, False))
    add(('API-14', 'POST', '/api/v1/orders/{order_no}/refund/retry', '缺失身份', None, {}, {}, False))
    add(('API-14', 'POST', '/api/v1/orders/{order_no}/refund/retry', '订单号不存在', 'cs01', {'order_no': 'NOT-EXIST-0001'}, {'remark': 'x'}, False))
    add(('API-15', 'POST', '/api/v1/refund/callback', '缺失身份', None, {}, {}, False))
    add(('API-15', 'POST', '/api/v1/refund/callback', '非法 JSON', 'mock01', {}, 'NOT_JSON', True))
    add(('API-15', 'POST', '/api/v1/refund/callback', '订单号为空', 'mock01', {}, {'order_no': '', 'refund_channel_trade_no': 'R1', 'amount': 1}, False))
    add(('API-16', 'POST', '/api/v1/orders/{order_no}/shipment', '缺失身份', None, {}, {}, False))
    add(('API-16', 'POST', '/api/v1/orders/{order_no}/shipment', '非法 JSON', 'warehouse01', {'order_no': 'NOT-EXIST-0001'}, 'NOT_JSON', True))
    add(('API-16', 'POST', '/api/v1/orders/{order_no}/shipment', '承运方为空', 'warehouse01', {'order_no': 'NOT-EXIST-0001'}, {'carrier': '', 'tracking_no': 'T1'}, False))
    add(('API-17', 'POST', '/api/v1/late-payment/{event_id}/verify', '缺失身份', None, {}, {}, False))
    add(('API-17', 'POST', '/api/v1/late-payment/{event_id}/verify', 'event_id 非数字', 'cs01', {'event_id': 'abc'}, {'reason': 'x'}, False))
    add(('API-17', 'POST', '/api/v1/late-payment/{event_id}/verify', '事件不存在', 'cs01', {'event_id': '999999'}, {'reason': 'x'}, False))
    add(('API-18', 'POST', '/api/v1/late-payment/{event_id}/refund/initiate', '缺失身份', None, {}, {}, False))
    add(('API-18', 'POST', '/api/v1/late-payment/{event_id}/refund/initiate', 'event_id 非数字', 'cs01', {'event_id': 'abc'}, {'refund_no': 'R1', 'reason': 'x'}, False))
    add(('API-19', 'POST', '/api/v1/late-payment/refund/callback', '缺失身份', None, {}, {}, False))
    add(('API-19', 'POST', '/api/v1/late-payment/refund/callback', '非法 JSON', 'mock01', {}, 'NOT_JSON', True))
    add(('API-19', 'POST', '/api/v1/late-payment/refund/callback', '订单号为空', 'mock01', {}, {'order_no': '', 'refund_no': 'R1', 'amount': 1}, False))
    add(('API-20', 'POST', '/api/v1/late-payment/refund/retry', '缺失身份', None, {}, {}, False))
    add(('API-20', 'POST', '/api/v1/late-payment/refund/retry', 'event_id 非数字', 'cs01', {}, {'event_id': 'abc', 'refund_no': 'R1', 'remark': 'x'}, False))
    add(('API-21', 'GET', '/api/v1/ops/summary', '缺失身份', None, {}, None, False))
    add(('API-21', 'GET', '/api/v1/ops/summary', '买家越权', 'buyer01', {}, None, False))
    add(('API-22', 'POST', '/api/v1/admin/goods/{goods_id}/price', '缺失身份', None, {}, {}, False))
    add(('API-22', 'POST', '/api/v1/admin/goods/{goods_id}/price', 'goods_id 非数字', 'ops01', {'goods_id': 'abc'}, {'unit_price': 100}, False))
    add(('API-22', 'POST', '/api/v1/admin/goods/{goods_id}/price', 'unit_price 非正', 'ops01', {'goods_id': '1'}, {'unit_price': 0}, False))
    add(('API-22', 'POST', '/api/v1/admin/goods/{goods_id}/price', '买家越权', 'buyer01', {'goods_id': '1'}, {'unit_price': 100}, False))
    add(('API-23', 'POST', '/api/v1/payment/timeout', '缺失身份', None, {}, {}, False))
    add(('API-23', 'POST', '/api/v1/payment/timeout', '非法 JSON', 'mock01', {}, 'NOT_JSON', True))
    add(('API-23', 'POST', '/api/v1/payment/timeout', '订单号为空', 'mock01', {}, {'order_no': '', 'channel_trade_no': 'T1'}, False))
    add(('API-24', 'GET', '/api/v1/ops/stock-check/{order_no}', '缺失身份', None, {}, None, False))
    add(('API-24', 'GET', '/api/v1/ops/stock-check/{order_no}', '订单号不存在', 'ops01', {'order_no': 'NOT-EXIST-0001'}, None, False))
    return c


# 巡检脚本内部序号 -> docs/interface-list.md 的正式接口编号
DOC_MAP = {
    'API-01': 'API-19', 'API-02': 'API-18', 'API-03': 'API-20', 'API-04': 'API-20',
    'API-05': 'API-01', 'API-06': 'API-02', 'API-07': 'API-17', 'API-08': 'API-03',
    'API-09': 'API-04', 'API-10': 'API-05', 'API-11': 'API-06', 'API-12': 'API-07',
    'API-13': 'API-08', 'API-14': 'API-09', 'API-15': 'API-10', 'API-16': 'API-11',
    'API-17': 'API-12', 'API-18': 'API-13', 'API-19': 'API-14', 'API-20': 'API-15',
    'API-21': 'API-16', 'API-22': '扩展 API-21', 'API-23': '扩展 API-22',
    'API-24': '扩展 API-23',
}


def main():
    log('===== 接口入参校验与异常分支巡检（真实 HTTP 探测）=====')
    log('时间：%s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    log('目标：http://127.0.0.1:%d（demo-memory 模式本地实例）' % PORT)
    build = subprocess.run(['go', 'build', '-o', str(EXE), '.'], cwd=ROOT,
                            capture_output=True, text=True, encoding='utf-8', errors='replace')
    log('$ go build -o %s .  -> exit=%d' % (EXE, build.returncode))
    if build.returncode != 0:
        log(build.stdout + build.stderr)
        return 2
    env = dict(os.environ)
    env['GVA_ADDR'] = ':%d' % PORT
    env.pop('GVA_MYSQL_DSN', None)
    handle = open(ROOT / 'evidence/api_probe_runtime.log', 'a', encoding='utf-8')
    proc = subprocess.Popen([str(EXE)], env=env, stdout=handle, stderr=handle)
    for _ in range(60):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(BASE + '/health', timeout=3) as resp:
                if resp.status == 200:
                    break
        except Exception:
            continue
    log('GET /health -> 服务已启动（mode=demo-memory）')
    log('')
    log('%-8s %-46s %-14s %-6s %-18s %s' % ('接口', '路径', '用例', 'HTTP', '业务码', '判定'))
    log('-' * 118)
    bad = 0
    total = 0
    for api, method, template, case, account, params, body, raw_json in build_cases():
        path = template
        for key, value in params.items():
            path = path.replace('{%s}' % key, str(value))
        status, text = call(method, path, body, account, raw_json)
        total += 1
        code = '(非 JSON 响应)'
        verdict = 'OK'
        try:
            payload = json.loads(text)
            code = str(payload.get('code'))
            if status >= 500 or code == 'INTERNAL_ERROR':
                verdict = 'BAD-500'
                bad += 1
        except Exception:
            verdict = 'BAD-NONJSON'
            bad += 1
        log('%-12s %-46s %-14s %-6s %-18s %s'
            % (DOC_MAP.get(api, api), path, case, status, code, verdict))
    log('-' * 118)
    log('探针总数：%d；不合规响应（500 / INTERNAL_ERROR / 非 JSON）：%d' % (total, bad))
    log('判定：%s' % ('全部异常分支均被显式兜住' if bad == 0 else '存在未兜住的异常分支'))
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
    LOG.write_text('\n'.join(LINES) + '\n', encoding='utf-8')
    print('written: %s' % LOG)
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
