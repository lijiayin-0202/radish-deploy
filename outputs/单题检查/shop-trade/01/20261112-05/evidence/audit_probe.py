#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查者独立反例探测（不依赖学生脚本、不修改学生产物）。"""
import concurrent.futures
import json
import os
import pathlib
import subprocess
import threading
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(r'd:/Desktop/shop')
OUT = ROOT / 'outputs/单题检查/shop-trade/01/20261112-05/evidence'
OUT.mkdir(parents=True, exist_ok=True)
PORT = 18097
BASE = f'http://127.0.0.1:{PORT}'
EXE = pathlib.Path(os.environ.get('TEMP', '/tmp')) / 'shop-trade-audit.exe'

LOG = []
RESULTS = []


def log(text=''):
    LOG.append(text)
    print(text)


def head(title):
    log('')
    log('=' * 76)
    log(title)
    log('=' * 76)


def call(method, path, account, body=None):
    headers = {'X-Demo-Account': account}
    payload = None
    if body is not None:
        payload = json.dumps(body, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(BASE + path, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode('utf-8', 'replace')
            try:
                obj = json.loads(raw)
            except ValueError:
                obj = None
            return r.status, obj, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', 'replace')
        try:
            obj = json.loads(raw)
        except ValueError:
            obj = None
        return e.code, obj, raw
    except Exception as e:  # noqa: BLE001
        return -1, None, str(e)


def code(obj):
    return obj.get('code') if isinstance(obj, dict) else '(no-json)'


def data(obj):
    if isinstance(obj, dict) and isinstance(obj.get('data'), dict):
        return obj['data']
    return {}


def check(name, expected, got, detail=''):
    ok = got == expected
    RESULTS.append({'case': name, 'expected': str(expected), 'actual': str(got),
                    'verdict': 'PASS' if ok else 'DIFF', 'detail': detail})
    log('[%s] %s | expected=%s actual=%s %s' % ('PASS' if ok else 'DIFF', name, expected, got, detail))
    return ok


def cmd(argv, cwd=ROOT):
    r = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return r.returncode, ((r.stdout or '') + (r.stderr or '')).strip()


def start():
    env = dict(os.environ)
    env['GVA_ADDR'] = ':%d' % PORT
    env.pop('GVA_MYSQL_DSN', None)
    p = subprocess.Popen([str(EXE)], cwd=str(ROOT), env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(80):
        st, _, _ = call('GET', '/health', 'buyer01')
        if st == 200:
            return p
        time.sleep(0.3)
    p.terminate()
    raise RuntimeError('health timeout')


def stop(p):
    p.terminate()
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        p.kill()
    time.sleep(0.4)


def goods1():
    st, obj, raw = call('GET', '/api/v1/goods', 'buyer01')
    return next((i for i in data(obj).get('items', []) if i.get('id') == 1), {})


def run_toolchain():
    head('0. 检查者环境与工具链（真实执行）')
    probes = [
        (['go', 'version'], 'go version'),
        (['go', 'env', 'CGO_ENABLED'], 'go env CGO_ENABLED'),
        (['where', 'gcc'], 'where gcc'),
        (['where', 'clang'], 'where clang'),
        (['where', 'mysql'], 'where mysql'),
        (['git', 'remote', '-v'], 'git remote -v'),
        (['git', 'rev-parse', 'HEAD'], 'git rev-parse HEAD'),
        (['git', 'status', '--short'], 'git status --short'),
        (['git', 'branch', '-a'], 'git branch -a'),
        (['git', 'log', '--format=%H|%ad|%s', '--date=iso', '-8'], 'git log -8'),
    ]
    for argv, label in probes:
        rc, out = cmd(argv)
        log('$ %s\n%s  (exit=%d)' % (label, out or '(空)', rc))
    rc, out = cmd(['gofmt', '-l', '.'])
    log('$ gofmt -l .\n%s  (exit=%d)' % (out or '(无输出：全部已格式化)', rc))
    check('gofmt -l . 无输出', '', out)
    rc, out = cmd(['go', 'vet', './...'])
    log('$ go vet ./...\n%s  (exit=%d)' % (out or '(无输出：通过)', rc))
    check('go vet 通过', 0, rc, out[:120])
    rc, out = cmd(['go', 'build', '-o', str(EXE), '.'])
    log('$ go build -o <tmp>/shop-trade-audit.exe .\n%s  (exit=%d)' % (out or '(无输出)', rc))
    check('go build 成功', 0, rc, out[:200])
    rc, out = cmd(['go', 'test', '-count=1', './...'])
    log('$ go test -count=1 ./...\n%s  (exit=%d)' % (out, rc))
    check('go test -count=1 ./... 全部通过', 0, rc)
    rc, out = cmd(['go', 'test', '-count=1', '-cover', './server/service/...'])
    log('$ go test -count=1 -cover ./server/service/...\n%s  (exit=%d)' % (out, rc))
    rc, out = cmd(['go', 'test', '-count=1', '-coverpkg=./...',
                   '-coverprofile=%s' % (OUT / 'audit-cover.out'), './...'])
    log('$ go test -count=1 -coverpkg=./... -coverprofile=<本批次>/audit-cover.out ./...\n%s  (exit=%d)' % (out, rc))
    rc, out = cmd(['go', 'tool', 'cover', '-func=%s' % (OUT / 'audit-cover.out')])
    log('$ go tool cover -func=audit-cover.out (按包逐函数覆盖)')
    by_pkg = {}
    for line in out.splitlines():
        if ':' not in line or line.startswith('total:'):
            continue
        pkg = line.split(':')[0].rsplit('/', 1)[0]
        by_pkg.setdefault(pkg, []).append(float(line.strip().split('\t')[-1].rstrip('%')))
    for pkg in sorted(by_pkg):
        v = by_pkg[pkg]
        log('  %s: 逐函数最低=%s%% 最高=%s%% 文件数=%d' % (pkg, min(v), max(v), len(v)))
    log('  overall: ' + (out.strip().splitlines()[-1] if out.strip() else ''))
    rc, out = cmd(['go', 'test', '-count=1', '-race', './server/...'])
    log('$ go test -count=1 -race ./server/...\n%s  (exit=%d)' % (out, rc))
    ci = ROOT / '.github/workflows/ci.yml'
    ci_text = ci.read_text(encoding='utf-8') if ci.exists() else ''
    eff = [l for l in ci_text.splitlines() if l.strip() and not l.strip().startswith('#')]
    log('.github/workflows/ci.yml 存在=%s 总行数=%d 非注释非空行数=%d'
        % (ci.exists(), len(ci_text.splitlines()), len(eff)))
    for l in eff:
        log('  有效行: ' + l)


def run_business():
    head('6. 启动 / 健康 / 业务规则与场景（检查者独立探测）')
    p = start()
    try:
        st, obj, raw = call('GET', '/health', 'buyer01')
        log('GET /health -> HTTP %d %s' % (st, raw))
        check('健康检查 200', 200, st, raw[:80])
        for acc, role in (('buyer01', '买家'), ('ops01', '运营'),
                          ('warehouse01', '仓库'), ('cs01', '客服'), ('mock01', '模拟渠道')):
            st, obj, raw = call('GET', '/api/v1/me', acc)
            check('身份解析 %s→%s' % (acc, role), role, data(obj).get('role'), raw[:80])
        st, obj, raw = call('GET', '/api/v1/me', 'nobody')
        check('未知身份被拒', 'PARAM_ERROR', code(obj), raw[:80])

        st, obj, raw = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 2})
        o1 = data(obj)
        check('下单成功(quantity=2)', '0', code(obj), raw[:120])
        no1 = o1.get('order_no')
        check('下单金额=单价×数量', 20000, o1.get('total_amount'))
        g = goods1()
        check('下单后可售=3', 3, g.get('available_stock'), str(g))
        check('下单后占用=2', 2, g.get('occupied_stock'), str(g))
        st, obj, raw = call('POST', '/api/v1/orders', 'ops01', {'goods_id': 1, 'quantity': 1})
        check('运营越权下单被拒', 'M-20', code(obj), raw[:100])

        st, obj, raw = call('POST', '/api/v1/admin/goods/1/price', 'ops01',
                            {'unit_price': 12000, 'reason': '检查者独立探测'})
        check('运营调价成功', '0', code(obj), raw[:120])
        check('调价 old_unit_price=10000', 10000, data(obj).get('old_unit_price'))
        check('调价 new_unit_price=12000', 12000, data(obj).get('new_unit_price'))
        st, obj, raw = call('GET', '/api/v1/orders/%s' % no1, 'buyer01')
        check('调价后旧单单价快照不变(M-12)', 10000, data(obj).get('unit_price'), raw[:120])
        st, obj, raw = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
        check('调价后新单按新价', 12000, data(obj).get('unit_price'), raw[:120])
        st, obj, raw = call('POST', '/api/v1/admin/goods/1/price', 'buyer01',
                            {'unit_price': 13000, 'reason': '越权调价'})
        check('买家越权调价被拒', 'M-20', code(obj), raw[:100])
        call('POST', '/api/v1/admin/goods/1/price', 'ops01',
             {'unit_price': 10000, 'reason': '检查者探测后还原'})

        pay_cases = [
            ({'order_no': no1, 'channel_trade_no': 'AUD-TR-1', 'amount': 999,
              'signature_valid': True}, 'M-29', '支付金额不符被拒'),
            ({'order_no': no1, 'channel_trade_no': 'AUD-TR-1', 'amount': 20000,
              'signature_valid': False}, 'M-28', '支付验签失败被拒'),
            ({'order_no': 'NO-SUCH', 'channel_trade_no': 'AUD-TR-0', 'amount': 100,
              'signature_valid': True}, 'M-30', '支付未知订单被拒'),
        ]
        for body, exp, label in pay_cases:
            st, obj, raw = call('POST', '/api/v1/payment/callback', 'mock01', body)
            check(label, exp, code(obj), raw[:100])
        st, obj, raw = call('POST', '/api/v1/payment/callback', 'mock01',
                            {'order_no': no1, 'channel_trade_no': 'AUD-TR-1', 'amount': 20000,
                             'signature_valid': True})
        check('支付成功', '0', code(obj), raw[:120])
        st, obj, raw = call('GET', '/api/v1/orders/%s' % no1, 'buyer01')
        check('支付后订单转待发货', '待发货', data(obj).get('status'), raw[:120])
        st, obj, raw = call('POST', '/api/v1/payment/callback', 'mock01',
                            {'order_no': no1, 'channel_trade_no': 'AUD-TR-1', 'amount': 20000,
                             'signature_valid': True})
        check('重复支付通知幂等返回0', '0', code(obj), raw[:120])
        check('重复通知留痕 event_type=重复支付通知', '重复支付通知', data(obj).get('event_type'), raw[:160])
        check('重复通知留痕 result=幂等未重复记款', '重复支付通知已幂等处理，未重复记款',
              data(obj).get('result'), raw[:160])
        st, obj, raw = call('POST', '/api/v1/orders', 'buyer02', {'goods_id': 2, 'quantity': 1})
        no2 = data(obj).get('order_no')
        st, obj, raw = call('POST', '/api/v1/payment/callback', 'mock01',
                            {'order_no': no2, 'channel_trade_no': 'AUD-TR-1', 'amount': 10000,
                             'signature_valid': True})
        check('同一渠道交易号不得归属两单', 'M-27', code(obj), raw[:120])
        st, obj, raw = call('GET', '/api/v1/orders/%s' % no1, 'buyer02')
        check('越权查询他人订单被拒', 'M-20', code(obj), raw[:100])
        st, obj, raw = call('POST', '/api/v1/orders/%s/cancel' % no1, 'buyer02', None)
        check('越权取消他人订单被拒', 'M-20', code(obj), raw[:100])

        st, obj, raw = call('POST', '/api/v1/orders/%s/shipment' % no1, 'warehouse01',
                            {'carrier': '检查者承运', 'tracking_no': 'AUD-SF-1'})
        check('登记发货成功', '0', code(obj), raw[:120])
        st, obj, raw = call('POST', '/api/v1/orders/%s/shipment' % no1, 'warehouse01',
                            {'carrier': '检查者承运', 'tracking_no': 'AUD-SF-1'})
        check('重复发货被拒(M-19)', 'M-19', code(obj), raw[:100])
        st, obj, raw = call('POST', '/api/v1/orders/%s/shipment' % no1, 'warehouse01',
                            {'carrier': '', 'tracking_no': 'AUD-SF-2'})
        check('空承运方发货被拒(M-23)', 'M-23', code(obj), raw[:100])
        st, obj, raw = call('POST', '/api/v1/orders/%s/refund/apply' % no1, 'buyer01',
                            {'reason': '已发货后申请售前退款'})
        check('已发货订单不受理售前退款(M-11)', 'M-11', code(obj), raw[:100])
        st, obj, raw = call('GET', '/api/v1/orders/%s' % no1, 'buyer01')
        check('发货后订单终态=已发货', '已发货', data(obj).get('status'), raw[:120])

        st, obj, raw = call('POST', '/api/v1/orders', 'buyer03', {'goods_id': 1, 'quantity': 1})
        no3 = data(obj).get('order_no')
        call('POST', '/api/v1/payment/callback', 'mock01',
             {'order_no': no3, 'channel_trade_no': 'AUD-S3', 'amount': 10000,
              'signature_valid': True})
        st, obj, raw = call('POST', '/api/v1/orders/%s/refund/apply' % no3, 'buyer03',
                            {'reason': '检查者售前退款'})
        check('申请整单退款成功', '0', code(obj), raw[:120])
        st, obj, raw = call('POST', '/api/v1/orders/%s/shipment' % no3, 'warehouse01',
                            {'carrier': '检查者承运', 'tracking_no': 'AUD-SF-3'})
        check('退款申请期间发货被拒(M-22)', 'M-22', code(obj), raw[:100])
        st, obj, raw = call('POST', '/api/v1/orders/%s/refund/approve' % no3, 'cs01',
                            {'remark': ''})
        check('客服同意缺原因被拒(M-24)', 'M-24', code(obj), raw[:100])
        st, obj, raw = call('POST', '/api/v1/orders/%s/refund/approve' % no3, 'buyer03',
                            {'remark': '买家越权'})
        check('买家越权审核被拒(M-20)', 'M-20', code(obj), raw[:100])
        st, obj, raw = call('POST', '/api/v1/orders/%s/refund/approve' % no3, 'cs01',
                            {'remark': '同意整单退款'})
        check('客服同意退款成功', '0', code(obj), raw[:120])
        st, obj, raw = call('POST', '/api/v1/refund/callback', 'mock01',
                            {'order_no': no3, 'refund_channel_trade_no': 'AUD-RF-1',
                             'amount': 10000, 'success': False, 'signature_valid': True})
        check('渠道退款首次失败(M-08)', 'M-08', code(obj), raw[:120])
        st, obj, raw = call('GET', '/api/v1/orders/%s' % no3, 'buyer03')
        check('渠道失败后仍在退款流程', '退款处理中', data(obj).get('status'), raw[:120])
        st, obj, raw = call('POST', '/api/v1/orders/%s/refund/retry' % no3, 'cs01',
                            {'remark': '渠道失败后重试'})
        check('客服登记重试成功', '0', code(obj), raw[:120])
        st, obj, raw = call('POST', '/api/v1/refund/callback', 'mock01',
                            {'order_no': no3, 'refund_channel_trade_no': 'AUD-RF-2',
                             'amount': 10000, 'success': True, 'signature_valid': True})
        check('渠道退款再次成功', '0', code(obj), raw[:120])
        st, obj, raw = call('GET', '/api/v1/orders/%s' % no3, 'buyer03')
        check('退款成功后订单=已退款', '已退款', data(obj).get('status'), raw[:120])
        check('退款后库存恢复标记', True, data(obj).get('stock_restored'), raw[:120])
        st, obj, raw = call('GET', '/api/v1/ops/stock-check/%s' % no3, 'ops01')
        check('逐单核查 期望恢复次数=1', 1, data(obj).get('expected_restore_times'), raw[:120])
        check('逐单核查 实际恢复次数=1', 1, data(obj).get('actual_restore_times'), raw[:120])
        check('逐单核查 一致', True, data(obj).get('consistent'), raw[:120])
        st, obj, raw = call('POST', '/api/v1/refund/callback', 'mock01',
                            {'order_no': no3, 'refund_channel_trade_no': 'AUD-RF-2',
                             'amount': 10000, 'success': True, 'signature_valid': True})
        check('重复退款通知幂等', '0', code(obj), raw[:120])
        st, obj, raw = call('GET', '/api/v1/ops/stock-check/%s' % no3, 'ops01')
        check('重复退款通知后恢复次数仍=1', 1, data(obj).get('actual_restore_times'), raw[:120])
        st, obj, raw = call('GET', '/api/v1/ops/stock-check/%s' % no3, 'buyer03')
        check('买家无权做库存核查(M-20)', 'M-20', code(obj), raw[:100])
        st, obj, raw = call('POST', '/api/v1/orders/%s/refund/apply' % no3, 'buyer03',
                            {'reason': '已退款再申请'})
        check('已退款订单再申请被拒(M-11)', 'M-11', code(obj), raw[:100])

        st, obj, raw = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
        no4 = data(obj).get('order_no')
        occ_before = goods1().get('occupied_stock')
        st, obj, raw = call('POST', '/api/v1/admin/clock', 'ops01', {'offset_minutes': 11})
        check('演示时钟推进 11 分钟', '0', code(obj), raw[:120])
        st, obj, raw = call('POST', '/api/v1/admin/orders/close-expired', 'ops01', {})
        check('超时关单执行成功', '0', code(obj), raw[:120])
        log('  closed_count=%s' % data(obj).get('closed_count'))
        st, obj, raw = call('GET', '/api/v1/orders/%s' % no4, 'buyer01')
        check('超时订单=已关闭', '已关闭', data(obj).get('status'), raw[:120])
        occ_after1 = goods1().get('occupied_stock')
        log('  本次 closed_count=%s，本进程此前累计待支付单占用释放后 occupied=%s'
            % (data(obj).get('closed_count'), occ_after1))
        call('POST', '/api/v1/admin/orders/close-expired', 'ops01', {})
        check('重复关单不多释放(占用不变)', occ_after1, goods1().get('occupied_stock'))
        st, obj, raw = call('POST', '/api/v1/admin/clock', 'ops01', {'offset_minutes': -1})
        check('演示时钟越界被拒', 'PARAM_ERROR', code(obj), raw[:100])

        st, obj, raw = call('GET', '/api/v1/orders/%s' % no4, 'buyer01')
        status_before = data(obj).get('status')
        occ_b2 = goods1().get('occupied_stock')
        st, obj, raw = call('POST', '/api/v1/payment/callback', 'mock01',
                            {'order_no': no4, 'channel_trade_no': 'AUD-LATE-1', 'amount': 10000,
                             'signature_valid': True})
        check('迟到支付返回 M-09', 'M-09', code(obj), raw[:120])
        eid = data(obj).get('event_id')
        log('  迟到支付 event_id=%s' % eid)
        st, obj, raw = call('GET', '/api/v1/orders/%s' % no4, 'buyer01')
        check('迟到支付不改订单状态', status_before, data(obj).get('status'), raw[:120])
        check('迟到支付不重新占用库存', occ_b2, goods1().get('occupied_stock'))
        st, obj, raw = call('POST', '/api/v1/late-payment/%s/verify' % eid, 'cs01',
                            {'reason': '检查者核实'})
        check('客服核实迟到支付异常', '0', code(obj), raw[:120])
        st, obj, raw = call('POST', '/api/v1/late-payment/%s/refund/initiate' % eid, 'cs01',
                            {'refund_no': 'AUD-LATE-RF', 'reason': '检查者发起退款'})
        check('发起迟到支付退款', '0', code(obj), raw[:120])
        st, obj, raw = call('POST', '/api/v1/late-payment/refund/callback', 'mock01',
                            {'event_id': eid, 'refund_no': 'AUD-LATE-RF', 'amount': 10000,
                             'success': True, 'signature_valid': True})
        check('迟到支付退款渠道成功', '0', code(obj), raw[:150])
        st, obj, raw = call('GET', '/api/v1/orders/%s' % no4, 'buyer01')
        check('迟到支付退款后订单仍为已关闭', '已关闭', data(obj).get('status'), raw[:120])
        check('迟到支付退款不二次恢复库存(M-26)', occ_b2, goods1().get('occupied_stock'))

        st, obj, raw = call('GET', '/api/v1/orders/%s/status' % no2, 'buyer02')
        stt = data(obj).get('status')
        st, obj, raw = call('POST', '/api/v1/payment/timeout', 'mock01',
                            {'order_no': no2, 'channel_trade_no': 'AUD-TO-1',
                             'reason': '检查者超时通知'})
        check('渠道超时通知受理', '0', code(obj), raw[:120])
        check('超时通知不改订单状态标记', True, data(obj).get('order_status_unchanged'), raw[:120])
        st, obj, raw = call('GET', '/api/v1/orders/%s/status' % no2, 'buyer02')
        check('超时通知后订单状态不变', stt, data(obj).get('status'), raw[:120])
        st, obj, raw = call('POST', '/api/v1/payment/timeout', 'mock01',
                            {'order_no': no2, 'channel_trade_no': 'AUD-TO-1', 'reason': '重复通知'})
        check('重复超时通知幂等', True, data(obj).get('duplicate'), raw[:120])
        st, obj, raw = call('POST', '/api/v1/payment/timeout', 'buyer01',
                            {'order_no': no2, 'channel_trade_no': 'AUD-TO-2', 'reason': '买家越权'})
        check('买家越权发超时通知被拒', 'M-20', code(obj), raw[:100])

        st, obj, raw = call('GET', '/api/v1/ops/summary', 'ops01')
        check('运营汇总可查', '0', code(obj), raw[:160])
        st, obj, raw = call('GET', '/api/v1/ops/summary', 'buyer01')
        check('买家无权查看运营汇总', 'M-20', code(obj), raw[:100])

        st, obj, raw = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 2, 'quantity': 1})
        no5 = data(obj).get('order_no')
        st, obj, raw = call('POST', '/api/v1/orders/%s/cancel' % no5, 'buyer01', None)
        check('取消待支付订单成功', '0', code(obj), raw[:120])
        check('取消后订单=已取消', '已取消', data(obj).get('status'), raw[:120])
        st, obj, raw = call('POST', '/api/v1/orders/%s/cancel' % no5, 'buyer01', None)
        check('重复取消被拒(M-10)', 'M-10', code(obj), raw[:100])
    finally:
        stop(p)


