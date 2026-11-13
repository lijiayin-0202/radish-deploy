#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真实 InnoDB 行锁下的「退款申请 vs 登记发货」互斥裁决复现脚本。

【要解决的问题】
第 6 轮单题检查登记了 ISS-A1-13-SHIP-RACE：该并发裁决此前只在 demo-memory 的进程内互斥锁下
被验证过，缺少「同一断言在真实 InnoDB 行锁下复现」的证据。本脚本在真实 MySQL(InnoDB) 实例上补齐。

【复现步骤（Windows PowerShell，不使用 WSL）】
  1) 准备可用的 MySQL 账号（本机 MySQL 监听 127.0.0.1:3306，账号需对 shop_trade 有读写权限）：
       $env:MYSQL_USER='audit_chk'; $env:MYSQL_PASSWORD=''
  2) 执行本脚本（自动 go build 并以 mysql-innodb 模式拉起独立实例）：
       python -X utf8 evidence/db/inno_ship_refund_race.py --rounds 5
  3) 原始输出落在 evidence/db/inno_ship_refund_race_raw.txt，退出码 0 表示全部断言通过。

【三个阶段】
  阶段 A 并发裁决复现：对同一笔已支付待发货订单，并发发起「申请整单退款」与「登记发货」，
          断言每轮只形成一种合法结果，且订单行终态、库存守恒与审计事件唯一。
  阶段 B 行锁阻塞探针（决定性证据）：用外部事务 T0 对该订单行执行 SELECT ... FOR UPDATE 持锁，
          此时应用侧退款请求必须被阻塞；T0 回滚释放锁后请求立即成功。
          阻塞源是外部事务持有的数据库行锁，进程内互斥锁无法造成该现象，
          因此该探针证明并发裁决确实发生在 InnoDB 行锁层。
  阶段 C 表级一致性汇总与清理：核对订单行、库存列与审计流水，并回滚测试数据。

【退出码】
  0  全部断言通过
  1  任一断言失败
