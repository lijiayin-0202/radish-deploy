#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第四轮证据采集：单用例单文件、真实 HTTP 执行、不合并汇总。

输出 evidence/smoke/*.txt、evidence/manual/*.md、evidence/html-check/*.md。
口径：demo-memory 本地实例；不是独立测试 Agent 会话、不是 Apipost 运行导出、
不是浏览器截图、不是真实 MySQL / CI / race / 视频证据。
"""
import datetime
import json
import os
import pathlib
import subprocess
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(r'd:/Desktop/shop')
EV = ROOT / 'evidence'
SMOKE, MANUAL, HTMLCHECK = EV / 'smoke', EV / 'manual', EV / 'html-check'
for _d in (SMOKE, MANUAL, HTMLCHECK):
    _d.mkdir(parents=True, exist_ok=True)
PORT = 18084
BASE = f'http://127.0.0.1:{PORT}'
HEAD = '6083edd06cb4b289ee251bbca28efcdd83e15d6c'
EXE = pathlib.Path(os.environ.get('TEMP', '/tmp')) / 'shop-trade-r4.exe'
SCOPE = ('单用例独立冒烟记录；非独立测试 Agent 会话、非 Apipost 运行导出、'
         '非第 3 轮浏览器验收、非真实 MySQL / CI / race 证据。')


def now():
    return datetime.datetime.now().astimezone().isoformat()


def save(path, text):
    pathlib.Path(path).write_text(text, encoding='utf-8')


def call(method, path, account, body=None, extra=None):
    headers = {'X-Demo-Account': account}
    if extra:
        headers.update(extra)
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            raw = r.read().decode('utf-8')
            try:
                obj = json.loads(raw)
            except ValueError:
                obj = None
            return {'status': r.status, 'body': raw, 'obj': obj}
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            obj = json.loads(raw)
        except ValueError:
            obj = None
        return {'status': e.code, 'body': raw, 'obj': obj}
    except Exception as e:                      # noqa: BLE001
        return {'status': -1, 'body': str(e), 'obj': None}


def build():
    r = subprocess.run(['go', 'build', '-o', str(EXE), '.'], cwd=str(ROOT),
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise RuntimeError('go build failed: ' + r.stderr)


def start_demo():
    env = dict(os.environ)
    env['GVA_ADDR'] = f':{PORT}'
    env.pop('GVA_MYSQL_DSN', None)
    p = subprocess.Popen([str(EXE)], cwd=str(ROOT), env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        r = call('GET', '/health', 'buyer01')
        if r['status'] == 200:
            return p
        time.sleep(0.3)
    p.terminate()
    raise RuntimeError('health timeout')


def stop_demo(p):
    p.terminate()
    try:
        p.wait(timeout=4)
    except subprocess.TimeoutExpired:
        p.kill()
    time.sleep(0.4)


def assert_code(resp, expect):
    if expect == 'HTTP200':
        return resp['status'] == 200
    obj = resp.get('obj')
    return isinstance(obj, dict) and str(obj.get('code')) == expect


def record(cid, title, method, path, account, body, expect, resp):
    ok = assert_code(resp, expect)
    body_text = json.dumps(body, ensure_ascii=False) if body is not None else '(none)'
    lines = [
        f'CASE_ID      : {cid}',
        f'TITLE        : {title}',
        f'EXECUTED_AT  : {now()}',
        f'ENVIRONMENT  : local go build, mode=demo-memory (GVA_MYSQL_DSN NOT_SET), HEAD={HEAD}',
        f'REQUEST      : {method} {path}',
        f'HEADERS      : X-Demo-Account={account} (X-Role/X-User-Id ignored by server)',
        f'BODY         : {body_text}',
        f'EXPECTED     : {expect}',
        f'HTTP_STATUS  : {resp["status"]}',
        f'RESPONSE_RAW : {resp["body"]}',
        f'ASSERTION    : {"PASS" if ok else "FAIL"}',
        f'SCOPE_NOTE   : {SCOPE}',
    ]
    save(SMOKE / f'{cid}.txt', '\n'.join(lines) + '\n')
    if not ok:
        print(f'WARN SMOKE {cid}: expected={expect} actual={resp["body"]}')
    return resp


def case(cid, title, method, path, account, body, expect):
    return record(cid, title, method, path, account, body, expect,
                  call(method, path, account, body))


manual = {k: [] for k in ('下单', '退款', '库存核查', '调价', '超时通知')}


def manual_case(category, name, method, path, account, body, expect):
    r = call(method, path, account, body)
    ok = assert_code(r, expect)
    body_text = json.dumps(body, ensure_ascii=False) if body is not None else '(none)'
    verdict = 'PASS（预期与实际一致）' if ok else 'DIFF（预期与实际不一致，边界行为如实登记，不改动业务代码）'
    manual[category].append('\n'.join([
        f'### {name}',
        f'- 请求：`{method} {path}`，`X-Demo-Account={account}`',
        f'- 入参：`{body_text}`',
        f'- 预期：`{expect}`',
        f'- 实际 HTTP：`{r["status"]}`',
        f'- 实际响应：`{r["body"]}`',
        f'- 判定：**{verdict}**',
        '',
    ]))


build()
print('go build ok')

# ---------------- process 1: read-only / base / extension ----------------
p = start_demo()
try:
    case('HEALTH', '健康检查', 'GET', '/health', 'buyer01', None, 'HTTP200')
    case('API-19', '身份解析', 'GET', '/api/v1/me', 'buyer01', None, '0')
    case('API-18', '商品列表', 'GET', '/api/v1/goods', 'buyer01', None, '0')
    case('API-20', '演示时钟 GET', 'GET', '/api/v1/admin/clock', 'ops01', None, '0')
    case('API-16', '运营核查汇总', 'GET', '/api/v1/ops/summary', 'ops01', None, '0')

    o1 = case('API-01', '买家下单', 'POST', '/api/v1/orders', 'buyer01',
              {'goods_id': 1, 'quantity': 1}, '0')
    no1 = o1['obj']['data']['order_no']
    case('API-02', '订单详情', 'GET', f'/api/v1/orders/{no1}', 'buyer01', None, '0')
    case('API-17', '订单状态', 'GET', f'/api/v1/orders/{no1}/status', 'buyer01', None, '0')
    case('API-03', '取消弃单释放库存', 'POST', f'/api/v1/orders/{no1}/cancel',
         'buyer01', None, '0')
    case('API-05', '超时关单扫描', 'POST', '/api/v1/admin/orders/close-expired',
         'ops01', {'limit': 10}, '0')
    case('API-21', '运营商品调价', 'POST', '/api/v1/admin/goods/1/price',
         'ops01', {'unit_price': 12000, 'reason': '第四轮冒烟调价'}, '0')
    case('API-22', '渠道超时通知', 'POST', '/api/v1/payment/timeout', 'mock01',
         {'order_no': no1, 'channel_trade_no': 'R4-TO-001', 'reason': '渠道超时'}, '0')
    case('API-23', '库存恢复逐单核查', 'GET', f'/api/v1/ops/stock-check/{no1}',
         'ops01', None, '0')

    # 下单异常
    manual_case('下单', '空 goods_id / quantity 缺省', 'POST', '/api/v1/orders',
                'buyer01', {'quantity': 1}, 'PARAM_ERROR')
    manual_case('下单', '负数 goods_id', 'POST', '/api/v1/orders', 'buyer01',
                {'goods_id': -1, 'quantity': 1}, 'PARAM_ERROR')
    manual_case('下单', 'quantity=0 越界', 'POST', '/api/v1/orders', 'buyer01',
                {'goods_id': 1, 'quantity': 0}, 'M-03')
    manual_case('下单', 'quantity=3 越界', 'POST', '/api/v1/orders', 'buyer01',
                {'goods_id': 1, 'quantity': 3}, 'M-03')
    manual_case('下单', '负数 quantity', 'POST', '/api/v1/orders', 'buyer01',
                {'goods_id': 1, 'quantity': -2}, 'M-03')
    manual_case('下单', '不存在商品', 'POST', '/api/v1/orders', 'buyer01',
                {'goods_id': 999999, 'quantity': 1}, 'M-01')
    manual_case('下单', '超长商品编号', 'POST', '/api/v1/orders', 'buyer01',
                {'goods_id': 999999999999999999, 'quantity': 1}, 'M-01')
    manual_case('下单', '运营越权下单', 'POST', '/api/v1/orders', 'ops01',
                {'goods_id': 1, 'quantity': 1}, 'M-20')

    # 退款异常
    manual_case('退款', '不存在订单申请退款', 'POST',
                '/api/v1/orders/NO-SUCH-ORDER/refund/apply', 'buyer01',
                {'reason': 'x'}, 'M-05')
    manual_case('退款', '客服同意缺 remark', 'POST',
                f'/api/v1/orders/{no1}/refund/approve', 'cs01', {}, 'M-24')
    manual_case('退款', '买家越权审核', 'POST', f'/api/v1/orders/{no1}/refund/approve',
                'buyer01', {'remark': 'x'}, 'M-20')
    manual_case('退款', '回调金额不符', 'POST', '/api/v1/refund/callback', 'mock01',
                {'order_no': no1, 'refund_channel_trade_no': 'R4-RF-BAD',
                 'amount': 1, 'success': True, 'signature_valid': True}, 'M-29')
    manual_case('退款', '回调验签失败', 'POST', '/api/v1/refund/callback', 'mock01',
                {'order_no': no1, 'refund_channel_trade_no': 'R4-RF-SIG',
                 'amount': 10000, 'success': True, 'signature_valid': False}, 'M-28')
    manual_case('退款', '超长 reason', 'POST', f'/api/v1/orders/{no1}/refund/apply',
                'buyer01', {'reason': 'x' * 600}, 'M-05')

    # 库存核查异常
    manual_case('库存核查', '不存在订单号', 'GET',
                '/api/v1/ops/stock-check/NO-SUCH-ORDER', 'ops01', None, 'PARAM_ERROR')
    manual_case('库存核查', '超长订单号', 'GET',
                '/api/v1/ops/stock-check/' + 'A' * 300, 'ops01', None, 'PARAM_ERROR')
    manual_case('库存核查', '买家越权核查', 'GET', f'/api/v1/ops/stock-check/{no1}',
                'buyer01', None, 'M-20')
    manual_case('库存核查', '客服只读核查合法', 'GET', f'/api/v1/ops/stock-check/{no1}',
                'cs01', None, '0')
    manual_case('库存核查', '未知身份核查', 'GET', f'/api/v1/ops/stock-check/{no1}',
                'nobody', None, 'M-20')

    # 调价异常
    manual_case('调价', 'unit_price=0', 'POST', '/api/v1/admin/goods/1/price',
                'ops01', {'unit_price': 0, 'reason': 'x'}, 'PARAM_ERROR')
    manual_case('调价', 'unit_price 负数', 'POST', '/api/v1/admin/goods/1/price',
                'ops01', {'unit_price': -100, 'reason': 'x'}, 'PARAM_ERROR')
    manual_case('调价', 'unit_price 超长数值', 'POST', '/api/v1/admin/goods/1/price',
                'ops01', {'unit_price': 999999999999999999, 'reason': 'x'}, 'PARAM_ERROR')
    manual_case('调价', '不存在商品', 'POST', '/api/v1/admin/goods/999999/price',
                'ops01', {'unit_price': 12000, 'reason': 'x'}, 'PARAM_ERROR')
    manual_case('调价', '买家越权调价', 'POST', '/api/v1/admin/goods/1/price',
                'buyer01', {'unit_price': 13000, 'reason': 'x'}, 'M-20')
    manual_case('调价', '超长 reason', 'POST', '/api/v1/admin/goods/1/price',
                'ops01', {'unit_price': 12000, 'reason': 'r' * 600}, '0')

    # 超时通知异常
    manual_case('超时通知', '空 channel_trade_no', 'POST', '/api/v1/payment/timeout',
                'mock01', {'order_no': no1, 'channel_trade_no': '', 'reason': 'x'}, 'PARAM_ERROR')
    manual_case('超时通知', '不存在订单', 'POST', '/api/v1/payment/timeout', 'mock01',
                {'order_no': 'NO-SUCH-ORDER', 'channel_trade_no': 'R4-TO-BAD',
                 'reason': 'x'}, 'M-30')
    manual_case('超时通知', '超长渠道交易号', 'POST', '/api/v1/payment/timeout', 'mock01',
                {'order_no': no1, 'channel_trade_no': 'T' * 300, 'reason': 'x'}, 'PARAM_ERROR')
    manual_case('超时通知', '买家越权通知', 'POST', '/api/v1/payment/timeout', 'buyer01',
                {'order_no': no1, 'channel_trade_no': 'R4-TO-DENY', 'reason': 'x'}, 'M-20')
    manual_case('超时通知', '重复通知幂等', 'POST', '/api/v1/payment/timeout', 'mock01',
                {'order_no': no1, 'channel_trade_no': 'R4-TO-001', 'reason': '重复'}, '0')
finally:
    stop_demo(p)

# ---------------- process 2: payment / shipment / refund ----------------
p = start_demo()
try:
    pre = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
    no_a = pre['obj']['data']['order_no']
    case('API-04', '模拟渠道支付成功', 'POST', '/api/v1/payment/callback', 'mock01',
         {'order_no': no_a, 'channel_trade_no': 'R4-PAY-A2', 'amount': 10000,
          'signature_valid': True}, '0')
    case('API-11', '仓库登记发货', 'POST', f'/api/v1/orders/{no_a}/shipment',
         'warehouse01', {'carrier': '顺丰', 'tracking_no': 'R4-SF-A'}, '0')

    pre_b = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
    no_b = pre_b['obj']['data']['order_no']
    call('POST', '/api/v1/payment/callback', 'mock01',
         {'order_no': no_b, 'channel_trade_no': 'R4-PAY-B', 'amount': 10000,
          'signature_valid': True})
    case('API-06', '买家申请整单退款', 'POST', f'/api/v1/orders/{no_b}/refund/apply',
         'buyer01', {'reason': '不想要了'}, '0')
    case('API-07', '客服拒绝退款', 'POST', f'/api/v1/orders/{no_b}/refund/reject',
         'cs01', {'remark': '不符合售前退款条件'}, '0')

    pre_c = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
    no_c = pre_c['obj']['data']['order_no']
    call('POST', '/api/v1/payment/callback', 'mock01',
         {'order_no': no_c, 'channel_trade_no': 'R4-PAY-C', 'amount': 10000,
          'signature_valid': True})
    call('POST', f'/api/v1/orders/{no_c}/refund/apply', 'buyer01', {'reason': '退款'})
    case('API-08', '客服同意退款', 'POST', f'/api/v1/orders/{no_c}/refund/approve',
         'cs01', {'remark': '同意售前整单退款'}, '0')
    call('POST', '/api/v1/refund/callback', 'mock01',
         {'order_no': no_c, 'refund_channel_trade_no': 'R4-RF-C1', 'amount': 10000,
          'success': False, 'signature_valid': True})
    case('API-09', '客服退款重试登记', 'POST', f'/api/v1/orders/{no_c}/refund/retry',
         'cs01', {'remark': '渠道恢复，重试'}, '0')
    case('API-10', '渠道退款成功回调', 'POST', '/api/v1/refund/callback', 'mock01',
         {'order_no': no_c, 'refund_channel_trade_no': 'R4-RF-C2', 'amount': 10000,
          'success': True, 'signature_valid': True}, '0')
finally:
    stop_demo(p)

# ---------------- process 3: late payment ----------------
p = start_demo()
try:
    pre_d = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
    no_d = pre_d['obj']['data']['order_no']
    call('POST', '/api/v1/admin/clock', 'ops01', {'offset_minutes': 11})
    call('POST', '/api/v1/admin/orders/close-expired', 'ops01', {'limit': 50})
    late = call('POST', '/api/v1/payment/callback', 'mock01',
                {'order_no': no_d, 'channel_trade_no': 'R4-LATE-1',
                 'amount': 10000, 'signature_valid': True})
    eid = late['obj']['data']['event_id']
    case('API-12', '客服核实迟到支付异常', 'POST', f'/api/v1/late-payment/{eid}/verify',
         'cs01', {'reason': '已确认迟到支付'}, '0')
    case('API-13', '发起迟到支付退款', 'POST',
         f'/api/v1/late-payment/{eid}/refund/initiate', 'cs01',
         {'refund_no': 'R4-LRF-1', 'reason': '原路退回'}, '0')
    call('POST', '/api/v1/late-payment/refund/callback', 'mock01',
         {'event_id': eid, 'refund_no': 'R4-LRF-1', 'amount': 10000,
          'success': False, 'signature_valid': True})
    case('API-15', '迟到支付退款重试', 'POST', '/api/v1/late-payment/refund/retry',
         'cs01', {'event_id': eid, 'refund_no': 'R4-LRF-1', 'remark': '重试'}, '0')
    case('API-14', '迟到支付退款成功回调', 'POST',
         '/api/v1/late-payment/refund/callback', 'mock01',
         {'event_id': eid, 'refund_no': 'R4-LRF-1', 'amount': 10000,
          'success': True, 'signature_valid': True}, '0')
finally:
    stop_demo(p)

# ---------------- process 4: static pages ----------------
pages = [
    ('index', 'index.html', '/static/index.html', 'Home', 'buyer01'),
    ('V01', 'v01-goods.html', '/static/v01-goods.html', 'GoodsBrowse', 'buyer01'),
    ('V02', 'v02-orders.html', '/static/v02-orders.html', 'MyOrders', 'buyer01'),
    ('V03', 'v03-goods-admin.html', '/static/v03-goods-admin.html', 'GoodsAdmin', 'ops01'),
    ('V04', 'v04-ops-summary.html', '/static/v04-ops-summary.html', 'OpsSummary', 'ops01'),
    ('V05', 'v05-shipment-list.html', '/static/v05-shipment-list.html', 'ShipmentList', 'warehouse01'),
    ('V06', 'v06-shipment-form.html', '/static/v06-shipment-form.html', 'ShipmentForm', 'warehouse01'),
    ('V07', 'v07-refund-review.html', '/static/v07-refund-review.html', 'RefundReview', 'cs01'),
    ('V08', 'v08-late-payment.html', '/static/v08-late-payment.html', 'LatePayment', 'cs01'),
]
p = start_demo()
try:
    for pid, filename, path, name, account in pages:
        req = urllib.request.Request(BASE + path, headers={'X-Demo-Account': account})
        try:
            with urllib.request.urlopen(req, timeout=8) as r:
                status, raw = r.status, r.read().decode('utf-8', 'replace')
        except Exception as e:                  # noqa: BLE001
            status, raw = -1, str(e)
        markers = {
            'title': '<title>' in raw,
            'h1': '<h1>' in raw,
            'app.js': '/static/app.js' in raw,
            'Shop.init': 'Shop.init(' in raw,
            'out': 'id="out"' in raw,
        }
        ok = status == 200 and all(markers[k] for k in ('title', 'h1', 'app.js', 'Shop.init'))
        save(SMOKE / f'PAGE-{pid}.txt', '\n'.join([
            f'CASE_ID      : PAGE-{pid}',
            f'TITLE        : {pid} {name} 页面独立访问冒烟',
            f'EXECUTED_AT  : {now()}',
            f'REQUEST      : GET {path}',
            f'ROLE_ACCOUNT : {account}',
            f'HTTP_STATUS  : {status}',
            f'BYTES        : {len(raw)}',
            'MARKERS      : ' + ' '.join(f'{k}={v}' for k, v in markers.items()),
            f'ASSERTION    : {"PASS" if ok else "FAIL"}',
            'SCOPE_NOTE   : HTTP 层单页访问断言；无浏览器截图文件，非第 3 轮浏览器验收、非独立验收会话。',
        ]) + '\n')
        if not ok:
            print(f'WARN PAGE {pid}: status={status} markers={markers}')

        if pid == 'index':
            continue
        rows = '\n'.join([
            f'| A1 | HTTP 状态 200 | {status} | {"PASS" if status == 200 else "FAIL"} |',
            f'| A2 | 含 `<title>` | {markers["title"]} | {"PASS" if markers["title"] else "FAIL"} |',
            f'| A3 | 含 `<h1>` 视图标题 | {markers["h1"]} | {"PASS" if markers["h1"] else "FAIL"} |',
            f'| A4 | 引用 `/static/app.js` | {markers["app.js"]} | {"PASS" if markers["app.js"] else "FAIL"} |',
            f'| A5 | 含 `Shop.init` 身份初始化 | {markers["Shop.init"]} | {"PASS" if markers["Shop.init"] else "FAIL"} |',
            f'| A6 | 含 `id="out"` 结果区 | {markers["out"]} | {"PASS" if markers["out"] else "FAIL"} |',
            f'| A7 | 响应字节数 > 0 | {len(raw)} | {"PASS" if len(raw) > 0 else "FAIL"} |',
        ])
        doc = '\n'.join([
            f'# {pid} 页面测试截图说明与独立访问断言',
            '',
            '| 项 | 内容 |',
            '| --- | --- |',
            f'| 页面 | `{path}` |',
            f'| 原型视图 | {pid} {name} |',
            f'| 演示账号 | `{account}` |',
            f'| 采集时间 | {now()} |',
            '| 运行模式 | `demo-memory`（本地编译实例，非真实 MySQL / 非部署版本） |',
            '',
            '## 独立访问断言（本页单独执行，不合并汇总）',
            '',
            '| 编号 | 断言 | 实际 | 结论 |',
            '| --- | --- | --- | --- |',
            rows,
            '',
            '## 截图说明（如实标注，不伪造）',
            '',
            '- **本轮未生成浏览器截图文件**：本机复核只做 HTTP 层访问断言，未使用浏览器自动化、未导出截图。',
            '- 截图须由第 3 轮浏览器页面验收在**独立验收 Agent 会话**中补充，并与本页 A1~A7 断言、提交哈希、采集时间一起归档。',
            '- 本文件不冒充截图、不冒充第 3 轮验收结论、不冒充独立测试/验收会话产物。',
            '',
            '## 关联证据',
            '',
            f'- 单页冒烟记录：`evidence/smoke/PAGE-{pid}.txt`',
            f'- 页面源码：`resource/static/{filename}`',
            '- 接口契约：`docs/interface-list.md` 第 6.1 节 / 附录 A',
            '',
        ])
        save(HTMLCHECK / f'{pid}-{name}.md', doc)
finally:
    stop_demo(p)

# ---------------- Skill file-level smoke (one file per skill) ----------------
skill_root = ROOT / '.codebuddy/skills'
for name in ('gva-model-generate', 'unit-test-race', 'apipost-case-gen', 'acceptance-check'):
    f = skill_root / name / 'SKILL.md'
    exists = f.exists()
    text = f.read_text(encoding='utf-8') if exists else ''
    checks = {
        'YAML_name': bool(__import__('re').search(r'(?m)^name:\s*\S+', text)),
        'YAML_description': bool(__import__('re').search(r'(?m)^description:\s*\S+', text)),
        'has_purpose': any(k in text for k in ('用途', 'Overview')),
        'has_trigger': any(k in text for k in ('触发', '不触发')),
        'has_input': '输入' in text,
        'has_output': '输出' in text,
        'has_boundary': any(k in text for k in ('禁用', '禁止', '约束', '边界')),
        'has_failure_handling': '失败' in text,
        'has_completion': any(k in text for k in ('完成标准', '验收检查点', '完成判定')),
        'mysql_innodb': 'MySQL' in text,
    }
    ok = exists and all(checks.values())
    lines = [
        f'CASE_ID      : SKILL-{name}',
        f'TITLE        : {name} SKILL.md 文件级独立冒烟核查',
        f'EXECUTED_AT  : {now()}',
        f'PATH         : {f}',
        f'EXISTS       : {exists}',
        'CHECKS       :',
    ] + [f'  - {k} = {v}' for k, v in sorted(checks.items())] + [
        f'ASSERTION    : {"PASS" if ok else "FAIL"}',
        'SCOPE_NOTE   : 文件结构与口径核查；不是工具加载记录、不是独立测试/验收会话调用证据。',
    ]
    save(SMOKE / f'SKILL-{name}.txt', '\n'.join(lines) + '\n')
    if not ok:
        print(f'WARN SKILL {name}: {checks}')

plugin = pathlib.Path(r'C:/Users/10990/.codebuddy/skills/student-project-audit/SKILL.md')
script = pathlib.Path(r'C:/Users/10990/.codebuddy/skills/student-project-audit/scripts/score_audit.py')
save(SMOKE / 'SKILL-student-project-audit.txt', '\n'.join([
    'CASE_ID      : SKILL-student-project-audit',
    'TITLE        : 内置检查 Skill 文件级独立冒烟核查',
    f'EXECUTED_AT  : {now()}',
    f'PATH         : {plugin}',
    f'EXISTS       : {plugin.exists()}',
    f'HAS_SCRIPT   : {script.exists()}',
    f'ASSERTION    : {"PASS" if plugin.exists() and script.exists() else "FAIL"}',
    'SCOPE_NOTE   : 第四轮复核真实加载该 Skill 并调用 score_audit.py；文件核查本身不等于调用记录。',
]) + '\n')

# ---------------- manual exception documents ----------------
titles = {'下单': '下单', '退款': '退款', '库存核查': '库存恢复逐单核查',
          '调价': '商品调价', '超时通知': '渠道超时通知'}
for cat in ('下单', '退款', '库存核查', '调价', '超时通知'):
    head = '\n'.join([
        f'# {titles[cat]} 异常场景手工测试记录',
        '',
        '| 项 | 内容 |',
        '| --- | --- |',
        '| 采集方式 | 本地 `go build` 实例逐条真实 HTTP 调用，单条记录不合并汇总 |',
        f'| 采集时间 | {now()} |',
        '| 运行模式 | `demo-memory`；非真实 MySQL(InnoDB)、非 Apipost 运行导出、非独立测试 Agent 会话 |',
        f'| 版本 | `dev/01` HEAD `{HEAD[:12]}…` + 第四轮工作区增量（未提交） |',
        '| 断言 | 每条含请求、入参、预期、实际 HTTP 与实际响应，均逐条判定 |',
        '',
        '## 异常用例（空 / 超长 / 越权 / 负数 / 不存在 / 重复）',
        '',
    ])
    foot = '\n'.join([
        '',
        '## 边界说明',
        '',
        '- 以上为开发会话内的手工执行记录，**不是独立测试 Agent 会话产物，也不是第 2 轮 Apipost 正式证据**。',
        '- 未在真实 MySQL(InnoDB) 下复跑，唯一键冲突、行锁并发与重启后查询证据仍属环境缺失。',
        '- 判定为 `DIFF` 的条目如实登记边界行为差异，不改动业务代码、不弱化断言、不删除失败用例。',
        '- 不改写订单状态消除异常、不删除业务记录、不新增业务状态机。',
        '',
    ])
    save(MANUAL / f'{titles[cat]}-异常场景手工测试记录.md',
         head + '\n'.join(manual[cat]) + foot)

print('smoke_files=', len(list(SMOKE.glob('*.txt'))))
print('manual_docs=', len(list(MANUAL.glob('*.md'))))
print('html_check_docs=', len(list(HTMLCHECK.glob('*.md'))))
print('R4 EVIDENCE SUITE COMPLETE')