def run_close_release():
    head('7b. 超时关闭释放库存：独立进程单独验证（检查者独立探测）')
    p = start()
    try:
        st, obj, raw = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 2})
        no = data(obj).get('order_no')
        g = goods1()
        check('下单 qty=2 后可售=3', 3, g.get('available_stock'), str(g))
        check('下单 qty=2 后占用=2', 2, g.get('occupied_stock'), str(g))
        st, obj, raw = call('POST', '/api/v1/admin/clock', 'ops01', {'offset_minutes': 11})
        check('演示时钟推进 11 分钟', '0', code(obj), raw[:120])
        st, obj, raw = call('POST', '/api/v1/admin/orders/close-expired', 'ops01', {})
        check('超时关单执行成功', '0', code(obj), raw[:120])
        check('本次关闭订单数=1', 1, data(obj).get('closed_count'), raw[:120])
        g = goods1()
        check('超时关闭后可售回到5', 5, g.get('available_stock'), str(g))
        check('超时关闭后占用归零', 0, g.get('occupied_stock'), str(g))
        st, obj, raw = call('GET', '/api/v1/orders/%s' % no, 'buyer01')
        check('超时订单=已关闭', '已关闭', data(obj).get('status'), raw[:120])
        call('POST', '/api/v1/admin/orders/close-expired', 'ops01', {})
        g = goods1()
        check('重复关单不多释放(占用仍为0)', 0, g.get('occupied_stock'), str(g))
        check('重复关单后可售仍为5', 5, g.get('available_stock'), str(g))
    finally:
        stop(p)