"""
import argparse
import json
import os
import pathlib
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

import pymysql

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / 'evidence/db/inno_ship_refund_race_raw.txt'
LOG = []
RESULTS = []


def log(msg=''):
    line = str(msg)
    LOG.append(line)
    print(line, flush=True)


def head(title):
    log('')
    log('=' * 78)
    log(title)
    log('=' * 78)


def check(name, ok, detail=''):
    RESULTS.append({'case': name, 'verdict': 'PASS' if ok else 'FAIL', 'detail': str(detail)})
    log('[断言] %s | %s | %s' % ('PASS' if ok else 'FAIL', name, detail))
    return ok


def sql(cur, query, args=None):
    cur.execute(query, args or ())
    return cur.fetchall()


def http(method, path, body=None, account='buyer01', base='http://127.0.0.1:18099', timeout=30):
    headers = {'X-Demo-Account': account} if account else {}
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as e:
        return e.code, {'code': 'HTTP%d' % e.code, 'message': e.read().decode('utf-8', 'replace')}
    except Exception as e:
        return -1, {'code': 'REQUEST_FAILED', 'message': repr(e)}


def code_of(obj):
    return (obj or {}).get('code')


def data_of(obj):
    return (obj or {}).get('data') or {}


def build_binary(out_path):
    r = subprocess.run(['go', 'build', '-o', str(out_path), '.'], cwd=str(ROOT),
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    if r.returncode != 0:
        raise SystemExit('构建失败：%s' % ((r.stderr or r.stdout or '').strip()[:400]))
    return out_path


def start_app(exe, dsn, port, log_path):
    env = dict(os.environ)
    env['GVA_ADDR'] = ':%d' % port
    env['GVA_MYSQL_DSN'] = dsn
    h = open(log_path, 'a', encoding='utf-8')
    p = subprocess.Popen([str(exe)], cwd=str(ROOT), env=env, stdout=h, stderr=h)
    base = 'http://127.0.0.1:%d' % port
    for _ in range(80):
        time.sleep(0.5)
        if p.poll() is not None:
            raise SystemExit('应用进程提前退出，退出码 %s' % p.returncode)
        try:
            with urllib.request.urlopen(base + '/health', timeout=3) as r:
                if r.status == 200:
                    return p, base
        except Exception:
            continue
    p.kill()
    raise SystemExit('应用启动超时')


def main():
    ap = argparse.ArgumentParser(description='InnoDB 行锁下退款与发货互斥裁决复现')
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=3306)
    ap.add_argument('--user', default=os.environ.get('MYSQL_USER', 'audit_chk'))
    ap.add_argument('--password', default=os.environ.get('MYSQL_PASSWORD', ''))
    ap.add_argument('--db', default='shop_trade')
    ap.add_argument('--app-port', type=int, default=18099)
    ap.add_argument('--rounds', type=int, default=5)
    ap.add_argument('--lock-wait-seconds', type=float, default=4.0,
                    help='行锁阻塞探针中持锁观察时长')
    args = ap.parse_args()

    head('真实 InnoDB 行锁下「退款申请 vs 登记发货」互斥裁决复现')
    log('时间：%s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    log('仓库：%s' % ROOT)
    log('MySQL：%s:%d/%s（用户 %s）' % (args.host, args.port, args.db, args.user))
    log('轮次：%d' % args.rounds)

    conn = pymysql.connect(host=args.host, port=args.port, user=args.user,
                           password=args.password, database=args.db,
                           charset='utf8mb4', autocommit=True, connect_timeout=10)
    cur = conn.cursor()

    head('0. 环境与表引擎核验')
    rows = sql(cur, "SELECT table_name, engine, table_collation FROM information_schema.tables "
                     "WHERE table_schema=%s AND table_name IN ('goods','order','payment') "
                     "ORDER BY table_name", (args.db,))
    for r in rows:
        log('  %s' % (r,))
    check('三张业务表均为 InnoDB', all(r[1] == 'InnoDB' for r in rows) and len(rows) == 3,
          '共 %d 张表' % len(rows))
    iso = sql(cur, 'SELECT @@transaction_isolation, @@innodb_lock_wait_timeout')
    log('  隔离级别与锁等待超时：%s' % (iso,))

    goods_rows = sql(cur, "SELECT id, goods_no, available_stock, occupied_stock, status "
                           "FROM goods ORDER BY available_stock DESC, id")
    for r in goods_rows:
        log('  商品基线：%s' % (r,))
    # 选取当前可售最多的在售商品作为并发测试载体
    candidates = [r for r in goods_rows if r[2] > 0 and (len(r) < 5 or r[4] == '在售')]
    if not candidates:
        candidates = goods_rows
    goods_id = candidates[0][0]
    original_available = candidates[0][2]
    original_occupied = candidates[0][3]
    required = args.rounds + 1
    if original_available < required:
        topup = required - original_available
        sql(cur, "UPDATE goods SET available_stock=available_stock+%s WHERE id=%s", (topup, goods_id))
        log('  [测试夹具] 该商品可售不足 %d 件，临时补 %d 件以完成 %d 轮并发，'
            '阶段 C 将按原值完整还原' % (required, topup, args.rounds))
    baseline_available = sql(cur, "SELECT available_stock FROM goods WHERE id=%s", (goods_id,))[0][0]
    baseline_occupied = sql(cur, "SELECT occupied_stock FROM goods WHERE id=%s", (goods_id,))[0][0]
    check('测试载体与库存基线已就绪', baseline_available >= required,
          'goods_id=%d available=%d occupied=%d 需用量=%d'
          % (goods_id, baseline_available, baseline_occupied, required))

    created_orders = []
    exe = build_binary(pathlib.Path(os.environ.get('TEMP', '/tmp')) / 'shop-trade-inno-race.exe')
    app_log = ROOT / 'evidence/db/inno_ship_refund_race.app.log'
    dsn = ('%s:%s@tcp(%s:%d)/%s?charset=utf8mb4&parseTime=True&loc=Local'
           % (args.user, args.password, args.host, args.port, args.db))
    proc, base = start_app(exe, dsn, args.app_port, app_log)
    log('应用已以 mysql-innodb 模式启动：%s（pid=%s）' % (base, proc.pid))

    def make_paid_order(tag):
        st, obj = http('POST', '/api/v1/orders', {'goods_id': goods_id, 'quantity': 1}, base=base)
        no = data_of(obj).get('order_no')
        if not no:
            return None, obj
        created_orders.append(no)
        st, obj = http('POST', '/api/v1/payment/callback',
                       {'order_no': no, 'channel_trade_no': 'INNO-RACE-%s-%s' % (tag, no[-8:]),
                        'amount': 10000, 'signature_valid': True}, account='mock01', base=base)
        return no, obj

    try:
        head('1. 阶段 A：并发裁决复现（退款申请 vs 登记发货）')
        for i in range(args.rounds):
            no, pobj = make_paid_order('A%d' % i)
            if not no:
                check('第%d轮下单成功' % (i + 1), False, json.dumps(pobj, ensure_ascii=False)[:160])
                continue
            st, obj = http('GET', '/api/v1/orders/%s' % no, base=base)
            before_status = data_of(obj).get('status')
            check('第%d轮并发前置：订单已支付待发货' % (i + 1), before_status == '待发货',
                  'order_no=%s status=%s' % (no, before_status))

            box = {}

            def do_refund(n=no, b=box):
                b['refund'] = http('POST', '/api/v1/orders/%s/refund/apply' % n,
                                   {'reason': 'InnoDB 行锁并发复现：申请整单退款'},
                                   account='buyer01', base=base)[1]

            def do_ship(n=no, b=box):
                b['ship'] = http('POST', '/api/v1/orders/%s/shipment' % n,
                                 {'carrier': '检查者承运', 'tracking_no': 'INNO-SF-%d' % i},
                                 account='warehouse01', base=base)[1]

            t1 = threading.Thread(target=do_refund)
            t2 = threading.Thread(target=do_ship)
            t1.start()
            t2.start()
            t1.join()
            t2.join()
            rc = code_of(box.get('refund'))
            sc = code_of(box.get('ship'))

            row = sql(cur, "SELECT status, quantity, total_amount, stock_restored "
                           "FROM `order` WHERE order_no=%s", (no,))[0]
            g = sql(cur, "SELECT available_stock, occupied_stock FROM goods WHERE id=%s",
                    (goods_id,))[0]
            ev = sql(cur, "SELECT event_type, result, failure_code FROM payment "
                          "WHERE order_no=%s ORDER BY id", (no,))
            legal = ((rc == '0' and sc == 'M-22') or
                     (sc == '0' and rc in ('M-05', 'M-10', 'M-11')))
            log('  第%d轮 refund=%s ship=%s → 表内 status=%s' % (i + 1, rc, sc, row[0]))
            log('    订单行：%s' % (row,))
            log('    商品行：%s' % (g,))
            log('    审计事件：%s' % (ev,))
            check('第%d轮并发只形成一种合法结果' % (i + 1), legal,
                  'refund=%s ship=%s' % (rc, sc))
            if sc == '0':
                check('第%d轮发货胜出则订单行为已发货' % (i + 1), row[0] == '已发货', row[0])
            if rc == '0':
                check('第%d轮退款胜出则订单行为退款审核中' % (i + 1), row[0] == '退款审核中', row[0])
            check('第%d轮订单终态唯一（已发货/退款审核中）' % (i + 1),
                  row[0] in ('已发货', '退款审核中'), row[0])
            check('第%d轮库存守恒 available+occupied 恒定' % (i + 1),
                  g[0] + g[1] == baseline_available + baseline_occupied,
                  'available=%d occupied=%d 合计=%d 基线=%d'
                  % (g[0], g[1], g[0] + g[1], baseline_available + baseline_occupied))
            terminal = [e for e in ev if e[0] in ('发货登记', '售前退款申请')]
            check('第%d轮审计流水无重复终态事件' % (i + 1), len(terminal) <= 1,
                  '终态类事件 %d 条：%s' % (len(terminal), terminal))

        head('2. 阶段 B：行锁阻塞探针（外部事务持锁 → 应用请求被阻塞）')
        no, pobj = make_paid_order('B')
        if not no:
            check('阻塞探针前置下单成功', False, json.dumps(pobj, ensure_ascii=False)[:160])
        else:
            st, obj = http('GET', '/api/v1/orders/%s' % no, base=base)
            log('  探针订单：%s status=%s' % (no, data_of(obj).get('status')))

            lock_conn = pymysql.connect(host=args.host, port=args.port, user=args.user,
                                        password=args.password, database=args.db,
                                        charset='utf8mb4', autocommit=False, connect_timeout=10)
            lc = lock_conn.cursor()
            lc.execute("SELECT id, status FROM `order` WHERE order_no=%s FOR UPDATE", (no,))
            held = lc.fetchone()
            log('  外部事务 T0 已对订单行加 X 锁（未提交）：id=%s status=%s'
                % (held[0] if held else '?', held[1] if held else '?'))

            result = {}
            done = threading.Event()

            def probe():
                result['obj'] = http('POST', '/api/v1/orders/%s/refund/apply' % no,
                                     {'reason': '行锁阻塞探针'}, account='buyer01',
                                     base=base, timeout=60)[1]
                done.set()

            th = threading.Thread(target=probe)
            t0 = time.time()
            th.start()
            blocked = not done.wait(args.lock_wait_seconds)
            elapsed = time.time() - t0
            check('T0 持锁期间应用退款请求被阻塞（未提前返回）', blocked,
                  '观察 %.1fs 后请求仍未返回' % args.lock_wait_seconds)
            try:
                trx = sql(cur, "SELECT trx_state, trx_started, trx_query FROM information_schema.innodb_trx")
                log('  阻塞期 InnoDB 活动事务：%s' % (trx,))
                wait_rows = [t for t in trx if str(t[0]).upper() == 'LOCK WAIT']
                if wait_rows:
                    check('数据库侧可见应用事务处于 LOCK WAIT 状态', True,
                          'trx_state=LOCK WAIT count=%d' % len(wait_rows))
                else:
                    log('  说明：当前账号缺少查看其它连接事务的权限，未能直接读到 LOCK WAIT 状态；'
                        '以请求阻塞时长与释放锁后的立即成功作为等价证据')
            except Exception as e:
                log('  说明：读取 information_schema.innodb_trx 失败（%s）；'
                    '以请求阻塞时长与释放锁后的立即成功作为等价证据' % str(e)[:120])

            lock_conn.rollback()
            lock_conn.close()
            log('  T0 已回滚，订单行锁释放')
            finished = done.wait(30)
            check('释放行锁后应用退款请求立即返回', finished,
                  '请求在释放锁后返回，阻塞观察时长约 %.1fs' % elapsed)
            if finished:
                obj = result.get('obj')
                check('释放锁后退款申请成功（证明此前阻塞源为 InnoDB 行锁）',
                      code_of(obj) == '0', json.dumps(obj, ensure_ascii=False)[:160])
                row = sql(cur, "SELECT status FROM `order` WHERE order_no=%s", (no,))[0]
                check('探针订单最终状态为退款审核中', row[0] == '退款审核中', row[0])

        head('3. 阶段 C：表级一致性汇总与测试数据清理')
        for no in created_orders:
            sql(cur, "DELETE FROM payment WHERE order_no=%s", (no,))
            sql(cur, "DELETE FROM `order` WHERE order_no=%s", (no,))
        sql(cur, "UPDATE goods SET available_stock=%s, occupied_stock=%s WHERE id=%s",
            (original_available, original_occupied, goods_id))
        g = sql(cur, "SELECT available_stock, occupied_stock FROM goods WHERE id=%s", (goods_id,))[0]
        check('测试数据已清理，商品库存已按原值复原',
              (g[0], g[1]) == (original_available, original_occupied),
              'available=%d occupied=%d 原值=(%d,%d)' % (g[0], g[1], original_available, original_occupied))
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
        log('应用实例已停止')

    head('4. 断言汇总')
    passed = sum(1 for r in RESULTS if r['verdict'] == 'PASS')
    failed = len(RESULTS) - passed
    log('共 %d 条断言：PASS %d 条，FAIL %d 条' % (len(RESULTS), passed, failed))
    for r in RESULTS:
        if r['verdict'] != 'PASS':
            log('  FAIL: %s | %s' % (r['case'], r['detail']))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text('\n'.join(LOG) + '\n', encoding='utf-8')
    (OUT.with_suffix('.json')).write_text(
        json.dumps(RESULTS, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    log('原始输出：%s' % OUT)
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
