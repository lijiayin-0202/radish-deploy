#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M-01~M-30 业务错误码逐条穷举脚本（真实 HTTP 探测）。

目的：把「非法入参 / 非法状态 → 业务错误码」的映射从抽查若干条升级为逐条穷举：

  1. 从 server/service/types.go 的 messages 表解析出权威的 30 个错误码及其文案；
  2. 用可控业务流程（下单→支付→退款→发货→迟到支付→核查）逐个触发错误码；
  3. 递归扫描响应体所有字符串，登记每个错误码出现在哪个字段、由哪个用例触发；
  4. 未被任何分支返回的错误码，按源码引用次数如实分类为
     「文案常量未被任何分支引用」或「本次未观测到」，不推测、不补写。

用法：python -X utf8 scripts/error_code_enumeration.py
输出：evidence/error_code_enumeration.txt（UTF-8 原始输出）
      evidence/error_code_enumeration.json（结构化结果）
"""
import json
import os
import pathlib
import re
import subprocess
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOG = ROOT / 'evidence/error_code_enumeration.txt'
JSON_OUT = ROOT / 'evidence/error_code_enumeration.json'
PORT = 18098
BASE = 'http://127.0.0.1:%d' % PORT
EXE = pathlib.Path(os.environ.get('TEMP', '/tmp')) / 'shop-trade-errcode.exe'
TYPES = ROOT / 'server/service/types.go'
LINES = []


def log(text=''):
    LINES.append(text)
    print(text)


def parse_messages():
    """从 types.go 的 messages 表解析错误码 -> 文案（保持源码顺序）。"""
    text = TYPES.read_text(encoding='utf-8')
    block = re.search(r'var messages = map\[string\]string\{(.*?)\n\}', text, re.S)
    if not block:
        raise SystemExit('未找到 messages 表')
    return re.findall(r'"(M-\d\d)":\s*"([^"]*)"', block.group(1))


def source_ref_counts():
    """统计每个错误码在 types.go 之外的 Go 源码中的引用次数。"""
    counts = {}
    for path in (ROOT / 'server').rglob('*.go'):
        if path.name == 'types.go':
            continue
        body = path.read_text(encoding='utf-8', errors='replace')
        for code in re.findall(r'M-\d\d', body):
            counts[code] = counts.get(code, 0) + 1
    return counts


def call(method, path, body=None, account=None):
    url = BASE + path
    data = None
    headers = {}
    if account:
        headers['X-Demo-Account'] = account
    if body is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(body, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode('utf-8', 'replace')
        try:
            return exc.code, json.loads(body_text)
        except Exception:  # noqa: BLE001
            return exc.code, {'_raw': body_text}
    except Exception as exc:  # noqa: BLE001
        return -1, {'_raw': repr(exc)}


def walk_strings(node, path='$'):
    """递归产出 (字段路径, 字符串值)。"""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from walk_strings(value, '%s.%s' % (path, key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_strings(value, '%s[%d]' % (path, index))
    elif isinstance(node, str):
        yield path, node


def order_no(payload):
    data = payload.get('data') or {}
    return str(data.get('order_no'))


def main():
    codes = parse_messages()
    refs = source_ref_counts()
    observed = {code: [] for code, _ in codes}
    steps = []
    failures = []

    def probe(label, method, path, expect=None, body=None, account=None, note=''):
        status, payload = call(method, path, body, account)
        matched = []
        for code, text in codes:
            for field, value in walk_strings(payload):
                if code in value or (text and text in value):
                    if (label, field) not in observed[code]:
                        observed[code].append((label, field))
                    matched.append(code)
                    break
        top = str(payload.get('code')) if isinstance(payload, dict) else '(非 JSON)'
        ok = True
        if expect is not None:
            ok = expect in matched
            if not ok:
                failures.append((label, expect, top, matched))
        steps.append({'label': label, 'method': method, 'path': path, 'account': account,
                      'http': status, 'top_code': top, 'matched_codes': sorted(set(matched)),
                      'expect': expect, 'ok': ok, 'note': note})
        log('%-44s %-6s %-5s %-10s %-12s %s'
            % (label, method, status, top, ','.join(sorted(set(matched))) or '-',
               'OK' if ok else 'MISS'))
        return payload

    log('===== M-01~M-30 业务错误码逐条穷举（真实 HTTP 探测）=====')
    log('时间：%s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    log('目标：http://127.0.0.1:%d（demo-memory 模式本地实例）' % PORT)
    log('错误码来源：server/service/types.go 的 messages 表，共 %d 个' % len(codes))

    build = subprocess.run(['go', 'build', '-o', str(EXE), '.'], cwd=ROOT,
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
    log('$ go build -o %s .  -> exit=%d' % (EXE, build.returncode))
    if build.returncode != 0:
        log(build.stdout + build.stderr)
        return 2
    env = dict(os.environ)
    env['GVA_ADDR'] = ':%d' % PORT
    env.pop('GVA_MYSQL_DSN', None)
    handle = open(ROOT / 'evidence/error_code_enumeration_runtime.log', 'w', encoding='utf-8')
    proc = subprocess.Popen([str(EXE)], env=env, stdout=handle, stderr=handle)
    try:
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
        log('%-44s %-6s %-5s %-10s %-12s %s'
            % ('用例', '方法', 'HTTP', '业务码', '命中码', '判定'))
        log('-' * 120)

        # 一、下单入参与库存边界
        probe('下单 goods_id=0', 'POST', '/api/v1/orders', 'M-04',
              {'goods_id': 0, 'quantity': 1}, 'buyer01', '一单只能购买一种商品')
        probe('下单 quantity=3', 'POST', '/api/v1/orders', 'M-03',
              {'goods_id': 1, 'quantity': 3}, 'buyer01', '数量只能 1 或 2 件')
        probe('下单 goods_id=999', 'POST', '/api/v1/orders', 'M-01',
              {'goods_id': 999, 'quantity': 1}, 'buyer01', '商品未上架')

        pay_a = probe('下单 A（商品1×2）', 'POST', '/api/v1/orders', None,
                      {'goods_id': 1, 'quantity': 2}, 'buyer01')
        order_a = order_no(pay_a)
        pay_b = probe('下单 B（商品1×2）', 'POST', '/api/v1/orders', None,
                      {'goods_id': 1, 'quantity': 2}, 'buyer01')
        order_b = order_no(pay_b)
        probe('下单 C（商品1×2，可售不足）', 'POST', '/api/v1/orders', 'M-02',
              {'goods_id': 1, 'quantity': 2}, 'buyer01', '可售数量不足')
        pay_e = probe('下单 E（商品1×1，退款链专用）', 'POST', '/api/v1/orders', None,
                      {'goods_id': 1, 'quantity': 1}, 'buyer03')
        order_e = order_no(pay_e)

        # 二、支付通知鉴权、匹配与幂等
        probe('支付 A 验签失败', 'POST', '/api/v1/payment/callback', 'M-28',
              {'order_no': order_a, 'channel_trade_no': 'TR-A', 'amount': 20000,
               'signature_valid': False}, 'mock01')
        probe('支付 A 金额不符', 'POST', '/api/v1/payment/callback', 'M-29',
              {'order_no': order_a, 'channel_trade_no': 'TR-A', 'amount': 19999,
               'signature_valid': True}, 'mock01')
        probe('支付 A 正常成功', 'POST', '/api/v1/payment/callback', None,
              {'order_no': order_a, 'channel_trade_no': 'TR-A', 'amount': 20000,
               'signature_valid': True}, 'mock01')
        probe('支付 A 重复通知（幂等）', 'POST', '/api/v1/payment/callback', 'M-25',
              {'order_no': order_a, 'channel_trade_no': 'TR-A', 'amount': 20000,
               'signature_valid': True}, 'mock01', '未重复记款')
        probe('同一渠道交易号用于另一订单', 'POST', '/api/v1/payment/callback', 'M-27',
              {'order_no': order_b, 'channel_trade_no': 'TR-A', 'amount': 20000,
               'signature_valid': True}, 'mock01')
        probe('支付未知订单', 'POST', '/api/v1/payment/callback', 'M-30',
              {'order_no': 'NOT-EXIST-0001', 'channel_trade_no': 'TR-X', 'amount': 20000,
               'signature_valid': True}, 'mock01')

        # 三、越权隔离
        probe('买家查他人订单', 'GET', '/api/v1/orders/' + order_a, 'M-20', None, 'buyer02')
        probe('买家查运营汇总', 'GET', '/api/v1/ops/summary', 'M-20', None, 'buyer01')
        probe('买家调整演示时钟', 'POST', '/api/v1/admin/clock', 'M-20',
              {'offset_minutes': 1}, 'buyer01')

        # 四、发货规则
        probe('待支付订单登记发货', 'POST', '/api/v1/orders/' + order_b + '/shipment', 'M-18',
              {'carrier': '顺丰', 'tracking_no': 'SF-B'}, 'warehouse01')
        probe('发货不填承运方', 'POST', '/api/v1/orders/' + order_a + '/shipment', 'M-23',
              {'carrier': '', 'tracking_no': 'SF-B'}, 'warehouse01')
        probe('发货登记成功', 'POST', '/api/v1/orders/' + order_a + '/shipment', None,
              {'carrier': '顺丰', 'tracking_no': 'SF-A'}, 'warehouse01')
        probe('重复登记发货', 'POST', '/api/v1/orders/' + order_a + '/shipment', 'M-19',
              {'carrier': '顺丰', 'tracking_no': 'SF-A2'}, 'warehouse01')

        # 五、售前退款链
        probe('支付 E 正常成功', 'POST', '/api/v1/payment/callback', None,
              {'order_no': order_e, 'channel_trade_no': 'TR-E', 'amount': 10000,
               'signature_valid': True}, 'mock01')
        probe('申请整单退款', 'POST', '/api/v1/orders/' + order_e + '/refund/apply', None,
              {'reason': '不想要了'}, 'buyer03')
        probe('退款审核中登记发货', 'POST', '/api/v1/orders/' + order_e + '/shipment', 'M-22',
              {'carrier': '顺丰', 'tracking_no': 'SF-E'}, 'warehouse01')
        probe('退款审核不写原因', 'POST', '/api/v1/orders/' + order_e + '/refund/approve', 'M-24',
              {'remark': ''}, 'cs01')
        probe('退款审核同意', 'POST', '/api/v1/orders/' + order_e + '/refund/approve', None,
              {'remark': '同意整单退款'}, 'cs01')
        probe('退款渠道首次失败', 'POST', '/api/v1/refund/callback', 'M-08',
              {'order_no': order_e, 'refund_channel_trade_no': 'RF-E', 'amount': 10000,
               'signature_valid': True, 'success': False}, 'mock01')
        probe('客服重试退款', 'POST', '/api/v1/orders/' + order_e + '/refund/retry', None,
              {'remark': '客服重试'}, 'cs01')
        probe('退款渠道成功', 'POST', '/api/v1/refund/callback', None,
              {'order_no': order_e, 'refund_channel_trade_no': 'RF-E', 'amount': 10000,
               'signature_valid': True, 'success': True}, 'mock01')
        probe('已退款订单再申请退款', 'POST', '/api/v1/orders/' + order_e + '/refund/apply', 'M-11',
              {'reason': '再退一次'}, 'buyer03')
        probe('退款通知缺渠道交易号', 'POST', '/api/v1/refund/callback', 'M-27',
              {'order_no': order_e, 'amount': 10000, 'signature_valid': True, 'success': True},
              'mock01')

        # 六、取消、重复操作与终态
        probe('取消订单 B', 'POST', '/api/v1/orders/' + order_b + '/cancel', None, None, 'buyer01')
        probe('重复取消订单 B', 'POST', '/api/v1/orders/' + order_b + '/cancel', 'M-10',
              None, 'buyer01')
        probe('已取消订单申请退款', 'POST', '/api/v1/orders/' + order_b + '/refund/apply', 'M-05',
              {'reason': '退不了'}, 'buyer01')
        probe('已取消订单支付通知（终态非已关闭）', 'POST', '/api/v1/payment/callback', 'M-15',
              {'order_no': order_b, 'channel_trade_no': 'TR-B', 'amount': 20000,
               'signature_valid': True}, 'mock01')

        # 七、运营侧提示与核查结论
        probe('运营调价（回传 M-12 / M-13 提示）', 'POST', '/api/v1/admin/goods/1/price',
              'M-12', {'unit_price': 12000, 'reason': '活动价格调整'}, 'ops01')
        probe('逐单核查库存恢复（回传 M-17 结论）', 'GET',
              '/api/v1/ops/stock-check/' + order_e, 'M-17', None, 'ops01')
        probe('运营核查汇总', 'GET', '/api/v1/ops/summary', None, None, 'ops01')

        # 八、服务端时间：超时关单与迟到支付
        pay_c = probe('下单 C（商品2×1）', 'POST', '/api/v1/orders', None,
                      {'goods_id': 2, 'quantity': 1}, 'buyer02')
        order_c = order_no(pay_c)
        pay_d = probe('下单 D（商品2×1）', 'POST', '/api/v1/orders', None,
                      {'goods_id': 2, 'quantity': 1}, 'buyer03')
        order_d = order_no(pay_d)
        probe('推进演示时钟 11 分钟', 'POST', '/api/v1/admin/clock', None,
              {'offset_minutes': 11}, 'ops01')
        probe('取消已超时订单', 'POST', '/api/v1/orders/' + order_c + '/cancel', 'M-06',
              None, 'buyer02')
        probe('关闭超时订单', 'POST', '/api/v1/admin/orders/close-expired', None,
              {'limit': 100}, 'ops01')
        probe('已关闭订单支付通知（迟到支付）', 'POST', '/api/v1/payment/callback', 'M-09',
              {'order_no': order_c, 'channel_trade_no': 'TR-C', 'amount': 10000,
               'signature_valid': True}, 'mock01')
        late = probe('订单 D 迟到支付（生成异常记录）', 'POST', '/api/v1/payment/callback', 'M-09',
                     {'order_no': order_d, 'channel_trade_no': 'TR-D', 'amount': 10000,
                      'signature_valid': True}, 'mock01')
        event_id = int((late.get('data') or {}).get('event_id') or 0)
        probe('核实异常支付（不写原因）', 'POST', '/api/v1/late-payment/1/verify', 'M-24',
              {'reason': ''}, 'cs01')
        probe('核实异常支付', 'POST', '/api/v1/late-payment/%d/verify' % event_id, None,
              {'reason': '核实为迟到支付'}, 'cs01')
        probe('发起迟到支付退款', 'POST', '/api/v1/late-payment/%d/refund/initiate' % event_id,
              'M-26', {'refund_no': 'LR-D', 'reason': '核实后发起退款'}, 'cs01')
        probe('迟到退款渠道首次失败', 'POST', '/api/v1/late-payment/refund/callback', 'M-08',
              {'event_id': event_id, 'refund_no': 'LR-D', 'amount': 10000,
               'signature_valid': True, 'success': False}, 'mock01')
        probe('迟到退款客服重试', 'POST', '/api/v1/late-payment/refund/retry', None,
              {'event_id': event_id, 'refund_no': 'LR-D', 'remark': '客服重试'}, 'cs01')
        probe('迟到退款渠道成功', 'POST', '/api/v1/late-payment/refund/callback', None,
              {'event_id': event_id, 'refund_no': 'LR-D', 'amount': 10000,
               'signature_valid': True, 'success': True}, 'mock01')
        probe('核实未知异常事件', 'POST', '/api/v1/late-payment/999999/verify', 'M-14',
              {'reason': '核实'}, 'cs01')
        probe('恢复演示时钟', 'POST', '/api/v1/admin/clock', None,
              {'offset_minutes': 0}, 'ops01')

        log('-' * 120)
        log('')
        log('===== 错误码逐条覆盖结论 =====')
        log('%-6s %-10s %-10s %-8s %s' % ('编号', '状态', '源码引用', '命中数', '说明'))
        log('-' * 110)
        covered = 0
        for code, text in codes:
            hits = observed[code]
            if hits:
                covered += 1
                state = '已触发'
                detail = '；'.join('%s @ %s' % (label, field) for label, field in hits[:3])
            elif refs.get(code, 0) == 0:
                state = '文案常量'
                detail = '该文案仅在 types.go 定义，源码中无任何分支引用（未作为错误码返回）'
            else:
                state = '未观测'
                detail = '源码引用 %d 处，本次流程未构造出该分支' % refs.get(code, 0)
            log('%-6s %-10s %-10d %-8d %s' % (code, state, refs.get(code, 0), len(hits), detail))
        log('-' * 110)
        log('错误码总数：%d；作为业务错误码被真实触发：%d；仅作文案常量：%d；未观测：%d'
            % (len(codes), covered,
               sum(1 for code, _ in codes if not observed[code] and refs.get(code, 0) == 0),
               sum(1 for code, _ in codes if not observed[code] and refs.get(code, 0) > 0)))
        log('用例总数：%d；断言未命中：%d' % (len(steps), len(failures)))
        for label, expect, top, matched in failures:
            log('  未命中用例：%s 期望 %s，实际顶层码 %s，命中 %s'
                % (label, expect, top, matched))
        log('判定：%s' % ('全部期望错误码均被真实触发' if not failures else '存在未命中用例'))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()

    LOG.write_text('\n'.join(LINES) + '\n', encoding='utf-8')
    JSON_OUT.write_text(json.dumps(
        {'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
         'port': PORT, 'mode': 'demo-memory',
         'codes': [{'code': code, 'message': text, 'source_refs': refs.get(code, 0),
                    'observed': [{'case': label, 'field': field} for label, field in observed[code]],
                    'state': ('已触发' if observed[code] else
                              ('文案常量' if refs.get(code, 0) == 0 else '未观测'))}
                   for code, text in codes],
         'steps': steps, 'failures': failures}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('written: %s / %s' % (LOG, JSON_OUT))
    return 0 if not failures else 1


if __name__ == '__main__':
    raise SystemExit(main())