def run_concurrency():
    head('7. 场景S2/S5：20 并发下单库存守恒（检查者独立探测）')
    p = start()
    try:
        def place(_):
            return call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            res = list(pool.map(place, range(20)))
        okc = sum(1 for r in res if code(r[1]) == '0')
        m02 = sum(1 for r in res if code(r[1]) == 'M-02')
        oth = [(code(r[1]), r[2][:60]) for r in res if code(r[1]) not in ('0', 'M-02')]
        log('20 并发：成功=%d M-02=%d 其他=%d 合计=%d' % (okc, m02, len(oth), okc + m02 + len(oth)))
        for o in oth:
            log('  其他返回: ' + str(o))
        check('20 并发请求全部有明确结果', 20, okc + m02 + len(oth))
        check('成功下单数=可售5', 5, okc)
        check('库存不足数=15', 15, m02)
        g = goods1()
        check('并发后可售=0', 0, g.get('available_stock'), str(g))
        check('并发后占用=5', 5, g.get('occupied_stock'), str(g))
    finally:
        stop(p)


def run_persistence():
    head('8. 重启后业务结果可查（检查者独立探测）')
    p = start()
    try:
        st, obj, raw = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
        no6 = data(obj).get('order_no')
        call('POST', '/api/v1/payment/callback', 'mock01',
             {'order_no': no6, 'channel_trade_no': 'AUD-PERSIST', 'amount': 10000,
              'signature_valid': True})
        st, obj, raw = call('GET', '/api/v1/orders/%s' % no6, 'buyer01')
        check('重启前订单可查', '0', code(obj), raw[:120])
        log('  重启前订单号 %s' % no6)
    finally:
        stop(p)
    p = start()
    try:
        st, obj, raw = call('GET', '/api/v1/orders/%s' % no6, 'buyer01')
        log('  重启后查询同一订单 -> HTTP %d %s' % (st, raw))
        check('【环境限制·非代码缺陷】重启后同一订单仍可查（demo-memory 无持久化，真实 MySQL 未验证）',
              '0', code(obj), raw[:120])
        check('【环境限制·非代码缺陷】重启后商品可售回到初始5', 5, goods1().get('available_stock'))
    finally:
        stop(p)


