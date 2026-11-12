#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真实 MySQL(InnoDB) 模式下的应用级持久化与并发验证脚本。

补齐 evidence/mysql核查记录.md 的两项操作：
  操作4：真实终止应用进程后重启，同一订单仍可查询（持久化证明）
  操作5：20 并发下单在真实 InnoDB 行锁下不超卖、库存守恒

前提（均为真实环境准备，不产生任何伪造记录）：
  1. WSL Ubuntu 内已启动 MySQL 8.4（InnoDB / utf8mb4）；
  2. 已用 evidence/schema.sql 建库建表；
  3. 应用账号口令只保存在 WSL 的 /tmp/shop_dsn_pw，不写入仓库；
  4. Windows 侧可通过 127.0.0.1:3306 访问 WSL 内的 mysqld。

用法：python -X utf8 evidence/mysql_app_persistence.py
输出：evidence/mysql_raw_05_app_persistence.txt（UTF-8）
"""
import json
import os
import pathlib
import subprocess
import threading
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOG = ROOT / 'evidence/mysql_raw_05_app_persistence.txt'
PORT = 18098
BASE = 'http://127.0.0.1:%d' % PORT
EXE = pathlib.Path(os.environ.get('TEMP', '/tmp')) / 'shop-trade-mysql-verify.exe'
WSL = ['wsl', '-d', 'Ubuntu', '-u', 'root', '--']
LINES = []
RESULTS = []


def log(text=''):
    LINES.append(text)
    print(text)


def sql(statement):
    # 通过 stdin 传 SQL，避免反引号等字符在 wsl 参数传递时被 shell 解释
    proc = subprocess.run(WSL + ['mysql', '-uroot', 'shop_trade'], input=statement,
                          capture_output=True, text=True, encoding='utf-8', errors='replace')
    return (proc.stdout or '') + (proc.stderr or '')


def http(method, path, body=None, account='buyer01', timeout=20):
    headers = {}
    data = None
    if account:
        headers['X-Demo-Account'] = account
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as exc:
        return {'code': 'HTTP%d' % exc.code,
                'message': exc.read().decode('utf-8', 'replace'), 'data': None}
    except Exception as exc:
        return {'code': 'REQUEST_FAILED', 'message': repr(exc), 'data': None}


def check(name, ok, detail):
    status = 'PASS' if ok else 'FAIL'
    RESULTS.append((name, status, detail))
    log('[断言] %s | %s | %s' % (status, name, detail))
    return ok


def start_app(dsn, tag):
    env = dict(os.environ)
    env['GVA_ADDR'] = ':%d' % PORT
    env['GVA_MYSQL_DSN'] = dsn
    # 应用输出写入文件而非 PIPE，避免管道缓冲区写满后阻塞服务处理请求
    handle = open(ROOT / 'evidence/app_mysql_runtime.log', 'a', encoding='utf-8')
    proc = subprocess.Popen([str(EXE)], env=env, stdout=handle, stderr=handle)
    log('[启动] %s pid=%s DSN=shoptrade:***@tcp(127.0.0.1:3306)/shop_trade?charset=utf8mb4'
        % (tag, proc.pid))
    for _ in range(60):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(BASE + '/health', timeout=3) as resp:
                if resp.status == 200:
                    log('[启动] %s 就绪，GET /health -> HTTP %d' % (tag, resp.status))
                    return proc
        except Exception:
            continue
    log('[启动] %s 启动超时' % tag)
    proc.kill()
    raise SystemExit('应用启动失败')


def stop_app(proc, tag):
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)
    log('[停止] %s 已退出（用于模拟服务重启）' % tag)


def goods_row():
    out = sql("SELECT available_stock,occupied_stock FROM goods WHERE goods_no='GOODS-ACT-001';")
    lines = [x for x in out.strip().split('\n') if x.strip()]
    parts = lines[-1].split('\t')
    return int(parts[0]), int(parts[1])


def main():
    log('===== 真实 MySQL(InnoDB) 模式：应用级持久化与并发验证 =====')
    log('工作目录：%s' % ROOT)
    log('时间：%s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    log('')
    log('--- 0. 准备：读取 WSL 内应用账号口令（仅存在于 WSL /tmp，不写入仓库）---')
    pw = subprocess.run(WSL + ['cat', '/tmp/shop_dsn_pw'], capture_output=True, text=True)
    password = pw.stdout.strip()
    if not password:
        log('[准备] 未找到 /tmp/shop_dsn_pw，先执行 mysql_prepare_user.sh 重建应用账号')
        prep = subprocess.run(WSL + ['bash', '/mnt/d/Desktop/shop/evidence/mysql_prepare_user.sh'],
                              capture_output=True, text=True, encoding='utf-8', errors='replace')
        log((prep.stdout or '') + (prep.stderr or ''))
        pw = subprocess.run(WSL + ['cat', '/tmp/shop_dsn_pw'], capture_output=True, text=True)
        password = pw.stdout.strip()
    if not password:
        log('[准备] 仍无法读取应用账号口令，脚本退出')
        return 2
    log('[准备] 已读取应用账号口令（值不回显、不落盘）')
    dsn = ('shoptrade:%s@tcp(127.0.0.1:3306)/shop_trade?charset=utf8mb4&parseTime=True&loc=Local'
           % password)
    log('')
    log('--- 0.5 重置验证基线（验证环境专用，业务数据可清空后重建）---')
    log(sql("DELETE FROM payment;"))
    log(sql("DELETE FROM `order`;"))
    log(sql("UPDATE goods SET available_stock=5, occupied_stock=0 WHERE goods_no='GOODS-ACT-001';"))
    log(sql("SELECT goods_no,available_stock,occupied_stock FROM goods WHERE goods_no='GOODS-ACT-001';"))
    log('')
    log('--- 1. 构建应用二进制 ---')
    build = subprocess.run(['go', 'build', '-o', str(EXE), '.'], cwd=ROOT,
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
    log('$ go build -o %s .' % EXE)
    log((build.stdout or '') + (build.stderr or ''))
    log('build_exit=%d' % build.returncode)
    if build.returncode != 0:
        return 2
    log('')
    log('--- 2. 启动进程1（MySQL 模式）---')
    proc = start_app(dsn, '进程1')
    me = http('GET', '/api/v1/me')
    log('GET /api/v1/me -> %s' % json.dumps(me, ensure_ascii=False))
    check('应用以 mysql-innodb 模式启动', (me.get('data') or {}).get('mode') == 'mysql-innodb',
          'mode=%s' % (me.get('data') or {}).get('mode'))
    goods_resp = http('GET', '/api/v1/goods')
    items = goods_resp.get('data', {}).get('items', [])
    for item in items:
        log('    商品 %s' % json.dumps(item, ensure_ascii=False))
    target = next((i for i in items if i.get('goods_no') == 'GOODS-ACT-001'), None)
    if target is None:
        check('存在演示商品 GOODS-ACT-001', False, '商品列表未找到')
        return 2
    goods_id = target.get('id')
    log('')
    log('--- 3. 真实业务：下单 -> 支付 -> 查单（全部落库）---')
    created = http('POST', '/api/v1/orders', {'goods_id': goods_id, 'quantity': 2})
    log('POST /api/v1/orders -> %s' % json.dumps(created, ensure_ascii=False))
    check('下单成功', created.get('code') == '0',
          'code=%s message=%s' % (created.get('code'), created.get('message')))
    order_no = created.get('data', {}).get('order_no')
    total = created.get('data', {}).get('total_amount')
    log('[订单] order_no=%s total_amount=%s' % (order_no, total))
    log('SQL 订单落库：')
    log(sql(("SELECT order_no,status,quantity,unit_price,total_amount FROM `order` "
             "WHERE order_no='%s';") % order_no))
    log('SQL 库存扣减：')
    log(sql("SELECT goods_no,available_stock,occupied_stock FROM goods "
            "WHERE goods_no='GOODS-ACT-001';"))
    paid = http('POST', '/api/v1/payment/callback',
                {'order_no': order_no, 'channel_trade_no': 'TRADE-MYSQL-VERIFY-0001',
                 'amount': total, 'signature_valid': True}, account='mock01')
    log('POST /api/v1/payment/callback -> %s' % json.dumps(paid, ensure_ascii=False))
    queried = http('GET', '/api/v1/orders/%s' % order_no)
    log('GET /api/v1/orders/%s -> %s' % (order_no, json.dumps(queried, ensure_ascii=False)))
    check('支付后订单状态为待发货', queried.get('data', {}).get('status') == '待发货',
          'status=%s' % queried.get('data', {}).get('status'))
    log('SQL 支付事件落库：')
    log(sql("SELECT id,order_no,channel_trade_no,dedup_key,effective,event_type,result,amount "
            "FROM payment WHERE order_no='%s' ORDER BY id;" % order_no))
    log('')
    log('--- 4. 操作4：终止应用进程后重启，同一订单仍可查询 ---')
    stop_app(proc, '进程1')
    log('SQL（进程已停止，MySQL 中数据仍在）：')
    log(sql("SELECT order_no,status,paid_at FROM `order` WHERE order_no='%s';" % order_no))
    proc2 = start_app(dsn, '进程2')
    again = http('GET', '/api/v1/orders/%s' % order_no)
    log('[重启后] GET /api/v1/orders/%s -> %s' % (order_no, json.dumps(again, ensure_ascii=False)))
    check('应用重启后同一订单仍可查询且状态一致',
          again.get('code') == '0' and again.get('data', {}).get('status') == '待发货',
          'code=%s status=%s' % (again.get('code'), again.get('data', {}).get('status')))
    log('SQL（重启后再次读取）：')
    log(sql("SELECT order_no,status,paid_at,total_amount FROM `order` WHERE order_no='%s';" % order_no))
    log(sql("SELECT goods_no,available_stock,occupied_stock FROM goods "
            "WHERE goods_no='GOODS-ACT-001';"))
    log('')
    log('--- 5. 操作5：20 并发下单，真实 InnoDB 行锁下不超卖 ---')
    avail_before, occupied_before = goods_row()
    log('[并发前] available_stock=%d occupied_stock=%d' % (avail_before, occupied_before))
    results = []
    lock = threading.Lock()

    def place(idx):
        resp = http('POST', '/api/v1/orders', {'goods_id': goods_id, 'quantity': 1},
                    account='buyer0%d' % ((idx % 3) + 1))
        payload = resp.get('data') or {}
        with lock:
            results.append((resp.get('code'), resp.get('message'), payload.get('order_no')))

    threads = [threading.Thread(target=place, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    ok_count = sum(1 for code, _, _ in results if code == '0')
    fails = {}
    for code, message, _ in results:
        if code != '0':
            key = '%s:%s' % (code, message)
            fails[key] = fails.get(key, 0) + 1
    log('[并发结果] 发起 20 次下单，收到响应 %d 次，成功 %d 次，失败 %d 次'
        % (len(results), ok_count, len(results) - ok_count))
    for key, cnt in sorted(fails.items()):
        log('    失败 %d 次 -> %s' % (cnt, key))
    avail_after, occupied_after = goods_row()
    log('[并发后] available_stock=%d occupied_stock=%d' % (avail_after, occupied_after))
    check('并发成功数不超过可售库存（无超卖）', ok_count <= avail_before,
          '可售=%d 成功=%d' % (avail_before, ok_count))
    check('库存守恒：available + occupied == 初始总量 5', avail_after + occupied_after == 5,
          'available=%d occupied=%d 合计=%d' % (avail_after, occupied_after, avail_after + occupied_after))
    check('占用增量等于成功下单数（占用 2 + 成功数）', occupied_after == 2 + ok_count,
          '占用=%d 期望=%d' % (occupied_after, 2 + ok_count))
    log('')
    log('--- 6. 幂等复核：同一渠道交易号重复通知不重复记款 ---')
    again_pay = http('POST', '/api/v1/payment/callback',
                     {'order_no': order_no, 'channel_trade_no': 'TRADE-MYSQL-VERIFY-0001',
                      'amount': total, 'signature_valid': True}, account='mock01')
    log('重复支付通知 -> %s' % json.dumps(again_pay, ensure_ascii=False))
    rows = sql("SELECT COUNT(*) FROM payment WHERE order_no='%s' AND effective=1 AND event_type='支付成功';"
               % order_no)
    effective_rows = rows.strip().split('\n')[-1].strip()
    log('SQL 有效收款笔数：%s' % effective_rows)
    check('重复支付通知后有效收款仍为 1 笔', effective_rows == '1', 'effective_rows=%s' % effective_rows)
    log('')
    stop_app(proc2, '进程2')
    log('===== 断言汇总 =====')
    passed = sum(1 for _, status, _ in RESULTS if status == 'PASS')
    log('断言通过 %d / %d' % (passed, len(RESULTS)))
    for name, status, detail in RESULTS:
        log('  %s | %s | %s' % (status, name, detail))
    LOG.write_text('\n'.join(LINES) + '\n', encoding='utf-8')
    print('written: %s' % LOG)
    return 0 if passed == len(RESULTS) else 1


if __name__ == '__main__':
    raise SystemExit(main())