def run_pages():
    head('9. 8 个原型页面可达性（检查者独立探测）')
    p = start()
    try:
        for i in range(1, 9):
            found = None
            for name in sorted((ROOT / 'resource/static').glob('v0%d-*.html' % i)):
                found = name.name
            st, obj, raw = call('GET', '/static/%s' % found, 'buyer01')
            check('页面 %s 可达' % found, 200, st)
    finally:
        stop(p)


def run_reject_then_ship():
    head('7c. 客服拒绝退款后允许继续发货（规则 01-A1-05）')
    p = start()
    try:
        st, obj, raw = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
        no = data(obj).get('order_no')
        call('POST', '/api/v1/payment/callback', 'mock01',
             {'order_no': no, 'channel_trade_no': 'AUD-B1', 'amount': 10000,
              'signature_valid': True})
        st, obj, raw = call('POST', '/api/v1/orders/%s/refund/apply' % no, 'buyer01',
                            {'reason': '申请退款以验证拒绝路径'})
        check('申请退款成功', '0', code(obj), raw[:120])
        st, obj, raw = call('POST', '/api/v1/orders/%s/refund/reject' % no, 'cs01',
                            {'remark': '不符合退款条件，拒绝'})
        check('客服拒绝退款成功', '0', code(obj), raw[:120])
        st, obj, raw = call('GET', '/api/v1/orders/%s' % no, 'buyer01')
        check('拒绝后订单恢复为待发货', '待发货', data(obj).get('status'), raw[:160])
        check('拒绝后退款状态留痕为已拒绝', '已拒绝', data(obj).get('refund_state'), raw[:160])
        st, obj, raw = call('POST', '/api/v1/orders/%s/shipment' % no, 'warehouse01',
                            {'carrier': '检查者承运', 'tracking_no': 'AUD-B1-SF'})
        check('拒绝后允许继续发货', '0', code(obj), raw[:120])
        st, obj, raw = call('GET', '/api/v1/orders/%s' % no, 'buyer01')
        check('发货后订单=已发货', '已发货', data(obj).get('status'), raw[:120])
    finally:
        stop(p)


def run_refund_ship_race():
    head('7d. 退款申请与发货并发裁决（规则 01-A1-13 / 场景 S5）')
    p = start()
    try:
        for i in range(3):
            st, obj, raw = call('POST', '/api/v1/orders', 'buyer01', {'goods_id': 1, 'quantity': 1})
            no = data(obj).get('order_no')
            check('第%d轮并发前置下单成功（库存充足）' % (i + 1), '0', code(obj), raw[:120])
            if code(obj) != '0':
                log('  第%d轮下单失败，跳过本轮并发（探测脚本资源不足，非代码缺陷）' % (i + 1))
                continue
            call('POST', '/api/v1/payment/callback', 'mock01',
                 {'order_no': no, 'channel_trade_no': 'AUD-B2-%d' % i, 'amount': 10000,
                  'signature_valid': True})
            box = {}

            def do_refund(n=no, b=box):
                b['refund'] = call('POST', '/api/v1/orders/%s/refund/apply' % n,
                                   'buyer01', {'reason': '并发退款申请'})[1]

            def do_ship(n=no, b=box):
                b['ship'] = call('POST', '/api/v1/orders/%s/shipment' % n, 'warehouse01',
                                 {'carrier': '检查者承运',
                                  'tracking_no': 'AUD-B2-SF-%d' % i})[1]

            t1 = threading.Thread(target=do_refund)
            t2 = threading.Thread(target=do_ship)
            t1.start()
            t2.start()
            t1.join()
            t2.join()
            rc = code(box.get('refund'))
            sc = code(box.get('ship'))
            stt = call('GET', '/api/v1/orders/%s' % no, 'buyer01')[1]
            status = data(stt).get('status')
            log('  第%d轮 并发结果：refund=%s ship=%s → 订单状态=%s'
                % (i + 1, rc, sc, status))
            legal = ((rc == '0' and sc == 'M-22') or
                     (sc == '0' and rc in ('M-05', 'M-10', 'M-11')))
            check('第%d轮并发只形成一种合法结果' % (i + 1), True, legal,
                  'refund=%s ship=%s status=%s' % (rc, sc, status))
            if sc == '0':
                check('第%d轮发货成功则终态为已发货' % (i + 1), '已发货', status)
            if rc == '0':
                check('第%d轮退款成功则状态为退款审核中' % (i + 1), '退款审核中', status)
    finally:
        stop(p)


def main():
    run_toolchain()
    run_business()
    run_close_release()
    run_reject_then_ship()
    run_refund_ship_race()
    run_concurrency()
    run_persistence()
    run_pages()
    head('10. 探测汇总')
    passed = sum(1 for r in RESULTS if r['verdict'] == 'PASS')
    diffs = [r for r in RESULTS if r['verdict'] != 'PASS']
    log('独立反例探测：共 %d 条，PASS %d 条，DIFF %d 条' % (len(RESULTS), passed, len(diffs)))
    for r in diffs:
        log('  DIFF: %s | expected=%s actual=%s %s'
            % (r['case'], r['expected'], r['actual'], r['detail']))
    (OUT / '独立反例探测输出.txt').write_text('\n'.join(LOG) + '\n', encoding='utf-8')
    (OUT / '独立反例探测结果.json').write_text(
        json.dumps(RESULTS, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('probe done: %d cases, %d PASS, %d DIFF' % (len(RESULTS), passed, len(diffs)))


if __name__ == '__main__':
    main()
